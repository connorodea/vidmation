#!/usr/bin/env python3
"""
Mix the voiceover with ambient background music using Python's wave module.

- Converts voiceover MP3 to WAV first (via ffmpeg)
- Reads both WAV files
- Mixes: voice + music at ~5% of voice volume
- Saves as WAV, then converts to AAC via ffmpeg
"""

import wave
import array
import subprocess
import os
import sys

WORK_DIR = "/Users/connorodea/Developer/vidmation/data/work/prod_v2"
VOICEOVER_MP3 = os.path.join(WORK_DIR, "voiceover.mp3")
VOICEOVER_WAV = os.path.join(WORK_DIR, "vo_for_mix.wav")
AMBIENT_WAV = os.path.join(WORK_DIR, "ambient_music.wav")
MIXED_WAV = os.path.join(WORK_DIR, "final_mixed_audio.wav")
MIXED_M4A = os.path.join(WORK_DIR, "final_mixed_audio.m4a")

# Music volume relative to voice (5% = very subtle background)
MUSIC_VOLUME = 0.05

# Step 1: Convert voiceover MP3 to WAV (24kHz mono 16-bit)
print("Step 1: Converting voiceover MP3 to WAV...")
cmd = [
    "ffmpeg", "-y",
    "-i", VOICEOVER_MP3,
    "-ar", "24000",
    "-ac", "1",
    "-c:a", "pcm_s16le",
    VOICEOVER_WAV
]
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print(f"FFmpeg error: {result.stderr}")
    sys.exit(1)
print("  Done.")

# Step 2: Read both WAV files
print("Step 2: Reading WAV files...")

with wave.open(VOICEOVER_WAV, 'r') as vf:
    vo_params = vf.getparams()
    vo_frames = vf.readframes(vf.getnframes())
    vo_nframes = vf.getnframes()
    print(f"  Voiceover: {vo_nframes} frames, {vo_params.framerate}Hz, "
          f"{vo_params.nchannels}ch, {vo_nframes/vo_params.framerate:.1f}s")

with wave.open(AMBIENT_WAV, 'r') as mf:
    mu_params = mf.getparams()
    mu_frames = mf.readframes(mf.getnframes())
    mu_nframes = mf.getnframes()
    print(f"  Music:     {mu_nframes} frames, {mu_params.framerate}Hz, "
          f"{mu_params.nchannels}ch, {mu_nframes/mu_params.framerate:.1f}s")

# Verify both are same format
assert vo_params.framerate == mu_params.framerate, \
    f"Sample rate mismatch: {vo_params.framerate} vs {mu_params.framerate}"
assert vo_params.nchannels == mu_params.nchannels, \
    f"Channel mismatch: {vo_params.nchannels} vs {mu_params.nchannels}"
assert vo_params.sampwidth == mu_params.sampwidth == 2, \
    f"Sample width mismatch (need 16-bit)"

# Step 3: Mix the audio
print("Step 3: Mixing audio...")

# Convert bytes to signed 16-bit arrays
vo_samples = array.array('h')
vo_samples.frombytes(vo_frames)

mu_samples = array.array('h')
mu_samples.frombytes(mu_frames)

# Use voiceover length as the output length
output_len = len(vo_samples)
mixed = array.array('h')

# Calculate RMS of voiceover to set music level relative to it
# Sample a portion to get RMS
sample_count = min(output_len, vo_params.framerate * 60)  # first 60s
rms_sum = 0
nonzero_count = 0
for i in range(sample_count):
    val = vo_samples[i]
    if abs(val) > 100:  # ignore silence
        rms_sum += val * val
        nonzero_count += 1

if nonzero_count > 0:
    vo_rms = (rms_sum / nonzero_count) ** 0.5
else:
    vo_rms = 3000  # fallback

# Calculate music RMS
mu_rms_sum = 0
mu_sample_count = min(len(mu_samples), mu_params.framerate * 60)
for i in range(mu_sample_count):
    mu_rms_sum += mu_samples[i] * mu_samples[i]
mu_rms = (mu_rms_sum / mu_sample_count) ** 0.5 if mu_sample_count > 0 else 1

# Scale music so it's at MUSIC_VOLUME relative to voice
if mu_rms > 0:
    music_scale = (vo_rms * MUSIC_VOLUME) / mu_rms
else:
    music_scale = 0.05

print(f"  Voice RMS: {vo_rms:.1f}")
print(f"  Music RMS: {mu_rms:.1f}")
print(f"  Music scale factor: {music_scale:.4f}")

# Mix
for i in range(output_len):
    vo_val = vo_samples[i]

    # Get music sample (loop if needed, though music is longer)
    if i < len(mu_samples):
        mu_val = mu_samples[i]
    else:
        mu_val = mu_samples[i % len(mu_samples)]

    # Mix
    mixed_val = vo_val + int(mu_val * music_scale)

    # Clip to 16-bit range
    mixed_val = max(-32768, min(32767, mixed_val))
    mixed.append(mixed_val)

    if i % (vo_params.framerate * 60) == 0 and i > 0:
        mins = i / vo_params.framerate / 60
        print(f"  Mixed {mins:.0f} min...")

print(f"  Mixed {output_len / vo_params.framerate:.1f}s of audio.")

# Step 4: Write mixed WAV
print("Step 4: Writing mixed WAV...")
with wave.open(MIXED_WAV, 'w') as wf:
    wf.setnchannels(vo_params.nchannels)
    wf.setsampwidth(vo_params.sampwidth)
    wf.setframerate(vo_params.framerate)
    wf.writeframes(mixed.tobytes())
print(f"  Saved: {MIXED_WAV}")

# Step 5: Convert to AAC
print("Step 5: Converting to AAC (m4a)...")
cmd = [
    "ffmpeg", "-y",
    "-i", MIXED_WAV,
    "-c:a", "aac",
    "-b:a", "192k",
    MIXED_M4A
]
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print(f"FFmpeg error: {result.stderr}")
    sys.exit(1)
print(f"  Saved: {MIXED_M4A}")

# Cleanup temp file
os.remove(VOICEOVER_WAV)
print("\nAll done!")
print(f"  WAV: {MIXED_WAV}")
print(f"  M4A: {MIXED_M4A}")

# Show file sizes
wav_size = os.path.getsize(MIXED_WAV) / (1024 * 1024)
m4a_size = os.path.getsize(MIXED_M4A) / (1024 * 1024)
print(f"  WAV size: {wav_size:.1f} MB")
print(f"  M4A size: {m4a_size:.1f} MB")
