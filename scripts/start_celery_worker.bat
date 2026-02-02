@echo off
REM Start Celery worker for background task processing (Windows)

setlocal

REM Get the directory of this script
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Change to project root
cd /d "%PROJECT_ROOT%"

REM Try to activate conda environment first, then venv
where conda >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    conda env list | findstr /C:"simple-rag-system" >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo Activating conda environment: simple-rag-system
        call conda activate simple-rag-system
    )
)

REM Activate virtual environment if conda not available or not found
if "%CONDA_DEFAULT_ENV%"=="" (
    if exist "venv\Scripts\activate.bat" (
        call venv\Scripts\activate.bat
    ) else if exist ".venv\Scripts\activate.bat" (
        call .venv\Scripts\activate.bat
    )
)

REM Set environment variables if not set
if "%CELERY_BROKER_URL%"=="" set CELERY_BROKER_URL=redis://localhost:6379/0
if "%CELERY_RESULT_BACKEND%"=="" set CELERY_RESULT_BACKEND=redis://localhost:6379/0

REM Start Celery worker
echo Starting Celery worker...
echo Broker: %CELERY_BROKER_URL%
echo Backend: %CELERY_RESULT_BACKEND%

celery -A src.tasks.celery_app worker ^
    --loglevel=info ^
    --queues=documents,embeddings ^
    --concurrency=4 ^
    --max-tasks-per-child=1000 ^
    --time-limit=3600 ^
    --soft-time-limit=3000

endlocal
