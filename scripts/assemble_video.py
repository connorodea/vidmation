#!/usr/bin/env python3
"""Production video assembler — creates a real 8-10 min faceless YouTube video.

Usage: cd ~/Developer/aividio && python3 scripts/assemble_video.py
"""
import json, subprocess, math, os, sys, time, shutil
from pathlib import Path

TOPIC = "5 Signs You Are Experiencing a Spiritual Awakening"
TARGET_MINUTES = 8
WORK = Path("data/work/production")
OUTPUT = Path("output/spiritual_awakening_production.mp4")
PEXELS_KEY = os.environ.get("VIDMATION_PEXELS_API_KEY", "")
FPS = 30
MUSIC_VOL = 0.12
WORK.mkdir(parents=True, exist_ok=True)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

def run(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

def dur(p):
    r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",str(p)], capture_output=True, text=True)
    return float(r.stdout.strip()) if r.stdout.strip() else 0

def srt_ts(t):
    return f"{int(t//3600):02d}:{int((t%3600)//60):02d}:{int(t%60):02d},{int((t%1)*1000):03d}"

print("="*60)
print("  VIDMATION Production Pipeline")
print("="*60)
t0 = time.time()

# ── 1: EXPANDED SCRIPT ──
print(f"\n[1/9] Generating {TARGET_MINUTES}-min script (GPT-4o)...")
import openai
oa = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
resp = oa.chat.completions.create(
    model="gpt-4o",
    messages=[{"role":"user","content":f"""Write a YouTube script about "{TOPIC}". 
Return ONLY valid JSON: {{"title":"...","hook":"opening hook ~40 words","sections":[{{"section_number":1,"heading":"...","narration":"~300 words of narration","visual_query":"stock footage search","estimated_duration_seconds":120}}],"outro":"closing CTA ~75 words","tags":["..."],"total_estimated_duration_seconds":600}}
Create 5 sections, each ~300 words. Total ~{TARGET_MINUTES} minutes. Conversational, engaging tone with rhetorical questions and specific examples."""}],
    response_format={"type":"json_object"}, max_tokens=8000)
script = json.loads(resp.choices[0].message.content)
json.dump(script, open(WORK/"script.json","w"), indent=2)
tw = sum(len(s["narration"].split()) for s in script["sections"]) + len(script.get("hook","").split()) + len(script.get("outro","").split())
print(f"  {script['title']} | {len(script['sections'])} sections | ~{tw} words | ~{tw/2.5/60:.1f}min")

# ── 2: VOICEOVER ──
print(f"\n[2/9] Generating voiceover (TTS-HD, onyx)...")
narr = script.get("hook","") + "\n\n"
for s in script["sections"]: narr += s["narration"] + "\n\n"
narr += script.get("outro","")
chunks, cur = [], ""
for p in narr.split("\n\n"):
    if len(cur)+len(p) > 4000 and cur: chunks.append(cur.strip()); cur = p
    else: cur += "\n\n"+p if cur else p
if cur.strip(): chunks.append(cur.strip())
parts = []
for i,ch in enumerate(chunks):
    pp = WORK/f"vo_{i}.mp3"
    print(f"  Part {i+1}/{len(chunks)} ({len(ch)} chars)...")
    r = oa.audio.speech.create(model="tts-1-hd", voice="onyx", input=ch, response_format="mp3")
    r.stream_to_file(str(pp)); parts.append(pp)
vo = WORK/"voiceover.mp3"
if len(parts)==1: shutil.copy(parts[0],vo)
else:
    cf = WORK/"vo_cat.txt"
    with open(cf,"w") as f:
        for p in parts: f.write(f"file '{p.resolve()}'\n")
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(cf),"-c:a","copy",str(vo)])
vd = dur(vo)
print(f"  Voiceover: {vd:.1f}s ({vd/60:.1f}min)")

# ── 3: TRANSCRIBE ──
print(f"\n[3/9] Transcribing (faster-whisper)...")
from faster_whisper import WhisperModel
mdl = WhisperModel("base", device="cpu", compute_type="int8")
segs, info = mdl.transcribe(str(vo), word_timestamps=True)
words = []
for sg in segs:
    if sg.words:
        for w in sg.words: words.append({"word":w.word.strip(),"start":round(w.start,3),"end":round(w.end,3)})
json.dump(words, open(WORK/"words.json","w"), indent=2)
print(f"  {len(words)} words, {words[-1]['end']:.1f}s")

# ── 4: SECTION TIMINGS ──
print(f"\n[4/9] Mapping sections to timing...")
secs = script["sections"]
hook_wc = len(script.get("hook","").split())
outro_wc = len(script.get("outro","").split())
timings, wi = [], 0
# Hook
hr = hook_wc/tw; hei = int(hr*len(words))
timings.append({"heading":"Introduction","num":0,"start":0,"end":words[min(hei,len(words)-1)]["end"],"type":"hook","vq":"spiritual peaceful meditation nature"})
timings[0]["duration"] = timings[0]["end"]
wi = hei
# Sections
sec_tw = tw - hook_wc - outro_wc
for i,s in enumerate(secs):
    swc = len(s["narration"].split())
    r = swc/sec_tw if sec_tw else 0.2
    wc = int(r*(len(words)-hei-int(outro_wc/tw*len(words))))
    if i==len(secs)-1: wc = len(words)-wi-int(outro_wc/tw*len(words))
    wc = max(wc,10); sw = words[wi:wi+wc]
    if sw:
        timings.append({"heading":s["heading"],"num":i+1,"start":sw[0]["start"],"end":sw[-1]["end"],
                        "duration":sw[-1]["end"]-sw[0]["start"],"type":"section","vq":s.get("visual_query",s["heading"])})
    wi += wc
# Outro
if wi < len(words):
    timings.append({"heading":"Thank You","num":len(secs)+1,"start":words[wi]["start"],"end":words[-1]["end"],
                    "duration":words[-1]["end"]-words[wi]["start"],"type":"outro","vq":"sunset peaceful gratitude nature"})
for t in timings: print(f"  [{t['start']:.0f}s-{t['end']:.0f}s] {t['heading']} ({t['duration']:.0f}s)")

# ── 5: STOCK FOOTAGE ──
print(f"\n[5/9] Downloading stock clips (Pexels)...")
import httpx
px = httpx.Client(base_url="https://api.pexels.com", headers={"Authorization":PEXELS_KEY}, timeout=30)
sec_clips = {}
for t in timings:
    q = t["vq"]; idx = t["num"]
    print(f"  S{idx} '{q[:35]}':", end=" ")
    try:
        rv = px.get("/videos/search", params={"query":q,"per_page":6,"orientation":"landscape"})
        vids = rv.json().get("videos",[]) if rv.status_code==200 else []
    except: vids = []
    dl = []
    for v in vids:
        if len(dl)>=3: break
        fs = v.get("video_files",[]); hd = [f for f in fs if f.get("width",0)>=1280] or fs
        if not hd: continue
        best = min(hd, key=lambda f: abs(f.get("width",0)-1920)); url = best.get("link","")
        if not url: continue
        cp = WORK/f"stock_{idx}_{len(dl)}.mp4"
        try:
            with httpx.stream("GET",url,timeout=60,follow_redirects=True) as r:
                r.raise_for_status()
                with open(cp,"wb") as f:
                    for c in r.iter_bytes(8192): f.write(c)
            sz = cp.stat().st_size/(1024*1024)
            if sz > 40: cp.unlink(); continue
            dl.append(cp)
        except: 
            if cp.exists(): cp.unlink()
    sec_clips[idx] = dl
    print(f"{len(dl)} clips")
print(f"  Total: {sum(len(v) for v in sec_clips.values())} clips")

# ── 6: COLOR GRADE + TRIM ──
print(f"\n[6/9] Color grading + trimming...")
sec_segs = {}
for t in timings:
    idx = t["num"]; clips = sec_clips.get(idx,[])
    if not clips: continue
    d = t["duration"]; pc = d/len(clips)
    graded = []
    for ci,clip in enumerate(clips):
        dst = WORK/f"g_{idx}_{ci}.mp4"; sd = dur(clip)
        td = min(pc+0.5, sd) if sd>0 else pc; loops = max(0,math.ceil(pc/sd)-1) if sd>0 else 0
        cmd = ["ffmpeg","-y"]
        if loops>0: cmd += ["-stream_loop",str(loops)]
        cmd += ["-i",str(clip),"-t",str(td),"-vf",
            f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black,setsar=1,fps={FPS},"
            "eq=contrast=1.04:brightness=0.005:saturation=1.08:gamma=0.97,vignette=PI/6",
            "-c:v","libx264","-preset","fast","-crf","20","-an",str(dst)]
        r = run(cmd, timeout=120)
        if r.returncode==0: graded.append(dst)
    sec_segs[idx] = graded
    print(f"  S{idx}: {len(graded)} clips ({d:.0f}s)")

# ── 7: TITLE CARDS ──
print(f"\n[7/9] Creating title cards...")
titles = {}
for t in timings:
    if t["type"]=="outro": continue
    idx = t["num"]; png = WORK/f"t_{idx}.png"; vid = WORK/f"tv_{idx}.mp4"
    h = t["heading"]
    if t["type"]=="hook":
        run(["magick","-size","1920x1080","xc:#0a0a0a","-font","Helvetica-Bold","-pointsize","64","-fill","white",
             "-gravity","center","-annotate","+0-20",script["title"],"-font","Helvetica","-pointsize","26",
             "-fill","#10a37f","-gravity","center","-annotate","+0+50","A Journey of Self-Discovery",str(png)],timeout=10)
    else:
        run(["magick","-size","1920x1080","xc:#0a0a0a","-font","Helvetica","-pointsize","22","-fill","#10a37f",
             "-gravity","center","-annotate","+0-50",f"SECTION {idx}","-font","Helvetica-Bold","-pointsize","56",
             "-fill","white","-gravity","center","-annotate","+0+5",h,"-stroke","#10a37f","-strokewidth","2",
             "-draw","line 860,575 1060,575",str(png)],timeout=10)
    if png.exists():
        r = run(["ffmpeg","-y","-loop","1","-i",str(png),"-t","2.5","-vf",f"fps={FPS},format=yuv420p",
                 "-c:v","libx264","-preset","fast","-crf","18","-an",str(vid)],timeout=10)
        if r.returncode==0: titles[idx] = vid; print(f"  T{idx}: {h}")

# Outro card
op = WORK/"outro.png"; ov = WORK/"outro.mp4"
run(["magick","-size","1920x1080","xc:#0a0a0a","-font","Helvetica-Bold","-pointsize","48","-fill","white",
     "-gravity","center","-annotate","+0-30","Thank You for Watching","-font","Helvetica","-pointsize","26",
     "-fill","#10a37f","-gravity","center","-annotate","+0+30","Subscribe for more",str(op)],timeout=10)
if op.exists():
    run(["ffmpeg","-y","-loop","1","-i",str(op),"-t","4","-vf",f"fps={FPS},format=yuv420p",
         "-c:v","libx264","-preset","fast","-crf","18","-an",str(ov)],timeout=10)

# ── 8: MUSIC ──
print(f"\n[8/9] Generating ambient music...")
mp = WORK/"music.mp3"; md = vd+5
run(["ffmpeg","-y","-f","lavfi","-i",f"sine=f=174:d={md}:sample_rate=44100,volume=0.3,aecho=0.8:0.88:60:0.4",
     "-f","lavfi","-i",f"sine=f=261:d={md}:sample_rate=44100,volume=0.2,aecho=0.8:0.9:40:0.3",
     "-f","lavfi","-i",f"sine=f=329:d={md}:sample_rate=44100,volume=0.15,aecho=0.8:0.85:80:0.35",
     "-filter_complex",f"[0:a][1:a][2:a]amix=inputs=3:duration=first:dropout_transition=3,volume={MUSIC_VOL},"
     f"afade=t=in:st=0:d=3,afade=t=out:st={md-4}:d=4[a]","-map","[a]","-c:a","aac","-b:a","128k",str(mp)],timeout=30)
print(f"  Music: {dur(mp):.0f}s ambient pad")

# ── 9: FINAL ASSEMBLY ──
print(f"\n[9/9] Final assembly...")
seq = []
for t in timings:
    idx = t["num"]
    if idx in titles: seq.append(titles[idx])
    for c in sec_segs.get(idx,[]): seq.append(c)
if ov.exists(): seq.append(ov)
print(f"  Joining {len(seq)} clips...")

cf = WORK/"final.txt"
with open(cf,"w") as f:
    for c in seq: f.write(f"file '{c.resolve()}'\n")
jn = WORK/"joined.mp4"
run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(cf),"-c:v","libx264","-preset","fast","-crf","20","-an",str(jn)],timeout=300)

# SRT captions
sp = WORK/"caps.srt"
with open(sp,"w") as f:
    ci = 1
    for j in range(0,len(words),3):
        ch = words[j:j+3]
        if not ch: break
        f.write(f"{ci}\n{srt_ts(ch[0]['start'])} --> {srt_ts(ch[-1]['end'])}\n{' '.join(w['word'] for w in ch)}\n\n")
        ci += 1

# Mix audio
mx = WORK/"mix.mp3"
run(["ffmpeg","-y","-i",str(vo),"-i",str(mp),"-filter_complex",
     f"[0:a]volume=1.0[v];[1:a]volume={MUSIC_VOL}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=3[a]",
     "-map","[a]","-c:a","aac","-b:a","192k",str(mx)],timeout=60)

# Final mux
run(["ffmpeg","-y","-i",str(jn),"-i",str(mx),"-i",str(sp),"-map","0:v","-map","1:a","-map","2:0",
     "-c:v","copy","-c:a","aac","-b:a","192k","-c:s","mov_text","-metadata:s:s:0","language=eng",
     "-shortest","-movflags","+faststart",str(OUTPUT)],timeout=120)

if OUTPUT.exists():
    sz = OUTPUT.stat().st_size/(1024*1024); d = dur(OUTPUT); el = time.time()-t0
    print(f"\n{'='*60}")
    print(f"  PRODUCTION VIDEO COMPLETE")
    print(f"{'='*60}")
    print(f"  File:     {OUTPUT}")
    print(f"  Size:     {sz:.1f} MB")
    print(f"  Duration: {d:.1f}s ({d/60:.1f} min)")
    print(f"  Time:     {el:.0f}s ({el/60:.1f} min)")
    print(f"  open {OUTPUT}")
else:
    print("  FAILED!")
