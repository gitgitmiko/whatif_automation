"""Step 4: narration.mp3 and narration.srt from edge-tts; word timings give scene times and captions."""
import asyncio, re, sys
import edge_tts
from common import *

VOICE, RATE = "id-ID-ArdiNeural", "+5%"
# The same closing line on every video, read in the narrator's voice; the end card times its buttons to it.
OUTRO = ("Kalau video ini bikin kamu penasaran, jangan lupa like, subscribe, dan nyalakan loncengnya, "
         "supaya tidak ketinggalan video apa yang terjadi jika berikutnya. Sampai jumpa!")
ALNUM = re.compile(r"[^\w]", re.U)


def alnum(s):
    return ALNUM.sub("", s).replace("_", "")


async def synth(text, mp3):
    words = []
    with open(mp3, "wb") as f:
        async for c in edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary").stream():
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


def main(slug):
    d = run_dir(slug)
    s, scenes = load(d / "script.json"), load(d / "scenes.json")
    text = " ".join(x["text"] for x in scenes)
    spoken = asyncio.run(synth(text, d / "narration.mp3"))
    assert spoken, "no word timings from edge-tts"
    words = align(text.split(), spoken)
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
    log(f"audio {dur:.1f}s, {len(words)} words, {len(cs)} cues, scenes {len(scenes)} "
        f"avg {sum(durs) / len(durs):.1f}s max {max(durs):.1f}s")


if __name__ == "__main__":
    main(sys.argv[1])
