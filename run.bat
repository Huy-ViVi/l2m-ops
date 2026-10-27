@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Tu chuan bi moi truong: may chua co Python thi tu tai ban portable vao thu muc app (xem tools\setup.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup.ps1"
if errorlevel 1 goto :err
if "%L2M_SERVER_ADDRESS%"=="" set L2M_SERVER_ADDRESS=localhost
if /i "%L2M_APP_MODE%"=="team" (
  echo [L2M Ops - TEAM] Server cho ca team. Thanh vien truy cap http://^<IP may nay^>:8501 - xem IP o trang Cai dat.
  echo [L2M Ops - TEAM] Giu cua so nay mo trong luc team dang dung app.
) else (
  echo [L2M Ops] Dang mo app tai http://localhost:8501 ...
)
".venv\Scripts\python.exe" -m streamlit run app.py --server.address %L2M_SERVER_ADDRESS%
goto :eof

:err
echo.
echo Cai dat that bai (xem thong bao phia tren). Can mang Internet de tai Python va thu vien.
pause
