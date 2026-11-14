# Run Rajasthan Royals Intelligence Hub Frontend
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting Rajasthan Royals Intelligence Hub - Frontend" -ForegroundColor Yellow
Write-Host "Dashboard: http://localhost:5500" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
python -m http.server 5500 --directory frontend
