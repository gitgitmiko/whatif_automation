"""Step 0: pre-production research. Finds what Indonesians actually search for (YouTube autocomplete), checks how
the existing videos on each candidate did, then fixes the package (topic, title, thumbnail hook, promise) before
any script is written, so the script is made to deliver what the title and thumbnail promise."""
import random, string, sys, urllib.parse, urllib.request
from common import *

SEEDS = ["apa yang terjadi jika", "apa jadinya jika", "bagaimana jika", "apa yang terjadi kalau"]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept-Language": "id"}

SAFETY = """Hindari: bunuh diri atau melukai diri, cara berbahaya yang bisa ditiru, kekerasan grafis, seksual, SARA, agama, politik praktis atau negara/konflik nyata (mis. bubar, merdeka, darurat militer, perang yang sedang terjadi), tokoh nyata yang masih hidup, bencana yang baru terjadi, nasihat medis atau keuangan pribadi."""

IDEAS_SYS = f"""Kamu produser channel YouTube edukasi sains berbahasa Indonesia, seri "Apa yang terjadi jika ...", video 6-7 menit.
Kamu diberi daftar pencarian NYATA dari autocomplete YouTube Indonesia, dan daftar topik yang sudah dibuat.
Usulkan 12 kandidat topik yang:
- Sesuai dengan pencarian nyata yang ada di daftar (permintaan terbukti), atau sangat dekat dengannya.
- Taruhannya besar atau dekat dengan hidup penonton (tubuhmu, rumahmu, Indonesia, hidup sehari-hari, bencana kosmik besar), bukan detail teknis kecil.
- Bisa dijawab dengan sains dan data nyata, cukup untuk 6-7 menit.
- Bervariasi bidangnya, dan tidak mirip topik yang sudah dibuat.
{SAFETY}
"query" = frasa pencarian YouTube yang paling mungkin diketik penonton untuk topik itu (ambil dari daftar bila ada).
Balas HANYA JSON: {{"candidates":[{{"topic":"Apa yang terjadi jika ...","query":"...","field":"bidang","why":"alasan singkat"}}]}}"""

PICK_SYS = f"""Kamu strategi konten YouTube yang ahli. Channel kita kecil dan baru mulai video panjang, jadi kita butuh topik yang dicari orang TAPI masih bisa kita menangkan dengan sudut yang lebih segar atau lebih jelas dari video yang sudah ada.
Untuk setiap kandidat kamu diberi hasil pencarian YouTube Indonesia: judul pesaing, views, umur, durasi, nama channel.
Cara menilai:
- Permintaan: views tinggi di video topik ini = orang mau menonton topik ini.
- Peluang: ada video baru (< 2 tahun) atau dari channel kecil yang tetap dapat views lumayan = topik masih hidup. Kalau semua video top berumur tua, kita bisa jadi versi yang lebih baru dan lebih jelas.
- Hindari topik yang hasil teratasnya penuh video raksasa yang baru dan persis sama sudutnya.
{SAFETY}
Pilih SATU, lalu tetapkan paketnya:
- "title": judul YouTube maks 60 karakter. Kata kunci pencarian di depan. Bahasa Indonesia natural, memancing rasa ingin tahu, JUJUR (isi video harus benar-benar menjawabnya). Huruf besar biasa (bukan semua kapital).
- "hook": teks thumbnail 2-4 kata HURUF BESAR berupa PREMIS KONKRET yang menyebut subjek topik, idealnya dengan angka, "VS", atau kontras (contoh gaya: "90 HARI VS ZOMBIE", "1 HARI TANPA NYAMUK", "TOBA VS DUNIA"). Bukan kalimat teka-teki yang tak bisa dipahami tanpa judul.
- "highlight": satu kata dari hook untuk diberi warna merah.
- "visual": adegan sisi KANAN thumbnail dalam BAHASA INGGRIS maks 35 kata: momen paling dramatis, konkret dan ramai, ancaman atau akibat yang terlihat jelas (Indonesia bila cocok). Jangan deskripsikan stickman utama (otomatis close-up di kiri). Tanpa teks.
- "promise": satu kalimat: apa yang dijanjikan judul+thumbnail kepada penonton, yang WAJIB ditepati naskah.
- "angle": apa yang membuat video kita berbeda/lebih baik dari pesaing.
- "peak": momen paling mengejutkan dari topik ini, yang ditaruh sekitar 2/3 video.
Balas HANYA JSON: {{"topic":"Apa yang terjadi jika ...","query":"...","title":"...","hook":"...","highlight":"...","visual":"...","promise":"...","angle":"...","peak":"...","reason":"alasan pilihan, sebut data"}}"""


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
    """Real what-if searches: each seed alone and followed by every letter."""
    found = []
    for seed in SEEDS:
        for q in [seed] + [f"{seed} {c}" for c in string.ascii_lowercase]:
            try:
                found += suggest(q)
            except Exception as e:
                log("suggest failed", q, e)
            time.sleep(random.uniform(0.2, 0.6))
    return list(dict.fromkeys(s for s in found if s not in SEEDS))


def plan(previous, d):
    """Researches and fixes the video's package; saves research.json and plan.json in the run folder."""
    if (d / "plan.json").exists():
        return load(d / "plan.json")
    pool = demand()
    log("research: searches found", len(pool))
    ideas = claude_json("sonnet", IDEAS_SYS, json.dumps({"pencarian_nyata": pool, "sudah_dibuat": previous[-200:]},
                                                        ensure_ascii=False))["candidates"]
    done = {p.lower() for p in previous}
    ideas = [x for x in ideas if x["topic"].lower().startswith("apa yang terjadi jika") and x["topic"].lower() not in done]
    for x in ideas:
        try:
            x["competition"] = search(x["query"])
        except Exception as e:
            x["competition"] = []
            log("search failed", x["query"], e)
        time.sleep(random.uniform(1, 3))
    save(d / "research.json", {"searches": pool, "candidates": ideas})
    p = claude_json("opus", PICK_SYS, json.dumps({"kandidat": ideas}, ensure_ascii=False))
    p["topic"] = " ".join(p["topic"].split())
    if not p["topic"].lower().startswith("apa yang terjadi jika") or p["topic"].lower() in done:
        raise ValueError(f"unusable topic: {p['topic']}")
    p["title"] = p["title"][:90]
    save(d / "plan.json", p)
    log("plan:", p["title"], "|", p["hook"], "|", p.get("reason", "")[:300])
    return p


if __name__ == "__main__":
    print(json.dumps(plan([], run_dir(sys.argv[1])), ensure_ascii=False, indent=1))
