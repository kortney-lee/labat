"""
labat/services/automation_service.py — LABAT Automation Engine

Executes real ad management actions automatically:
  - Auto-pause underperforming ads/adsets
  - Auto-scale winning ads/adsets (budget +20% max per day)
  - A/B creative rotation with winner selection
  - Scheduled health checks, anomaly detection, and reporting

Called by Cloud Scheduler via /api/labat/automation/cron.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.labat.config import META_AD_ACCOUNT_ID, META_SYSTEM_USER_TOKEN
from src.labat.meta_client import graph_get, MetaAPIError
from src.labat.services import ads_service
from src.labat.services.insights_service import get_insights, get_insights_by_brand
from src.labat.services.master_agent_service import get_master_agent
from src.labat.services.notify import send_notification

logger = logging.getLogger("labat.automation")

# ── Thresholds (configurable via env) ──────────────────────────────────────

import os

# Auto-pause: pause ad/adset if spend > threshold with zero conversions
PAUSE_SPEND_THRESHOLD = float(os.getenv("AUTOMATION_PAUSE_SPEND_THRESHOLD", "10.0"))
# Auto-pause: minimum impressions before evaluating (avoid killing new ads)
PAUSE_MIN_IMPRESSIONS = int(os.getenv("AUTOMATION_PAUSE_MIN_IMPRESSIONS", "1000"))
# Auto-pause: CTR floor — pause if below this after enough impressions
PAUSE_CTR_FLOOR = float(os.getenv("AUTOMATION_PAUSE_CTR_FLOOR", "0.5"))

# Auto-scale: ROAS threshold to qualify for scaling
SCALE_ROAS_THRESHOLD = float(os.getenv("AUTOMATION_SCALE_ROAS_THRESHOLD", "1.5"))
# Auto-scale: minimum conversions before scaling
SCALE_MIN_CONVERSIONS = int(os.getenv("AUTOMATION_SCALE_MIN_CONVERSIONS", "2"))
# Auto-scale: max budget increase per cycle (20% to avoid learning phase reset)
SCALE_MAX_INCREASE_PCT = float(os.getenv("AUTOMATION_SCALE_MAX_INCREASE_PCT", "20.0"))
# Auto-scale: budget ceiling in cents (avoid runaway spend)
SCALE_BUDGET_CEILING = int(os.getenv("AUTOMATION_SCALE_BUDGET_CEILING", "50000"))  # $500/day

# A/B test: minimum impressions per ad before declaring a winner
AB_MIN_IMPRESSIONS = int(os.getenv("AUTOMATION_AB_MIN_IMPRESSIONS", "500"))
# A/B test: winner must beat loser CTR by this factor
AB_WIN_MARGIN = float(os.getenv("AUTOMATION_AB_WIN_MARGIN", "1.2"))  # 20% better


def _token() -> str:
    if not META_SYSTEM_USER_TOKEN:
        raise MetaAPIError("META_SYSTEM_USER_TOKEN not configured", status_code=500)
    return META_SYSTEM_USER_TOKEN


def _acct() -> str:
    if not META_AD_ACCOUNT_ID:
        raise MetaAPIError("META_AD_ACCOUNT_ID not configured", status_code=500)
    return META_AD_ACCOUNT_ID


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _extract_conversions(actions: list) -> int:
    """Extract purchase/lead conversions from Meta actions array."""
    if not actions:
        return 0
    total = 0
    for a in actions:
        if a.get("action_type") in ("purchase", "offsite_conversion.fb_pixel_purchase",
                                     "lead", "offsite_conversion.fb_pixel_lead",
                                     "complete_registration"):
            total += _safe_int(a.get("value", 0))
    return total


def _extract_roas(roas_list) -> float:
    """Extract ROAS value from Meta purchase_roas array."""
    if not roas_list:
        return 0.0
    if isinstance(roas_list, list) and roas_list:
        return _safe_float(roas_list[0].get("value", 0))
    return _safe_float(roas_list)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Auto-Pause Underperformers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def auto_pause_underperformers(
    date_preset: str = "last_7d",
    dry_run: bool = False,
    brand: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Scan active adsets. Pause any that meet underperformance criteria:
    1. Spend > $PAUSE_SPEND_THRESHOLD with zero conversions
    2. CTR < PAUSE_CTR_FLOOR% after PAUSE_MIN_IMPRESSIONS impressions

    When brand is set, only evaluates adsets belonging to that brand
    (filtered by campaign name prefix).
    """
    paused = []
    evaluated = 0
    errors = []

    try:
        _fields = [
            "adset_id", "adset_name", "campaign_name",
            "impressions", "clicks", "spend", "ctr",
            "actions", "cost_per_action_type",
        ]
        if brand and brand != "all":
            insights = await get_insights_by_brand(
                brand=brand, level="adset", date_preset=date_preset, fields=_fields,
            )
        else:
            insights = await get_insights(
                level="adset", date_preset=date_preset, fields=_fields,
            )
        data = insights.get("data", [])
    except MetaAPIError as e:
        logger.error("Failed to fetch insights for auto-pause: %s", e)
        return {"error": str(e), "paused": [], "evaluated": 0}

    for row in data:
        adset_id = row.get("adset_id")
        if not adset_id:
            continue

        evaluated += 1
        spend = _safe_float(row.get("spend"))
        impressions = _safe_int(row.get("impressions"))
        ctr = _safe_float(row.get("ctr"))
        conversions = _extract_conversions(row.get("actions", []))
        adset_name = row.get("adset_name", "unknown")
        campaign_name = row.get("campaign_name", "unknown")

        reason = None

        # Rule 1: High spend, zero conversions
        if spend >= PAUSE_SPEND_THRESHOLD and conversions == 0 and impressions >= PAUSE_MIN_IMPRESSIONS:
            reason = f"Spent ${spend:.2f} with 0 conversions after {impressions} impressions"

        # Rule 2: CTR too low after enough data
        elif impressions >= PAUSE_MIN_IMPRESSIONS and ctr < PAUSE_CTR_FLOOR:
            reason = f"CTR {ctr:.2f}% below floor {PAUSE_CTR_FLOOR}% after {impressions} impressions"

        if reason:
            entry = {
                "adset_id": adset_id,
                "adset_name": adset_name,
                "campaign_name": campaign_name,
                "spend": spend,
                "impressions": impressions,
                "ctr": ctr,
                "conversions": conversions,
                "reason": reason,
                "action": "paused" if not dry_run else "would_pause",
            }

            if not dry_run:
                try:
                    await ads_service.update_adset(adset_id, status="PAUSED")
                    logger.info("AUTO-PAUSE: %s (%s) — %s", adset_name, adset_id, reason)
                except MetaAPIError as e:
                    entry["action"] = "pause_failed"
                    entry["error"] = str(e)
                    errors.append(str(e))
                    logger.error("Failed to pause adset %s: %s", adset_id, e)

            paused.append(entry)

    result = {
        "evaluated": evaluated,
        "paused": paused,
        "paused_count": len([p for p in paused if p["action"] == "paused"]),
        "dry_run": dry_run,
        "thresholds": {
            "spend_threshold": PAUSE_SPEND_THRESHOLD,
            "min_impressions": PAUSE_MIN_IMPRESSIONS,
            "ctr_floor": PAUSE_CTR_FLOOR,
        },
    }
    if errors:
        result["errors"] = errors

    # Notify if any paused
    if paused and not dry_run:
        import asyncio
        asyncio.ensure_future(send_notification(
            agent="labat-automation",
            severity="warning",
            title=f"Auto-paused {len(paused)} underperforming ad set(s)",
            message="\n".join(f"• {p['adset_name']}: {p['reason']}" for p in paused),
            service="labat",
            details={"paused_adsets": paused},
        ))

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Auto-Scale Winners
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def auto_scale_winners(
    date_preset: str = "last_7d",
    dry_run: bool = False,
    brand: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find winning adsets and increase their budgets by up to SCALE_MAX_INCREASE_PCT%.
    Winners: ROAS > threshold AND conversions >= minimum.
    Budget never exceeds SCALE_BUDGET_CEILING.

    When brand is set, only evaluates adsets belonging to that brand.
    """
    scaled = []
    evaluated = 0
    errors = []

    try:
        _fields = [
            "adset_id", "adset_name", "campaign_name",
            "impressions", "clicks", "spend", "ctr",
            "actions", "purchase_roas", "website_purchase_roas",
            "cost_per_action_type",
        ]
        if brand and brand != "all":
            insights = await get_insights_by_brand(
                brand=brand, level="adset", date_preset=date_preset, fields=_fields,
            )
        else:
            insights = await get_insights(
                level="adset", date_preset=date_preset, fields=_fields,
            )
        data = insights.get("data", [])
    except MetaAPIError as e:
        logger.error("Failed to fetch insights for auto-scale: %s", e)
        return {"error": str(e), "scaled": [], "evaluated": 0}

    for row in data:
        adset_id = row.get("adset_id")
        if not adset_id:
            continue

        evaluated += 1
        roas = _extract_roas(row.get("purchase_roas") or row.get("website_purchase_roas"))
        conversions = _extract_conversions(row.get("actions", []))

        if roas < SCALE_ROAS_THRESHOLD or conversions < SCALE_MIN_CONVERSIONS:
            continue

        # Fetch current budget
        try:
            adset_info = await ads_service.get_adset(adset_id)
        except MetaAPIError:
            continue

        current_budget = _safe_int(adset_info.get("daily_budget", 0))
        if current_budget <= 0:
            continue

        # Calculate new budget (max +20%, capped at ceiling)
        increase = int(current_budget * (SCALE_MAX_INCREASE_PCT / 100.0))
        new_budget = min(current_budget + increase, SCALE_BUDGET_CEILING)

        if new_budget <= current_budget:
            continue  # already at ceiling

        entry = {
            "adset_id": adset_id,
            "adset_name": row.get("adset_name", "unknown"),
            "campaign_name": row.get("campaign_name", "unknown"),
            "roas": roas,
            "conversions": conversions,
            "current_budget_cents": current_budget,
            "new_budget_cents": new_budget,
            "increase_pct": round((new_budget - current_budget) / current_budget * 100, 1),
            "action": "scaled" if not dry_run else "would_scale",
        }

        if not dry_run:
            try:
                await ads_service.update_adset(adset_id, daily_budget=new_budget)
                logger.info(
                    "AUTO-SCALE: %s (%s) budget %d→%d cents (ROAS %.2f, %d conversions)",
                    entry["adset_name"], adset_id, current_budget, new_budget, roas, conversions
                )
            except MetaAPIError as e:
                entry["action"] = "scale_failed"
                entry["error"] = str(e)
                errors.append(str(e))
                logger.error("Failed to scale adset %s: %s", adset_id, e)

        scaled.append(entry)

    result = {
        "evaluated": evaluated,
        "scaled": scaled,
        "scaled_count": len([s for s in scaled if s["action"] == "scaled"]),
        "dry_run": dry_run,
        "thresholds": {
            "roas_threshold": SCALE_ROAS_THRESHOLD,
            "min_conversions": SCALE_MIN_CONVERSIONS,
            "max_increase_pct": SCALE_MAX_INCREASE_PCT,
            "budget_ceiling_cents": SCALE_BUDGET_CEILING,
        },
    }
    if errors:
        result["errors"] = errors

    if scaled and not dry_run:
        import asyncio
        asyncio.ensure_future(send_notification(
            agent="labat-automation",
            severity="info",
            title=f"Auto-scaled {len(scaled)} winning ad set(s)",
            message="\n".join(
                f"• {s['adset_name']}: ${s['current_budget_cents']/100:.2f}→${s['new_budget_cents']/100:.2f} (ROAS {s['roas']:.2f})"
                for s in scaled
            ),
            service="labat",
            details={"scaled_adsets": scaled},
        ))

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# A/B Creative Rotation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def ab_creative_rotation(
    date_preset: str = "last_7d",
    dry_run: bool = False,
    brand: Optional[str] = None,
) -> Dict[str, Any]:
    """
    For each adset with multiple active ads, compare performance.
    Pause losers (lower CTR/conversions), keep winners running.

    When brand is set, only evaluates ads belonging to that brand.

    Logic:
    1. Group ads by adset_id
    2. For each adset with 2+ active ads, compare metrics
    3. If winner beats loser by AB_WIN_MARGIN, pause the loser
    """
    rotations = []
    evaluated_adsets = 0
    errors = []

    try:
        _fields = [
            "ad_id", "ad_name", "adset_id", "adset_name",
            "campaign_name",
            "impressions", "clicks", "spend", "ctr",
            "actions", "purchase_roas",
            "cost_per_action_type",
        ]
        if brand and brand != "all":
            insights = await get_insights_by_brand(
                brand=brand, level="ad", date_preset=date_preset, fields=_fields,
            )
        else:
            insights = await get_insights(
                level="ad", date_preset=date_preset, fields=_fields,
            )
        data = insights.get("data", [])
    except MetaAPIError as e:
        logger.error("Failed to fetch ad insights for A/B rotation: %s", e)
        return {"error": str(e), "rotations": [], "evaluated_adsets": 0}

    # Group by adset
    adset_ads: Dict[str, List[Dict[str, Any]]] = {}
    for row in data:
        adset_id = row.get("adset_id")
        if adset_id:
            adset_ads.setdefault(adset_id, []).append(row)

    for adset_id, ads in adset_ads.items():
        if len(ads) < 2:
            continue  # Need at least 2 ads to compare

        evaluated_adsets += 1

        # Check all have enough impressions
        if not all(_safe_int(a.get("impressions")) >= AB_MIN_IMPRESSIONS for a in ads):
            continue  # Not enough data yet

        # Score ads by: conversions first, then CTR, then cost efficiency
        def score_ad(ad: Dict) -> float:
            conversions = _extract_conversions(ad.get("actions", []))
            ctr = _safe_float(ad.get("ctr"))
            roas = _extract_roas(ad.get("purchase_roas"))
            # Weighted score: conversions dominate, CTR secondary, ROAS bonus
            return conversions * 100 + ctr * 10 + roas * 5

        scored = [(score_ad(a), a) for a in ads]
        scored.sort(key=lambda x: x[0], reverse=True)

        winner_score, winner = scored[0]
        winner_ctr = _safe_float(winner.get("ctr"))

        for loser_score, loser in scored[1:]:
            loser_ctr = _safe_float(loser.get("ctr"))

            # Check if winner meaningfully beats loser
            if winner_score <= 0 or loser_score <= 0:
                continue
            if winner_score / max(loser_score, 0.01) < AB_WIN_MARGIN:
                continue  # Not enough margin

            ad_id = loser.get("ad_id")
            entry = {
                "adset_id": adset_id,
                "adset_name": loser.get("adset_name", "unknown"),
                "winner": {
                    "ad_id": winner.get("ad_id"),
                    "ad_name": winner.get("ad_name"),
                    "ctr": winner_ctr,
                    "score": winner_score,
                },
                "loser": {
                    "ad_id": ad_id,
                    "ad_name": loser.get("ad_name"),
                    "ctr": loser_ctr,
                    "score": loser_score,
                },
                "margin": round(winner_score / max(loser_score, 0.01), 2),
                "action": "paused_loser" if not dry_run else "would_pause_loser",
            }

            if not dry_run and ad_id:
                try:
                    await ads_service.update_ad(ad_id, status="PAUSED")
                    logger.info(
                        "A/B ROTATION: Paused loser %s (%s) — winner %s (margin %.2fx)",
                        loser.get("ad_name"), ad_id, winner.get("ad_name"),
                        winner_score / max(loser_score, 0.01),
                    )
                except MetaAPIError as e:
                    entry["action"] = "pause_failed"
                    entry["error"] = str(e)
                    errors.append(str(e))

            rotations.append(entry)

    result = {
        "evaluated_adsets": evaluated_adsets,
        "rotations": rotations,
        "losers_paused": len([r for r in rotations if r["action"] == "paused_loser"]),
        "dry_run": dry_run,
        "thresholds": {
            "min_impressions": AB_MIN_IMPRESSIONS,
            "win_margin": AB_WIN_MARGIN,
        },
    }
    if errors:
        result["errors"] = errors

    if rotations and not dry_run:
        import asyncio
        asyncio.ensure_future(send_notification(
            agent="labat-automation",
            severity="info",
            title=f"A/B Rotation: {len(rotations)} loser ad(s) paused",
            message="\n".join(
                f"• {r['adset_name']}: Winner={r['winner']['ad_name']} (CTR {r['winner']['ctr']:.2f}%) beat {r['loser']['ad_name']} (CTR {r['loser']['ctr']:.2f}%)"
                for r in rotations
            ),
            service="labat",
            details={"rotations": rotations},
        ))

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Full Automation Cycle
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def run_full_cycle(
    dry_run: bool = False,
    brand: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run all automation tasks in sequence:
    1. Master agent health check + anomaly detection
    2. Auto-pause underperformers
    3. Auto-scale winners
    4. A/B creative rotation
    5. Generate and send report

    When brand is set, all steps operate only on that brand's campaigns.
    Called by Cloud Scheduler every hour.
    """
    started = datetime.utcnow()
    results = {
        "started_at": started.isoformat(),
        "dry_run": dry_run,
        "steps": {},
    }

    # Step 1: Health check + anomaly detection
    try:
        master = get_master_agent()
        health = await master.health_check_all_services()
        anomalies = await master.detect_anomalies()
        results["steps"]["health_check"] = {
            "status": "completed",
            "services": health,
            "anomalies": anomalies,
        }

        # Alert on critical anomalies
        for anomaly in anomalies:
            if anomaly.get("severity") == "critical" and not dry_run:
                await master.send_alert_to_auth(
                    severity="critical",
                    title=anomaly.get("type", "Critical Anomaly"),
                    message=anomaly.get("message", ""),
                    service=anomaly.get("service", "unknown"),
                    details=anomaly,
                )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        results["steps"]["health_check"] = {"status": "error", "error": str(e)}

    # Step 2: Auto-pause underperformers
    try:
        pause_result = await auto_pause_underperformers(dry_run=dry_run, brand=brand)
        results["steps"]["auto_pause"] = {
            "status": "completed",
            "paused_count": pause_result.get("paused_count", 0),
            "evaluated": pause_result.get("evaluated", 0),
            "details": pause_result,
        }
    except Exception as e:
        logger.error("Auto-pause failed: %s", e)
        results["steps"]["auto_pause"] = {"status": "error", "error": str(e)}

    # Step 3: Auto-scale winners
    try:
        scale_result = await auto_scale_winners(dry_run=dry_run, brand=brand)
        results["steps"]["auto_scale"] = {
            "status": "completed",
            "scaled_count": scale_result.get("scaled_count", 0),
            "evaluated": scale_result.get("evaluated", 0),
            "details": scale_result,
        }
    except Exception as e:
        logger.error("Auto-scale failed: %s", e)
        results["steps"]["auto_scale"] = {"status": "error", "error": str(e)}

    # Step 4: A/B creative rotation
    try:
        ab_result = await ab_creative_rotation(dry_run=dry_run, brand=brand)
        results["steps"]["ab_rotation"] = {
            "status": "completed",
            "losers_paused": ab_result.get("losers_paused", 0),
            "evaluated_adsets": ab_result.get("evaluated_adsets", 0),
            "details": ab_result,
        }
    except Exception as e:
        logger.error("A/B rotation failed: %s", e)
        results["steps"]["ab_rotation"] = {"status": "error", "error": str(e)}

    # Step 5: Generate and send report
    try:
        master = get_master_agent()
        report = await master.generate_report()
        # Enrich report with automation results
        report["automation"] = {
            "paused": results["steps"].get("auto_pause", {}).get("paused_count", 0),
            "scaled": results["steps"].get("auto_scale", {}).get("scaled_count", 0),
            "ab_rotations": results["steps"].get("ab_rotation", {}).get("losers_paused", 0),
        }
        if not dry_run:
            await master.send_report_to_auth(report)
        results["steps"]["report"] = {"status": "completed" if not dry_run else "skipped_dry_run"}
    except Exception as e:
        logger.error("Report generation failed: %s", e)
        results["steps"]["report"] = {"status": "error", "error": str(e)}

    elapsed = (datetime.utcnow() - started).total_seconds()
    results["completed_at"] = datetime.utcnow().isoformat()
    results["elapsed_seconds"] = round(elapsed, 2)

    logger.info(
        "AUTOMATION CYCLE %s: pause=%s scale=%s ab=%s in %.1fs",
        "DRY-RUN" if dry_run else "LIVE",
        results["steps"].get("auto_pause", {}).get("paused_count", "err"),
        results["steps"].get("auto_scale", {}).get("scaled_count", "err"),
        results["steps"].get("ab_rotation", {}).get("losers_paused", "err"),
        elapsed,
    )

    return results
