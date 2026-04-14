@echo off
echo Starting ChoppingBlock...
echo.

:: Check if node_modules exists, if not run npm install
IF NOT EXIST node_modules (
    echo Installing root dependencies...
    cmd /c npm install
)

:: Run the npm start script which uses concurrently
npm start

pause
