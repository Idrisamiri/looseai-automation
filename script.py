import os
import json
import time
import base64
import requests

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
HF_API_KEY = os.environ["HF_API_KEY"]
IMGBB_API_KEY = os.environ["IMGBB_API_KEY"]
IG_ACCESS_TOKEN = os.environ["IG_ACCESS_TOKEN"]
IG_USER_ID = os.environ["IG_USER_ID"]


def generate_concept():
    """Ask Groq for an image prompt + caption."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Generate a random, visually striking image concept for an "
                    "Instagram account that posts AI-generated surprises. "
                    "Respond ONLY with valid JSON in this exact format: "
                    '{"image_prompt": "a detailed visual description for an AI image generator", '
                    '"caption": "a short engaging Instagram caption with 2-3 relevant emojis"}'
                ),
            }
