@echo off
chcp 65001 >nul
rem Agent: chay tren may nay cac thao tac NC tool / MyTool ban bam tren website (dung VPN + SSO cua may nay).
rem May moi: tu cai Python + thu vien (tools\setup.ps1), hoi dia chi CSDL chung va tai khoan L2M Ops mot lan.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup.ps1"
if errorlevel 1 goto :err
set PYTHONUTF8=1
echo [L2M Ops Agent] Giu cua so nay mo trong luc dung website. Dong cua so hoac Ctrl+C de tat.
".venv\Scripts\python.exe" -m automation.agent %*
pause
goto :eof

:err
echo.
echo Cai dat that bai (xem thong bao phia tren). Can mang Internet de tai Python va thu vien.
pause
