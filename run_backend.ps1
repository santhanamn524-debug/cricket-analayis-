# Run Rajasthan Royals Intelligence Hub Backend API
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting Rajasthan Royals Intelligence Hub - Backend API" -ForegroundColor Yellow
Write-Host "URL: http://localhost:8000" -ForegroundColor Green
Write-Host "Swagger Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
