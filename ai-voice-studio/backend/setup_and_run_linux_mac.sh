#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"'
if [ ! -x .venv/bin/python ]; then "$PYTHON" -m venv .venv; fi
V=".venv/bin"
"$V/pip" install --upgrade pip
"$V/pip" install torch --index-url https://download.pytorch.org/whl/cpu
"$V/pip" install -r requirements.txt
"$V/python" -m spacy download en_core_web_sm\nif [ ! -f mithi-v2-flash/run.py ]; then
  "$V/hf" download Oomni/mithi-v2-flash --local-dir mithi-v2-flash
fi
if [ ! -f .voice_api_key ]; then
  "$V/python" -c 'import secrets; open(".voice_api_key","w").write(secrets.token_urlsafe(32))'
  chmod 600 .voice_api_key
fi
export VOICE_API_KEY="$(cat .voice_api_key)"
export MITHI_MODEL_DIR="$PWD/mithi-v2-flash"
export MITHI_DEVICE=cpu
export TORCH_NUM_THREADS="${TORCH_NUM_THREADS:-4}"
export CORS_ORIGINS="https://smartdigitalseva05-hash.github.io"
echo "Local server: http://127.0.0.1:8000"
echo "Health: http://127.0.0.1:8000/health"
echo "Private token (do not share):"
cat .voice_api_key
echo "Keep this terminal open. Ctrl+C stops the server."
exec "$V/uvicorn" app:app --host 127.0.0.1 --port 8000
