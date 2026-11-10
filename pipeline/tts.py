"""Step 4: narration.mp3 and narration.srt from edge-tts; word timings give scene times and captions."""
import asyncio, re, sys
import edge_tts
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
SR = 24000  # edge-tts audio rate
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
    # A little room on the voice: two faint, short echoes so it sits in a dark space instead of a booth.
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ac", "1", "-ar", str(SR), "-i", "-", "-af",
                    "aecho=0.8:0.6:45|85:0.13|0.07", "-ar", "48000", "-b:a", "192k", str(d / "narration.mp3")],
                   input=bytes(audio), check=True)
    return words


def main(slug):
    d = run_dir(slug)
    s, scenes = load(d / "script.json"), load(d / "scenes.json")
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
    outro = asyncio.run(synth(OUTRO, d / "outro.mp3"))
    save(d / "outro_words.json", [{"w": t, "s": a, "e": b} for t, a, b in outro])
    cs = cues(words)
    (d / "narration.srt").write_text("".join(
        f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}\n\n" for i, c in enumerate(cs, 1)))
    durs = [x["end"] - x["start"] for x in scenes]
    moods = {k: sum(1 for x in scenes if x.get("delivery") == k) for k in DELIVERY}
    log(f"audio {dur:.1f}s, {len(words)} words, {len(cs)} cues, scenes {len(scenes)} "
        f"avg {sum(durs) / len(durs):.1f}s max {max(durs):.1f}s | delivery {moods}")


if __name__ == "__main__":
    main(sys.argv[1])
