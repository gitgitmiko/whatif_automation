"""Step 0: pre-production research for the horror channel "Jangan Sendirian". Finds what Indonesians search for in
horror (YouTube autocomplete), which themes the big horror podcasts (RJL 5, Lentera Malam, ...) pull views with, and
how existing videos on each candidate did, then fixes the package (premise, title, thumbnail hook, promise) before any
script is written. The big podcasts are research only: their stories are never retold."""
import random, string, sys, urllib.parse, urllib.request
from common import *

SEEDS = ["bagaimana jika kamu", "cerita horor", "pengalaman horor", "kisah horor", "horor pov"]
# Theme research only: what these channels' popular titles are about, never their stories.
TREND_QUERIES = ["rjl 5 horor", "lentera malam horor", "nessie judge horor", "malam mencekam horor",
                 "cerita horor kos", "cerita horor pendakian"]
PREFIX = "bagaimana jika kamu"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept-Language": "id"}

SAFETY = """Hindari: bunuh diri atau melukai diri, kekerasan grafis atau darah berlebihan (gore), konten seksual, SARA dan menjelekkan agama atau suku, ritual sesat yang bisa ditiru, anak sebagai korban, tokoh nyata, kejadian/kasus nyata atau tragedi yang baru terjadi, dan menuduh tempat nyata yang spesifik (sekolah, rumah sakit, hotel bernama) angker. Tempat boleh berupa jenis tempat yang umum (kos lama, pasar malam, jalur pendakian, rumah nenek di desa)."""

ORIGINAL = """Cerita WAJIB ORISINAL. Judul populer dari podcast horor (RJL 5, Lentera Malam, dll.) hanya dipakai untuk membaca TEMA yang diminati (mis. kos, pendakian, pesugihan, kerja shift malam, KKN), JANGAN mengambil atau menceritakan ulang cerita, tokoh, atau alur mereka. Hindari juga cerita viral yang punya penulis jelas (mis. KKN di Desa Penari). Folklor umum (kuntilanak, pocong, genderuwo, wewe gombel, tuyul, banaspati, kuyang, dll.) boleh dipakai."""

IDEAS_SYS = f"""Kamu produser channel YouTube horor berbahasa Indonesia "Jangan Sendirian": cerita horor POV ORISINAL, seri "Bagaimana jika kamu ...", video 6-7 menit. Penonton ADALAH tokohnya ("kamu"), dan di gambar "kamu" diperankan maskot Kepo, wibu penakut yang sok berani.
Kamu diberi: pencarian NYATA dari autocomplete YouTube Indonesia, judul-judul populer channel horor besar beserta views (untuk membaca tema yang laku), dan daftar premis yang sudah dibuat.
Usulkan 12 kandidat premis yang:
- Temanya terbukti diminati (dekat dengan pencarian nyata atau tema judul populer), tapi premis dan ceritanya baru.
- Situasi sehari-hari orang Indonesia yang bisa dibayangkan penonton sendiri (ngekos, pulang malam, mudik, ronda, kerja shift, nginep di rumah nenek, KKN, mendaki), dengan satu aturan atau ancaman yang jelas dan bikin penasaran.
- Bisa jadi cerita menegangkan 6-7 menit dengan eskalasi dan twist.
- Bervariasi temanya dan tidak mirip premis yang sudah dibuat.
{ORIGINAL}
{SAFETY}
"query" = frasa pencarian YouTube yang paling mungkin diketik penonton untuk tema itu (ambil dari daftar bila ada).
Balas HANYA JSON: {{"candidates":[{{"topic":"Bagaimana jika kamu ...","query":"...","theme":"tema","why":"alasan singkat, sebut data"}}]}}"""

PICK_SYS = f"""Kamu ahli strategi konten YouTube horor. Channel kita baru, jadi butuh premis yang temanya dicari orang TAPI masih bisa kita menangkan dengan sudut POV yang segar.
Untuk setiap kandidat kamu diberi hasil pencarian YouTube Indonesia: judul pesaing, views, umur, durasi, nama channel.
Cara menilai: views tinggi = tema diminati; ada video baru atau channel kecil yang tetap dapat views = tema masih hidup; hindari tema yang hasil teratasnya penuh video raksasa yang baru dengan sudut yang persis sama.
{ORIGINAL}
{SAFETY}
Pilih SATU, lalu tetapkan paketnya:
- "title": judul YouTube maks 60 karakter. Kata kunci tema di depan atau sangat awal. Bahasa Indonesia natural, mencekam, memancing rasa penasaran, JUJUR (cerita benar-benar memberikannya). Huruf besar biasa. Contoh gaya: "Bagaimana Jika Kamu Ngekos di Kamar yang Terlalu Murah?"
- "hook": teks thumbnail 2-4 kata HURUF BESAR berupa PREMIS KONKRET atau ATURAN yang menyeramkan (contoh gaya: "JANGAN BUKA JAM 3", "KOS 200 RIBU", "DIA IKUT PULANG", "SATU MALAM DI PASAR"). Bisa dipahami tanpa judul.
- "highlight": satu kata dari hook untuk diberi warna merah.
- "visual": adegan sisi KANAN thumbnail dalam BAHASA INGGRIS maks 35 kata: momen paling mencekam, konkret, latar Indonesia, sosok atau ancaman terlihat jelas tapi tanpa darah atau gore. Jangan deskripsikan stickman utama (otomatis close-up di kiri). Tanpa teks.
- "promise": satu kalimat: pengalaman yang dijanjikan judul+thumbnail kepada penonton, yang WAJIB ditepati naskah.
- "angle": apa yang membuat cerita kita berbeda dari pesaing.
- "peak": twist atau momen paling menyeramkan, yang ditaruh sekitar 2/3 sampai 3/4 video.
Balas HANYA JSON: {{"topic":"Bagaimana jika kamu ...","query":"...","title":"...","hook":"...","highlight":"...","visual":"...","promise":"...","angle":"...","peak":"...","reason":"alasan pilihan, sebut data"}}"""


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read().decode("utf-8", "replace")


def suggest(q):
    u = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
        {"client": "firefox", "ds": "yt", "hl": "id", "gl": "ID", "q": q})
    return json.loads(fetch(u))[1]


def views(text):
    digits = re.sub(r"\D", "", text or "")
    return int(digits) if digits else 0


def days(text):
    """'9 thn lalu', '4 mgg lalu', '11 jam lalu' -> rough age in days."""
    m = re.match(r"(\d+)\s*(\w+)", text or "")
    if not m:
        return None
    unit = {"thn": 365, "tahun": 365, "bln": 30, "bulan": 30, "mgg": 7, "minggu": 7, "hari": 1}.get(m[2], 0)
    return int(m[1]) * unit


def search(q, n=10):
    """Top long-form results for a query on YouTube Indonesia."""
    u = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": q, "hl": "id", "gl": "ID"})
    data = json.loads(re.search(r"var ytInitialData = (\{.*?\});</script>", fetch(u)).group(1))
    out = []

    def walk(o):
        if isinstance(o, dict):
            if "videoRenderer" in o and len(out) < n:
                v = o["videoRenderer"]
                out.append({"title": "".join(r["text"] for r in v["title"]["runs"]),
                            "views": views(v.get("viewCountText", {}).get("simpleText")),
                            "age_days": days(v.get("publishedTimeText", {}).get("simpleText")),
                            "length": v.get("lengthText", {}).get("simpleText"),
                            "channel": v.get("ownerText", {}).get("runs", [{}])[0].get("text")})
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(data)
    return out


def demand():
    """Real horror searches: each seed alone and followed by every letter."""
    found = []
    for seed in SEEDS:
        for q in [seed] + [f"{seed} {c}" for c in string.ascii_lowercase]:
            try:
                found += suggest(q)
            except Exception as e:
                log("suggest failed", q, e)
            time.sleep(random.uniform(0.2, 0.6))
    return list(dict.fromkeys(s for s in found if s not in SEEDS))


def trends():
    """Titles and views of popular horror videos: which themes pull an audience (theme research only)."""
    out = []
    for q in TREND_QUERIES:
        try:
            out += [{k: v[k] for k in ("title", "views", "channel")} for v in search(q, 15)]
        except Exception as e:
            log("trend search failed", q, e)
        time.sleep(random.uniform(1, 3))
    return sorted({v["title"]: v for v in out}.values(), key=lambda v: -v["views"])[:60]


def plan(previous, d):
    """Researches and fixes the video's package; saves research.json and plan.json in the run folder."""
    if (d / "plan.json").exists():
        return load(d / "plan.json")
    pool = demand()
    popular = trends()
    log("research: searches found", len(pool), "popular titles", len(popular))
    ideas = claude_json("sonnet", IDEAS_SYS, json.dumps({"pencarian_nyata": pool, "judul_populer": popular,
                                                        "sudah_dibuat": previous[-200:]}, ensure_ascii=False))["candidates"]
    done = {p.lower() for p in previous}
    ideas = [x for x in ideas if x["topic"].lower().startswith(PREFIX) and x["topic"].lower() not in done]
    for x in ideas:
        try:
            x["competition"] = search(x["query"])
        except Exception as e:
            x["competition"] = []
            log("search failed", x["query"], e)
        time.sleep(random.uniform(1, 3))
    save(d / "research.json", {"searches": pool, "popular": popular, "candidates": ideas})
    p = claude_json("opus", PICK_SYS, json.dumps({"kandidat": ideas}, ensure_ascii=False))
    p["topic"] = " ".join(p["topic"].split())
    if not p["topic"].lower().startswith(PREFIX) or p["topic"].lower() in done:
        raise ValueError(f"unusable topic: {p['topic']}")
    p["title"] = p["title"][:90]
    save(d / "plan.json", p)
    log("plan:", p["title"], "|", p["hook"], "|", p.get("reason", "")[:300])
    return p


if __name__ == "__main__":
    print(json.dumps(plan([], run_dir(sys.argv[1])), ensure_ascii=False, indent=1))
