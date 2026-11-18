@echo off
setlocal
cd /d "%~dp0"
title AI Voice Studio - Local Mithi Server
where py >nul 2>nul
if errorlevel 1 (echo Install Python 3.10+ from https://www.python.org/downloads/ and enable Add Python to PATH.& pause& exit /b 1)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install torch --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
if not exist "mithi-v2-flash\run.py" (
  ".venv\Scripts\hf.exe" download Oomni/mithi-v2-flash --local-dir mithi-v2-flash
  if errorlevel 1 goto failed
)
if not exist ".voice_api_key" (
  ".venv\Scripts\python.exe" -c "import secrets; open('.voice_api_key','w').write(secrets.token_urlsafe(32))"
)
set /p VOICE_API_KEY=<.voice_api_key
set "MITHI_MODEL_DIR=%CD%\mithi-v2-flash"
set "MITHI_DEVICE=cpu"
set "TORCH_NUM_THREADS=4"
set "CORS_ORIGINS=https://smartdigitalseva05-hash.github.io"
echo Local server: http://127.0.0.1:8000
echo Health check: http://127.0.0.1:8000/health
echo Private token (do not share):
type .voice_api_key
echo Keep this window open while generating audio. Ctrl+C stops the server.
".venv\Scripts\uvicorn.exe" app:app --host 127.0.0.1 --port 8000
goto end
:failed
echo Setup failed. Check the error, internet and free disk space, then retry.
pause
exit /b 1
:end
endlocal
