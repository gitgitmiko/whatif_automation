"""The next day's five Shorts, researched and judged at 19:00 -> data/ideas/<tomorrow>.json

  riset  yt-dlp reads the latest Shorts of proven explainer channels and marks the outliers (views far above the
         channel's own median), plus this month's most-viewed Shorts for a few POV / fact searches; the opening lines
         of the biggest ones are fetched to see how they hook
  ide    Sonnet (with web search) turns what makes those winners and what is viral now into 10 "kalau kamu jadi
         <profesi>" ideas (8 fakta, 2 horor)
  naskah Sonnet writes a full draft script for every idea
  juri   Opus scores every draft for its chance of views; the best 4 fakta go to slot1-slot4, the best horor to
         slot5, and Opus fact-checks each winner (a draft that fails the check gives way to the next best)

server.py's productions (01:00-07:00) then render each slot's checked script (produce.py --script).

  .venv/bin/python shorts/ideas.py [YYYY-MM-DD]     # default: tomorrow
"""
import base64, datetime as dt, json, statistics, subprocess, sys, time, urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from common import STYLE_REMOTION_FROM, load, log, save  # noqa: E402
from peran import ask_json, asker  # noqa: E402
from produce import ENDING_BY_SLOT, SERIES, WORLDS, brief_for, check_draft, write_draft  # noqa: E402

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
2. Terjemahkan jadi 10 ide POV PROFESI untuk besok: 8 bermode "fakta" dan 2 bermode "horor". Kesepuluh ide harus beda profesi dan mencakup ketiga kelompok ini:
   - satu profesi sehari-hari yang akrab di Indonesia (driver ojol, kasir minimarket, tukang parkir, satpam, petugas tol, montir bengkel, penjual bakso, kurir paket, petugas SPBU, dll.),
   - satu profesi berbahaya atau berisiko tinggi (pilot, pemadam kebakaran, penyelam, tim SAR, teknisi PLN di tiang, ABK kapal, penambang, petugas jalan tol malam, dll.),
   - satu profesi di balik layar yang jarang dilihat orang (petugas menara ATC, dokter IGD, operator bendungan, penjaga mercusuar, teknisi lift, petugas forensik, penerjemah bahasa isyarat, dll.).
   Rumus tiap ide: PROFESI + WAKTU ATAU KEADAAN EKSTREM + KEJADIAN TAK TERDUGA (dokter IGD saat malam tahun baru, kasir minimarket pukul 02.00, kurir saat banjir). Ide bermode "fakta": berpusat pada SATU momen krisis atau keputusan yang benar-benar bisa dialami profesi itu, dijelaskan dengan 4+ fakta nyata (prosedur, angka, alat, aturan). Ide bermode "horor": cerita horor FIKSI orisinal di pekerjaan nyata (paling cocok profesi shift malam atau tempat sepi), ketakutan dari detail janggal (CCTV, jam, panggilan, pintu terkunci, suara dari ruang kosong) tanpa darah, sadis, atau agama/ritual tertentu, tetap dengan 2-3 fakta nyata tentang prosedur atau alat profesinya. Boleh pakai pencarian web untuk memastikan faktanya.
   Tiap ide masuk SATU seri: {SERIES}.
3. Hormati profesinya (horor pun tanpa humor dan tanpa merendahkan): nadanya kagum dan empatik ("ternyata berat banget"), BUKAN mengejek atau merendahkan. Jangan menyebut perusahaan/merek tertentu secara negatif.
4. Kalau ada "performa_channel_sendiri" (data YouTube Analytics video channel ini), pakai pembagian 70/20/10: sekitar 70% ide (7 dari 10) adalah VARIASI dari yang terbukti paling banyak ditonton dan paling lama ditonton di channel ini (seri, kelompok profesi, jenis momen, atau mode yang sama, tapi topik baru), 2-3 ide EKSPERIMEN (profesi, seri, atau sudut yang belum dicoba); kira-kira sekali dalam sepuluh ide, eksperimennya boleh IDE GILA (misalnya penjaga penjara tahun 2099, petugas di stasiun luar angkasa). Perhatikan juga "turun_di_detik": kalau penonton banyak pergi di detik awal, hook-nya yang harus lebih kuat. Tulis alasannya di "insight".
5. DILARANG mengulang atau sangat mirip dengan topik yang sudah pernah dibuat (daftar diberikan). Hindari politik, agama, SARA, tragedi nyata tertentu (kecelakaan/bencana spesifik yang bisa dicari namanya), polisi/tentara dalam konteks kontroversial, hal jorok, dan sadis.
6. DUNIA 3D YANG TERSEDIA: video dianimasikan sebagai 3D real-time di dunia yang sudah dibangun. Tiap ide WAJIB menyebut "world": nama dunia yang paling cocok dari daftar ini, atau "flow" kalau benar-benar tidak ada yang cocok (ide itu lalu digambar dengan cara lama). UTAMAKAN ide yang cocok dengan dunia yang tersedia; konten kereta sedang paling banyak ditonton di channel ini, jadi beri kereta porsi besar selama datanya masih paling kuat, tapi jangan mengulang momen yang sama.
{WORLDS}

Balas HANYA JSON:
{"insight":"3-5 kalimat: pola yang sedang menang hari ini",
 "ideas":[{"mode":"fakta|horor","seri":"salah satu nama seri","world":"nama dunia atau flow","topic":"nama profesi singkat, misalnya pilot pesawat",
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
# The 3D worlds count only once tomorrow (the day being researched) is on or after STYLE_REMOTION_FROM; before that
# the research, drafts and judging stay exactly as they were.
ACTIVE = (dt.date.today() + dt.timedelta(days=1)).isoformat() >= STYLE_REMOTION_FROM
_WORLD_RULE = SYS[SYS.index("6. DUNIA 3D YANG TERSEDIA"):SYS.index("\n\nBalas HANYA JSON:") + 1]


def research_sys():
    if not ACTIVE:
        return SYS.replace(_WORLD_RULE, "").replace('"world":"nama dunia atau flow",', "")
    return SYS.replace("{WORLDS}", "\n".join(f"   - {k}: {w['cocok']}" for k, w in WORLDS.items()))


def world_of(idea):
    """The idea's 3D world when the worlds are active and it names one that exists; None means the old picture
    styles (Flow, then cartoon)."""
    w = (idea or {}).get("world")
    return w if ACTIVE and w in WORLDS else None


ENDING = ENDING_BY_SLOT["slot1"]   # every slot ends on the loop

JUDGE_SYS = """Kamu juri YouTube Shorts "Gimana Jadinya?" (POV profesi, animasi 3D 30-40 detik, penonton Indonesia) yang
galak, dengan target VIEWS setinggi mungkin. Diberi beberapa naskah. Nilai tiap naskah 1-10 dari peluangnya ditonton
banyak orang dan ditonton sampai habis: kalimat pertama yang langsung di tengah krisis dengan taruhan nyata, rasa
penasaran yang menahan penonton, satu belokan yang mengejutkan, fakta yang bikin "ternyata begitu", judul yang bikin
klik, dan nyambung dengan yang sedang ramai (nilai plus). Potong nilai keras untuk: hook lemah atau pembuka suasana,
cerita datar, premis mirip yang sudah dibuat, nada mengejek profesi, atau fakta yang meragukan.
Bandingkan antar naskah; jangan beri semua nilai yang sama.
Balas HANYA JSON: {"nilai":[angka per naskah sesuai urutan],"alasan":["1 kalimat per naskah, sesuai urutan"]}"""


def judge(drafts):
    """The Peran AI judge (Opus by default) scores every draft; fills nilai/alasan, returns who judged."""
    listing = "\n\n".join(
        f"NASKAH {k + 1} [{x['idea']['mode']}] \"{x['draft'].get('yt_title') or x['draft'].get('title')}\"\n"
        + "\n".join(sc.get("text", "") for sc in x["draft"].get("scenes", [])) for k, x in enumerate(drafts))
    try:
        j, who = ask_json("juri", JUDGE_SYS, listing)
    except Exception as e:  # noqa: BLE001 - without a judge the drafts keep their writing order
        log(f"juri gagal: {str(e)[:200]}")
        return None
    nilai, alasan = j.get("nilai") or [], j.get("alasan") or []
    for k, x in enumerate(drafts):
        x["nilai"] = nilai[k] if k < len(nilai) else None
        x["alasan"] = alasan[k] if k < len(alasan) else ""
    log(f"juri {who}: {nilai}")
    return who


def pick(drafts):
    """slot -> checked draft: best 4 fakta to slot1-slot4, best horor to slot5; a failed fact-check gives way to the
    next best of the same mode, and a missing horor falls back to the best fakta left."""
    best = lambda mode: sorted((x for x in drafts if x["idea"]["mode"] == mode), key=lambda x: x.get("nilai") or 0, reverse=True)
    pools = {"fakta": best("fakta"), "horor": best("horor")}
    chosen = {}
    for slot in SLOTS:
        want = "horor" if slot == "slot5" else "fakta"
        for mode in ([want, "fakta"] if want == "horor" else [want]):
            while pools[mode] and slot not in chosen:
                x = pools[mode].pop(0)
                try:
                    x["script"] = check_draft(x["draft"], True, ENDING, mode, asker("cek"), world=world_of(x["idea"]))
                except Exception as e:  # noqa: BLE001 - the next best takes the slot
                    log(f"cek fakta gagal untuk '{x['idea']['topic']}': {str(e)[:200]}")
                    x["status"] = "gagal cek fakta"
                    continue
                x["slot"], chosen[slot] = slot, x
    return chosen


def main(day=None):
    day = day or (dt.date.today() + dt.timedelta(days=1)).isoformat()  # researched the evening before
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
    out, who = ask_json("riset", research_sys(), json.dumps(brief, ensure_ascii=False), web=True)
    log(f"riset oleh {who}")
    ideas = [i for i in out.get("ideas", []) if i.get("topic")]
    if not ideas:
        raise RuntimeError("no ideas in Claude's reply")
    for i in ideas:
        i["mode"] = "horor" if i.get("mode") == "horor" else "fakta"
        if i.get("seri") not in SERIES:
            i.pop("seri", None)
        log(f"ide [{i['mode']}/{world_of(i) or 'flow'}]: kamu jadi {i['topic']} | {i.get('hook', '')}")
    print("STAGE naskah", flush=True)
    drafts = []
    for i in ideas:
        try:
            drafts.append({"idea": i, "draft": write_draft(brief_for(i), True, ENDING, i["mode"], asker("penulis"), world=world_of(i))})
        except Exception as e:  # noqa: BLE001 - one bad draft does not stop the research
            log(f"draf '{i['topic']}' gagal: {str(e)[:200]}")
    if not drafts:
        raise RuntimeError("no draft script could be written")
    print("STAGE juri", flush=True)
    juri = judge(drafts)
    chosen = pick(drafts)
    if not chosen:
        raise RuntimeError("no draft passed the fact-check")
    slots = [{**x["idea"], "slot": s, "mode": x["script"].get("mode") or x["idea"]["mode"], "nilai": x.get("nilai"),
              "alasan": x.get("alasan", ""), "script": x["script"]} for s, x in chosen.items()]
    for x in slots:
        log(f"{x['slot']} ({x['nilai']}): kamu jadi {x['topic']} | {x['script'].get('yt_title')}")
    summary = [{"topic": x["idea"]["topic"], "mode": x["idea"]["mode"], "title": x["draft"].get("yt_title") or x["draft"].get("title"),
                "hook": (x["draft"].get("scenes") or [{}])[0].get("text", ""), "nilai": x.get("nilai"), "alasan": x.get("alasan", ""),
                "slot": x.get("slot"), "status": x.get("status")} for x in drafts]
    save(IDEAS / f"{day}.json", {"date": day, "insight": out.get("insight"), "juri": juri or "tidak ada (urutan tulis)",
                                 "ideas": slots, "drafts": summary, "data": {"outliers": outliers, "search": hits}})
    log("saved", IDEAS / f"{day}.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
