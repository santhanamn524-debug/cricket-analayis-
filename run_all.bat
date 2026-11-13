@echo off
echo ========================================================
echo Starting Rajasthan Royals Intelligence Hub (Full Stack)
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5500
echo Swagger:  http://localhost:8000/docs
echo ========================================================
start "RR Backend" cmd /k "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
start "RR Frontend" cmd /k "python -m http.server 5500 --bind 127.0.0.1 --directory frontend"
echo Platform started! Open http://localhost:5500 in your browser.
pause
