import os
import json
import time
import base64
import requests
import random


GROQ_API_KEY = os.environ["GROQ_API_KEY"]
HF_API_KEY = os.environ["HF_API_KEY"]
IMGBB_API_KEY = os.environ["IMGBB_API_KEY"]
IG_ACCESS_TOKEN = os.environ["IG_ACCESS_TOKEN"]
IG_USER_ID = os.environ["IG_USER_ID"]


def load_topics():
    with open("topics.json", "r") as f:
        return json.load(f)





def generate_concept():
    topics = load_topics()
    chosen = random.choice(topics)
    topic_name = chosen["topic"]
    topic_type = chosen["type"]

    print(f"Chosen topic: {topic_name} ({topic_type})")

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
                    f"Today's content theme is: \"{topic_name}\" (category: {topic_type}). "
                    "Generate a visually striking image concept AND a caption that actually "
                    "delivers the theme's content, not just a vague tagline. Examples: if the "
                    "theme is a joke, the caption must contain an actual joke with a punchline. "
                    "If it's a mini-story or myth, the caption must tell a short story with a "
                    "clear beginning and ending, not just mood-setting. If it's a fact, state the "
                    "actual fact. If it's a question ('What if...'), pose the specific question "
                    "itself. Stay strictly on-topic for the theme given — do not drift into an "
                    "unrelated idea. The caption must be 2-4 short sentences MAXIMUM, under 200 "
                    "characters total (not counting hashtags), substantive rather than a poetic "
                    "tagline, and end with 2-3 relevant emojis and up to 2 hashtags. "
                    "Respond ONLY with valid JSON in this exact format: "
                    '{"image_prompt": "a detailed visual description for an AI image generator", '
                    '"caption": "a short, substantive, on-topic caption ending with emojis and '
                    'hashtags"}'
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

    # Wait for the container to finish processing before publishing
    status_url = f"https://graph.instagram.com/v21.0/{creation_id}"
    for attempt in range(10):
        status_resp = requests.get(
            status_url,
            params={"fields": "status_code", "access_token": IG_ACCESS_TOKEN},
            timeout=30,
        )
        status_resp.raise_for_status()
        status = status_resp.json().get("status_code")
        print(f"Container status check {attempt + 1}: {status}")
        if status == "FINISHED":
            break
        time.sleep(5)
    else:
        raise RuntimeError(f"Container never finished processing, last status: {status}")

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
