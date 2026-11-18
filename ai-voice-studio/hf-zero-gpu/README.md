---
title: AI Voice Studio Pro Neural TTS
emoji: 🎙️
colorFrom: indigo
colorTo: teal
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: false
---

# AI Voice Studio Pro — Mithi Neural TTS

A Gradio demo for Mithi v2 Flash, supporting Hindi, Odia, English and eight more Indian languages, with five male and five female voices.

## Deploy as a Hugging Face Space

1. Sign in to Hugging Face.
2. Create a new **Space** and choose **Gradio** as the SDK.
3. Choose **ZeroGPU** hardware in the Space settings (not CPU Basic).
4. Upload the three files from this folder: `app.py`, `requirements.txt`, and this `README.md`.
5. Wait for the Space to build and download the model weights on first start.
6. Open the Space, choose language and voice, enter text (up to 1,200 characters per request), and generate audio.

Free ZeroGPU hosting is conditional: Hugging Face currently says personal accounts in good standing with a verified email and account older than 30 days can host up to two ZeroGPU Spaces. Free accounts have a shared daily quota of 5 GPU minutes and medium queue priority. Quota resets 24 hours after first GPU use. The Space may queue or become unavailable when quota is exhausted. This is not unlimited or guaranteed always-on hosting. Check current official rules before deployment:
https://huggingface.co/docs/hub/spaces-zerogpu

## Model

- Model: https://huggingface.co/Oomni/mithi-v2-flash
- License: Apache-2.0
- 11 languages, 10 voices, 24 kHz mono output.
- Model card notes that expressiveness is flatter than natural speech and some Odia words may be spoken faster or mispronounced.

## Notes

- The model weights are downloaded at Space startup and are not stored in this GitHub repository.
- This Space is a public demo. Do not submit confidential or sensitive text.
- The app caps requests at 1,200 characters to reduce GPU queue time and fit the free shared quota.
- This folder is a deployment package only. It does not automatically create a Space or connect it to the existing GitHub Pages site. The user must create the Space and provide its URL before frontend linking can be completed.
