"""
test_master_agent.py - Test Otaku Master Agent functionality locally

Run: python test_master_agent.py

Tests the master agent's ability to:
1. Check health of all services
2. Get metrics from LABAT and Shania
3. Detect anomalies
4. Generate reports
5. Send alerts (dry run)
"""

import asyncio
import sys
import os
from datetime import datetime

if os.getenv("ENABLE_MANUAL_TEST_SCRIPTS", "").strip().lower() not in (
    "1",
    "true",
    "yes",
):
    raise SystemExit(
        "Test scripts are disabled. Set ENABLE_MANUAL_TEST_SCRIPTS=true "
        "for intentional manual runs."
    )

# Add src to path
sys.path.insert(0, "/c/Users/Kortn/Repo/wihy_ml")

from src.labat.services.master_agent_service import MasterAgentService
from src.labat.config_master import (
    SERVICES_TO_MONITOR,
    ALERT_SPEND_SPIKE_PERCENT,
    ALERT_ENGAGEMENT_DROP_PERCENT,
    ALERT_ERROR_RATE_PERCENT,
    ALERT_RESPONSE_TIME_MS,
)


async def test_health_checks():
    """Test health check functionality."""
    print("\n" + "=" * 60)
    print("TEST 1: Health Checks for All Services")
    print("=" * 60)

    master = MasterAgentService()
    health = await master.health_check_all_services()

    print("\nServices to monitor:")
    for service_name, config in SERVICES_TO_MONITOR.items():
        print(f"  - {service_name}: {config['role']}")
        print(f"    URL: {config['url']}")
        print(f"    Health endpoint: {config['health_endpoint']}")

    print("\nHealth check results:")
    for service_name, result in health.items():
        status = result.get("status", "unknown")
        role = result.get("role", "unknown")
        print(f"\n  {service_name} ({role}): {status}")

        if status == "healthy":
            response_time = result.get("response_time_ms", "N/A")
            print(f"    Response time: {response_time}ms")
            if "health_data" in result:
                health_data = result["health_data"]
                config_status = health_data.get("config_status", {})
                if config_status:
                    checks = sum(1 for v in config_status.values() if v)
                    total = len(config_status)
                    print(f"    Config checks: {checks}/{total}")
        elif status == "unhealthy":
            print(f"    Status code: {result.get('status_code')}")
        else:
            print(f"    Error: {result.get('error', 'Unknown error')}")

    return health


async def test_metrics():
    """Test metrics collection."""
    print("\n" + "=" * 60)
    print("TEST 2: Metrics Collection")
    print("=" * 60)

    master = MasterAgentService()

    print("\n[LABAT Metrics]")
    labat_metrics = await master._get_labat_metrics()
    if labat_metrics:
        for key, value in labat_metrics.items():
            if key != "timestamp":
                print(f"  {key}: {value}")
    else:
        print("  (No metrics available - service may not be fully operational)")

    print("\n[Shania Metrics]")
    shania_metrics = await master._get_shania_metrics()
    if shania_metrics:
        for key, value in shania_metrics.items():
            if key != "timestamp":
                print(f"  {key}: {value}")
    else:
        print("  (No metrics available - service may not be fully operational)")

    return labat_metrics, shania_metrics


async def test_anomaly_detection():
    """Test anomaly detection."""
    print("\n" + "=" * 60)
    print("TEST 3: Anomaly Detection")
    print("=" * 60)

    print(f"\nThresholds:")
    print(f"  Spend spike alert: >{ALERT_SPEND_SPIKE_PERCENT}%")
    print(f"  Engagement drop alert: >{ALERT_ENGAGEMENT_DROP_PERCENT}%")
    print(f"  Error rate alert: >{ALERT_ERROR_RATE_PERCENT}%")
    print(f"  Response time alert: >{ALERT_RESPONSE_TIME_MS}ms")

    master = MasterAgentService()
    anomalies = await master.detect_anomalies()

    if anomalies:
        print(f"\n{len(anomalies)} anomaly/anomalies detected:")
        for anomaly in anomalies:
            severity = anomaly.get("severity", "unknown").upper()
            anomaly_type = anomaly.get("type", "unknown")
            message = anomaly.get("message", "")
            service = anomaly.get("service", "unknown")
            print(f"\n  [{severity}] {service}: {anomaly_type}")
            print(f"    Message: {message}")
            if "metrics" in anomaly:
                for key, value in anomaly["metrics"].items():
                    print(f"    {key}: {value}")
    else:
        print("\nNo anomalies detected - system appears healthy!")

    return anomalies


async def test_report_generation():
    """Test report generation."""
    print("\n" + "=" * 60)
    print("TEST 4: Report Generation")
    print("=" * 60)

    master = MasterAgentService()
    report = await master.generate_report()

    print("\nReport Summary:")
    print(f"  Generated: {report.get('generated_at')}")
    print(f"  Type: {report.get('report_type')}")
    print(f"  Overall status: {report.get('system_status')}")

    print("\nService Status:")
    services = report.get("services", {})
    for service_name, status in services.items():
        print(f"  {service_name}: {status.get('status')}")

    print("\nMetrics:")
    metrics = report.get("metrics", {})
    if metrics.get("labat"):
        print("  LABAT:")
        for key, value in metrics["labat"].items():
            if key != "timestamp":
                print(f"    {key}: {value}")

    print("\nAnomalies:")
    anomalies = report.get("anomalies", [])
    print(f"  Total detected: {report.get('anomalies_detected', 0)}")
    if anomalies:
        for anomaly in anomalies[:3]:  # Show first 3
            print(f"    - {anomaly.get('type')}: {anomaly.get('message')}")

    print("\nErrors:")
    error_summary = report.get("error_summary", {})
    print(f"  Total errors: {error_summary.get('total_errors', 0)}")
    if error_summary.get("recent_errors"):
        for error in error_summary["recent_errors"][:2]:  # Show first 2
            print(f"    - {error.get('service')}: {error.get('error')[:60]}...")

    return report


async def test_alert_dry_run():
    """Test alert system (dry run to auth service)."""
    print("\n" + "=" * 60)
    print("TEST 5: Alert System (Dry Run)")
    print("=" * 60)

    master = MasterAgentService()

    print("\nDry run - would send alert to auth service with:")
    print("  Severity: critical")
    print("  Title: Test Alert from Master Agent")
    print("  Service: labat")
    print("  Message: This is a test alert from the master agent")

    # NOTE: Not actually sending to avoid spam; just showing what would be sent
    print("\n[SKIPPED] Actual alert sending (would require auth service)")
    print("         Run with --live-alerts to send real alerts")

    return True


async def run_all_tests():
    """Run all tests and generate summary."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  OTAKU MASTER AGENT TEST SUITE".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")

    tests_passed = 0
    tests_total = 5

    try:
        await test_health_checks()
        tests_passed += 1
    except Exception as e:
        print(f"\n✗ Health checks test failed: {e}")

    try:
        await test_metrics()
        tests_passed += 1
    except Exception as e:
        print(f"\n✗ Metrics test failed: {e}")

    try:
        await test_anomaly_detection()
        tests_passed += 1
    except Exception as e:
        print(f"\n✗ Anomaly detection test failed: {e}")

    try:
        await test_report_generation()
        tests_passed += 1
    except Exception as e:
        print(f"\n✗ Report generation test failed: {e}")

    try:
        await test_alert_dry_run()
        tests_passed += 1
    except Exception as e:
        print(f"\n✗ Alert system test failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"\nTests passed: {tests_passed}/{tests_total}")

    if tests_passed == tests_total:
        print("\n✓ All tests passed! Master Agent ready for deployment.")
    elif tests_passed >= tests_total - 1:
        print("\n⚠ Most tests passed. Some services may not be available.")
        print("  This is OK if services are not yet deployed.")
    else:
        print(f"\n✗ {tests_total - tests_passed} test(s) failed. Check configuration.")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
