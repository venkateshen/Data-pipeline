# Demo Script for Sales Data Pipeline

# 1. Set Execution Policy for this process
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

Write-Host "--- Starting Sales Data Pipeline Demo ---" -ForegroundColor Cyan

# Check if Azurite is already running
$azuriteRunning = Get-Process -Name "azurite" -ErrorAction SilentlyContinue
if ($azuriteRunning) {
    Write-Host "Azurite is already running. Restarting to ensure fresh state..." -ForegroundColor Gray
    Stop-Process -Name "azurite" -Force -ErrorAction SilentlyContinue
}

# 2. Start Azurite in the background
Write-Host "[1/5] Starting Azurite (Local Storage)..." -ForegroundColor Yellow
$azuriteProc = Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass", "-Command", "azurite --silent --location ./azurite_data --skipApiVersionCheck" -NoNewWindow -PassThru

Write-Host "Waiting for Azurite to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# 3. Setup Storage and Upload Raw Data
Write-Host "[2/5] Initializing containers and uploading sample data..." -ForegroundColor Yellow
if (Test-Path ".\.venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" setup_local_storage.py
} else {
    python setup_local_storage.py
}

# 4. Start Azure Functions Host in the background
Write-Host "[3/5] Starting Azure Functions Host..." -ForegroundColor Yellow
$funcCommand = if (Test-Path ".\.venv\Scripts\activate.ps1") { ".\.venv\Scripts\activate.ps1; func start" } else { "func start" }
$funcProc = Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass", "-NoExit", "-Command", "$funcCommand" -NoNewWindow -PassThru

Write-Host "Waiting 15 seconds for functions to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 15

# 5. Trigger Pipeline
Write-Host "[4/5] Triggering CleanSales1 and CleanSales2..." -ForegroundColor Yellow

try {
    # CleanSales1
    Invoke-RestMethod -Uri "http://localhost:7071/api/CleanSales1" -Method Post -InFile "tests/sample_blob_event.json" -ContentType "application/json" | Out-Null
    Write-Host "  -> Source 1 Cleaned." -ForegroundColor Green

    # CleanSales2
    Invoke-RestMethod -Uri "http://localhost:7071/api/CleanSales2" -Method Post -InFile "tests/sample_blob_event_s2.json" -ContentType "application/json" | Out-Null
    Write-Host "  -> Source 2 Cleaned." -ForegroundColor Green

    # 6. Reconcile
    Write-Host "[5/5] Running Reconcile (Merge)..." -ForegroundColor Yellow
    $body = @{
        file_1_url = "http://127.0.0.1:10000/devstoreaccount1/c1raw/cleaned_s1_raw.csv"
        file_2_url = "http://127.0.0.1:10000/devstoreaccount1/c2raw/cleaned_s2_raw.csv"
        batchId = "demo_batch"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "http://localhost:7071/api/Reconcile" -Method Post -Body $body -ContentType "application/json"
    Write-Host "  -> $response" -ForegroundColor Green

    Write-Host "`n--- Demo Complete ---" -ForegroundColor Cyan
    Write-Host "Final Report: Check 'reconciled' container in Azurite (batch: demo_batch)"
} catch {
    Write-Host "`nError during demo: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure 'func start' initialized correctly (it usually takes 10-20 seconds)." -ForegroundColor Gray
}

Write-Host "Press any key to stop the services and exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup
Stop-Process -Id $azuriteProc.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $funcProc.Id -Force -ErrorAction SilentlyContinue
Get-Process -Name "func" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "azurite" -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host "Services stopped." -ForegroundColor Gray
