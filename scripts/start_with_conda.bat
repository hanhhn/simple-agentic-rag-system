@echo off
REM Script to start the application with conda environment
setlocal

echo Checking conda environment...

REM Check if conda is available
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Conda is not found in PATH. Please install conda or add it to PATH.
    exit /b 1
)

REM Check if environment exists
conda env list | findstr /C:"simple-rag-system" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Conda environment 'simple-rag-system' not found.
    echo Creating environment from environment.yml...
    conda env create -f environment.yml
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Failed to create conda environment.
        exit /b 1
    )
)

REM Activate environment
echo Activating conda environment...
call conda activate simple-rag-system
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to activate conda environment.
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo ⚠️  .env file not found. Creating from env.example...
    if exist "env.example" (
        copy env.example .env >nul
        echo ✅ Created .env file. Please review and edit if needed.
    ) else (
        echo ❌ env.example file not found. Please create .env manually.
        exit /b 1
    )
)

REM Start the application
echo Starting application...
echo.
echo ✅ Conda environment activated: simple-rag-system
echo 📝 Make sure Qdrant, Ollama, and Redis are running
echo 🚀 Starting FastAPI server...
echo.

uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
