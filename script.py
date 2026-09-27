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



MASCOT_DESCRIPTION = (
    "a friendly metallic silver robot mascot with a boxy head, glowing blue "
    "square eyes, small antennas, articulated silver arms and hands, standing "
    "against a solid bright red background"
)




def get_random_recent_comment():
    """Fetch a real comment from a recent post, excluding the bot's own replies."""
    media_url = f"https://graph.instagram.com/v21.0/{IG_USER_ID}/media"
    media_resp = requests.get(
        media_url,
        params={"fields": "id", "limit": 5, "access_token": IG_ACCESS_TOKEN},
        timeout=30,
    )
    media_resp.raise_for_status()
    media_items = media_resp.json().get("data", [])

    real_comments = []
    for item in media_items:
        media_id = item["id"]
        comments_url = f"https://graph.instagram.com/v21.0/{media_id}/comments"
        comments_resp = requests.get(
            comments_url,
            params={"fields": "text,username", "access_token": IG_ACCESS_TOKEN},
            timeout=30,
        )
        if comments_resp.status_code != 200:
            continue
        for c in comments_resp.json().get("data", []):
            if c.get("username") != "looseai.feed" and c.get("text"):
                real_comments.append(c)

    if not real_comments:
        return None
    return random.choice(real_comments)





def load_topics():
    with open("topics.json", "r") as f:
        return json.load(f)





def generate_concept():
    topics = load_topics()
    chosen = random.choice(topics)
    topic_name = chosen["topic"]
    topic_type = chosen["type"]

    spotlight_context = ""
    spotlight_username = None

    if topic_name == "Commenter Spotlight":
        comment = get_random_recent_comment()
        if comment:
            spotlight_username = comment["username"]
            spotlight_context = (
                f"\n\nThis is a 'Commenter Spotlight' post. A real follower, "
                f"@{spotlight_username}, left this comment: \"{comment['text']}\". "
                f"The image must show {MASCOT_DESCRIPTION}, standing NEXT TO an "
                "imagined character that represents this commenter, invented "
                "based on the vibe, tone, or content of their comment. Make the "
                "imagined character fun, flattering, or whimsical — never mocking "
                "or embarrassing. The two characters (mascot + imagined commenter) "
                "should look like they're interacting or posing together. "
                f"The caption MUST include the exact text \"@{spotlight_username}\" "
                "to tag them, thank them for the comment, and briefly explain how "
                "the AI imagined them based on what they said."
            )
        else:
            fallback = [t for t in topics if t["topic"] != "Commenter Spotlight"]
            chosen = random.choice(fallback)
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
                    f"Today's content theme is: \"{topic_name}\" (category: {topic_type})."
                    f"{spotlight_context}"
                    "Generate a visually striking image concept AND a caption that actually "
                    "delivers the theme's content, not just a vague tagline. Stay strictly "
                    "on-topic. The image_prompt must NOT include any text, words, speech "
                    "bubbles, signs, or writing of any kind — describe the scene purely "
                    "visually. The caption must be 2-4 short sentences, under 220 characters, "
                    "and end with 2-3 emojis and up to 2 hashtags. "
                    "Respond ONLY with valid JSON in this exact format: "
                    '{"image_prompt": "a detailed visual description with NO text or writing '
                    'elements", "caption": "a short, substantive, on-topic caption ending with '
                    'emojis and hashtags"}'
                ),
            }
        ],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]

# Strip markdown code fences if the model wrapped its JSON in them
content = content.strip()
if content.startswith("```"):
    content = content.split("```")[1]
    if content.startswith("json"):
        content = content[4:]
    content = content.strip()

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

    resp = None
    for attempt in range(3):
        resp = requests.post(create_url, params=create_params, timeout=60)
        if resp.status_code == 200:
            break
        print(f"Attempt {attempt + 1}: Instagram error response: {resp.text}")
        time.sleep(10)

    resp.raise_for_status()
    creation_id = resp.json()["id"]

    # ... the rest of the function (status check + publish) stays exactly the same
    

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
