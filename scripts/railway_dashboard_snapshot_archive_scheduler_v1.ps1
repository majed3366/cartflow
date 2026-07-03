# Enable Dashboard Snapshot Archive on Railway SCHEDULER service only (operator script).
# Requires: railway login + railway link (project + scheduler service).
#
# Usage:
#   .\scripts\railway_dashboard_snapshot_archive_scheduler_v1.ps1
#   .\scripts\railway_dashboard_snapshot_archive_scheduler_v1.ps1 -SchedulerService "your-scheduler-service-name"
#
# After deploy, run migration once:
#   railway run --service <SchedulerService> alembic upgrade r4s5t6u7v8w9
# Or: alembic upgrade head
#
# Verify (read-only):
#   python scripts/dashboard_snapshot_archive_deploy_verify_v1.py

param(
    [string]$SchedulerService = "smart-reply-ai-scheduler",
    [string]$ApiService = "smart-reply-ai"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Step 1: Confirm API service does NOT enable archive ==="
railway variable set CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED=0 --service $ApiService
Write-Host "API archive disabled on $ApiService"

Write-Host ""
Write-Host "=== Step 2: Enable archive on scheduler (conservative first-run batch) ==="
railway variable set CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED=1 --service $SchedulerService
railway variable set CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_RETENTION_DAYS=30 --service $SchedulerService
railway variable set CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_BATCH_SIZE=100 --service $SchedulerService
railway variable set CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_MAX_BATCHES_PER_TICK=1 --service $SchedulerService
railway variable set CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_TICK_MAX_SECONDS=60 --service $SchedulerService
railway variable set CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_INTERVAL_SECONDS=3600 --service $SchedulerService

Write-Host ""
Write-Host "=== Step 3: Run migration on scheduler (creates dashboard_snapshots_archive) ==="
railway run --service $SchedulerService alembic upgrade r4s5t6u7v8w9

Write-Host ""
Write-Host "=== Step 4: Redeploy scheduler ==="
railway redeploy --service $SchedulerService -y

Write-Host "Waiting 90s for deploy ..."
Start-Sleep -Seconds 90

Write-Host ""
Write-Host "=== Step 5: Read-only production verify (public API URL) ==="
python scripts/dashboard_snapshot_archive_deploy_verify_v1.py
exit $LASTEXITCODE
