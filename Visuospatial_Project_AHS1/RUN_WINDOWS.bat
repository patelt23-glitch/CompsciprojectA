@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py"
) else (
  set "PY=python"
)
if not exist .venv\Scripts\python.exe (
  %PY% -m venv .venv || goto :error
)
.venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error
.venv\Scripts\python.exe manage.py migrate || goto :error
.venv\Scripts\python.exe manage.py check || goto :error
echo.
echo Open http://127.0.0.1:8000/ in your browser.
.venv\Scripts\python.exe manage.py runserver 8000
goto :end
:error
echo Setup failed. Check Python, internet access, and terminal error details.
:end
pause
