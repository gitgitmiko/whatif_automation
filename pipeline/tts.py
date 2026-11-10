"""Step 4: narration.mp3 and narration.srt. The voice is Gemini TTS (Charon), read a few scenes per request so the
telling flows; faster-whisper then times every word, which gives the scene times and the captions. If Gemini cannot
be used (no key, quota, a bad take that will not go away), the whole narration falls back to edge-tts."""
import asyncio, base64, re, sys, urllib.error, urllib.request, wave
import edge_tts
import numpy as np
from common import *

VOICE, RATE = "id-ID-ArdiNeural", "-5%"  # the outro's pace; the story is read scene by scene in DELIVERY
# How each scene is read, set per scene by annotate.py: (rate, pitch, volume). edge-tts has no speaking styles for
# Indonesian, so the mood comes from pace, pitch and loudness changing with the story, plus the pauses between scenes.
DELIVERY = {
    "normal": ("-3%", "-2Hz", "+0%"),
    "tegang": ("-8%", "-4Hz", "-6%"),
    "bisik": ("-14%", "-7Hz", "-30%"),
    "dingin": ("-12%", "-9Hz", "-4%"),
    "kaget": ("+8%", "+3Hz", "+12%"),
    "lega": ("+0%", "+1Hz", "+0%"),
}
# English words the Indonesian voice reads wrongly, spelled the way an Indonesian says them. Only the voice sees
# these; captions keep the written word. annotate.py adds a story's own cases per scene.
SAY = {"rice cooker": "rais kuker", "magic com": "mejik kom", "magicom": "mejikom", "charger": "cajer",
       "laptop": "leptop", "wifi": "waifai", "wi-fi": "waifai", "online": "onlen", "headset": "hedset",
       "update": "apdet", "chat": "cet", "game": "gem", "power bank": "pawer beng", "powerbank": "pawerbeng",
       "lockscreen": "lokskrin", "earphone": "irfon", "freezer": "frizer",
       "cosplay": "kosplei", "figure": "figur", "streaming": "striming", "flashlight": "flesh lait"}
SR = 24000  # edge-tts and Gemini audio rate

ENV = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().split() if "=" in l) if (ROOT / ".env").exists() else {}
# The free tier allows 10 requests a day per model, so a story goes in a few long takes, and when a model is out of
# quota the whole story is read again by the next one (a voice that changes pace halfway would be worse).
# gemini-2.5 follows a style line in front of the text without reading it out; 3.8 reads every word it is sent, so
# it gets the short tags only. Measured 2026-11-10 on the same passage: 2.5 67 s, slow and close; 3.8 48 s.
GEMINI_MODELS = [("gemini-2.5-flash-preview-tts", True), ("gemini-3.8-flash-tts", False)]
GEMINI_VOICE = "Charon"
GEMINI_STYLE = ("Read aloud in a low, intimate, slow and tense voice, like a late-night horror podcast storyteller, "
                "whispering the frightening lines:")
model, styled = GEMINI_MODELS[0]
# Short English tags per scene; longer cues get translated and read out, these do not.
GEMINI_TAG = {"normal": "", "tegang": "[tense]", "bisik": "[whispering]", "dingin": "[slow and cold]",
              "kaget": "[startled]", "lega": "[sighs with relief]"}
BATCH_CHARS = 1800  # about two minutes of speech per request: 4-5 requests a story, retries included
WHISPER = "small"
# The same closing line on every video, read in the narrator's voice; the end card times its buttons to it.
OUTRO = ("Kalau kamu masih berani, like, subscribe, dan nyalakan loncengnya, "
         "supaya tidak ketinggalan cerita berikutnya. Dan ingat... malam ini, jangan sendirian.")
ALNUM = re.compile(r"[^\w]", re.U)


def alnum(s):
    return ALNUM.sub("", s).replace("_", "")


def spoken_form(text, extra=()):
    """The text as the voice should read it: SAY plus the scene's own respellings, whole words, any case."""
    for written, say in sorted([*SAY.items(), *extra], key=lambda kv: -len(kv[0])):
        text = re.sub(rf"(?<!\w){re.escape(written)}(?!\w)", say, text, flags=re.I)
    return text


async def synth(text, mp3, rate=RATE, pitch="+0Hz", volume="+0%"):
    words = []
    with open(mp3, "wb") as f:
        async for c in edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch, volume=volume,
                                            boundary="WordBoundary").stream():
            if c["type"] == "audio":
                f.write(c["data"])
            elif c["type"] == "WordBoundary":
                words.append((c["text"], c["offset"] / 1e7, (c["offset"] + c["duration"]) / 1e7))
    return words


def align(tokens, spoken):
    """Start and end of each narration token, matched on the running count of alphanumerics.
    Punctuation and how the voice chunks words differ; the letters do not (much)."""
    spans, at = [], 0
    for t, s, e in spoken:
        n = len(alnum(t))
        spans.append((at, at + n, s, e))
        at += n
    total = max(at, 1)
    want = sum(len(alnum(t)) for t in tokens) or 1
    k = total / want  # absorbs the odd spoken/written mismatch without drifting
    out, pos, j = [], 0, 0
    for t in tokens:
        a, b = pos * k, (pos + len(alnum(t))) * k
        pos += len(alnum(t))
        while j < len(spans) - 1 and spans[j][1] <= a:
            j += 1
        m = j
        while m < len(spans) - 1 and spans[m][1] < b:
            m += 1
        out.append({"w": t, "s": spans[j][2], "e": spans[m][3]})
    return out


def cues(words, max_chars=32, max_words=6, gap=0.5):
    out, cur = [], []
    def flush():
        if cur:
            out.append({"start": cur[0]["s"], "end": cur[-1]["e"], "text": " ".join(x["w"] for x in cur)})
            cur.clear()
    for w in words:
        if cur and (len(" ".join(x["w"] for x in cur)) + len(w["w"]) >= max_chars or len(cur) >= max_words
                    or w["s"] - cur[-1]["e"] > gap):
            flush()
        cur.append(w)
        # Sentence ends always break; a comma only once there is enough to read.
        if w["w"][-1] in ".?!" or (w["w"][-1] in ",;:" and len(cur) >= 3):
            flush()
    flush()
    for a, b in zip(out, out[1:]):  # hold through short pauses instead of flickering
        if b["start"] - a["end"] < 0.35:
            a["end"] = b["start"]
    return out


def stamp(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def pcm(mp3):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp3), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                          capture_output=True, check=True).stdout


def gemini(text, out):
    """One Gemini TTS take of text, saved as a WAV at 24 kHz mono."""
    body = {"contents": [{"parts": [{"text": text}]}], "generationConfig": {"responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI_VOICE}}}}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": ENV["GEMINI_API_KEY"]})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gemini TTS HTTP {e.code}: {e.read().decode()[:300]}") from e
    data = base64.b64decode(r["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    if data[:4] == b"RIFF":  # some models send a whole WAV file, others bare PCM
        out.write_bytes(data)
    else:
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data)


_whisper = None


def heard(wav):
    """The words faster-whisper hears in wav, with their times: [(text, start, end)]."""
    global _whisper
    from faster_whisper import WhisperModel
    if _whisper is None:
        _whisper = WhisperModel(WHISPER, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = _whisper.transcribe(np.frombuffer(raw, np.int16).astype(np.float32) / 32768, language="id",
                                  word_timestamps=True)
    return [(w.word.strip(), w.start, w.end) for s in segs for w in s.words if alnum(w.word)]


def batches(scenes):
    out, cur = [], []
    for x in scenes:
        if cur and sum(len(y["text"]) for y in cur) + len(x["text"]) > BATCH_CHARS:
            out.append(cur)
            cur = []
        cur.append(x)
    return out + [cur] if cur else out


def take(text, written, f, tries=3):
    """A Gemini take of text whose words match the script: a take that reads out cues or drops lines is redone."""
    want = len(alnum("".join(written)))
    for n in range(tries):
        if not f.exists():
            gemini(text, f)
        spoken = heard(f)
        got = len(alnum("".join(t for t, _, _ in spoken)))
        if spoken and 0.8 * want <= got <= 1.2 * want:
            return spoken
        log(f"{f.name}: heard {got} letters for {want} in the script; take {n + 1} redone")
        f.unlink()
    raise RuntimeError(f"no clean Gemini take for {f.name} in {tries} tries")


def narrate_gemini(scenes, d):
    """A few scenes per Gemini take, each take timed by whisper and cut at the scene breaks, so every scene still
    gets its own pause after it. Returns word timings over the joined narration.mp3."""
    parts = d / "tts"
    parts.mkdir(exist_ok=True)
    audio, words, t = bytearray(), [], 0.0
    for b, group in enumerate(batches(scenes)):
        text = (GEMINI_STYLE + "\n" if styled else "") + "\n".join(f"{GEMINI_TAG.get(x.get('delivery'), '')} {x['text']}".strip()
                                               for x in group)
        f = parts / f"{model}-{b:02}.wav"
        tokens = [w for x in group for w in x["text"].split()]
        timed = align(tokens, take(text, tokens, f))
        raw = pcm(f)
        end_all = len(raw) / 2 / SR
        at = 0
        for k, x in enumerate(group):
            n = len(x["text"].split())
            mine = timed[at:at + n]
            at += n
            # Cut halfway into the silence on each side, so no word loses its tail.
            a = max(mine[0]["s"] - 0.05, 0.0) if k == 0 else (timed[at - n - 1]["e"] + mine[0]["s"]) / 2
            nxt = timed[at]["s"] if at < len(timed) else None
            z = min(mine[-1]["e"] + 0.15, end_all) if nxt is None else (mine[-1]["e"] + nxt) / 2
            for w in mine:
                words.append({"w": w["w"], "s": w["s"] - a + t, "e": w["e"] - a + t})
            piece = raw[int(a * SR) * 2:int(z * SR) * 2]
            gap = (nxt - mine[-1]["e"]) if nxt is not None else 0.15
            pause = min(max(float(x.get("pause") or 0.15), 0.0), 1.6)
            extra = max(pause - gap, 0.0)  # the voice's own silence counts towards the pause the scene asked for
            audio += piece + bytes(int(extra * SR) * 2)
            t += len(piece) / 2 / SR + extra
        log(f"take {b + 1}: scenes {group[0]['i']}-{group[-1]['i']}")
    finish(audio, d)
    return words


def finish(audio, d):
    # A little room on the voice: two faint, short echoes so it sits in a dark space instead of a booth.
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ac", "1", "-ar", str(SR), "-i", "-", "-af",
                    "aecho=0.8:0.6:45|85:0.13|0.07", "-ar", "48000", "-b:a", "192k", str(d / "narration.mp3")],
                   input=bytes(audio), check=True)


def narrate(scenes, d):
    """Each scene read in its own delivery, then a pause; returns word timings over the joined narration.mp3."""
    parts = d / "tts"
    parts.mkdir(exist_ok=True)
    audio, words, t = bytearray(), [], 0.0
    for x in scenes:
        rate, pitch, vol = DELIVERY.get(x.get("delivery"), DELIVERY["normal"])
        say = spoken_form(x["text"], [(a["tulis"], a["ucap"]) for a in x.get("lafal") or []])
        f = parts / f"{x['i']:04}.mp3"
        spoken = asyncio.run(synth(say, f, rate, pitch, vol))
        assert spoken, f"no word timings from edge-tts for scene {x['i']}"
        raw = pcm(f)
        # edge-tts pads every clip with silence at both ends; cut it so the pauses are only the ones we chose.
        a = max(spoken[0][1] - 0.05, 0.0)
        b = min(spoken[-1][2] + 0.15, len(raw) / 2 / SR)
        raw = raw[int(a * SR) * 2:int(b * SR) * 2]
        for w in align(x["text"].split(), spoken):
            words.append({"w": w["w"], "s": w["s"] - a + t, "e": w["e"] - a + t})
        pause = min(max(float(x.get("pause") or 0.15), 0.0), 1.6)
        audio += raw + bytes(int(pause * SR) * 2)
        t += len(raw) / 2 / SR + pause
    finish(audio, d)
    return words


def outro_take(d):
    """The closing line in the narrator's voice, and its word times (the end card's buttons land on them)."""
    if voice.startswith("gemini"):
        try:
            return outro_gemini(d)
        except Exception as e:  # noqa: BLE001 - the end card still needs a closing line
            log("Gemini outro failed, using edge-tts for it:", str(e)[:300])
    return [{"w": t, "s": a, "e": b} for t, a, b in asyncio.run(synth(OUTRO, d / "outro.mp3"))]


def outro_gemini(d):
    f = d / "tts" / f"{model}-outro.wav"
    style = GEMINI_STYLE.replace("whispering the frightening lines", "warmer now, but still eerie") + "\n"
    timed = align(OUTRO.split(), take((style if styled else "") + OUTRO, OUTRO.split(), f))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f), "-ar", "48000", "-b:a", "192k", str(d / "outro.mp3")],
                   check=True)
    return timed


voice = "edge"


def main(slug):
    d = run_dir(slug)
    s, scenes = load(d / "script.json"), load(d / "scenes.json")
    global voice, model, styled
    words = None
    for model, styled in (GEMINI_MODELS if ENV.get("GEMINI_API_KEY") else []):
        try:
            words = narrate_gemini(scenes, d)
            voice = f"gemini {model} {GEMINI_VOICE}"
            break
        except Exception as e:  # noqa: BLE001 - quota, network or bad takes: the video still gets a voice
            log(f"{model} failed:", str(e)[:400])
    if words is None:
        log("no Gemini voice; edge-tts reads the story")
    if words is None:
        words = narrate(scenes, d)
    at = 0
    for x in scenes:
        n = len(x["text"].split())
        x["start"], x["speech_end"] = words[at]["s"], words[at + n - 1]["e"]
        at += n
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", d / "narration.mp3"]).strip())
    # A picture holds until the next one starts, so nothing shows a gap.
    scenes[0]["start"] = 0.0
    for a, b in zip(scenes, scenes[1:]):
        a["end"] = b["start"]
    scenes[-1]["end"] = dur + 0.6
    save(d / "scenes.json", scenes)
    save(d / "words.json", words)
    save(d / "outro_words.json", outro_take(d))
    cs = cues(words)
    (d / "narration.srt").write_text("".join(
        f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}\n\n" for i, c in enumerate(cs, 1)))
    durs = [x["end"] - x["start"] for x in scenes]
    moods = {k: sum(1 for x in scenes if x.get("delivery") == k) for k in DELIVERY}
    log(f"voice {voice}, audio {dur:.1f}s, {len(words)} words, {len(cs)} cues, scenes {len(scenes)} "
        f"avg {sum(durs) / len(durs):.1f}s max {max(durs):.1f}s | delivery {moods}")


if __name__ == "__main__":
    main(sys.argv[1])
