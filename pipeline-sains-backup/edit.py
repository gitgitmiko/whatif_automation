"""Step 6: assemble in Concat over MCP: pictures with camera moves, varied cuts that each carry a matching
sound, content sound effects, narration and captions with coloured moments."""
import contextlib, io, random, re, sys, time
from common import *
from mcpclient import M

CONCAT = ROOT / "vendor" / "concat" / "concat"
SFX = ROOT / "assets" / "sfx"
# Cuts are built from keys and masks, not Concat's transition feature: in a long project its transitions
# rendered whole pictures black, a different scene on each export. Pictures alternate between two lanes and
# overlap by XF; the upper picture animates over the lower one - in when it is the new scene, out when it is
# the old one.
LOW, HIGH, XF = "T1", "T3", 0.45
EASE = [0.42, 0.0, 0.58, 1.0]
OUT_EASE = [0.2, 0.8, 0.3, 1.0]  # fast start, gentle landing
IN_EASE = [0.4, 0.0, 0.7, 1.0]   # leaving: moves from the first frame and keeps going
BACK = [0.3, 1.5, 0.6, 1.0]      # overshoots a little: a bounce

# Camera moves: (name, weight, scale a->b, x a->b, y a->b, rotation a->b). Zooms are a quarter of the mix.
MOVES = [
    ("hold", 3, (1.06, 1.07), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)),
    ("pan-right", 3, (1.12, 1.12), (0.045, -0.045), (0.0, 0.0), (0.0, 0.0)),
    ("pan-left", 3, (1.12, 1.12), (-0.045, 0.045), (0.0, 0.0), (0.0, 0.0)),
    ("tilt-down", 2, (1.12, 1.12), (0.0, 0.0), (0.04, -0.04), (0.0, 0.0)),
    ("tilt-up", 2, (1.12, 1.12), (0.0, 0.0), (-0.04, 0.04), (0.0, 0.0)),
    ("drift", 2, (1.10, 1.10), (0.03, -0.03), (0.025, -0.025), (0.0, 0.0)),
    ("tilt-roll", 2, (1.10, 1.10), (0.0, 0.0), (0.0, 0.0), (-1.6, 1.6)),
    ("zoom-in", 3, (1.03, 1.15), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)),
    ("zoom-out", 2, (1.15, 1.03), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)),
]

# Cuts: name -> (sound, its volume, seconds before the cut it starts). Each is drawn in cut_keys() as the new
# picture coming in (it is on top) or the old one going out (it is on top).
CUTS = {
    "fade": ("whoosh-soft", 0.35, 0.15),
    "slide": ("whoosh-fast", 0.5, 0.12),
    "push-up": ("whoosh-soft", 0.5, 0.15),
    "drop": ("boing-short", 0.45, -0.25),
    "zoom-pop": ("pop", 0.55, -0.05),
    "spin": ("whoosh-fast", 0.5, 0.1),
    "iris": ("sparkle", 0.4, 0.0),
    "curtain": ("whoosh-soft", 0.5, 0.1),
    "star": ("pop-up", 0.5, 0.0),
    "punch": ("hit", 0.55, -0.02),
}
MASKED = {"iris": "circle", "star": "star", "curtain": "rectangle"}
MASK_FULL = {"circle": 2.3, "star": 4.2, "rectangle": 4.0}  # sizes that cover the whole frame
CAPTION = {"fontFamily": '"Bangers"', "fontSize": 0.075, "fontWeight": 400, "color": "#FFFFFF", "strokeColor": "#000000",
           "strokeWidth": 0.0035, "shadow": True, "tracking": 0.004, "maxWidth": 0.9, "align": "center"}
MOOD_COLOR = {"fakta": "#FFD84D", "bahaya": "#FF5A5A", "positif": "#5BE37D", "ajaib": "#6FD8FF", "tanya": "#FFA94D"}
SFX_VOL = 0.5
ENDCARD = ROOT / "assets" / "endcard" / "endcard.jpg"
# The end card's buttons: (label, colour, x, y, the spoken word it lands on, its sound).
BUTTONS = [("LIKE", "#1E88E5", 0.2, -0.17, "like", "click"),
           ("SUBSCRIBE", "#E53935", 0.2, 0.0, "subscribe", "pop-up"),
           ("NYALAKAN LONCENG", "#F9A825", 0.2, 0.17, "lonceng", "bell")]


def read_srt(path):
    def sec(t):
        h, m, r = t.split(":")
        s, ms = r.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    out = []
    for block in Path(path).read_text().strip().split("\n\n"):
        lines = block.split("\n")
        a, b = lines[1].split(" --> ")
        out.append({"start": sec(a), "end": sec(b), "text": " ".join(lines[2:])})
    return out


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(path)]))


def norm(s):
    return " ".join(re.sub(r"[^\w\s]", " ", s.lower()).split())


def pick(rng, options, last, weights=None, avoid=()):
    """A random choice that never repeats the one before."""
    while True:
        c = rng.choices(options, weights)[0]
        if c != last and c not in avoid:
            return c


class Keys:
    """A clip's keys per property; a cut placed after the camera move replaces the camera's key there."""

    def __init__(self):
        self.k = {}

    def put(self, prop, at, value, ease=None):
        self.k.setdefault(prop, {})[round(min(max(at, 0.0), 1.0), 4)] = (value, ease)

    def commands(self, cid):
        return [{"op": "setClipKey", "clipId": cid, "property": prop, "at": at, "value": v, **({"ease": e} if e else {})}
                for prop, pts in self.k.items() for at, (v, e) in sorted(pts.items())]


def camera(keys, move, head, tail):
    """The move runs between the cut windows, so a cut's own animation is never fought."""
    _, _, s, x, y, r = move
    for prop, (a, b) in (("scale", s), ("offsetX", x), ("offsetY", y), ("rotation", r)):
        keys.put(prop, head, a)
        keys.put(prop, 1.0 - tail, b, EASE)
    return {"scale": s, "offsetX": x, "offsetY": y, "rotation": r}


def cut_keys(keys, cam, kind, entering, h, rng):
    """Keys for one cut on the upper picture; `h` is the cut's share of the clip. Entering animates 0..h into
    the camera's first frame, leaving animates 1-h..1 out of its last. Returns the mask it needs, if any."""
    a, b = (0.0, h) if entering else (1.0 - h, 1.0)
    rest = {p: v[0] if entering else v[1] for p, v in cam.items()}

    def go(prop, away, ease=None):
        if entering:
            keys.put(prop, a, away)
            keys.put(prop, b, rest.get(prop, 1.0), ease or OUT_EASE)
        else:
            keys.put(prop, a, rest.get(prop, 1.0))
            keys.put(prop, b, away, ease or IN_EASE)

    side = rng.choice([-1, 1])
    if kind == "fade":
        go("opacity", 0.0, EASE)
    elif kind == "slide":
        go("offsetX", side * 1.15)
    elif kind == "push-up":
        go("offsetY", 1.15 if entering else -1.15)
    elif kind == "drop":
        go("offsetY", -1.2 if entering else 1.2, BACK if entering else None)
    elif kind == "zoom-pop":
        go("scale", 0.15 if entering else 0.1, BACK if entering else None)
        go("opacity", 0.0)
    elif kind == "spin":
        go("rotation", side * 200.0)
        go("scale", 0.1)
    elif kind == "punch":
        if entering:  # lands a little big and settles; the hit sells it
            keys.put("scale", a, rest["scale"] * 1.22)
            keys.put("scale", b, rest["scale"], OUT_EASE)
        else:  # a hard cut: the old picture is simply gone
            keys.put("opacity", a, 1.0)
            keys.put("opacity", a + 0.002, 0.0)
    elif kind in MASKED:
        shape = MASKED[kind]
        full = MASK_FULL[shape]
        for prop in (["maskWidth"] if kind == "curtain" else ["maskWidth", "maskHeight"]):
            go(prop, 0.0)
            keys.put(prop, b if entering else a, full, OUT_EASE if entering else None)
        return {"shape": shape, "width": full, "height": full, "feather": 0.02}
    return None


def outro(q, batch, P, d, t0, media, lanes, ends):
    """The closing line over a waving stickman, with like / subscribe / bell buttons that pop in on their word,
    each with its sound; the subscribe button gets pressed. Returns where the video ends."""
    words = load(d / "outro_words.json")
    voice = d / "outro.wav"
    ff("-i", str(d / "outro.mp3"), "-af", "loudnorm=I=-15:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "2", str(voice))
    length = duration(voice) + 1.2
    q("clip_add", path=P, mediaId=q("media_import", path=P, file=str(voice))["createdId"], trackId="T2", start=t0)
    top = q("track_add", path=P)["createdId"]
    card = q("clip_add", path=P, mediaId=q("media_import", path=P, file=str(ENDCARD))["createdId"], trackId=top,
             start=t0 - XF)["createdId"]
    q("clip_trim", path=P, clipId=card, edge="end", delta=length + XF - 5.0)
    full = length + XF
    cmds = [{"op": "setClipKey", "clipId": card, "property": "opacity", "at": 0.0, "value": 0.0},
            {"op": "setClipKey", "clipId": card, "property": "opacity", "at": XF / full, "value": 1.0, "ease": EASE},
            {"op": "setClipKey", "clipId": card, "property": "scale", "at": 0.0, "value": 1.04},
            {"op": "setClipKey", "clipId": card, "property": "scale", "at": 1.0, "value": 1.1, "ease": EASE}]
    for label, colour, x, y, word, snd in BUTTONS:
        w = next((w for w in words if word in norm(w["w"])), None)
        at = t0 + (w["s"] if w else 1.0)
        style = dict(CAPTION, content=label, color="#FFFFFF", background=colour, fontSize=0.06,
                     backgroundPaddingX=0.035, backgroundPaddingY=0.022, backgroundRadius=0.025, strokeWidth=0.0,
                     maxWidth=0.0)  # the plate hugs the word
        cid = q("title_add", path=P, start=at, duration=t0 + length - at, above=True, style=style)["createdId"]
        q("clip_transform", path=P, clipId=cid, offsetX=x, offsetY=y)
        dur = t0 + length - at
        cmds += [{"op": "setClipKey", "clipId": cid, "property": "scale", "at": 0.0, "value": 0.2},
                 {"op": "setClipKey", "clipId": cid, "property": "scale", "at": 0.25 / dur, "value": 1.0, "ease": BACK}]
        if word == "subscribe":  # pressed once, like a viewer would
            p0 = 0.75 / dur
            cmds += [{"op": "setClipKey", "clipId": cid, "property": "scale", "at": p0, "value": 1.0},
                     {"op": "setClipKey", "clipId": cid, "property": "scale", "at": p0 + 0.08 / dur, "value": 0.86, "ease": EASE},
                     {"op": "setClipKey", "clipId": cid, "property": "scale", "at": p0 + 0.22 / dur, "value": 1.0, "ease": BACK}]
        for t, sid in ((at, snd),) + (((at + 0.75, "click"),) if word == "subscribe" else ()):
            if sid not in media:
                media[sid] = (q("media_import", path=P, file=str(SFX / f"{sid}.wav"))["createdId"], duration(SFX / f"{sid}.wav"))
            lane = min(ends, key=lambda k: ends[k])
            if ends[lane] <= t:
                sc = q("clip_add", path=P, mediaId=media[sid][0], trackId=lane, start=t)["createdId"]
                q("clip_update", path=P, clipId=sc, patch={"volume": 0.6})
                ends[lane] = t + media[sid][1]
    batch(cmds)
    return t0 + length


def main(slug, limit=None):
    d = run_dir(slug)
    scenes = load(d / "scenes.json")
    if limit:
        scenes = scenes[:limit]
    rng = random.Random(slug)  # the same run always cuts the same way
    m = M([str(CONCAT), "--mcp", "headless"], str(d / "concat.log"))

    def q(n, **a):
        b = io.StringIO()
        try:
            with contextlib.redirect_stdout(b):
                return m.call(n, **a)
        except SystemExit:
            print(b.getvalue()[-1500:])  # the tool's refusal, which would otherwise vanish
            raise

    def batch(cmds, size=150):
        for i in range(0, len(cmds), size):
            q("edit_apply", path=P, command={"op": "batch", "commands": cmds[i:i + size]})

    name = "Project"
    P = str(d / name)
    q("project_create", location=str(d), name=name, video={"width": 1920, "height": 1080, "rateNum": 30, "rateDen": 1})
    t0 = time.time()
    voice = d / "narration.wav"
    ff("-i", str(d / "narration.mp3"), "-af", "loudnorm=I=-15:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "2", str(voice))
    audio = q("media_import", path=P, file=str(voice))["createdId"]

    clips = []
    for n, x in enumerate(scenes):
        media = q("media_import", path=P, file=str(d / "images" / f"{x['i']:04}.jpg"))["createdId"]
        cid = q("clip_add", path=P, mediaId=media, trackId=HIGH if n % 2 else LOW, start=x["start"])["createdId"]
        length = x["end"] - x["start"] + (XF if n < len(scenes) - 1 else 0)
        q("clip_trim", path=P, clipId=cid, edge="end", delta=length - 5.0)
        clips.append((cid, length))
    log(f"placed {len(clips)} images in {time.time() - t0:.0f}s")

    # One cut per scene change, never the same twice running. Odd scenes sit on the upper lane and draw both
    # their entry and their exit, and a picture has one mask, so those two never both need one.
    names = list(CUTS)
    cuts = [None]
    for n in range(1, len(scenes)):
        avoid = set(MASKED) if n % 2 == 0 and cuts[n - 1] in MASKED else ()
        cuts.append(pick(rng, names, cuts[-1], avoid=avoid))
    moves = []
    for _ in scenes:
        moves.append(pick(rng, MOVES, moves[-1] if moves else None, [mv[1] for mv in MOVES]))
    cmds, masks = [], {}
    for n, (cid, length) in enumerate(clips):
        keys = Keys()
        enter = cuts[n] if n % 2 else None
        leave = cuts[n + 1] if n % 2 and n + 1 < len(clips) else None
        head, tail = (XF / length if enter else 0.0), (XF / length if leave else 0.0)
        cam = camera(keys, moves[n], head, tail)
        for kind, entering, h in ((enter, True, head), (leave, False, tail)):
            if kind and (mk := cut_keys(keys, cam, kind, entering, h, rng)):
                masks[cid] = mk
        cmds += keys.commands(cid)
    for cid, mk in masks.items():
        q("clip_mask", path=P, clipId=cid, mask=mk)
    batch(cmds)
    log("cuts: " + ", ".join(f"{k} {cuts.count(k)}" for k in names) + " | moves: " +
        ", ".join(f"{mv[0]} {moves.count(mv)}" for mv in MOVES))

    # Each cut's sound, then content sounds at their word unless a cut's sound is already there.
    hits = []
    for n in range(1, len(scenes)):
        snd, vol, lead = CUTS[cuts[n]]
        hits.append((max(scenes[n]["start"] - lead, 0.0), snd, vol))
    words = load(d / "words.json")
    at, content = 0, 0
    for x in scenes:
        span = words[at:at + len(x["text"].split())]
        at += len(x["text"].split())
        if not x.get("sfx"):
            continue
        want = norm(x.get("sfx_word") or "")
        w = next((w for w in span if want and norm(w["w"]) == want), None)
        t = w["s"] if w else x["start"] + 0.6
        if all(abs(t - h[0]) > 0.9 for h in hits):
            hits.append((t, x["sfx"], SFX_VOL))
            content += 1

    q("clip_add", path=P, mediaId=audio, trackId="T2", start=0)
    lanes = [q("track_add", path=P, bottom=True)["createdId"] for _ in range(2)]
    media, ends, placed = {}, {ln: -1.0 for ln in lanes}, 0
    for t, sid, vol in sorted(hits):
        if sid not in media:
            media[sid] = (q("media_import", path=P, file=str(SFX / f"{sid}.wav"))["createdId"], duration(SFX / f"{sid}.wav"))
        lane = min(ends, key=lambda k: ends[k])
        if ends[lane] > t:
            continue  # both lanes busy: drop it rather than pile sounds up
        cid = q("clip_add", path=P, mediaId=media[sid][0], trackId=lane, start=t)["createdId"]
        q("clip_update", path=P, clipId=cid, patch={"volume": vol})
        ends[lane] = t + media[sid][1]
        placed += 1
    log(f"sounds: {placed} placed ({len(scenes) - 1} cuts, {content} content)")
    outro_end = outro(q, batch, P, d, scenes[-1]["end"], media, lanes, ends)
    log(f"end card until {outro_end:.1f}s")

    # Captions: white by default; a scene's highlighted phrase turns its caption the mood's colour, larger,
    # with a bouncier entrance. Never two coloured scenes in a row.
    end = scenes[-1]["end"]
    caps = [c for c in read_srt(d / "narration.srt") if c["start"] < end]
    mood_of, prev = {}, False
    for x in scenes:
        h = x.get("highlight")
        if not h or prev:
            prev = False
            continue
        first = norm(h["phrase"]).split()[0]
        k = next((k for k, c in enumerate(caps)
                  if x["start"] - 0.05 <= c["start"] < x["end"] and first in norm(c["text"]).split()), None)
        if k is not None:
            mood_of[k] = h["mood"]
            prev = True
    groups = {None: [c for k, c in enumerate(caps) if k not in mood_of]}
    for k, mood in mood_of.items():
        groups.setdefault(mood, []).append(caps[k])
    cmds = []
    for mood, group in groups.items():
        if not group:
            continue
        style = dict(CAPTION)
        if mood:
            style.update(color=MOOD_COLOR[mood], fontSize=CAPTION["fontSize"] * 1.25, strokeWidth=0.0045)
        before = {c["id"] for c in q("timeline_read", path=P)["timeline"]["clips"]}
        r = q("captions_add", path=P, captions=group, offsetY=0.38 if mood else 0.39, style=style)
        for c in (c for c in r["timeline"]["clips"] if c["id"] not in before):
            dur = max(c["duration"], 0.2)
            key = lambda prop, at, v, e=None: {"op": "setClipKey", "clipId": c["id"], "property": prop, "at": at,
                                               "value": v, **({"ease": e} if e else {})}
            if mood:  # pops in big and tilted, and settles
                tilt = rng.choice([-4.0, 4.0])
                cmds += [key("scale", 0.0, 0.5), key("scale", min(0.22 / dur, 0.5), 1.0, BACK),
                         key("rotation", 0.0, tilt), key("rotation", min(0.3 / dur, 0.6), 0.0, OUT_EASE)]
            else:  # a small lift into place
                cmds += [key("scale", 0.0, 0.9), key("scale", min(0.1 / dur, 0.3), 1.0, OUT_EASE)]
    batch(cmds)
    log(f"captions {len(caps)}, coloured {len(mood_of)}")

    # A guard against Concat rendering a picture black (seen with its transitions): look at every scene.
    probe = d / "probe.png"

    def luma(t):
        q("preview_frame", path=P, time=t, output=str(probe), width=160, height=90)
        out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(probe), "-vf", "signalstats,metadata=print:file=-",
                              "-f", "null", "-"], capture_output=True, text=True).stdout
        return float(re.search(r"YAVG=([\d.]+)", out).group(1))
    black = [x["i"] for x in scenes if luma((x["start"] + x["end"]) / 2) < 30]
    if black:
        sys.exit(f"scenes render black: {black}")
    log(f"checked {len(scenes)} scenes: none black")
    q("project_save", path=P)
    t0 = time.time()
    job = q("export_start", path=P, output=str(d / "final.mp4"), codec="h264", crf=20)["job"]
    while True:
        st = q("export_wait", job=job, timeoutSeconds=300)
        log("export", st.get("state"), round(st.get("fraction", 0), 3))
        if st.get("state") == "done":
            break
        if st.get("state") not in ("running", "queued"):
            sys.exit(f"export failed: {st}")
    log(f"export took {time.time() - t0:.0f}s")
    out = subprocess.run(["ffmpeg", "-nostats", "-i", str(d / "final.mp4"), "-vf", "blackdetect=d=0.5:pix_th=0.1", "-an",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    black = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", out)
    if black:
        sys.exit(f"final.mp4 has black spans {black}")
    log("final check: no black spans")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
