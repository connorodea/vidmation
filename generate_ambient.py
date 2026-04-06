#!/usr/bin/env python3
"""
Generate a rich ambient meditation soundtrack using wave synthesis.

Layers:
  - C2 (65.41 Hz) — deep bass
  - C3 (130.81 Hz) — root
  - G3 (196 Hz) — fifth
  - C4 (261.63 Hz) — octave
  - E4 (329.63 Hz) — major third

Plus detuned doubles (+1-2 Hz) for a lush chorus effect,
slow tremolo modulation, and fade in/out.
"""

import struct
import wave
import math
import array
import sys

SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit
DURATION = 870  # seconds (854s voiceover + 16s buffer)
FADE_IN = 5.0   # seconds
FADE_OUT = 5.0  # seconds

# Frequencies and amplitudes for the main pad
VOICES = [
    # (freq_hz, amplitude, detune_hz)
    # Main voices
    (65.41,  0.15, 0.0),   # C2 deep bass
    (130.81, 0.25, 0.0),   # C3 root
    (196.00, 0.18, 0.0),   # G3 fifth
    (261.63, 0.12, 0.0),   # C4 octave
    (329.63, 0.08, 0.0),   # E4 major third
    # Detuned chorus voices
    (65.41 + 0.7,  0.10, 0.0),  # C2 detuned
    (130.81 + 1.2, 0.18, 0.0),  # C3 detuned
    (196.00 + 1.5, 0.12, 0.0),  # G3 detuned
    (261.63 + 1.8, 0.08, 0.0),  # C4 detuned
    (329.63 + 2.0, 0.05, 0.0),  # E4 detuned
    # Sub-bass layer (very low, adds warmth)
    (32.70,  0.08, 0.0),   # C1
]

# Tremolo / breathing modulation
TREMOLO_RATE = 0.05    # Hz (one cycle every 20 seconds)
TREMOLO_DEPTH = 0.30   # 30% volume modulation

# Second slow modulation for organic feel
MOD2_RATE = 0.017      # Hz (~59 second cycle)
MOD2_DEPTH = 0.15

total_samples = SAMPLE_RATE * DURATION
fade_in_samples = int(FADE_IN * SAMPLE_RATE)
fade_out_samples = int(FADE_OUT * SAMPLE_RATE)

print(f"Generating {DURATION}s ambient track at {SAMPLE_RATE}Hz...")
print(f"Total samples: {total_samples:,}")
print(f"Voices: {len(VOICES)}")

# Pre-compute angular frequencies
voice_params = []
for freq, amp, _ in VOICES:
    voice_params.append((2.0 * math.pi * freq / SAMPLE_RATE, amp))

tremolo_omega = 2.0 * math.pi * TREMOLO_RATE / SAMPLE_RATE
mod2_omega = 2.0 * math.pi * MOD2_RATE / SAMPLE_RATE

# Generate in chunks to show progress
CHUNK_SIZE = SAMPLE_RATE * 10  # 10 seconds at a time
samples = array.array('h')  # signed 16-bit

for chunk_start in range(0, total_samples, CHUNK_SIZE):
    chunk_end = min(chunk_start + CHUNK_SIZE, total_samples)

    progress = chunk_start / total_samples * 100
    if chunk_start % (SAMPLE_RATE * 60) < CHUNK_SIZE:
        elapsed_min = chunk_start / SAMPLE_RATE / 60
        print(f"  {progress:5.1f}% ({elapsed_min:.0f} min / {DURATION/60:.0f} min)")

    for i in range(chunk_start, chunk_end):
        # Sum all voices
        sample = 0.0
        for omega, amp in voice_params:
            sample += amp * math.sin(omega * i)

        # Apply tremolo modulation (slow breathing)
        tremolo = 1.0 - TREMOLO_DEPTH * 0.5 * (1.0 + math.sin(tremolo_omega * i))
        mod2 = 1.0 - MOD2_DEPTH * 0.5 * (1.0 + math.sin(mod2_omega * i + 1.3))
        sample *= tremolo * mod2

        # Apply fade in
        if i < fade_in_samples:
            sample *= i / fade_in_samples

        # Apply fade out
        fade_out_start = total_samples - fade_out_samples
        if i >= fade_out_start:
            sample *= (total_samples - i) / fade_out_samples

        # Scale to prevent clipping — overall volume control
        sample *= 0.06

        # Convert to 16-bit integer
        val = int(sample * 32767)
        val = max(-32768, min(32767, val))
        samples.append(val)

print("  100.0% — Writing WAV file...")

output_path = "/Users/connorodea/Developer/vidmation/data/work/prod_v2/ambient_music.wav"
with wave.open(output_path, 'w') as wf:
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(SAMPLE_WIDTH)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(samples.tobytes())

print(f"Done! Saved to {output_path}")
print(f"Duration: {DURATION}s ({DURATION/60:.1f} min)")
file_size_mb = len(samples) * 2 / (1024 * 1024)
print(f"File size: {file_size_mb:.1f} MB")
