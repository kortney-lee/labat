"""
labat/services/master_agent_service.py - Otaku Master Agent service

Monitors LABAT, Shania, and all services.
Aggregates metrics, logs, generates reports, sends alerts.
"""

from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import httpx

from src.labat.config_master import (
    SERVICES_TO_MONITOR,
    INTERNAL_ADMIN_TOKEN,
    ALERT_SPEND_SPIKE_PERCENT,
    ALERT_ENGAGEMENT_DROP_PERCENT,
    ALERT_ERROR_RATE_PERCENT,
    ALERT_RESPONSE_TIME_MS,
)
from src.labat.services.notify import send_notification, send_report as _send_report

logger = logging.getLogger("labat.master_agent")


class MasterAgentService:
    """Orchestration service monitoring all WIHY systems."""

    def __init__(self):
        self.last_report_time = datetime.utcnow()
        self.service_metrics = {}
        self.error_buffer = []

    async def health_check_all_services(self) -> Dict[str, Any]:
        """Check health of all monitored services."""
        results = {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for service_name, service_config in SERVICES_TO_MONITOR.items():
                try:
                    url = service_config["url"] + service_config["health_endpoint"]
                    r = await client.get(
                        url,
                        headers={"X-Admin-Token": INTERNAL_ADMIN_TOKEN},
                    )
                    if r.status_code == 200:
                        health = r.json()
                        results[service_name] = {
                            "status": "healthy",
                            "response_time_ms": r.elapsed.total_seconds() * 1000,
                            "role": service_config["role"],
                            "health_data": health,
                        }
                    else:
                        results[service_name] = {
                            "status": "unhealthy",
                            "status_code": r.status_code,
                            "role": service_config["role"],
                        }
                except Exception as e:
                    results[service_name] = {
                        "status": "error",
                        "error": str(e),
                        "role": service_config["role"],
                    }
                    self.error_buffer.append(
                        {
                            "timestamp": datetime.utcnow().isoformat(),
                            "service": service_name,
                            "error": str(e),
                            "severity": "high",
                        }
                    )
                    logger.error("Health check failed for %s: %s", service_name, e)

        return results

    async def get_service_metrics(self, service_name: str) -> Dict[str, Any]:
        """Get current metrics from a service."""
        if service_name == "labat":
            return await self._get_labat_metrics()
        elif service_name == "shania":
            return await self._get_shania_metrics()
        return {}

    async def _get_labat_metrics(self) -> Dict[str, Any]:
        """Get LABAT ad spend and engagement metrics."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Get account summary (spend, ROI, conversions)
                r = await client.get(
                    SERVICES_TO_MONITOR["labat"]["url"] + "/api/labat/insights/summary",
                    headers={"X-Admin-Token": INTERNAL_ADMIN_TOKEN},
                )
                if r.status_code == 200:
                    insights = r.json()
                    data = insights.get("data", [])
                    if data:
                        row = data[0]
                        return {
                            "service": "labat",
                            "timestamp": datetime.utcnow().isoformat(),
                            "spend_today": float(row.get("spend", 0)),
                            "impressions_today": int(row.get("impressions", 0)),
                            "clicks_today": int(row.get("clicks", 0)),
                            "cpm": float(row.get("cpm", 0)),
                            "cpc": float(row.get("cpc", 0)),
                            "conversions": int(row.get("conversions", 0)),
                            "purchase_roas": row.get("purchase_roas", "N/A"),
                        }
            except Exception as e:
                logger.error("Failed to get LABAT metrics: %s", e)
        return {}

    async def _get_shania_metrics(self) -> Dict[str, Any]:
        """Get Shania engagement metrics."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                r = await client.get(
                    SERVICES_TO_MONITOR["shania"]["url"] + "/health",
                    headers={"X-Admin-Token": INTERNAL_ADMIN_TOKEN},
                )
                if r.status_code == 200:
                    health = r.json()
                    monitor = health.get("monitor", {})
                    metrics: Dict[str, Any] = {
                        "service": "shania",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    # Only include monitor fields when Shania actually reports them
                    if monitor:
                        metrics["monitor_running"] = monitor.get("running", False)
                        metrics["tracked_threads"] = monitor.get("tracked_threads", 0)
                        metrics["total_auto_replies"] = monitor.get("total_auto_replies", 0)
                        metrics["last_poll"] = monitor.get("last_poll")
                        metrics["poll_interval_seconds"] = monitor.get("poll_interval_seconds")
                    return metrics
            except Exception as e:
                logger.error("Failed to get Shania metrics: %s", e)
        return {}

    async def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in metrics (spend spikes, engagement drops, etc.)."""
        anomalies = []
        
        labat_metrics = await self._get_labat_metrics()
        shania_metrics = await self._get_shania_metrics()

        # Check LABAT spend spike
        if labat_metrics.get("spend_today", 0) > 1000:  # Over $10
            if labat_metrics.get("impressions_today", 0) < 1000:  # But low impressions
                anomalies.append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "service": "labat",
                        "type": "high_spend_low_impressions",
                        "severity": "warning",
                        "message": "High spend but low impressions detected",
                        "metrics": {
                            "spend": labat_metrics.get("spend_today"),
                            "impressions": labat_metrics.get("impressions_today"),
                        },
                    }
                )

        # Check LABAT conversion rate
        conversions = labat_metrics.get("conversions", 0)
        clicks = labat_metrics.get("clicks_today", 0)
        if clicks > 0:
            conversion_rate = (conversions / clicks) * 100
            if conversion_rate < 0.5:  # Below 0.5%
                anomalies.append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "service": "labat",
                        "type": "low_conversion_rate",
                        "severity": "warning",
                        "message": "Conversion rate below expected",
                        "metrics": {"conversion_rate": conversion_rate},
                    }
                )

        # Check Shania monitor — only alert if the service actually reports
        # a monitor that exists but is not running (skip when field is absent)
        if shania_metrics and "monitor_running" in shania_metrics:
            if not shania_metrics["monitor_running"]:
                anomalies.append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "service": "shania",
                        "type": "monitor_offline",
                        "severity": "warning",
                        "message": "Thread monitor is offline",
                    }
                )

        return anomalies

    async def send_alert_to_auth(
        self,
        severity: str,
        title: str,
        message: str,
        service: str,
        details: Optional[Dict[str, Any]] = None,
        recipient: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send alert to auth.wihy.ai for email/SMS delivery."""
        return await send_notification(
            agent="otaku-master",
            severity=severity,
            title=title,
            message=message,
            service=service,
            details=details,
            recipient=recipient,
        )

    async def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive system report."""
        health = await self.health_check_all_services()
        labat_metrics = await self._get_labat_metrics()
        shania_metrics = await self._get_shania_metrics()
        anomalies = await self.detect_anomalies()

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "report_type": "hourly_system_report",
            "services": health,
            "metrics": {
                "labat": labat_metrics,
                "shania": shania_metrics,
            },
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "error_summary": {
                "total_errors": len(self.error_buffer),
                "recent_errors": self.error_buffer[-10:],
            },
            "system_status": "healthy" if all(
                s.get("status") == "healthy" for s in health.values()
            ) else "degraded",
        }

        # Clear error buffer after report
        self.error_buffer = []
        self.last_report_time = datetime.utcnow()

        return report

    async def send_report_to_auth(self, report: Dict[str, Any]) -> bool:
        """Send hourly digest report to auth.wihy.ai for email delivery."""
        return await _send_report(report)


# Global instance
_master_agent = None


def get_master_agent() -> MasterAgentService:
    """Get or create master agent singleton."""
    global _master_agent
    if _master_agent is None:
        _master_agent = MasterAgentService()
    return _master_agent
