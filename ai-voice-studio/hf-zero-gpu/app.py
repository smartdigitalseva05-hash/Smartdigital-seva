"""Mithi v2 Flash demo for a Hugging Face ZeroGPU Gradio Space."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import gradio as gr
import spaces
import torch
from huggingface_hub import snapshot_download

MODEL_ID = "Oomni/mithi-v2-flash"
MODEL_DIR = Path(os.getenv("MODEL_DIR", "/tmp/mithi-v2-flash"))

# ZeroGPU requires the model to be placed on CUDA at module import time.
# Its CUDA emulation layer makes this initialization possible before a GPU is allocated.
torch.set_num_threads(2)
snapshot_download(repo_id=MODEL_ID, local_dir=str(MODEL_DIR))
sys.path.insert(0, str(MODEL_DIR))
from run import Mithi  # noqa: E402

tts = Mithi(device="cuda")

LANGUAGES = [
    ("Hindi", "hi"), ("Odia", "or"), ("English", "en"),
    ("Bengali", "bn"), ("Gujarati", "gu"), ("Kannada", "kn"),
    ("Malayalam", "ml"), ("Marathi", "mr"), ("Punjabi", "pa"),
    ("Tamil", "ta"), ("Telugu", "te"),
]
VOICES = [
    ("Satvik — Male", "satvik"), ("Anirban — Male", "anirban"),
    ("Nakul — Male", "nakul"), ("Vasant — Male", "vasant"),
    ("Siddhant — Male", "siddhant"), ("Charvi — Female", "charvi"),
    ("Ahana — Female", "ahana"), ("Vaidehi — Female", "vaidehi"),
    ("Malini — Female", "malini"), ("Jahnavi — Female", "jahnavi"),
]


@spaces.GPU(duration=120)
def generate_speech(text: str, language: str, voice: str):
    clean_text = (text or "").strip()
    if not clean_text:
        raise gr.Error("Please enter some text.")
    if len(clean_text) > 1200:
        raise gr.Error("For this free demo, please keep each request within 1,200 characters.")

    audio = tts.synthesize(clean_text, lang=language, voice=voice)
    fd, output_path = tempfile.mkstemp(prefix="mithi-voice-", suffix=".wav")
    os.close(fd)
    tts.save(audio, output_path)
    return output_path


with gr.Blocks(title="AI Voice Studio Pro — Neural TTS") as demo:
    gr.Markdown(
        "# AI Voice Studio Pro — Neural AI\n"
        "Hindi • Odia • English • 11 Indian languages • 10 voices\n\n"
        "**Free ZeroGPU demo:** shared daily GPU quota applies. This is not unlimited hosting."
    )
    text_input = gr.Textbox(
        label="Text to speak",
        lines=7,
        max_lines=12,
        max_length=1200,
        placeholder="यहाँ हिंदी, ଓଡ଼ିଆ କିମ୍ବା English text लिखें…",
    )
    with gr.Row():
        language_input = gr.Dropdown(
            choices=LANGUAGES, value="hi", label="Language"
        )
        voice_input = gr.Dropdown(
            choices=VOICES, value="ahana", label="Voice"
        )
    generate_button = gr.Button("Generate Neural Voice", variant="primary")
    audio_output = gr.Audio(label="Generated WAV audio", type="filepath")
    generate_button.click(
        fn=generate_speech,
        inputs=[text_input, language_input, voice_input],
        outputs=audio_output,
        api_name="generate",
    )
    gr.Markdown(
        "Model: [Oomni/Mithi v2 Flash](https://huggingface.co/Oomni/mithi-v2-flash) "
        "— Apache-2.0. Audio quality and pronunciation can vary by language."
    )

demo.queue(default_concurrency_limit=1).launch()
