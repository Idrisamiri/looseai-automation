import re
import subprocess
import asyncio
import edge_tts

from script import generate_concept, generate_image


def clean_for_narration(text):
    """Strip hashtags and emoji so the voiceover doesn't read them aloud."""
    text = re.sub(r"#\S+", "", text)
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002600-\U000027BF"
        "\U0001F000-\U0001F2FF"
        "\U00002190-\U000021FF"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def generate_voiceover(text, output_path="voice.mp3"):
    async def _run():
        communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
        await communicate.save(output_path)
    asyncio.run(_run())
    return output_path


def get_audio_duration(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("ffprobe stderr:", result.stderr)
        raise RuntimeError(f"ffprobe failed on {path}")
    return float(result.stdout.strip())


def split_into_chunks(text, n=4):
    words = text.split()
    if not words:
        return [text]
    chunk_size = max(1, len(words) // n)
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    return chunks[:n] if len(chunks) > n else chunks


def format_srt_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def build_subtitle_file(chunks, duration, path="subs.srt"):
    per_chunk = duration / len(chunks)
    with open(path, "w") as f:
        for i, chunk in enumerate(chunks):
            start = i * per_chunk
            end = (i + 1) * per_chunk
            f.write(f"{i + 1}\n{format_srt_time(start)} --> {format_srt_time(end)}\n{chunk}\n\n")
    return path


def build_video(image_path, audio_path, subtitle_path, duration, output_path="reel.mp4"):
    fps = 25
    frames = max(1, int(duration * fps))
    filter_complex = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0015,1.3)':d={frames}:s=1080x1920:fps={fps},"
        f"subtitles={subtitle_path}:force_style="
        f"'FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,BorderStyle=3,Outline=2'"
    )
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        "-t", str(duration),
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg stderr:", result.stderr[-3000:])
        raise RuntimeError("ffmpeg failed")
    return output_path


def main():
    print("Step 1: generating concept...")
    concept = generate_concept()
    print("Concept:", concept)

    print("Step 2: generating image...")
    image_bytes = generate_image(concept["image_prompt"])
    with open("image.png", "wb") as f:
        f.write(image_bytes)
    print("Image saved.")

    print("Step 3: generating voiceover...")
    narration_text = clean_for_narration(concept["caption"])
    print("Narration text:", narration_text)
    generate_voiceover(narration_text, "voice.mp3")
    print("Voiceover saved.")

    duration = get_audio_duration("voice.mp3")
    print("Audio duration:", duration, "seconds")

    print("Step 4: building subtitles...")
    chunks = split_into_chunks(narration_text, n=4)
    build_subtitle_file(chunks, duration, "subs.srt")
    print("Subtitles built:", chunks)

    print("Step 5: rendering video...")
    build_video("image.png", "voice.mp3", "subs.srt", duration, "reel.mp4")
    print("Video created: reel.mp4")


if __name__ == "__main__":
    main()
