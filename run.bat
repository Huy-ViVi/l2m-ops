@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [L2M Ops] Lan dau chay: dang tao moi truong Python va cai thu vien...
  python -m venv .venv || goto :err
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :err
)
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
echo Cai dat that bai. Kiem tra da cai Python 3.10+ va co mang Internet.
pause
