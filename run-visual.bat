@echo off
setlocal enabledelayedexpansion

:: Define cleanup function with a label and trap with Ctrl+C
set "EXITING=false"
call :trapCtrlC

:: Start server
cd server || exit /b 1
call npm install
start "server" /B node server.js
:: Give it time to initialize
:waitForServer
timeout /t 1 > nul
powershell -command "try { (New-Object System.Net.Sockets.TcpClient).Connect('localhost', 3000) } catch { exit 1 }"
if errorlevel 1 goto waitForServer

:: Start client
cd ..\clients || exit /b 1
call npm install
start "client" /B node agent.js l apple

:: Wait indefinitely (you can improve this if needed)
:waitLoop
if "!EXITING!"=="true" goto end
timeout /t 1 > nul
goto waitLoop

:end
echo Cleaning up...
taskkill /f /im node.exe > nul 2>&1
exit /b 0

:: Trap Ctrl+C (SIGINT)
:trapCtrlC
:: Uses PowerShell to register Ctrl+C handler
powershell -Command "$handler = { Set-Content -Path env:EXITING -Value 'true' }; [Console]::CancelKeyPress += $handler"
goto :eof