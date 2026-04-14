"""
labat/routers/master_agent_routes.py - Master Agent endpoints

Exposes monitoring, alerting, and reporting capabilities.
"""

from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from src.labat.services.master_agent_service import get_master_agent
from src.labat.config import INTERNAL_ADMIN_TOKEN


logger = logging.getLogger("labat.routers.master_agent")
router = APIRouter(prefix="/api/otaku/master", tags=["master-agent"])


def _verify_admin(token: Optional[str] = Header(None)) -> bool:
    """Verify admin token."""
    if not token or token != INTERNAL_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@router.get("/health")
async def master_agent_health():
    """Master agent health check."""
    return {"status": "running", "service": "otaku-master-agent"}


@router.get("/status")
async def master_agent_status(x_admin_token: Optional[str] = Header(None)):
    """Get comprehensive status of all services."""
    _verify_admin(x_admin_token)
    master = get_master_agent()
    health = await master.health_check_all_services()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "services": health,
        "overall_status": "healthy"
        if all(s.get("status") == "healthy" for s in health.values())
        else "degraded",
    }


@router.get("/metrics/{service_name}")
async def get_service_metrics(
    service_name: str, x_admin_token: Optional[str] = Header(None)
):
    """Get metrics for a specific service."""
    _verify_admin(x_admin_token)
    if service_name not in ["labat", "shania"]:
        raise HTTPException(status_code=400, detail="Unknown service")
    
    master = get_master_agent()
    metrics = await master.get_service_metrics(service_name)
    return metrics


@router.get("/anomalies")
async def detect_anomalies(x_admin_token: Optional[str] = Header(None)):
    """Detect system anomalies."""
    _verify_admin(x_admin_token)
    master = get_master_agent()
    anomalies = await master.detect_anomalies()
    return {"timestamp": datetime.utcnow().isoformat(), "anomalies": anomalies}


@router.post("/alert")
async def send_alert(
    alert_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Send alert to auth service."""
    _verify_admin(x_admin_token)
    
    master = get_master_agent()
    background_tasks.add_task(
        master.send_alert_to_auth,
        severity=alert_data.get("severity", "warning"),
        title=alert_data.get("title", "System Alert"),
        message=alert_data.get("message", ""),
        service=alert_data.get("service", "unknown"),
        details=alert_data.get("details"),
        recipient=alert_data.get("recipient"),
    )
    
    return {"status": "alert_sent"}


@router.get("/report")
async def generate_report(x_admin_token: Optional[str] = Header(None)):
    """Generate comprehensive system report."""
    _verify_admin(x_admin_token)
    master = get_master_agent()
    report = await master.generate_report()
    return report


@router.post("/report/send")
async def send_system_report(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Generate and send report to auth service."""
    _verify_admin(x_admin_token)
    master = get_master_agent()
    
    async def _send():
        report = await master.generate_report()
        await master.send_report_to_auth(report)
    
    background_tasks.add_task(_send)
    return {"status": "report_generation_started"}


@router.post("/check")
async def run_critical_check(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Run critical health check and alert if issues found."""
    _verify_admin(x_admin_token)
    master = get_master_agent()
    
    async def _check():
        health = await master.health_check_all_services()
        anomalies = await master.detect_anomalies()
        
        # Alert on critical issues
        for service, status in health.items():
            if status.get("status") != "healthy":
                await master.send_alert_to_auth(
                    severity="critical",
                    title=f"{service} health check failed",
                    message=f"Service {service} is not healthy: {status}",
                    service=service,
                    details={"health_status": status},
                )
        
        # Alert on anomalies
        for anomaly in anomalies:
            if anomaly.get("severity") == "critical":
                await master.send_alert_to_auth(
                    severity="critical",
                    title=anomaly.get("type", "Critical Anomaly"),
                    message=anomaly.get("message", ""),
                    service=anomaly.get("service", "unknown"),
                    details=anomaly,
                )
    
    background_tasks.add_task(_check)
    return {"status": "critical_check_started"}


@router.post("/notify")
async def send_customer_notification(
    notification: Dict[str, Any],
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Send customer notification for important events."""
    _verify_admin(x_admin_token)
    master = get_master_agent()
    
    background_tasks.add_task(
        master.send_alert_to_auth,
        severity=notification.get("severity", "info"),
        title=notification.get("title", "Notification"),
        message=notification.get("message", ""),
        service=notification.get("service", "wihy"),
        details=notification.get("details"),
    )
    
    return {"status": "notification_queued"}
