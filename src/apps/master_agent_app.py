"""
apps/master_agent_app.py - Otaku Master Agent FastAPI application

Independent service that orchestrates monitoring, alerting, and reporting.
Deployed separately to Cloud Run.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging

from src.labat.routers.master_agent_routes import router as master_router
from src.labat.routers.blog_routes import router as blog_router
from src.labat.routers.content_routes import router as content_router
from src.labat.services.master_agent_service import get_master_agent
from src.labat.config_master import validate_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("master_agent")


# Background tasks
background_tasks = {}


async def _run_hourly_report():
    """Generate hourly report."""
    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour
            master = get_master_agent()
            report = await master.generate_report()
            await master.send_report_to_auth(report)
            logger.info("Hourly report sent to auth service")
        except Exception as e:
            logger.error("Hourly report failed: %s", e)


async def _run_critical_checks():
    """Run 5-minute critical health checks."""
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            master = get_master_agent()
            health = await master.health_check_all_services()
            anomalies = await master.detect_anomalies()
            
            # Alert on critical issues
            for service, status in health.items():
                if status.get("status") != "healthy":
                    logger.warning(
                        "Service %s unhealthy: %s", service, status.get("status")
                    )
                    await master.send_alert_to_auth(
                        severity="critical",
                        title=f"CRITICAL: {service} is down",
                        message=f"Service {service} failed health check",
                        service=service,
                        details={"health_status": status},
                    )
            
            # Alert on critical anomalies
            for anomaly in anomalies:
                if anomaly.get("severity") == "critical":
                    logger.warning("Critical anomaly detected: %s", anomaly)
                    await master.send_alert_to_auth(
                        severity="critical",
                        title=anomaly.get("type", "CRITICAL ANOMALY"),
                        message=anomaly.get("message", ""),
                        service=anomaly.get("service", "unknown"),
                        details=anomaly,
                    )
        except Exception as e:
            logger.error("Critical check failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of background tasks."""
    # Validate config on startup
    config_status = validate_config()
    logger.info("Master Agent config validation: %s", config_status)
    
    if not all(config_status.values()):
        logger.warning("Some config checks failed (see above for details)")
    
    # Start background tasks
    logger.info("Starting master agent background tasks...")
    background_tasks["hourly_report"] = asyncio.create_task(_run_hourly_report())
    background_tasks["critical_checks"] = asyncio.create_task(_run_critical_checks())
    logger.info("Background tasks started")
    
    yield  # App running
    
    # Cleanup on shutdown
    logger.info("Shutting down master agent...")
    for task_name, task in background_tasks.items():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Cancelled task: %s", task_name)


# Create app with lifespan management
app = FastAPI(
    title="WIHY Otaku Master Agent",
    description="System orchestration and monitoring service",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routes
app.include_router(master_router)
app.include_router(blog_router)
app.include_router(content_router)


@app.get("/health")
async def health():
    """Master agent health check."""
    master = get_master_agent()
    all_healthy = await master.health_check_all_services()
    status = "healthy" if all(
        s.get("status") == "healthy" for s in all_healthy.values()
    ) else "degraded"
    return {"status": status, "service": "otaku-master-agent"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Otaku Master Agent",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "status": "/api/otaku/master/status",
            "metrics": "/api/otaku/master/metrics/{service_name}",
            "anomalies": "/api/otaku/master/anomalies",
            "report": "/api/otaku/master/report",
            "alert": "/api/otaku/master/alert",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True,
    )
