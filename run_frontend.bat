@echo off
echo ========================================================
echo Starting Rajasthan Royals Intelligence Hub - Frontend
echo Dashboard: http://localhost:5500
echo ========================================================
python -m http.server 5500 --directory frontend
pause
