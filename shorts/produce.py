"""One "Gimana Jadinya?" Short, start to finish, into runs/<id>/:

  naskah  Claude (with web search) picks a fresh "gimana jadinya kalau…" question and writes the narration, scene by
          scene, choosing each scene's visual from the Remotion library in src/visuals.tsx      -> script.draft.json
  cek     a second Claude pass checks every claim and number on the web and fixes them        -> script.json
  suara   edge-tts (Ardi) reads each scene; its word timings drive captions and cues          -> vo*.mp3, props.json
  render  Remotion draws the 1080x1920 video                                                   -> final.mp4

  .venv/bin/python shorts/produce.py <id> [--script file.json]   (--script skips naskah and cek)
"""
import asyncio, json, re, shutil, sqlite3, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path
import edge_tts

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from common import RUNS, claude_json, load, log, save  # noqa: E402

VOICE, RATE = "id-ID-ArdiNeural", "+8%"
FPS, GAP = 30, 0.25  # a short breath between scenes
SFX = {
    "whoosh": "sapuan cepat", "pop": "sesuatu muncul", "pop-up": "muncul ceria", "boing": "memantul, lucu",
    "riser": "ketegangan naik", "boom": "ledakan besar", "sub-drop": "dentuman berat, kejutan", "slam": "hantaman",
    "hit": "pukulan", "splash": "air menerjang", "sparkle": "ajaib, berkilau", "question": "tanda tanya, penasaran",
    "correct": "benar", "wrong": "salah", "clock": "detak jam, waktu berjalan", "heartbeat": "detak jantung",
    "bell": "lonceng", "gong": "gong", "glass": "kaca pecah", "drop": "jatuh", "metal": "logam", "machine": "mesin",
    "weird": "aneh",
}
TYPES = {"globe", "icon", "gauge", "bars", "versus", "fly", "rise", "swarm", "timeline", "thermo", "number", "wind", "outro"}

LIBRARY = """JENIS VISUAL (field "visual" tiap adegan; semua teks di layar HURUF BESAR otomatis, buat SINGKAT):
- {"type":"globe","mode":"spin|stop|night|hot|frozen","stamp":"..."}  Bumi animasi. stop = berputar lalu berhenti mendadak di kata cue; night = setengah gelap dengan Matahari; hot = memerah membara; frozen = membeku putih.
- {"type":"icon","emoji":"🦖","motion":"pop|shake|float|spin|grow|shrink|explode","stamp":"..."}  satu emoji besar. explode = meledak di kata cue; grow/shrink = membesar/mengecil sampai kata cue.
- {"type":"gauge","value":1660,"unit":"km/jam","label":"Jakarta","max":2000}  speedometer naik ke value di kata cue.
- {"type":"bars","unit":"km/jam","items":[{"label":"Pesawat","value":900,"emoji":"✈️","at":"pesawat"},{"label":"Kamu","value":1660,"emoji":"🧍","highlight":true}]}  perbandingan 2-4 batang; tiap batang muncul saat kata "at" diucapkan (kosongkan "at" = muncul di awal). Nilai harus sebanding (rasio terbesar/terkecil < 50).
- {"type":"versus","left":{"emoji":"🌞","label":"Sekarang"},"right":{"emoji":"🥶","label":"Nanti"},"stamp":"..."}  dua sisi dibandingkan; sisi kanan muncul di kata cue.
- {"type":"fly","emojis":["🏠","🚗","🧍"],"direction":"right|left|up|down","ground":true,"stamp":"..."}  1-4 benda diam lalu terlempar ke arah itu di kata cue.
- {"type":"rise","fluid":"water|lava|ice|sand","stamp":"..."}  cairan naik menenggelamkan kota.
- {"type":"swarm","emoji":"🧍","count_label":"8 miliar","stamp":"..."}  satu emoji berlipat ganda memenuhi layar sampai kata cue.
- {"type":"timeline","steps":[{"time":"1 detik","emoji":"⚡","label":"Listrik padam","at":"detik"}]}  2-4 langkah waktu, tiap langkah muncul di kata "at"-nya.
- {"type":"thermo","value":60,"unit":"°C","min":0,"max":80,"label":"Suhu Jakarta","stamp":"..."}  termometer naik ke value di kata cue.
- {"type":"number","value":8000000000,"unit":"orang","label":"...","emoji":"🧍","stamp":"..."}  satu angka besar menghitung naik.
- {"type":"wind","emoji":"🌴","stamp":"..."}  angin kencang menerpa sesuatu.
- {"type":"outro"}  WAJIB untuk adegan terakhir: tanda tanya + ajakan komentar.
"stamp" opsional, maks 3 kata / 18 huruf, menegaskan momen di kata cue (contoh "STOP!", "3× LEBIH KENCANG", "TSUNAMI RAKSASA"). Emoji harus emoji Unicode standar yang umum. Variasikan jenis visual; jangan memakai jenis yang sama lebih dari 2 kali."""

WRITER_SYS = f"""Kamu penulis naskah YouTube Shorts untuk channel "Gimana Jadinya?" (tagline: Pertanyaan gila. Jawaban ilmiah.). Penonton: orang Indonesia umum, remaja sampai dewasa. Setiap video menjawab SATU pertanyaan "gimana jadinya kalau…" yang mengejutkan dengan sains yang BENAR, dalam animasi grafis 35-50 detik.

1. Pilih topik baru: skenario hipotetis yang bikin penasaran dan bisa dijawab dengan fisika/biologi/astronomi/geografi/teknologi (contoh: Bumi berhenti berputar, semua orang melompat bersamaan, Bulan hilang, manusia berhenti tidur, internet mati sedunia). Boleh terinspirasi dari saran pencarian YouTube yang diberikan. DILARANG mengulang atau sangat mirip dengan judul yang sudah pernah dibuat. Hindari politik, agama, SARA, tragedi nyata, dan hal sadis.
2. Riset dengan pencarian web: pastikan setiap angka dan klaim benar menurut sumber tepercaya (NASA, jurnal, ensiklopedia, universitas). Kalau sesuatu masih teori, katakan "menurut perkiraan ilmuwan".
3. Tulis narasi Bahasa Indonesia santai (pakai "kamu"), total 95-125 kata, dalam 7-10 adegan, tiap adegan 6-20 kata. Adegan pertama WAJIB diawali "Gimana jadinya kalau" lalu pertanyaannya, sebagai hook. Lalu eskalasi akibat demi akibat, makin dahsyat, ditutup fakta paling mengejutkan. Adegan terakhir (visual outro) menutup singkat lalu bertanya ke penonton dan memuat "Tulis di komentar!".
4. Angka ditulis dengan digit format Indonesia (1.660, 8 miliar, 3,5) supaya terbaca di caption; satuan ditulis seperti diucapkan: "km/jam", "derajat Celsius", "persen". Hindari kata bahasa Inggris dan singkatan yang sulit dibaca mesin suara.
5. Tiap adegan: "text" (narasi), "visual" (dari daftar di bawah, isinya harus sesuai dengan narasi dan angkanya sama persis), "cue" (SATU kata yang ada persis di text adegan itu, saat aksi utama/stamp terjadi), "sfx" (satu dari: {", ".join(f"{k} ({v})" for k, v in SFX.items())}; boleh kosong).

{LIBRARY}

Balas HANYA JSON:
{{"title":"Kalau ...?" (maks 42 huruf, tampil di bawah label GIMANA JADINYA?),
 "yt_title":"Gimana Jadinya Kalau ...?" (maks 70 huruf, memancing klik tapi jujur),
 "description":"2-3 kalimat ringkasan menarik",
 "tags":["8-12 tag"],
 "sources":["2-4 URL sumber yang benar-benar kamu pakai"],
 "scenes":[{{"text":"...","visual":{{...}},"cue":"...","sfx":"..."}}]}}"""

CHECK_SYS = f"""Kamu pemeriksa fakta dan editor naskah YouTube Shorts "Gimana Jadinya?". Kamu menerima naskah JSON.
1. Periksa SETIAP klaim dan angka di narasi DAN di visual dengan pencarian web ke sumber tepercaya. Perbaiki yang salah atau berlebihan; samakan angka di visual dengan narasi. Klaim spekulatif harus ditandai "menurut perkiraan ilmuwan" atau sejenisnya.
2. Pastikan aturan: 7-10 adegan; total 95-125 kata; adegan pertama diawali "Gimana jadinya kalau"; adegan terakhir visual outro dan memuat "Tulis di komentar!"; tiap "cue" adalah kata yang ada persis di text adegannya; angka pakai digit format Indonesia; stamp maks 18 huruf; visual sesuai daftar berikut.

{LIBRARY}

3. Jangan mengubah topik. Pertahankan gaya santai. Perbarui "sources" dengan URL yang kamu pakai untuk memeriksa.
Balas HANYA JSON: {{"issues":["daftar yang kamu perbaiki, kosong kalau tidak ada"],"script":{{...naskah lengkap yang sudah diperbaiki, format sama...}}}}"""


def suggestions():
    out = []
    for q in ("gimana jadinya kalau", "apa yang terjadi jika", "bagaimana jika bumi", "apa jadinya jika manusia"):
        try:
            u = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
                {"client": "firefox", "ds": "yt", "hl": "id", "gl": "ID", "q": q})
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            out += json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace"))[1]
        except Exception as e:  # noqa: BLE001 - inspiration only
            log("suggest failed:", q, e)
    return out


def previous_titles():
    db = ROOT / "data" / "whatif.db"
    if not db.exists():
        return []
    with sqlite3.connect(db) as c:
        return [r[0] for r in c.execute("SELECT title FROM runs WHERE title IS NOT NULL AND slot IN "
                                        "('pagi','sore','malam') ORDER BY started_at DESC LIMIT 300")]


def tidy(s):
    """Holds the script to what the template can draw; anything unusable falls back rather than fails."""
    scenes = [x for x in s.get("scenes", []) if str(x.get("text", "")).strip()]
    if len(scenes) < 4:
        raise ValueError(f"script has only {len(scenes)} scenes")
    for i, x in enumerate(scenes):
        v = x.get("visual") if isinstance(x.get("visual"), dict) else {}
        if v.get("type") not in TYPES or (v["type"] == "outro" and i != len(scenes) - 1):
            v = {"type": "icon", "emoji": v.get("emoji") or "🤔", "motion": "pop", "stamp": v.get("stamp")}
        for k in ("value", "max", "min"):
            if k in v:
                try:
                    v[k] = float(str(v[k]).replace(",", "."))
                except ValueError:
                    v.pop(k)
        for it in v.get("items", []) + v.get("steps", []):
            if "value" in it:
                try:
                    it["value"] = float(str(it["value"]).replace(",", "."))
                except ValueError:
                    it["value"] = 0
        if v.get("stamp") and len(v["stamp"]) > 22:
            v.pop("stamp")
        x["visual"] = v
        spoken = [w.lower().strip(".,?!;:") for w in x["text"].split()]
        cue = str(x.get("cue") or "").lower().strip(".,?!;:")
        if cue and not any(w.startswith(cue) for w in spoken):
            log(f"scene {i}: cue {cue!r} not in its text, dropped")
            x.pop("cue", None)
        if x.get("sfx") not in SFX:
            x.pop("sfx", None)
    scenes[-1]["visual"] = {"type": "outro"}
    s["scenes"] = scenes
    s["title"] = str(s.get("title") or "")[:60]
    s["yt_title"] = str(s.get("yt_title") or "Gimana Jadinya " + s["title"])[:90]
    n = sum(len(x["text"].split()) for x in scenes)
    if not scenes[0]["text"].lower().startswith("gimana jadinya kalau"):
        log("warning: first scene does not open with 'Gimana jadinya kalau'")
    log(f"script: {len(scenes)} scenes, {n} words, title {s['title']!r}")
    return s


async def synth(text, mp3, tries=5):
    # Microsoft's server now and then stalls on one request; a moment later it answers.
    for attempt in range(tries):
        words = []
        try:
            with open(mp3, "wb") as f:
                async for c in edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary").stream():
                    if c["type"] == "audio":
                        f.write(c["data"])
                    elif c["type"] == "WordBoundary":
                        words.append({"w": c["text"], "s": c["offset"] / 1e7, "e": (c["offset"] + c["duration"]) / 1e7})
            if words:
                return words
            raise RuntimeError("no word timings")
        except Exception as e:  # noqa: BLE001 - aiohttp and edge-tts raise several kinds for the same hiccup
            if attempt == tries - 1:
                raise
            log(f"edge-tts failed ({type(e).__name__}: {str(e)[:100]}), retrying")
            await asyncio.sleep(10 * (attempt + 1))


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(path)]).strip())


def voice(s, d, pub):
    t, scenes = 0.0, []
    for i, x in enumerate(s["scenes"]):
        mp3 = pub / f"vo{i:02}.mp3"
        words = asyncio.run(synth(x["text"], mp3))
        # Word boundaries drop punctuation; put back the mark after each word so captions break on sentences.
        at = 0
        for w in words:
            k = x["text"].find(w["w"], at)
            if k >= 0:
                at = k + len(w["w"])
                m = re.match(r"[.,?!;:]+", x["text"][at:])
                if m:
                    w["w"] += m.group()
        # edge-tts pads silence at both ends: the scene runs from the first word to just after the last.
        lead = max(words[0]["s"] - 0.05, 0)
        end = min(words[-1]["e"] + 0.2, duration(mp3))
        length = end - lead + GAP
        scenes.append({**x, "audio": mp3.name, "audioFrom": round(lead * FPS), "from": round(t * FPS),
                       "frames": round(length * FPS),
                       "words": [{"w": w["w"], "s": round((w["s"] - lead) * FPS), "e": round((w["e"] - lead) * FPS)}
                                 for w in words]})
        t += length
    props = {"title": s["title"], "fps": FPS, "frames": round(t * FPS) + FPS, "scenes": scenes}
    save(d / "props.json", props)
    log(f"voice: {t:.1f} s")
    return props


def render(d, pub):
    subprocess.run(["npx", "remotion", "render", "Short", str(d / "final.mp4"), f"--props={d / 'props.json'}",
                    f"--public-dir={pub}", "--concurrency=6", "--crf=20", "--log=error"], cwd=HERE, check=True,
                   timeout=1800)


def main(rid, script_file=None):
    d = RUNS / rid
    d.mkdir(parents=True, exist_ok=True)
    if script_file:
        s = tidy(load(script_file))
    else:
        print("STAGE naskah", flush=True)
        brief = {"judul_yang_sudah_pernah_dibuat": previous_titles(), "saran_pencarian_youtube": suggestions()}
        draft = claude_json("opus", WRITER_SYS, json.dumps(brief, ensure_ascii=False), web=True)
        save(d / "script.draft.json", draft)
        tidy(json.loads(json.dumps(draft)))  # fail early on a draft the checker could not save
        print("STAGE cek", flush=True)
        checked = claude_json("opus", CHECK_SYS, json.dumps(draft, ensure_ascii=False), web=True)
        for issue in checked.get("issues", []):
            log("fixed:", issue)
        s = tidy(checked.get("script") or draft)
    save(d / "script.json", s)
    print("STAGE suara", flush=True)
    pub = d / "public"
    pub.mkdir(exist_ok=True)
    shutil.copy(HERE / "public" / "Anton-Regular.ttf", pub)
    shutil.copytree(HERE / "public" / "sfx", pub / "sfx", dirs_exist_ok=True)
    voice(s, d, pub)
    print("STAGE render", flush=True)
    render(d, pub)
    shutil.rmtree(pub / "sfx", ignore_errors=True)
    log("done:", d / "final.mp4", f"{duration(d / 'final.mp4'):.1f} s")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[a.index("--script") + 1] if "--script" in a else None)
