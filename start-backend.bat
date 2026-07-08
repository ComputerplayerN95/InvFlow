@echo off
chcp 65001 >nul
cd /d "%~dp0FastAPI-backend"
call "%~dp0FastAPI-backend\venv\Scripts\activate.bat"
echo ========================================
echo  InvFlow Backend Starting...
echo  http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo ========================================
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
