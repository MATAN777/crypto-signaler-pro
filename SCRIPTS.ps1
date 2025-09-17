# PowerShell script for Windows to build and run the Linux Docker container

# === CONFIG ===
# Set Telegram test credentials for this session
$env:TELEGRAM_BOT_TOKEN = "8203351641:AAGRz813XLXXcVk_IM9cl2W02dB5F00ymeU"
$env:TELEGRAM_CHAT_ID   = "819529484"

# Optional: restrict timeframes (uncomment to override)
# $env:TIMEFRAMES = "15m,30m,1h,2h,4h,6h,12h,d,w"

$DataPath = "$PWD\data"

# Create data dir if missing
if (!(Test-Path $DataPath)) { New-Item -ItemType Directory -Path $DataPath | Out-Null }

# === BUILD IMAGE ===
Write-Host "🔨 Building Docker image..." -ForegroundColor Blue
docker build -t crypto-signaler:latest .
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Build failed!" -ForegroundColor Red; exit 1 }
Write-Host "✅ Build successful!" -ForegroundColor Green

# === STOP OLD CONTAINER ===
Write-Host "🔄 Stopping old container..." -ForegroundColor Yellow
docker rm -f uvicorn_app 2>$null

# === RUN NEW CONTAINER ===
Write-Host "🚀 Starting new container..." -ForegroundColor Blue
docker run -d `
  --name uvicorn_app `
  -p 127.0.0.1:7000:7000 `
  -e TELEGRAM_BOT_TOKEN="$env:TELEGRAM_BOT_TOKEN" `
  -e TELEGRAM_CHAT_ID="$env:TELEGRAM_CHAT_ID" `
  -e TIMEFRAMES="$env:TIMEFRAMES" `
  -e SIGNAL_STATE_PATH="/app/data/signal_state.json" `
  --mount type=bind,source="$DataPath",target=/app/data `
  --restart unless-stopped `
  crypto-signaler:latest
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Container start failed!" -ForegroundColor Red; exit 1 }
Write-Host "✅ Container started!" -ForegroundColor Green

# === VERIFY ===
Write-Host "🔍 Verifying container..." -ForegroundColor Yellow
docker ps --filter "name=uvicorn_app"
docker port uvicorn_app
docker exec uvicorn_app sh -lc 'echo $TELEGRAM_BOT_TOKEN; echo $TELEGRAM_CHAT_ID'

# === TEST TELEGRAM PING ===
Write-Host "📱 Testing Telegram ping..." -ForegroundColor Cyan
Invoke-RestMethod -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/sendMessage" `
  -Method Post -Body @{ chat_id = $env:TELEGRAM_CHAT_ID; text = "Ping from container ✅" }

# === VIEW LOGS ===
Write-Host "📋 Container logs (Ctrl+C to stop viewing):" -ForegroundColor Yellow
docker logs -f uvicorn_app