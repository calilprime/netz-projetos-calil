@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 ( py hub_app.py ) else ( python hub_app.py )
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro. Verifique se o Python esta instalado.
    echo.
    pause
)
