"""
labat/config_master.py - Otaku Master Agent configuration

Master agent oversees LABAT, Shania, and all services.
Aggregates logs, monitors metrics, generates reports, alerts on errors.
"""

import os
import logging

logger = logging.getLogger(__name__)

# GCP Logging
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "wihy-ai")
GCP_LOG_NAME = os.getenv("GCP_LOG_NAME", "projects/wihy-ai/logs/wihy-master-agent")

# Monitoring thresholds
ALERT_SPEND_SPIKE_PERCENT = float(os.getenv("ALERT_SPEND_SPIKE_PERCENT", "50"))  # 50% increase
ALERT_ENGAGEMENT_DROP_PERCENT = float(os.getenv("ALERT_ENGAGEMENT_DROP_PERCENT", "30"))  # 30% drop
ALERT_ERROR_RATE_PERCENT = float(os.getenv("ALERT_ERROR_RATE_PERCENT", "5"))  # 5% error rate
ALERT_RESPONSE_TIME_MS = float(os.getenv("ALERT_RESPONSE_TIME_MS", "5000"))  # 5 second response time

# Report intervals
REPORT_INTERVAL_MINUTES = int(os.getenv("REPORT_INTERVAL_MINUTES", "60"))  # Hourly reports
CRITICAL_ALERT_CHECK_MINUTES = int(os.getenv("CRITICAL_ALERT_CHECK_MINUTES", "5"))  # Check every 5 min

# Services to monitor
SERVICES_TO_MONITOR = {
    "labat": {
        "url": os.getenv("LABAT_URL", "https://wihy-labat-n4l2vldq3q-uc.a.run.app"),
        "health_endpoint": "/health",
        "role": "ads_money_leads"
    },
    "shania": {
        "url": os.getenv("SHANIA_URL", "https://wihy-shania-12913076533.us-central1.run.app"),
        "health_endpoint": "/health",
        "role": "engagement_social_facebook"
    },
    "alex": {
        "url": os.getenv("ALEX_URL", "https://wihy-alex-n4l2vldq3q-uc.a.run.app"),
        "health_endpoint": "/health",
        "role": "seo_content_authority"
    },
}

# Auth service integration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "https://auth.wihy.ai")
AUTH_NOTIFY_ENDPOINT = "/api/notifications/alert"
AUTH_REPORT_ENDPOINT = "/api/reports/master-agent"

# Internal admin token
INTERNAL_ADMIN_TOKEN = (os.getenv("INTERNAL_ADMIN_TOKEN", "") or "").strip()

# Master agent identity
MASTER_AGENT_ID = os.getenv("MASTER_AGENT_ID", "otaku-master-agent")
MASTER_AGENT_NAME = os.getenv("MASTER_AGENT_NAME", "Otaku Master")
MASTER_AGENT_VERSION = "1.0.0"

# Logging config
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "false").lower() == "true"


def validate_config() -> dict:
    """Check master agent configuration readiness."""
    return {
        "admin_token": bool(INTERNAL_ADMIN_TOKEN),
        "gcp_project": bool(GCP_PROJECT_ID),
        "labat_url": bool(SERVICES_TO_MONITOR.get("labat", {}).get("url")),
        "shania_url": bool(SERVICES_TO_MONITOR.get("shania", {}).get("url")),
        "auth_url": bool(AUTH_SERVICE_URL),
    }
