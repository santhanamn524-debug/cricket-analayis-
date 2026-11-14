@echo off
echo ========================================================
echo Starting Rajasthan Royals Intelligence Hub - Backend API
echo Server: http://localhost:8000
echo Swagger Docs: http://localhost:8000/docs
echo ========================================================
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause
