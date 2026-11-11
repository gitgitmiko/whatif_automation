"""Step 0: pre-production for "Hikayat Ancient", game hero lore videos. The games go in heroes.GAMES order (Dota 2
first, then League of Legends) and each game's heroes in alphabetical order (the user's choice), from the publisher's
own roster; for the next hero not covered yet it looks at what Indonesian YouTube already has on its lore and what
people type into the search box, then fixes the package (title, thumbnail hook, promise, mood) before any script is
written."""
import random, string, sys, urllib.parse, urllib.request
from common import *
import heroes

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept-Language": "id"}
MOODS = ["epik", "tragis", "misterius", "horor", "hangat"]

PICK_SYS = """Kamu ahli strategi konten YouTube untuk channel "Hikayat Ancient": video lore hero game berbahasa Indonesia yang menceritakan ulang kisah resmi hero dengan dramatis; panjang video mengikuti isi lore. Hero sudah ditetapkan (urutan abjad).
Kamu diberi: nama game, nama hero, lore resminya, saran pencarian YouTube untuk lore hero itu, dan video YouTube Indonesia yang sudah ada (judul, views, umur, channel). Pakai itu untuk mencari sudut yang membuat video kita menonjol dibanding yang sudah ada.
Tetapkan paketnya:
- "hero": nama pendek hero persis dari data (field "short").
- "title": judul YouTube maks 60 karakter, "Lore <Nama Hero>" atau nama hero di depan, Bahasa Indonesia natural, memancing rasa penasaran, JUJUR terhadap lore resmi. Contoh gaya: "Lore Pudge: Jagal yang Tak Pernah Bisa Berhenti".
- "hook": teks thumbnail 2-4 kata HURUF BESAR yang konkret dan bikin penasaran, sesuai lore (contoh gaya: "DIA TAK BISA MATI", "JAGAL MEDAN PERANG", "DIKUTUK SELAMANYA").
- "highlight": satu kata dari hook untuk diberi warna merah.
- "visual": latar sisi KANAN thumbnail dalam BAHASA INGGRIS maks 35 kata: tempat atau momen paling kuat dari lore (heronya sendiri TIDAK digambar: potret resminya otomatis di kiri). Tanpa teks.
- "mood": suasana utama cerita, salah satu: epik, tragis, misterius, horor, hangat.
- "promise": satu kalimat apa yang akan penonton dapat.
- "angle": sudut cerita yang membuat video ini beda (mis. dari sudut korban, misteri yang belum terjawab, tragedi di balik kekuatannya).
- "peak": momen paling kuat dari lore yang jadi puncak video.
Balas HANYA JSON: {"hero":"...","title":"...","hook":"...","highlight":"...","visual":"...","mood":"...","promise":"...","angle":"...","peak":"...","reason":"alasan sudut yang dipilih, sebut data"}"""


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


def topic_of(game, name):
    """The run's topic, also how "already made" is recorded; Dota 2 heroes keep the plain form used from the start."""
    return f"Lore {name}" if game.key == "dota2" else f"Lore {name} ({game.name})"


def next_hero(previous):
    """(game, folder, hero.json) of the first hero, game by game and A to Z, with no video yet."""
    done = {p.lower() for p in previous}
    for game in heroes.GAMES:
        for key, name in game.roster():
            if topic_of(game, name).lower() in done:
                continue
            d = game.collect(key)
            if d:
                return game, d, load(d / "hero.json")
    raise ValueError("every hero of every game has a video already; add a game to heroes.GAMES")


def plan(previous, d):
    """Fixes the next video's package; saves research.json and plan.json in the run folder."""
    if (d / "plan.json").exists():
        return load(d / "plan.json")
    game, folder, info = next_hero(previous)
    x = {"game": game.name, "short": info["key"], "name": info["name"], "lore": info["lore"]}
    try:
        x["searches"] = suggest(f"lore {info['name'].lower()}")
        time.sleep(random.uniform(0.3, 0.8))
        x["youtube"] = search(f"lore {info['name']} {game.query}")
    except Exception as e:
        x.setdefault("searches", [])
        x["youtube"] = []
        log("search failed", info["name"], e)
    save(d / "research.json", x)
    p = claude_json("opus", PICK_SYS, json.dumps(x, ensure_ascii=False))
    p.update(hero=info["key"], hero_name=info["name"], game=game.key, game_name=game.name,
             hero_dir=str(folder.relative_to(ROOT)), topic=topic_of(game, info["name"]))
    p["mood"] = p.get("mood") if p.get("mood") in MOODS else "misterius"
    p["title"] = p["title"][:90]
    save(d / "plan.json", p)
    log("plan:", game.name, "|", p["title"], "|", p["hook"], "|", p["mood"], "|", p.get("reason", "")[:300])
    return p


if __name__ == "__main__":
    print(json.dumps(plan([], run_dir(sys.argv[1])), ensure_ascii=False, indent=1))
