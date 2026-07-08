@echo off
chcp 65001 >nul
cd /d "%~dp0vue-frontend"
echo ========================================
echo  InvFlow Frontend Starting...
echo  http://localhost:5173
echo ========================================
npm run dev
pause
