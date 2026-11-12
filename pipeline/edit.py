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
    "fade": ("whoosh-soft", 0.25, 0.15),
    "slide": ("whoosh-soft", 0.3, 0.12),
    "push-up": ("whoosh-soft", 0.3, 0.15),
    "punch": ("hit", 0.3, -0.02),
    "curtain": ("whoosh-soft", 0.3, 0.1),
}
# Horror keeps the calm cuts; the cartoon ones (drop, zoom-pop, spin, iris, star) are still drawn in cut_keys().
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


def moving(d, x, length):
    """The scene's Omni clip (clips.py) fitted to the scene: no sound of its own, 1080p30, played up to 1.5x slower
    to fill the scene, then held on its last frame. None when the scene has no clip."""
    raw = d / "images" / f"{x['i']:04}.omni.mp4"
    if not raw.exists():
        return None
    out = d / "images" / f"{x['i']:04}.scene.mp4"
    slow = min(max(length / duration(raw), 1.0), 1.5)
    ff("-i", str(raw), "-an", "-vf", f"scale=1920:1080,setsar=1,setpts={slow:.4f}*PTS,fps=30,"
       f"tpad=stop_mode=clone:stop_duration={length + 1:.2f}", "-t", f"{length + 0.2:.2f}",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out))
    return out


def reveal(q, batch, P, d, scenes, folder):
    """The hero's official art (render or splash) over the scene storyboard.py marked, growing in slowly: the one moment the
    hero is shown as it really looks, since the drawn scenes keep it a silhouette. That scene carries the narration's
    bridge (the channel and today's hero), so the channel name and the hero's name stand at the top as a title card."""
    info = load(ROOT / folder / "hero.json") if folder and (ROOT / folder / "hero.json").exists() else {}
    render = ROOT / str(folder) / info.get("reveal", "render.png")
    x = next((x for x in scenes if x.get("reveal")), None)
    if not render.exists() or x is None:
        return
    length = x["end"] - x["start"]
    top = q("track_add", path=P)["createdId"]
    cid = q("clip_add", path=P, mediaId=q("media_import", path=P, file=str(render))["createdId"], trackId=top,
            start=x["start"])["createdId"]
    q("clip_trim", path=P, clipId=cid, edge="end", delta=length - 5.0)
    batch([{"op": "setClipKey", "clipId": cid, "property": "opacity", "at": 0.0, "value": 0.0},
           {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": min(0.6 / length, 0.3), "value": 1.0, "ease": EASE},
           {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": max(1 - 0.4 / length, 0.7), "value": 1.0},
           {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": 1.0, "value": 0.0},
           {"op": "setClipKey", "clipId": cid, "property": "scale", "at": 0.0, "value": 0.92},
           {"op": "setClipKey", "clipId": cid, "property": "scale", "at": 1.0, "value": 1.0, "ease": EASE}])
    cards = [("HIKAYAT ANCIENT", 0.042, "#FFD25A", -0.41)]
    name = " ".join(filter(None, [info.get("name"), info.get("title") and f"- {info['title']}"])).upper()
    if name:
        cards.append((name, 0.085, "#FFFFFF", -0.31))
    at, dur = x["start"] + 0.4, max(length - 0.8, 1.0)
    for text, size, colour, y in cards:
        style = dict(CAPTION, content=text, color=colour, fontSize=size, strokeWidth=0.004, maxWidth=0.9)
        tid = q("title_add", path=P, start=at, duration=dur, above=True, style=style)["createdId"]
        q("clip_transform", path=P, clipId=tid, offsetY=y)
        batch([{"op": "setClipKey", "clipId": tid, "property": "opacity", "at": 0.0, "value": 0.0},
               {"op": "setClipKey", "clipId": tid, "property": "opacity", "at": min(0.4 / dur, 0.3), "value": 1.0, "ease": EASE},
               {"op": "setClipKey", "clipId": tid, "property": "opacity", "at": max(1 - 0.3 / dur, 0.7), "value": 1.0},
               {"op": "setClipKey", "clipId": tid, "property": "opacity", "at": 1.0, "value": 0.0}])
    log(f"hero render and title card over scene {x['i']}: {name or '(no name)'}")


# Ambience beds by place, synthesised from noise and tones so they carry no licence (ffmpeg lavfi; D = seconds).
BEDS = {
    "sea": "anoisesrc=color=brown:amplitude=0.7:duration={D},lowpass=f=700,tremolo=f=0.1:d=0.85,volume=1.6",
    "rain": "anoisesrc=color=pink:amplitude=0.4:duration={D},highpass=f=900,lowpass=f=7000,volume=0.9",
    "wind": "anoisesrc=color=pink:amplitude=0.6:duration={D},bandpass=f=500:width_type=h:w=600,tremolo=f=0.17:d=0.7,volume=1.4",
    "cave": "sine=frequency=49:duration={D},volume=0.4,aecho=0.8:0.7:420|780:0.35|0.2",
    "fire": "anoisesrc=color=brown:amplitude=0.6:duration={D},lowpass=f=1400,tremolo=f=7:d=0.35,volume=1.2",
    "forest": "anoisesrc=color=pink:amplitude=0.3:duration={D},lowpass=f=2500,tremolo=f=0.12:d=0.5,volume=0.8",
    "battle": "anoisesrc=color=brown:amplitude=0.8:duration={D},lowpass=f=260,tremolo=f=0.6:d=0.5,volume=1.8",
    "magic": "sine=frequency=220:duration={D},tremolo=f=0.3:d=0.6,chorus=0.6:0.8:55:0.4:0.3:2,volume=0.25",
    "dark": "sine=frequency=55:duration={D},volume=0.5,tremolo=f=0.13:d=0.6",
}


def ambient(d, seconds, mood="misterius", scenes=()):
    """The ambience under the whole video: each run of scenes in one kind of place gets its bed, crossfading into the
    next over 1.5 s; quieter under the stories that are not dark."""
    out = d / "ambient.wav"
    runs = []  # (kind, start, end)
    for x in scenes:
        kind = x.get("ambience") or "dark"
        if runs and runs[-1][0] == kind:
            runs[-1][2] = x["end"]
        else:
            runs.append([kind, x["start"], x["end"]])
    if not runs:
        runs = [["dark", 0.0, seconds]]
    runs[0][1], runs[-1][2] = 0.0, seconds
    XA = 1.5
    parts = []
    for n, (kind, a, b) in enumerate(runs):
        f = d / f"bed-{n:02}.wav"
        length = b - a + (XA if n < len(runs) - 1 else 0)
        # Each bed levelled on its own first: raw, rain and magic came out 15 dB under fire and battle.
        ff("-f", "lavfi", "-i", BEDS[kind].format(D=f"{length:.2f}"), "-af", "loudnorm=I=-30:LRA=7",
           "-ar", "48000", "-ac", "2", str(f))
        parts.append(f)
    if len(parts) == 1:
        chain, label = "", "[0]"
    else:
        chain, label = "", "[0]"
        for n in range(1, len(parts)):
            chain += f"{label}[{n}]acrossfade=d={XA}:c1=tri:c2=tri[x{n}];"
            label = f"[x{n}]"
    level = -30 if mood in ("horor", "misterius") else -34
    ff(*[a for f in parts for a in ("-i", str(f))], "-filter_complex",
       chain + f"{label}afade=t=in:d=3,afade=t=out:st={seconds - 4:.1f}:d=4,loudnorm=I={level}[o]", "-map", "[o]",
       "-t", f"{seconds:.2f}", "-ar", "48000", "-ac", "2", str(out))
    for f in parts:
        f.unlink(missing_ok=True)
    log("ambience: " + " > ".join(k for k, _, _ in runs))
    return out


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

    clips, animated = [], set()
    for n, x in enumerate(scenes):
        length = x["end"] - x["start"] + (XF if n < len(scenes) - 1 else 0)
        clip = moving(d, x, length)
        media = q("media_import", path=P, file=str(clip or d / "images" / f"{x['i']:04}.jpg"))["createdId"]
        cid = q("clip_add", path=P, mediaId=media, trackId=HIGH if n % 2 else LOW, start=x["start"])["createdId"]
        # A still picture comes in 5 s long; a clip as long as its file.
        q("clip_trim", path=P, clipId=cid, edge="end", delta=length - (duration(clip) if clip else 5.0))
        clips.append((cid, length))
        if clip:
            animated.add(n)
    log(f"placed {len(clips)} scenes ({len(animated)} moving) in {time.time() - t0:.0f}s")
    plan = load(d / "plan.json") if (d / "plan.json").exists() else {}
    reveal(q, batch, P, d, scenes, plan.get("hero_dir"))

    # One cut per scene change, never the same twice running. Odd scenes sit on the upper lane and draw both
    # their entry and their exit, and a picture has one mask, so those two never both need one.
    names = list(CUTS)
    cuts = [None]
    for n in range(1, len(scenes)):
        avoid = set(MASKED) if n % 2 == 0 and cuts[n - 1] in MASKED else ()
        cuts.append(pick(rng, names, cuts[-1], avoid=avoid))
    moves = []
    for n in range(len(scenes)):
        moves.append(pick(rng, MOVES, moves[-1] if moves else None, [mv[1] for mv in MOVES]))
        if n in animated:  # the clip moves by itself; a camera move on top would fight it
            moves[-1] = MOVES[0]
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
    bed = q("track_add", path=P, bottom=True)["createdId"]
    # Exactly as long as the narration plus the outro (outro() adds 1.2 s after its line): a longer bed runs on past the end card as black.
    bed_len = scenes[-1]["end"] + duration(d / "outro.mp3") + 1.2
    q("clip_add", path=P, mediaId=q("media_import", path=P, file=str(ambient(d, bed_len, plan.get("mood", "misterius"), scenes)))["createdId"],
      trackId=bed, start=0)
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
