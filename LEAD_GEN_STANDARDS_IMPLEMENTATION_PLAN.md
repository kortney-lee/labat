# Lead Gen Standards Implementation Plan (Meta Ads)

Date: 2026-04-07
Status: Planned (not implemented)
Scope: Alex + LABAT lead-ad orchestration and automation pipeline

## Goal
Increase qualified lead volume and reduce false negative automation actions by aligning pipeline behavior with current lead-generation operating standards.

## Summary of Recommended Changes

### Critical (Implement First)

1. Budget floor update
- Recommendation: Change lead ad default budget from 500 cents ($5/day) to 2500 cents ($25/day).
- Why: $5/day is below practical learning and delivery thresholds for US lead-gen campaigns.
- Expected impact: Meaningful increase in delivery and faster learning stabilization.
- File touchpoint: src/alex/routers/alex_routes.py
- Code target: OrchestrateLeadAdRequest.daily_budget default in lead pipeline model.

2. Lead targeting broadening
- Recommendation: Remove Engaged Shoppers behavior from lead-ad targeting path (use awareness-style behavior stripping while preserving geo/age/interests).
- Why: Purchase-intent behaviors over-constrain top-of-funnel lead capture.
- Expected impact: Larger reachable audience and lower delivery friction.
- File touchpoints:
  - src/alex/routers/alex_routes.py
  - src/labat/services/strategy_rules.py
- Code targets:
  - Lead orchestration targeting stage logic in alex_routes.
  - Optional dedicated helper for lead-targeting mode in strategy_rules.

3. Lead sync automation
- Recommendation: Add lead_sync_service.sync_all_forms() into hourly automation cycle.
- Why: Leads currently rely on manual sync endpoint calls, causing data and follow-up lag.
- Expected impact: Automatic Firestore and email flow within cron cadence.
- File touchpoint: src/labat/services/automation_service.py
- Code target: run_full_cycle() sequence after optimization steps and before report finalization.

4. Conversion extraction completeness
- Recommendation: Extend _extract_conversions to include lead form action types, including leadgen and onsite_conversion.lead_grouped.
- Why: Current conversion parsing can undercount true lead outcomes.
- Expected impact: Prevents premature pause decisions on productive lead campaigns.
- File touchpoint: src/labat/services/automation_service.py
- Code target: _extract_conversions() action_type allow-list.

5. Advantage+ audience enablement
- Recommendation: Set targeting_automation.advantage_audience to 1 for lead adsets.
- Why: Meta optimization can safely expand delivery around seed constraints for prospecting.
- Expected impact: More stable reach and improved scale potential.
- File touchpoint: src/alex/routers/alex_routes.py
- Code target: lead adset creation payload in orchestrate-lead-ad flow.

### High (Standards Hardening)

6. Auto-pause threshold calibration
- Recommendation: Replace flat early pause behavior with CPL-aware thresholds tied to target lead cost and minimum evidence volume.
- Why: Static low spend threshold can terminate campaigns before statistically useful signal exists.
- Expected impact: Fewer false pauses and better campaign maturation.
- File touchpoint: src/labat/services/automation_service.py
- Suggested env knobs:
  - AUTOMATION_TARGET_CPL
  - AUTOMATION_PAUSE_SPEND_MULTIPLIER
  - AUTOMATION_PAUSE_MIN_CLICKS

7. A/B rotation sample size increase
- Recommendation: Increase minimum evidence requirement before pausing variants (impressions and/or lead/click thresholds).
- Why: Low sample decisions are noisy for lead objectives.
- Expected impact: More reliable winner selection.
- File touchpoint: src/labat/services/automation_service.py
- Code target: AB_MIN_IMPRESSIONS and winner gating logic.

8. Dedicated lead-targeting mode
- Recommendation: Introduce explicit lead-targeting strategy (separate from awareness/consideration/conversion ad-copy funnel semantics).
- Why: Lead form delivery behavior differs from traffic and purchase flows.
- Expected impact: Cleaner intent alignment and less cross-purpose logic coupling.
- File touchpoints:
  - src/labat/services/strategy_rules.py
  - src/alex/routers/alex_routes.py

## Proposed Implementation Order
1. Budget floor update
2. Conversion extraction completeness
3. Advantage+ audience enablement
4. Lead targeting broadening
5. Lead sync automation
6. Auto-pause threshold calibration
7. A/B rotation sample size increase
8. Dedicated lead-targeting mode refactor

## Validation Checklist (Post-Implementation)

### Functional
- Create new lead ad via /api/astra/orchestrate-lead-ad and confirm:
  - Campaign objective is OUTCOME_LEADS
  - Adset optimization_goal is LEAD_GENERATION
  - destination_type is ON_AD
  - targeting_automation.advantage_audience is enabled
  - Daily budget defaults to $25/day when omitted

### Automation
- Run hourly cron dry-run and live run:
  - run_full_cycle includes lead sync step result
  - Sync reports forms scanned and leads processed
  - No regression in auto_pause, auto_scale, or ab_rotation steps

### Metrics Integrity
- Verify _extract_conversions counts leadgen actions from insights payloads.
- Confirm lead campaigns are not paused when leads are present.

### Data Flow
- Confirm new leads appear in Firestore without manual endpoint trigger.
- Confirm welcome email workflow triggers from synced leads.

## Rollout Strategy
1. Deploy to one brand first (recommended: vowels).
2. Observe 24-48 hours:
- Delivery volume
- CPL trend
- Auto-pause events
- Sync throughput and dedupe behavior
3. Expand to all brands after stable results.

## Risks and Mitigations
- Risk: Budget increase raises spend faster than expected.
  - Mitigation: Use per-brand budget cap env vars and monitor first 48 hours.
- Risk: Broader targeting may lower lead quality.
  - Mitigation: Track downstream engagement and add quality filters in lead form questions.
- Risk: Cron sync introduces API rate pressure.
  - Mitigation: Keep incremental since-based sync and monitor API error rates.

## Notes
- This document is planning-only and does not change production behavior.
- Keep environment variables as primary control surface for tuning after rollout.
