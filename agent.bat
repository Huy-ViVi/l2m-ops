@echo off
chcp 65001 >nul
rem Agent: chay tren may nay cac thao tac NC tool / MyTool ban bam tren website (dung VPN + SSO cua may nay).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [L2M Ops Agent] Chua cai app tren may nay: chay run.bat mot lan, noi CSDL chung o trang Cai dat, roi mo lai agent.bat.
  pause
  exit /b 1
)
set PYTHONUTF8=1
echo [L2M Ops Agent] Giu cua so nay mo trong luc dung website. Dong cua so hoac Ctrl+C de tat.
".venv\Scripts\python.exe" -m automation.agent %*
pause
