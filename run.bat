@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY="
python -c "import django, rest_framework" >nul 2>&1
if not errorlevel 1 (
  set "PY=python"
) else (
  py -c "import django, rest_framework" >nul 2>&1
  if not errorlevel 1 (
    set "PY=py"
  )
)

if not defined PY (
  if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv 2>nul
    if errorlevel 1 py -m venv .venv
  )
  echo Installing Django and Django REST Framework...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install django djangorestframework
  set "PY=.venv\Scripts\python.exe"
)

echo Using: %PY%
"%PY%" -c "import django, rest_framework; print('Django', django.get_version(), '| DRF', rest_framework.VERSION)"

echo Running migrations...
"%PY%" manage.py makemigrations core
"%PY%" manage.py migrate

echo Seeding application data...
"%PY%" manage.py seed_data

echo.
echo ============================================================
echo  QuickRefill is ready
echo ============================================================
echo  Login:       http://127.0.0.1:8000/login/
echo  Customer:    http://127.0.0.1:8000/app/
echo  Rider:       http://127.0.0.1:8000/rider/
echo  Vendor:      http://127.0.0.1:8000/vendor/
echo.
echo ============================================================
echo.

"%PY%" manage.py runserver 0.0.0.0:8000
