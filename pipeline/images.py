"""Step 5: one image per scene through gflow. Resumable: existing scene files are skipped."""
import os, re, shutil, sys, random
from common import *

GFLOW = ROOT.parent / "gflow-cli" / ".venv" / "bin" / "gflow"
BATCH = 10
LOCK, LOCK_WAIT = "/tmp/gflow-profile.lock", 1800


def ensure_display():
    # gflow drives a real Chrome on a virtual display. Nothing restarts Xvfb after a reboot, and without it
    # Chrome dies on launch and gflow misreports that as "Profile locked", so bring :99 up ourselves.
    disp = os.environ.get("DISPLAY") or ":99"
    if Path(f"/tmp/.X11-unix/X{disp.lstrip(':')}").exists():
        return
    log(f"no X server on {disp}; starting Xvfb")
    Path(f"/tmp/.X{disp.lstrip(':')}-lock").unlink(missing_ok=True)
    subprocess.Popen(["Xvfb", disp, "-screen", "0", "1920x1080x24", "-nolisten", "tcp"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):
        if Path(f"/tmp/.X11-unix/X{disp.lstrip(':')}").exists():
            return
        time.sleep(0.2)
    sys.exit(f"Xvfb did not come up on {disp}")


def gflow(*a, timeout=2400):
    # Classic composer only: Flow's agent mode bills a much smaller "Agen Flow" quota than the
    # plan's daily image limit (Plus: 1,000 Nano Banana 2.1 images a day).
    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY") or ":99", "GFLOW_CLI_UI_MODE": "classic"}
    # youtube_short_automation drives the same Chrome profile; two gflow runs at once fail with "Profile locked",
    # so both take this lock and the later one waits.
    return subprocess.run(["flock", "-w", str(LOCK_WAIT), LOCK, GFLOW, *map(str, a)], capture_output=True, text=True,
                          timeout=timeout + LOCK_WAIT, env=env)


def main(slug, limit=None):
    ensure_display()
    d = run_dir(slug)
    scenes = load(d / "scenes.json")
    if limit:
        scenes = scenes[:limit]
    img = d / "images"
    img.mkdir(exist_ok=True)
    pf = d / "gflow-project.txt"
    if not pf.exists():
        r = gflow("project", "create", "--name", f"whatif-{slug}", "--json", timeout=300)
        out = json.loads(r.stdout[r.stdout.index("{"):]) if "{" in r.stdout else {}
        if "project_id" not in out:
            err = out.get("error") or {}
            sys.exit(f"gflow project create failed: {err.get('title')}: {err.get('detail')} {r.stderr[-500:]}")
        pf.write_text(out["project_id"])
    project = pf.read_text().strip()
    fails = 0
    while True:
        todo = [x for x in scenes if not (img / f"{x['i']:04}.jpg").exists()]
        log(f"{len(scenes) - len(todo)}/{len(scenes)} done")
        if not todo:
            return
        part = todo[:BATCH]
        tmp = d / "tmp-batch"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        (tmp / "p.txt").write_text("\n".join(x["prompt"] for x in part) + "\n")
        r = gflow("image", "t2i", "--prompts-file", tmp / "p.txt", "--aspect", "16:9", "--jitter", "10-30",
                  "--project", project, "--out", tmp)
        made = 0
        for n, x in enumerate(part):
            f = tmp / f"prompt_{n}_0.jpg"
            if f.exists():
                shutil.move(f, img / f"{x['i']:04}.jpg")
                made += 1
        (d / "gflow.log").open("a").write(r.stdout[-3000:] + r.stderr[-1500:] + "\n")
        # gflow prints Flow's reply wrapped inside a table, so flatten it before looking for the quota message.
        said = " ".join(re.sub(r"[^\w\s]", " ", r.stdout + r.stderr).lower().split())
        if not made and ("batas kuota" in said or "quota" in said):
            sys.exit(f"Google Flow quota reached at {len(scenes) - len(todo)}/{len(scenes)} images; try again later")
        fails = 0 if made else fails + 1
        if fails >= 3:
            sys.exit(f"gflow made nothing in 3 batches; stopping to protect the account. See {d / 'gflow.log'}")
        # Cool down between batches: backs off further after trouble.
        time.sleep(random.uniform(30, 90) * (1 + fails * 3))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
