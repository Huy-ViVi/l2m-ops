@echo off
chcp 65001 >nul
rem Agent: chay tren may nay cac thao tac NC tool / MyTool ban bam tren website (dung VPN + SSO cua may nay).
rem May moi: tu cai Python + thu vien (tools\setup.ps1), hoi dia chi CSDL chung va tai khoan L2M Ops mot lan.
rem Agent chay ngam (cham tron o khay he thong). Mo lai file nay khi agent dang chay: hien cua so log.
rem   agent.bat --stop        tat agent      agent.bat --logout      doi tai khoan
rem   agent.bat --foreground  chay trong cua so nay nhu ban cu (dong cua so la tat agent)
cd /d "%~dp0"
set PYTHONUTF8=1
rem Code moi giai nen de len: tat agent cu truoc khi cai thu vien (thu vien dang dung thi khong thay duoc).
if exist ".venv\Scripts\python.exe" ".venv\Scripts\python.exe" automation\agent.py --stop-if-outdated
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup.ps1"
if errorlevel 1 goto :err
".venv\Scripts\python.exe" automation\agent.py %*
if errorlevel 1 pause
goto :eof

:err
echo.
echo Cai dat that bai (xem thong bao phia tren). Can mang Internet de tai Python va thu vien.
pause
