# Launch Rajasthan Royals Intelligence Hub (Backend + Frontend)
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting Rajasthan Royals Intelligence Hub (Full Stack)" -ForegroundColor Yellow
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5500" -ForegroundColor Green
Write-Host "Swagger:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m http.server 5500 --bind 127.0.0.1 --directory frontend"

Write-Host "Platform launched! Access the dashboard at http://localhost:5500" -ForegroundColor Yellow
