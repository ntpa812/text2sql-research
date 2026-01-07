@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Kill processes using specified ports
REM Usage: kill_ports.bat 6804 8080 3000
REM ============================================================

if "%~1"=="" (
    echo Usage: kill_ports.bat PORT1 [PORT2] [PORT3] ...
    echo Example: kill_ports.bat 6804 8080 3000
    exit /b 1
)

echo.
echo ============================================================
echo Killing processes on ports: %*
echo ============================================================
echo.

set KILLED_COUNT=0

:loop
if "%~1"=="" goto :done

set PORT=%~1
echo.
echo [PORT %PORT%] Searching for process...

REM Find PID using the port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    set PID=%%a
    if not "!PID!"=="" (
        if not "!PID!"=="0" (
            echo [PORT %PORT%] Found PID: !PID!
            
            REM Get process name
            for /f "tokens=1" %%b in ('tasklist /fi "PID eq !PID!" /fo csv /nh 2^>nul') do (
                set PNAME=%%~b
                echo [PORT %PORT%] Process: !PNAME!
            )
            
            REM Kill the process
            taskkill /F /PID !PID! >nul 2>&1
            if !errorlevel! equ 0 (
                echo [PORT %PORT%] Successfully killed PID !PID!
                set /a KILLED_COUNT+=1
            ) else (
                echo [PORT %PORT%] Failed to kill PID !PID! - may need admin rights
            )
        )
    )
)

REM Check if no process found
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING" 2^>nul') do (
    goto :next
)
echo [PORT %PORT%] No process found using this port

:next
shift
goto :loop

:done
echo.
echo ============================================================
echo Done! Killed %KILLED_COUNT% process(es)
echo ============================================================

endlocal
