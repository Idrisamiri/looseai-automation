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
        ],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def generate_image(prompt):
    from huggingface_hub import InferenceClient
    import io

    client = InferenceClient(api_key=HF_API_KEY)
    image = client.text_to_image(prompt, model="black-forest-labs/FLUX.1-schnell")

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
    

def upload_to_imgbb(image_bytes):
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": base64.b64encode(image_bytes).decode("utf-8"),
    }
    resp = requests.post(url, data=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["data"]["url"]


def post_to_instagram(image_url, caption):
    create_url = f"https://graph.instagram.com/v21.0/{IG_USER_ID}/media"
    create_params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN,
    }
    resp = requests.post(create_url, params=create_params, timeout=60)
    resp.raise_for_status()
    creation_id = resp.json()["id"]

    publish_url = f"https://graph.instagram.com/v21.0/{IG_USER_ID}/media_publish"
    publish_params = {
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN,
    }
    resp2 = requests.post(publish_url, params=publish_params, timeout=60)
    resp2.raise_for_status()
    return resp2.json()


def main():
    print("Step 1: generating concept...")
    concept = generate_concept()
    print("Concept:", concept)

    print("Step 2: generating image...")
    image_bytes = generate_image(concept["image_prompt"])
    print("Image generated, size:", len(image_bytes), "bytes")

    print("Step 3: uploading to ImgBB...")
    image_url = upload_to_imgbb(image_bytes)
    print("Hosted at:", image_url)

    print("Step 4: posting to Instagram...")
    result = post_to_instagram(image_url, concept["caption"])
    print("Posted successfully:", result)


if __name__ == "__main__":
    main()
