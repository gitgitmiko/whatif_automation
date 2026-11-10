"""The "Apa yang terjadi jika" service: makes one video a day on its own clock and serves them to n8n,
which uploads them at their publishing time. Mirrors the KUISABON service's API so the same dashboard and
n8n patterns work.

  GET  /health
  POST /api/run {slot}                    starts a production now (siang | sore), 202
  GET  /api/ready?slot=siang|sore         the newest finished, not yet uploaded video for that slot (404 if none)
  GET  /api/videos/<id>.mp4
  POST /api/videos/<id>/uploaded {youtube_id} | /failed {error}
  GET  /api/monitor/overview | history?page&pageSize&status&date | logs?lines   for dashboard-gitgit
  GET  /api/preview/<id>/<key>.mp4          no token: the key is the link; works only until the video is uploaded
"""
import datetime as dt, hashlib, hmac, json, os, re, secrets, shutil, sqlite3, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, RUNS, load, log
from topic import plan

ENV = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().split() if "=" in l) if (ROOT / ".env").exists() else {}
HOST, PORT, TOKEN = ENV.get("HOST", "172.18.0.1"), int(ENV.get("PORT", 8798)), ENV.get("SERVICE_TOKEN", "")
WIB = dt.timezone(dt.timedelta(hours=7))
# slot -> (production starts, upload time). A video takes about two and a half hours to make; the rest is slack
# for a Google Flow hiccup. One a day: more of the same template risks YouTube's mass-produced content rule.
SLOTS = {"siang": ("07:00", "12:00")}
KEEP_DAYS = 7
PIPE = ROOT / "pipeline"
DB = ROOT / "data" / "whatif.db"
lock = threading.Lock()
state = {"busy": None}


def db():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, slot TEXT, topic TEXT, title TEXT,
        status TEXT, stage TEXT, error TEXT, started_at TEXT, finished_at TEXT, youtube_id TEXT, data TEXT)""")
    return c


def now():
    return dt.datetime.now(WIB)


def update(rid, **f):
    with db() as c:
        c.execute(f"UPDATE runs SET {', '.join(k + '=?' for k in f)} WHERE id=?", (*f.values(), rid))


def stage_of(rid):
    """What the run is doing, read from its logs; image progress counted from files."""
    d = RUNS / rid
    lines = [l for f in ("run.log", "script.log") if (d / f).exists() for l in (d / f).read_text().splitlines()]
    stage = next((l.split()[1] for l in reversed(lines) if l.startswith("STAGE ")), None)
    if not (d / "plan.json").exists():
        return "riset topik"
    if stage is None:
        return "naskah: " + ("verifikasi" if any("verifier" in l for l in lines) else "riset & menulis")
    if stage == "images" and (d / "scenes.json").exists():
        return f"gambar {len(list((d / 'images').glob('*.jpg')))}/{len(load(d / 'scenes.json'))}"
    return {"storyboard": "storyboard", "annotate": "storyboard", "tts": "suara", "clips": "gambar bergerak", "edit": "edit & export"}.get(stage, stage)


def mark_rendered(rid, d, s):
    """Records a finished final.mp4 with its YouTube title, description and tags; /api/ready then serves it."""
    desc = (f"{s['description']}\n\nSemua cerita di channel ini adalah fiksi orisinal. Kesamaan nama, tempat, atau "
            f"kejadian hanyalah kebetulan. Ilustrasi dan suara narator dibuat dengan bantuan AI; efek suara CC0 "
            f"(OpenGameArt, Kenney).\n\nPunya pengalaman yang mirip? Ceritakan di kolom komentar.\n\n"
            f"#horor #ceritahoror #hororindonesia #jangansendirian")
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                         "csv=p=0", d / "final.mp4"]))
    update(rid, status="rendered", stage=None, error=None, finished_at=now().isoformat(), data=json.dumps(
        {"title": s["title"][:100], "description": desc[:4900], "tags": s.get("tags", [])[:15], "duration_s": round(dur)},
        ensure_ascii=False))


def produce(slot):
    rid = f"{now():%Y%m%d}-{slot}-{secrets.token_hex(2)}"
    d = RUNS / rid
    d.mkdir(parents=True)
    with db() as c:
        c.execute("INSERT INTO runs (id, slot, status, stage, started_at) VALUES (?,?,?,?,?)",
                  (rid, slot, "running", "topik", now().isoformat()))
    state["busy"] = rid
    try:
        with db() as c:
            prev = [r[0] for r in c.execute("SELECT topic FROM runs WHERE topic IS NOT NULL")]
        topic = plan(prev, d)["topic"]
        update(rid, topic=topic)
        log(rid, "topic:", topic)
        with open(d / "script.log", "w") as f:
            subprocess.run([sys.executable, PIPE / "script.py", rid, topic, "6.5"], stdout=f, stderr=subprocess.STDOUT,
                           cwd=PIPE, check=True)
        s = load(d / "script.json")
        update(rid, title=s["title"])
        with open(d / "run.log", "w") as f:
            subprocess.run([PIPE / "run_all.sh", rid], stdout=f, stderr=subprocess.STDOUT, cwd=PIPE, check=True)
        mark_rendered(rid, d, s)
        log(rid, "rendered", s["title"])
    except Exception as e:
        tail = ""
        for f in ("run.log", "script.log"):
            if (d / f).exists():
                tail = " | ".join((d / f).read_text().strip().splitlines()[-3:])
                break
        update(rid, status="failed", stage=None, finished_at=now().isoformat(), error=f"{e} :: {tail}"[:1000])
        log(rid, "failed:", e, tail)
    finally:
        state["busy"] = None


def start(slot):
    with lock:
        if state["busy"]:
            return None
        state["busy"] = "starting"
    threading.Thread(target=produce, args=(slot,), daemon=True).start()
    return True


def scheduler():
    """Starts each slot's production at its time, once a day; also tidies runs older than a week."""
    done = set()
    while True:
        t = now()
        for slot, (make, _) in SLOTS.items():
            key = (t.date(), slot)
            hh, mm = map(int, make.split(":"))
            due = t.replace(hour=hh, minute=mm, second=0, microsecond=0)
            # PAUSE_PRODUCTION=1 in .env stops the daily run (e.g. while moving to a new channel); /api/run still works.
            if key not in done and ENV.get("PAUSE_PRODUCTION") != "1" and due <= t < due + dt.timedelta(minutes=30):
                done.add(key)
                if not start(slot):
                    log("scheduler: busy, skipped", slot)
                else:
                    log("scheduler: started", slot)
        if t.minute == 0:
            cutoff = time.time() - KEEP_DAYS * 86400
            for d in RUNS.glob("2*-*"):
                if d.is_dir() and d.stat().st_mtime < cutoff:
                    shutil.rmtree(d, ignore_errors=True)
        time.sleep(30)


def preview_key(rid):
    return hmac.new(TOKEN.encode(), rid.encode(), hashlib.sha256).hexdigest()[:32]


def view(r):
    data = json.loads(r["data"]) if r["data"] else {}
    yt = r["youtube_id"]
    started, finished = r["started_at"], r["finished_at"]
    dur = round((dt.datetime.fromisoformat(finished) - dt.datetime.fromisoformat(started)).total_seconds()) if finished else None
    return {"id": r["id"], "slot": r["slot"], "topic": r["topic"], "title": r["title"], "status": r["status"],
            "stage": stage_of(r["id"]) if r["status"] == "running" else None, "error": r["error"],
            "started_at": started, "finished_at": finished, "duration_s": dur, "video_s": data.get("duration_s"),
            "youtube_id": yt, "youtube_url": f"https://www.youtube.com/watch?v={yt}" if yt else None,
            "thumb": f"https://i.ytimg.com/vi/{yt}/mqdefault.jpg" if yt else None,
            # A download path for the dashboard's public link, offered only while the video waits for its upload.
            "preview": f"{r['id']}/{preview_key(r['id'])}.mp4"
            if r["status"] == "rendered" and TOKEN and (RUNS / r["id"] / "final.mp4").exists() else None}


def overview():
    t = now()
    today = t.date().isoformat()
    week = (t - dt.timedelta(days=6)).date().isoformat()
    with db() as c:
        rows = [view(r) for r in c.execute("SELECT * FROM runs WHERE started_at >= ? ORDER BY started_at", (week,))]
        last = c.execute("SELECT * FROM runs WHERE status='uploaded' ORDER BY finished_at DESC LIMIT 1").fetchone()
    todays = [r for r in rows if r["started_at"][:10] == today]
    schedule = []
    for slot, (make, up) in SLOTS.items():
        r = next((x for x in reversed(todays) if x["slot"] == slot), None)
        hh, mm = map(int, up.split(":"))
        late = t > t.replace(hour=hh, minute=mm) + dt.timedelta(minutes=45)
        schedule.append({"slot": slot, "produce": make, "upload": up, "run": r,
                         "status": r["status"] if r else ("missed" if late else "waiting")})
    nxt = None
    for day in range(2):
        for slot, (make, up) in SLOTS.items():
            hh, mm = map(int, up.split(":"))
            at = (t + dt.timedelta(days=day)).replace(hour=hh, minute=mm, second=0, microsecond=0)
            if at > t and not nxt:
                nxt = {"at": at.isoformat(), "slot": slot, "upload": up, "produce": make}
    count = lambda lst, s: sum(1 for x in lst if x["status"] == s)
    return {"now": t.isoformat(), "service": {"busy": state["busy"], "stage": stage_of(state["busy"]) if state["busy"] and state["busy"] != "starting" else None},
            "today": {"uploaded": count(todays, "uploaded"), "failed": count(todays, "failed"), "planned": len(SLOTS)},
            "week": {"uploaded": count(rows, "uploaded"), "failed": count(rows, "failed")},
            "next": nxt, "last": view(last) if last else None, "schedule": schedule}


def history(q):
    page = max(1, int(q.get("page", ["1"])[0] or 1))
    size = int(q.get("pageSize", ["10"])[0] or 10)
    size = size if size in (10, 25, 50, 100) else 10
    where, args = [], []
    if q.get("status", [""])[0] in ("uploaded", "rendered", "running", "failed"):
        where.append("status=?"); args.append(q["status"][0])
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", q.get("date", [""])[0]):
        where.append("substr(started_at,1,10)=?"); args.append(q["date"][0])
    sql = "FROM runs" + (" WHERE " + " AND ".join(where) if where else "")
    with db() as c:
        total = c.execute("SELECT COUNT(*) " + sql, args).fetchone()[0]
        pages = max(1, -(-total // size))
        page = min(page, pages)
        rows = [view(r) for r in c.execute(f"SELECT * {sql} ORDER BY started_at DESC LIMIT ? OFFSET ?",
                                           (*args, size, (page - 1) * size))]
    return {"page": page, "pageSize": size, "total": total, "totalPages": pages, "runs": rows}


def logs(q):
    n = min(1000, max(20, int(q.get("lines", ["200"])[0] or 200)))
    try:
        out = subprocess.run(["journalctl", "--user", "-u", "whatif", "-n", str(n), "--no-pager", "-o", "cat"],
                             capture_output=True, text=True, timeout=20).stdout
        return {"lines": [l for l in out.splitlines() if l]}
    except Exception as e:
        return {"lines": [], "error": str(e)}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body):
        b = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def send_file(self, f, name):
        """The whole file, or the one byte range asked for, so a browser can seek in the video."""
        size = f.stat().st_size
        start, end = 0, size - 1
        rng = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if rng and (rng[1] or rng[2]):
            start, end = (int(rng[1]), min(int(rng[2] or end), end)) if rng[1] else (max(0, size - int(rng[2])), end)
        self.send_response(206 if rng and start <= end else 200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Disposition", f'inline; filename="{name}"')
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with open(f, "rb") as fh:
            fh.seek(start)
            left = end - start + 1
            while left > 0 and (chunk := fh.read(min(1 << 20, left))):
                self.wfile.write(chunk)
                left -= len(chunk)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n < 1e5 else {}

    def route(self, method):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/health":
            return self.send(200, {"ok": True, "busy": state["busy"]})
        m = re.fullmatch(r"/api/preview/([\w-]+)/(\w+)\.mp4", u.path)
        if method == "GET" and m and TOKEN and hmac.compare_digest(m[2], preview_key(m[1])):
            with db() as c:
                r = c.execute("SELECT status FROM runs WHERE id=?", (m[1],)).fetchone()
            f = RUNS / m[1] / "final.mp4"
            if not r or r["status"] != "rendered" or not f.exists():
                return self.send(404, {"error": "preview no longer available"})
            return self.send_file(f, f"whatif-{m[1]}.mp4")
        if not TOKEN or self.headers.get("X-Token") != TOKEN:
            return self.send(401, {"error": "bad token"})
        if method == "POST" and u.path == "/api/run":
            slot = self.body().get("slot")
            if slot not in SLOTS:
                return self.send(400, {"error": f"slot must be one of {list(SLOTS)}"})
            return self.send(202, {"ok": True}) if start(slot) else self.send(409, {"error": "a production is already running"})
        if method == "GET" and u.path == "/api/ready":
            slot = q.get("slot", [""])[0]
            # UPLOAD_FROM=YYYY-MM-DD in .env holds uploads back until that day (a new channel warming up).
            if now().date().isoformat() < ENV.get("UPLOAD_FROM", ""):
                return self.send(404, {"error": f"uploads held until {ENV['UPLOAD_FROM']}"})
            with db() as c:
                r = c.execute("SELECT * FROM runs WHERE status='rendered' AND slot=? ORDER BY finished_at DESC LIMIT 1",
                              (slot,)).fetchone()
            if not r:
                return self.send(404, {"error": f"no finished video waiting for slot {slot}"})
            data = json.loads(r["data"])
            thumb = (RUNS / r["id"] / "thumbnail.jpg").exists()
            return self.send(200, {"id": r["id"], **data,
                                   "video_url": f"http://{HOST}:{PORT}/api/videos/{r['id']}.mp4",
                                   "thumbnail_url": f"http://{HOST}:{PORT}/api/videos/{r['id']}/thumbnail.jpg" if thumb else ""})
        m = re.fullmatch(r"/api/videos/([\w-]+)(\.mp4|/thumbnail\.jpg)", u.path)
        if method == "GET" and m:
            f = RUNS / m[1] / ("final.mp4" if m[2] == ".mp4" else "thumbnail.jpg")
            if not f.exists():
                return self.send(404, {"error": "video not found"})
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4" if f.suffix == ".mp4" else "image/jpeg")
            self.send_header("Content-Length", str(f.stat().st_size))
            self.end_headers()
            with open(f, "rb") as fh:
                shutil.copyfileobj(fh, self.wfile)
            return
        m = re.fullmatch(r"/api/videos/([\w-]+)/(uploaded|failed)", u.path)
        if method == "POST" and m:
            b = self.body()
            if m[2] == "uploaded":
                update(m[1], status="uploaded", youtube_id=str(b.get("youtube_id", "")))
            else:
                update(m[1], status="failed", error=("Upload gagal: " + str(b.get("error", "upload failed")))[:1000])
            log(m[1], "->", m[2])
            return self.send(200, {"ok": True})
        if method == "GET" and u.path.startswith("/api/monitor/"):
            part = u.path.rsplit("/", 1)[1]
            fn = {"overview": lambda: overview(), "history": lambda: history(q), "logs": lambda: logs(q)}.get(part)
            if fn:
                return self.send(200, fn())
        self.send(404, {"error": "not found"})

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")


def main():
    with db() as c:  # a restart interrupts whatever was running
        c.execute("UPDATE runs SET status='failed', error='service restarted mid-run', stage=NULL WHERE status='running'")
    threading.Thread(target=scheduler, daemon=True).start()
    log(f"whatif listening on {HOST}:{PORT}; productions at " + ", ".join(f"{s} {m} (upload {u})" for s, (m, u) in SLOTS.items()))
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()


if __name__ == "__main__":
    main()
