@echo off
REM Script to create .env file from .env.example for Windows
setlocal

set ROOT_DIR=%~dp0..
set ENV_EXAMPLE=%ROOT_DIR%\env.example
set ENV_FILE=%ROOT_DIR%\.env

if not exist "%ENV_EXAMPLE%" (
    echo ❌ .env.example file not found at %ENV_EXAMPLE%
    exit /b 1
)

if exist "%ENV_FILE%" (
    echo ⚠️  .env file already exists at %ENV_FILE%
    set /p OVERWRITE="Do you want to overwrite it? (y/N): "
    if /i not "%OVERWRITE%"=="y" (
        echo ❌ Cancelled. .env file was not changed.
        exit /b 0
    )
)

copy "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✅ Created .env file at %ENV_FILE%
    echo 📝 Please review and edit the values in .env file if needed.
    exit /b 0
) else (
    echo ❌ Error creating .env file
    exit /b 1
)
