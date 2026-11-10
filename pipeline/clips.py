"""Step 5c: one moving picture per minute of video. Sonnet picks a scene in each minute and writes how it moves,
then flowclip.py animates that scene's own picture into a 4-second Omni clip on Flow (12 credits each).
Resumable; never fails the run: a scene without a clip simply stays a still picture."""
import subprocess, sys
from common import *

GFLOW_PY = ROOT.parent / "gflow-cli" / ".venv" / "bin" / "python"
GFLOW = ROOT.parent / "gflow-cli" / ".venv" / "bin" / "gflow"
LOCK, LOCK_WAIT = "/tmp/gflow-profile.lock", 1800  # shared with images.py and the Shorts project
CLIP_CREDITS = 12  # measured 2026-11-10: one 4 s Omni 1.2 Flash clip
SECONDS = 4
# A clip is played a little slower to fill its scene, so scenes much longer than this end on its last frame.
MIN_SCENE, MAX_SCENE = 3.0, 9.0

SYS = """Kamu sutradara animasi untuk video cerita horor bergaya novel grafis. Video ini dibagi per menit; untuk SETIAP menit pilih SATU adegan dari kandidatnya yang paling hidup bila gambarnya dibuat bergerak 4 detik: ada sosok yang bisa menoleh atau mendekat, api atau lampu berkedip, hujan, kabut, kain atau rambut tertiup, pintu terbuka pelan, tokoh yang bereaksi. Utamakan momen yang mencekam.
Lalu tulis "motion": gerakan yang terjadi dalam 4 detik itu, dalam BAHASA INGGRIS, maks 35 kata, konkret dan pelan (horor terasa dari gerak kecil yang salah). Hanya gerakan dari isi gambar yang dideskripsikan; jangan tambah tokoh atau benda baru, jangan ganti lokasi, jangan potong ke adegan lain, tanpa teks. Kamera boleh bergerak pelan (slow push in, slight drift).
Balas HANYA JSON: {"clips":[{"minute":0,"i":12,"motion":"..."}]} dengan satu entri untuk setiap menit."""


def credits():
    r = subprocess.run(["flock", "-w", str(LOCK_WAIT), LOCK, GFLOW, "credits", "user"], capture_output=True, text=True,
                       timeout=LOCK_WAIT + 300, env={**os.environ, "DISPLAY": os.environ.get("DISPLAY") or ":99"})
    m = re.search(r"Credits:\s*(\d+)", r.stdout)
    return int(m.group(1)) if m else None


def plan(scenes):
    """{minute: scene} for each whole minute of narration that has a scene of a usable length."""
    total = scenes[-1]["end"]
    n = max(1, round(total / 60))
    width = total / n
    windows = {}
    for k in range(n):
        cands = [x for x in scenes if k * width <= x["start"] < (k + 1) * width
                 and MIN_SCENE <= x["end"] - x["start"] <= MAX_SCENE]
        if cands:
            windows[k] = cands
    ask = {str(k): [{"i": x["i"], "narasi": x["text"], "gambar": x["visual"]} for x in c] for k, c in windows.items()}
    picked = {}
    try:
        for c in claude_json("sonnet", SYS, json.dumps({"menit": ask}, ensure_ascii=False))["clips"]:
            k, i = int(c["minute"]), int(c["i"])
            if k in windows and any(x["i"] == i for x in windows[k]) and c.get("motion"):
                picked[k] = {"i": i, "motion": " ".join(c["motion"].split())}
    except Exception as e:  # noqa: BLE001 - fall back to a plain pick below
        log("clip choice failed:", str(e)[:300])
    for k, c in windows.items():  # a minute Sonnet skipped: its longest usable scene, moving gently
        if k not in picked:
            x = max(c, key=lambda x: x["end"] - x["start"])
            picked[k] = {"i": x["i"], "motion": "Subtle eerie motion: light flickers, fog and hair drift slowly, "
                                                "the people breathe and react, slow push in."}
    return [picked[k] for k in sorted(picked)]


def main(slug):
    d = run_dir(slug)
    scenes = load(d / "scenes.json")
    if not all("start" in x for x in scenes):
        sys.exit("scenes have no timings yet; run tts.py first")
    f = d / "clips.json"
    chosen = load(f) if f.exists() else plan(scenes)
    save(f, chosen)
    log("clips wanted:", len(chosen), "| scenes", [c["i"] for c in chosen])
    todo = [c for c in chosen if not (d / "images" / f"{c['i']:04}.omni.mp4").exists()]
    if not todo:
        return
    have = credits()
    if have is None:
        log("could not read the Flow credit balance; making no clips")
        return
    afford = have // CLIP_CREDITS
    if afford < len(todo):
        log(f"Flow credits {have} pay for {afford} of {len(todo)} clips; the rest stay still pictures")
        todo = todo[:afford]
    if not todo:
        return
    job = d / "clips-job.json"
    save(job, {"project": (d / "gflow-project.txt").read_text().strip(), "max_credits": CLIP_CREDITS,
               "items": [{"image": str(d / "images" / f"{c['i']:04}.jpg"), "prompt": c["motion"], "seconds": SECONDS,
                          "out": str(d / "images" / f"{c['i']:04}.omni.mp4")} for c in todo]})
    r = subprocess.run(["flock", "-w", str(LOCK_WAIT), LOCK, GFLOW_PY, ROOT / "pipeline" / "flowclip.py", job],
                       capture_output=True, text=True, timeout=LOCK_WAIT + 1200 * len(todo),
                       env={**os.environ, "DISPLAY": os.environ.get("DISPLAY") or ":99"})
    made = spent = 0
    for line in r.stdout.splitlines():
        if line.startswith("{"):
            res = json.loads(line)
            made += res["ok"]
            spent += res["credits"] or 0
            if not res["ok"]:
                log("clip failed:", Path(res["out"]).name, res["error"][:300])
    (d / "clips.log").write_text(r.stdout[-6000:] + r.stderr[-3000:])
    log(f"clips made {made}/{len(todo)}, {spent} credits spent")


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except Exception as e:  # noqa: BLE001 - moving pictures are extra; the video is still made without them
        log("clips step failed, the video keeps its still pictures:", str(e)[:500])
