# AI Voice Studio Pro — Neural TTS backend

This is an optional Python API for the static GitHub Pages app. It uses **Mithi v2 Flash** (Apache-2.0), which supports Hindi (`hi`), Odia (`or`), English (`en`) and eight other Indian languages, with five male and five female voices.

> GitHub Pages cannot run Python or load this model. This backend must run on a separate Python machine or Python hosting service. A free host may sleep, impose CPU/RAM limits, or stop long jobs; unlimited always-on free inference is not guaranteed.

## Requirements

- Python 3.10+
- A machine with enough RAM and disk for PyTorch and the model. CPU mode is supported, but low-power devices can be slow.
- Internet access for the initial model/dependency downloads.

## Install

Run these commands from this `backend` folder:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm
hf download Oomni/mithi-v2-flash --local-dir ./mithi-v2-flash
```

On Windows, set environment variables in PowerShell before starting:

```powershell
$env:VOICE_API_KEY = "replace-with-a-long-random-secret"
$env:CORS_ORIGINS = "https://smartdigitalseva05-hash.github.io"
$env:MITHI_MODEL_DIR = "$PWD/mithi-v2-flash"
$env:TORCH_NUM_THREADS = "2"
uvicorn app:app --host 127.0.0.1 --port 8000
```

Linux/macOS example:

```bash
export VOICE_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export CORS_ORIGINS="https://smartdigitalseva05-hash.github.io"
export MITHI_MODEL_DIR="$PWD/mithi-v2-flash"
export TORCH_NUM_THREADS=2
uvicorn app:app --host 127.0.0.1 --port 8000
```

For a remote host, bind to the host's required interface/port and put the service behind HTTPS. Set `VOICE_API_KEY`, `CORS_ORIGINS`, and `MITHI_MODEL_DIR` as private environment variables in the host dashboard. Never commit the API key or model weights to GitHub.

## API

- `GET /health` — basic readiness status.
- `POST /api/tts` — requires `Authorization: Bearer YOUR_SECRET`; returns a 24 kHz PCM WAV file.

Example request:

```bash
curl -X POST "http://127.0.0.1:8000/api/tts" \
  -H "Authorization: Bearer YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"text":"ନମସ୍କାର, ଆପଣ କେମିତି ଅଛନ୍ତି?","language":"or","voice":"charvi"}' \
  --output speech.wav
```

Allowed languages: `hi en bn gu kn ml mr or pa ta te`.

Voices:
- Male: `satvik`, `anirban`, `nakul`, `vasant`, `siddhant`
- Female: `charvi`, `ahana`, `vaidehi`, `malini`, `jahnavi`

The API caps each request at 3,000 characters and serializes model inference to reduce CPU/RAM spikes. Add host-level rate limiting and monitoring before public launch. CORS is not authentication; keep the API token private. Do not put a permanent shared token in public browser JavaScript.

## Current integration status

This backend is a separate scaffold. The GitHub Pages frontend now has an optional Neural AI mode: enter your backend HTTPS URL and private token in the Voice controls panel, then use Neural AI and select a language/voice. The token is kept in sessionStorage for the current browser tab session. Device mode remains available without a backend. No paid API is used by this code, but hosting, bandwidth, and compute may have free-tier limits.

## Model notes

Mithi v2 Flash is distributed under Apache-2.0. The model card reports 11 languages and 10 voices. It also notes flatter emotional intonation than natural speech and possible pronunciation/speed issues in Odia and some other languages. Test the generated audio before publishing.
