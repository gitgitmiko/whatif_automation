"""The day's three ideas, picked at 06:00 from Shorts that are pulling big views right now -> data/ideas/<date>.json

  riset  yt-dlp reads the latest Shorts of proven explainer channels and marks the outliers (views far above the
         channel's own median), plus this month's most-viewed Shorts for a few POV / fact searches; the opening lines
         of the biggest ones are fetched to see how they hook
  ide    Claude (with web search) turns what makes those winners work into three "kalau kamu jadi <profesi>" ideas,
         one per slot (slot1-slot5), each with its angle, a draft hook and the videos it learned from

produce.py then writes each slot's Short from its idea (server.py passes --idea).

  .venv/bin/python shorts/ideas.py [YYYY-MM-DD]
"""
import base64, datetime as dt, json, statistics, subprocess, sys, time, urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from common import claude_json, load, log, save  # noqa: E402
from produce import MODE_BY_SLOT, SERIES  # noqa: E402

IDEAS = ROOT / "data" / "ideas"
YTDLP = ROOT / ".venv" / "bin" / "yt-dlp"
SLOTS = ["slot1", "slot2", "slot3", "slot4", "slot5"]  # uploads 10:00, 12:00, 15:00, 18:00, 20:00
# Explainer channels whose Shorts reliably pull millions (median views measured 2026-11-15).
CHANNELS = ["zackdfilms", "MarkRober", "kurzgesagt", "TheActionLab", "SciShow", "AsapSCIENCE", "TEDEd", "kokbisa"]
SEARCHES = ["pov kamu jadi", "kalau kamu jadi", "pov jadi pilot", "sehari jadi", "a day in the life of",
            "pov you are a pilot", "pov you are a firefighter", "what it is like to be a"]
# YouTube search filter: sort by views; uploaded this month, videos only, under 4 minutes.
THIS_MONTH = base64.b64encode(bytes([0x08, 0x03, 0x12, 0x06, 0x08, 0x04, 0x10, 0x01, 0x18, 0x01])).decode()


def ytdlp(url, n):
    try:
        out = subprocess.run([YTDLP, "--flat-playlist", "-j", "--playlist-end", str(n), "--sleep-requests", "1", url],
                             capture_output=True, text=True, timeout=300).stdout
    except subprocess.TimeoutExpired:
        return []
    return [json.loads(l) for l in out.splitlines() if l.startswith("{")]


def channel_outliers():
    rows = []
    for c in CHANNELS:
        vids = [v for v in ytdlp(f"https://www.youtube.com/@{c}/shorts", 60) if v.get("view_count")]
        if len(vids) < 5:
            log(f"channel {c}: nothing read")
            continue
        med = statistics.median(v["view_count"] for v in vids)
        # Recent uploads (the tab is newest first) that beat the channel's own median: what works now.
        for rank, v in enumerate(vids):
            score = v["view_count"] / med
            if score >= 1.5 or rank < 3 and score >= 1:
                rows.append({"channel": c, "title": v["title"], "views": v["view_count"], "x_median": round(score, 1),
                             "recency_rank": rank, "id": v["id"]})
        log(f"channel {c}: {len(vids)} shorts, median {med:,.0f}")
        time.sleep(2)
    return sorted(rows, key=lambda r: -r["x_median"])[:40]


def search_hits():
    rows = []
    for q in SEARCHES:
        url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": q, "sp": THIS_MONTH})
        for v in ytdlp(url, 15):
            if (v.get("duration") or 999) <= 90 and (v.get("view_count") or 0) >= 30000:
                rows.append({"search": q, "channel": v.get("channel"), "title": v["title"], "views": v["view_count"],
                             "id": v["id"]})
        time.sleep(2)
    return sorted(rows, key=lambda r: -r["views"])[:30]


def openings(rows, n=12):
    """The first ~45 spoken words of the biggest videos: their hooks."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return
    api = YouTubeTranscriptApi()
    for r in rows[:n]:
        try:
            words = " ".join(s.text for s in api.fetch(r["id"], languages=["id", "en", "en-US"])).split()
            r["opening"] = " ".join(words[:45])
        except Exception:  # noqa: BLE001 - captions off or blocked: the title still says enough
            pass


def recent_topics(days=45):
    out = []
    for f in sorted(IDEAS.glob("*.json"))[-days:]:
        out += [i.get("topic") for i in load(f).get("ideas", [])]
    db = ROOT / "data" / "whatif.db"
    if db.exists():
        import sqlite3
        with sqlite3.connect(db) as c:
            out += [r[0] for r in c.execute("SELECT title FROM runs WHERE title IS NOT NULL ORDER BY started_at DESC LIMIT 200")]
    return [t for t in out if t]


SYS = """Kamu kepala riset konten channel YouTube Shorts "Gimana Jadinya?". Formatnya POINT OF VIEW PROFESI: setiap video membuat penonton membayangkan "gimana jadinya kalau KAMU jadi <profesi>" lalu menjalani SATU momen paling menegangkan dari pekerjaan itu, dengan fakta nyata, animasi 3D 30-40 detik, penonton Indonesia.

Kamu menerima data Shorts yang sedang meledak: "outlier_channel" (video terbaru dari channel penjelas besar yang views-nya jauh di atas median channel itu; x_median = berapa kali lipat), "pencarian_bulan_ini" (Shorts paling banyak ditonton bulan ini untuk kata kunci tertentu), dan "opening" (kata-kata pertama video, yaitu hook-nya).

Tugas:
1. Pelajari KENAPA video-video itu menang: momen apa yang memancing rasa penasaran (bahaya, keputusan sepersekian detik, angka gila, rahasia di balik pekerjaan, "ternyata begini caranya"), dan bagaimana hook-nya dibuka.
2. Terjemahkan jadi 5 ide POV PROFESI untuk hari ini, satu per slot (slot1 tayang 10:00, slot2 12:00, slot3 15:00, slot4 18:00, slot5 20:00). Kelima ide harus beda profesi dan mencakup ketiga kelompok ini:
   - satu profesi sehari-hari yang akrab di Indonesia (driver ojol, kasir minimarket, tukang parkir, satpam, petugas tol, montir bengkel, penjual bakso, kurir paket, petugas SPBU, dll.),
   - satu profesi berbahaya atau berisiko tinggi (pilot, pemadam kebakaran, penyelam, tim SAR, teknisi PLN di tiang, ABK kapal, penambang, petugas jalan tol malam, dll.),
   - satu profesi di balik layar yang jarang dilihat orang (petugas menara ATC, dokter IGD, operator bendungan, penjaga mercusuar, teknisi lift, petugas forensik, penerjemah bahasa isyarat, dll.).
   Rumus tiap ide: PROFESI + WAKTU ATAU KEADAAN EKSTREM + KEJADIAN TAK TERDUGA (dokter IGD saat malam tahun baru, kasir minimarket pukul 02.00, kurir saat banjir). Ide slot1 sampai slot4 bermode "fakta": berpusat pada SATU momen krisis atau keputusan yang benar-benar bisa dialami profesi itu, dijelaskan dengan 4+ fakta nyata (prosedur, angka, alat, aturan). Ide slot5 bermode "horor": cerita horor FIKSI orisinal di pekerjaan nyata (paling cocok profesi shift malam atau tempat sepi), ketakutan dari detail janggal (CCTV, jam, panggilan, pintu terkunci, suara dari ruang kosong) tanpa darah, sadis, atau agama/ritual tertentu, tetap dengan 2-3 fakta nyata tentang prosedur atau alat profesinya. Boleh pakai pencarian web untuk memastikan faktanya.
   Tiap ide masuk SATU seri: {SERIES}.
3. Hormati profesinya (horor pun tanpa humor dan tanpa merendahkan): nadanya kagum dan empatik ("ternyata berat banget"), BUKAN mengejek atau merendahkan. Jangan menyebut perusahaan/merek tertentu secara negatif.
4. Kalau ada "performa_channel_sendiri" (data YouTube Analytics video channel ini), pakai pembagian 70/20/10: sekitar 70% ide (3-4 dari 5) adalah VARIASI dari yang terbukti paling banyak ditonton dan paling lama ditonton di channel ini (seri, kelompok profesi, jenis momen, atau mode yang sama, tapi topik baru), 1-2 ide EKSPERIMEN (profesi, seri, atau sudut yang belum dicoba); kira-kira sekali dalam sepuluh ide, eksperimennya boleh IDE GILA (misalnya penjaga penjara tahun 2099, petugas di stasiun luar angkasa). Perhatikan juga "turun_di_detik": kalau penonton banyak pergi di detik awal, hook-nya yang harus lebih kuat. Tulis alasannya di "insight".
5. DILARANG mengulang atau sangat mirip dengan topik yang sudah pernah dibuat (daftar diberikan). Hindari politik, agama, SARA, tragedi nyata tertentu (kecelakaan/bencana spesifik yang bisa dicari namanya), polisi/tentara dalam konteks kontroversial, hal jorok, dan sadis.

Balas HANYA JSON:
{"insight":"3-5 kalimat: pola yang sedang menang hari ini",
 "ideas":[{"slot":"slot1|slot2|slot3|slot4|slot5","mode":"fakta|horor","seri":"salah satu nama seri","topic":"nama profesi singkat, misalnya pilot pesawat",
   "angle":"1-2 kalimat: momen krisis yang dialami dan rasa penasaran yang dijual",
   "hook":"draf kalimat pertama dengan sudut pandang 'kamu': langsung di tengah krisis, ada taruhan nyata (nyawa, uang, waktu, malu), maks 14 kata, tanpa 'gimana jadinya'",
   "facts":["3-5 fakta kunci dengan angka/prosedur, yang sudah kamu cek (horor: fakta nyata tentang profesinya, plus 1 kalimat twist fiksinya)"],
   "inspired_by":[{"title":"...","views":123,"why":"apa yang ditiru: pola, bukan isi"}]}]}"""


def own_performance():
    """The channel's own Shorts from data/analytics (pulled daily by n8n): best and weakest, with where viewers left."""
    f = ROOT / "data" / "analytics" / "videos.json"
    if not f.exists():
        return None
    vids = [v for v in load(f).get("videos", []) if v.get("run") and v.get("views") is not None]
    if len(vids) < 6:
        return None
    def row(v):
        r = {k: v.get(k) for k in ("title", "seri", "mode", "slot", "views", "averageViewPercentage", "averageViewDuration")}
        curve = ROOT / "data" / "analytics" / "retention" / f"{v['video']}.json"
        pts = load(curve).get("curve", []) if curve.exists() else []
        # the first point where fewer than 60% are still watching: where the video loses people
        r["turun_di_detik"] = next((round(p["t"] * (v.get("averageViewDuration") or 0) / max((v.get("averageViewPercentage") or 100) / 100, 0.01), 1)
                                    for p in pts if p.get("watch") is not None and p["watch"] < 0.6), None)
        return r
    vids.sort(key=lambda v: (v.get("views") or 0), reverse=True)
    return {"terbaik": [row(v) for v in vids[:6]], "terlemah": [row(v) for v in vids[-4:]],
            "rata_rata_views": round(sum(v["views"] for v in vids) / len(vids))}


SYS = SYS.replace("{SERIES}", "; ".join(f"{k} = {v}" for k, v in SERIES.items()))


def main(day=None):
    day = day or dt.date.today().isoformat()
    IDEAS.mkdir(parents=True, exist_ok=True)
    print("STAGE riset", flush=True)
    outliers, hits = channel_outliers(), search_hits()
    if len(outliers) + len(hits) < 5:
        raise RuntimeError(f"YouTube gave too little data ({len(outliers)} outliers, {len(hits)} search hits)")
    openings(sorted(outliers + hits, key=lambda r: -r["views"]))
    print("STAGE ide", flush=True)
    brief = {"tanggal": day, "outlier_channel": outliers, "pencarian_bulan_ini": hits,
             "topik_yang_sudah_pernah_dibuat": recent_topics()}
    own = own_performance()
    if own:
        brief["performa_channel_sendiri"] = own
        log(f"own analytics: {len(own['terbaik'])} best, {len(own['terlemah'])} weakest")
    out = claude_json("opus", SYS, json.dumps(brief, ensure_ascii=False), web=True)
    ideas = {i.get("slot"): i for i in out.get("ideas", []) if i.get("topic")}
    if not all(s in ideas for s in SLOTS):  # slots mislabelled: hand them out in order
        ideas = dict(zip(SLOTS, [i for i in out.get("ideas", []) if i.get("topic")]))
    if not ideas:
        raise RuntimeError("no ideas in Claude's reply")
    for s, i in ideas.items():
        i["slot"] = s
        i["mode"] = MODE_BY_SLOT[s] if s in MODE_BY_SLOT else i.get("mode", "fakta")
        if i.get("seri") not in SERIES:
            i.pop("seri", None)
        log(f"{s}: kamu jadi {i['topic']} | {i.get('hook', '')}")
    save(IDEAS / f"{day}.json", {"date": day, "insight": out.get("insight"), "ideas": list(ideas.values()),
                                 "data": {"outliers": outliers, "search": hits}})
    log("saved", IDEAS / f"{day}.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
