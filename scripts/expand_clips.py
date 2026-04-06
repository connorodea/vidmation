#!/usr/bin/env python3
"""
Expand video clips for prod_v2: download 5 Pexels clips + 2 DALL-E images per section.
Converts DALL-E images to Ken Burns video clips. Color grades everything.
"""

import httpx
import openai
import subprocess
import json
import os
import sys
import time
from pathlib import Path

WORK_DIR = Path(os.path.expanduser("~/Developer/vidmation/data/work/prod_v2"))
PEXELS_API_KEY = "NG80u2LYLNnqpbCBDSWFTDGHtb3f61iwsgPqwIwQXRUDMAwo8dKSBIxH"
MAX_FILE_SIZE_MB = 30

# 7 sections (0=hook, 1-5=main sections, 6=outro)
SECTION_QUERIES = {
    0: {
        "topic": "Spiritual Awakening Introduction",
        "pexels_queries": [
            "cosmic energy universe",
            "sunrise mountain spiritual",
            "person meditating dawn light",
        ],
        "dalle_prompts": [
            "A cinematic wide shot of a person standing on a mountaintop at dawn, golden light breaking through clouds, cosmic energy swirling around them, spiritual awakening concept, photorealistic, dramatic lighting, 16:9 aspect ratio",
            "A cinematic aerial view of a vast cosmic nebula merging with an earthly landscape, symbolizing the connection between human consciousness and the universe, ethereal purple and gold tones, photorealistic",
        ],
    },
    1: {
        "topic": "Heightened Intuition",
        "pexels_queries": [
            "person thinking deeply closeup",
            "glowing light abstract energy",
            "woman eyes closed peaceful concentration",
        ],
        "dalle_prompts": [
            "A cinematic portrait of a person with closed eyes, surrounded by soft ethereal light particles representing intuition and inner knowing, warm golden tones, shallow depth of field, photorealistic, dramatic lighting",
            "A cinematic wide shot of a luminous pathway through a mystical forest at twilight, representing following one's intuition, soft bioluminescent lights guiding the way, photorealistic",
        ],
    },
    2: {
        "topic": "Emotional Sensitivity",
        "pexels_queries": [
            "person emotional tears joy",
            "rain window contemplation",
            "heart compassion empathy hands",
        ],
        "dalle_prompts": [
            "A cinematic close-up of hands gently cradling a glowing orb of light that pulses with different colors representing emotions, warm and cool tones blending together, photorealistic, dramatic studio lighting",
            "A cinematic wide shot of a person sitting by a calm lake at sunset, their reflection showing vibrant emotional energy radiating outward as colorful ripples in the water, photorealistic, golden hour lighting",
        ],
    },
    3: {
        "topic": "Desire for Solitude",
        "pexels_queries": [
            "person alone nature peaceful",
            "quiet forest path solitude",
            "meditation room minimalist calm",
        ],
        "dalle_prompts": [
            "A cinematic wide shot of a solitary figure sitting in peaceful meditation on a quiet beach at dawn, vast empty space around them, soft mist rolling in, conveying beautiful solitude, photorealistic, pastel tones",
            "A cinematic overhead shot of a person reading in a cozy minimalist room with large windows overlooking a snowy forest, warm interior light contrasting with cool exterior, photorealistic",
        ],
    },
    4: {
        "topic": "Questioning Everything",
        "pexels_queries": [
            "person looking up sky wondering",
            "open book philosophy wisdom",
            "question mark abstract concept",
        ],
        "dalle_prompts": [
            "A cinematic shot of a person standing at a crossroads in a surreal landscape where each path leads to a different reality, symbolizing questioning life's direction, dramatic clouds overhead, photorealistic, wide angle",
            "A cinematic close-up of an open ancient book with pages transforming into birds flying away, representing the liberation of questioning old beliefs, warm golden light, photorealistic",
        ],
    },
    5: {
        "topic": "Synchronicities",
        "pexels_queries": [
            "clock time synchronicity numbers",
            "mirror reflection symmetry",
            "butterfly transformation nature sign",
        ],
        "dalle_prompts": [
            "A cinematic wide shot of repeating number patterns (11:11) appearing subtly in a dreamlike cityscape at night, neon reflections on wet streets, symbolizing synchronicity, photorealistic, moody lighting",
            "A cinematic shot of two puzzle pieces floating in cosmic space about to connect, surrounded by stars and sacred geometry patterns, representing meaningful coincidences, photorealistic, deep blue and gold tones",
        ],
    },
    6: {
        "topic": "Spiritual Journey Outro",
        "pexels_queries": [
            "peaceful sunset silhouette gratitude",
            "lotus flower blooming water",
            "starry night sky cosmic wonder",
        ],
        "dalle_prompts": [
            "A cinematic wide shot of a person with arms outstretched on a cliff edge at golden hour, light radiating from their chest outward, symbolizing spiritual growth and gratitude, photorealistic, epic scale",
            "A cinematic overhead shot of a blooming lotus flower in a still pond, each petal glowing with soft inner light, surrounded by floating candles, representing spiritual completion, photorealistic",
        ],
    },
}

COLOR_GRADE = "eq=contrast=1.04:brightness=0.005:saturation=1.08:gamma=0.97,vignette=PI/6"


def download_pexels_clips(section: int, queries: list[str], target_count: int = 5) -> list[Path]:
    """Download clips from Pexels for a section using multiple queries."""
    downloaded = []
    seen_ids = set()
    clips_per_query = max(2, (target_count + len(queries) - 1) // len(queries))

    for query in queries:
        if len(downloaded) >= target_count:
            break

        print(f"  [Pexels] Searching: '{query}'")
        try:
            resp = httpx.get(
                "https://api.pexels.com/videos/search",
                params={
                    "query": query,
                    "per_page": 15,
                    "size": "medium",
                    "orientation": "landscape",
                },
                headers={"Authorization": PEXELS_API_KEY},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"    ERROR searching '{query}': {e}")
            continue

        videos = data.get("videos", [])
        print(f"    Found {len(videos)} results")

        for video in videos:
            if len(downloaded) >= target_count:
                break

            vid_id = video["id"]
            if vid_id in seen_ids:
                continue
            seen_ids.add(vid_id)

            # Find the best HD file
            best_file = None
            for vf in video.get("video_files", []):
                w = vf.get("width", 0)
                h = vf.get("height", 0)
                if w >= 1280 and h >= 720 and vf.get("link"):
                    # Prefer 1080p but accept 720p+
                    if best_file is None or (w <= 1920 and w > best_file.get("width", 0)):
                        best_file = vf
                    elif best_file.get("width", 0) > 1920 and w <= 1920:
                        best_file = vf

            if not best_file:
                # Fallback: take any file with a link
                for vf in video.get("video_files", []):
                    if vf.get("link") and vf.get("width", 0) >= 640:
                        best_file = vf
                        break

            if not best_file:
                continue

            download_url = best_file["link"]
            idx = len(downloaded)
            raw_path = WORK_DIR / f"raw_extra_{section}_{idx}.mp4"

            print(f"    Downloading video {vid_id} ({best_file.get('width')}x{best_file.get('height')})...")
            try:
                with httpx.stream("GET", download_url, timeout=60, follow_redirects=True) as stream:
                    stream.raise_for_status()
                    # Check content-length
                    cl = stream.headers.get("content-length")
                    if cl and int(cl) > MAX_FILE_SIZE_MB * 1024 * 1024:
                        print(f"    Skipping (too large: {int(cl)/(1024*1024):.1f}MB)")
                        continue

                    total = 0
                    with open(raw_path, "wb") as f:
                        for chunk in stream.iter_bytes(chunk_size=65536):
                            total += len(chunk)
                            if total > MAX_FILE_SIZE_MB * 1024 * 1024:
                                print(f"    Skipping (exceeded {MAX_FILE_SIZE_MB}MB during download)")
                                break
                            f.write(chunk)
                        else:
                            # Completed successfully
                            downloaded.append(raw_path)
                            print(f"    Saved: {raw_path.name} ({total/(1024*1024):.1f}MB)")
                            continue

                    # If we broke out of the loop, remove partial file
                    raw_path.unlink(missing_ok=True)

            except Exception as e:
                print(f"    ERROR downloading {vid_id}: {e}")
                raw_path.unlink(missing_ok=True)

    return downloaded


def generate_dalle_images(section: int, prompts: list[str]) -> list[Path]:
    """Generate DALL-E images for a section."""
    client = openai.OpenAI()
    images = []

    for i, prompt in enumerate(prompts):
        img_path = WORK_DIR / f"dalle_{section}_{i}.png"
        print(f"  [DALL-E] Generating image {i} for section {section}...")
        print(f"    Prompt: {prompt[:80]}...")

        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            print(f"    Downloading generated image...")

            img_resp = httpx.get(image_url, timeout=60, follow_redirects=True)
            img_resp.raise_for_status()
            with open(img_path, "wb") as f:
                f.write(img_resp.content)
            images.append(img_path)
            print(f"    Saved: {img_path.name} ({len(img_resp.content)/(1024*1024):.1f}MB)")
        except Exception as e:
            print(f"    ERROR generating DALL-E image: {e}")

    return images


def image_to_ken_burns(img_path: Path, output_path: Path, duration: int = 8) -> bool:
    """Convert an image to a Ken Burns effect video clip."""
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
        "-t", str(duration),
        "-vf", (
            "scale=2112:1188,crop=1920:1080:"
            "'96+sin(t*0.2)*96':'54+cos(t*0.15)*54',"
            "setsar=1,fps=30"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"    Ken Burns: {output_path.name}")
            return True
        else:
            print(f"    ERROR Ken Burns: {result.stderr[-200:]}")
            return False
    except Exception as e:
        print(f"    ERROR Ken Burns: {e}")
        return False


def normalize_clip(input_path: Path, output_path: Path) -> bool:
    """Normalize a Pexels clip to 1920x1080@30fps."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-an",  # strip audio
        "-t", "20",  # cap at 20 seconds
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True
        else:
            print(f"    ERROR normalizing: {result.stderr[-200:]}")
            return False
    except Exception as e:
        print(f"    ERROR normalizing: {e}")
        return False


def color_grade(input_path: Path, output_path: Path) -> bool:
    """Apply color grading filter."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf", COLOR_GRADE,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-an",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True
        else:
            print(f"    ERROR grading: {result.stderr[-200:]}")
            return False
    except Exception as e:
        print(f"    ERROR grading: {e}")
        return False


def main():
    os.makedirs(WORK_DIR, exist_ok=True)

    total_pexels = 0
    total_dalle = 0
    total_final = 0

    for section in range(7):
        info = SECTION_QUERIES[section]
        print(f"\n{'='*60}")
        print(f"SECTION {section}: {info['topic']}")
        print(f"{'='*60}")

        # --- Pexels Downloads ---
        print(f"\n--- Downloading Pexels clips ---")
        raw_clips = download_pexels_clips(section, info["pexels_queries"], target_count=5)
        total_pexels += len(raw_clips)

        # Normalize and color grade Pexels clips
        pexels_graded = []
        for raw_path in raw_clips:
            idx = raw_path.stem.split("_")[-1]  # get the index
            norm_path = WORK_DIR / f"norm_extra_{section}_{idx}.mp4"
            final_path = WORK_DIR / f"extra_{section}_{idx}.mp4"

            print(f"  Normalizing {raw_path.name}...")
            if normalize_clip(raw_path, norm_path):
                print(f"  Color grading -> {final_path.name}...")
                if color_grade(norm_path, final_path):
                    pexels_graded.append(final_path)
                    total_final += 1
                norm_path.unlink(missing_ok=True)
            raw_path.unlink(missing_ok=True)

        print(f"  Pexels clips for section {section}: {len(pexels_graded)}")

        # --- DALL-E Images ---
        print(f"\n--- Generating DALL-E images ---")
        dalle_images = generate_dalle_images(section, info["dalle_prompts"])
        total_dalle += len(dalle_images)

        # Convert DALL-E images to Ken Burns video then color grade
        dalle_graded = []
        for img_path in dalle_images:
            idx = img_path.stem.split("_")[-1]
            kb_path = WORK_DIR / f"kb_dalle_{section}_{idx}.mp4"
            # Final naming: continue index after pexels clips
            final_idx = len(pexels_graded) + len(dalle_graded)
            final_path = WORK_DIR / f"extra_{section}_{final_idx}.mp4"

            print(f"  Ken Burns: {img_path.name} -> {kb_path.name}")
            if image_to_ken_burns(img_path, kb_path):
                print(f"  Color grading -> {final_path.name}...")
                if color_grade(kb_path, final_path):
                    dalle_graded.append(final_path)
                    total_final += 1
                kb_path.unlink(missing_ok=True)

        print(f"  DALL-E clips for section {section}: {len(dalle_graded)}")
        print(f"  Total extra clips for section {section}: {len(pexels_graded) + len(dalle_graded)}")

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Pexels clips downloaded: {total_pexels}")
    print(f"DALL-E images generated: {total_dalle}")
    print(f"Total new graded clips:  {total_final}")
    print(f"\nExisting clips per section: 3 (g_X_0 through g_X_2)")
    print(f"New clips per section: ~7 (extra_X_0 through extra_X_6)")
    print(f"Total clips per section: ~10")

    # List all final extra clips
    extras = sorted(WORK_DIR.glob("extra_*.mp4"))
    print(f"\nFinal extra clips ({len(extras)}):")
    for e in extras:
        size_mb = e.stat().st_size / (1024 * 1024)
        print(f"  {e.name}  ({size_mb:.1f}MB)")


if __name__ == "__main__":
    main()
