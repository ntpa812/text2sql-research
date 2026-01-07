@echo off
setlocal

REM Set port
set INSTANCE_ID=6804
set PORT=6804


set HF_HOME=data_models\models
set TRANSFORMERS_CACHE=data_models\models
set SENTENCE_TRANSFORMERS_HOME=data_models\models
set PIXELTABLE_HOME=data_models\database\pixeltable
@REM set PIXELTABLE_HOME=data_models\database
REM Set TMPDIR for Windows
set "TMPDIR=%TEMP%\javis_%PORT%"
if not exist "%TMPDIR%" mkdir "%TMPDIR%"
if not exist "%HF_HOME%" mkdir "%HF_HOME%"
if not exist "%TRANSFORMERS_CACHE%" mkdir "%TRANSFORMERS_CACHE%"
if not exist "%SENTENCE_TRANSFORMERS_HOME%" mkdir "%SENTENCE_TRANSFORMERS_HOME%"
if not exist "%PIXELTABLE_HOME%" mkdir "%PIXELTABLE_HOME%"

REM Windows - Change to project directory
cd /d "D:\TA\01_Projects\Dynamic_data_queries\Intent_Recognitions_notrain"


REM Check and set Python path from virtual environment
set "PYTHON_PATH="

if exist "D:\taEnv\Scripts\python.exe" (
    set "PYTHON_PATH=D:\taEnv\Scripts\python.exe"
    goto :run
)

if exist "..\taEnv\Scripts\python.exe" (
    set "PYTHON_PATH=..\taEnv\Scripts\python.exe"
    goto :run
)

REM Use default python if venv not found
set "PYTHON_PATH=python"

:run
echo Using TMPDIR=%TMPDIR%
echo.
echo Starting Knowledge Base API on port %PORT%...
echo Python: %PYTHON_PATH%
echo Press Ctrl+C to stop
echo.

REM Development mode with asyncio loop
"%PYTHON_PATH%" -m uvicorn ddq_intent_main:app --host 0.0.0.0 --port %PORT% --loop asyncio

endlocal
@REM pause
