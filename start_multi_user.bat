@echo off
echo Starting Multi-User IoT Stock Monitor Application...
echo.

REM Check if Python is installed
py --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

REM Check if requirements are installed
echo Checking dependencies...
pip show flask-sqlalchemy >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Start the multi-user Flask application
echo.
echo Starting Multi-User Flask application...
echo The web interface will be available at: http://localhost:5000
echo.
echo Default Admin Login:
echo   Username: admin
echo   Password: admin123
echo.
echo Press Ctrl+C to stop the application
echo.

py app_multi_user.py

pause
