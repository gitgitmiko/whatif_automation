"""Step 3b: Sonnet marks the moments the captions should colour: a short phrase from a scene and its mood."""
import sys
from common import *

SYS = """Kamu editor video YouTube cerita horor. Dari potongan narasi berikut, pilih momen yang layak ditonjolkan di subtitle dengan warna: aturan yang harus dipatuhi, bunyi atau sosok yang muncul, momen kaget, petunjuk penting, atau kalimat yang bikin merinding. Patokan: sekitar seperempat potongan, menyebar sepanjang video, tidak berurutan terus-menerus.
"phrase" adalah 1-4 kata PERSIS berurutan dari narasi potongan itu. "mood" salah satu: bahaya (sosok, ancaman, momen kaget), tanya (misteri, bunyi aneh, pertanyaan), fakta (aturan, jam, petunjuk penting), positif (lega, selamat), ajaib (hal gaib yang aneh tapi tidak mengancam).
Balas HANYA JSON: {"highlights":[{"i":0,"phrase":"...","mood":"fakta"}]}"""
MOODS = {"fakta", "bahaya", "positif", "ajaib", "tanya"}

VOICE_SYS = """Kamu sutradara pengisi suara untuk cerita horor yang dibacakan narator. Narator membaca potongan demi potongan; untuk SETIAP potongan tentukan cara membacanya agar cerita terasa hidup dan menyeramkan, tidak datar:
- "delivery" salah satu: normal (bercerita biasa, suasana masih aman), tegang (ketegangan naik, ada yang terasa salah), bisik (hening, bunyi kecil, sesuatu sangat dekat, menahan napas), dingin (fakta yang mengerikan, aturan, kalimat penutup yang bikin merinding: pelan dan berat), kaget (momen kejut, sosok muncul tiba-tiba: lebih cepat dan keras), lega (ketegangan turun sesaat, humor kecil).
- Ikuti alur: awal lebih banyak normal, makin ke puncak makin banyak tegang/bisik, kaget hanya di momen kejut yang sungguh penting (maksimal sekitar 5 kali), dingin untuk kalimat yang harus menancap. Jangan semua potongan sama.
- "pause": jeda hening SETELAH potongan itu dalam detik (0.1 sampai 1.5). Pendek (0.1-0.3) saat cerita mengalir; panjang (0.7-1.5) sebelum momen kejut, setelah kalimat yang mengerikan, atau saat bunyi aneh terdengar, agar penonton ikut menahan napas.
- "lafal": daftar kata atau frasa NON-bahasa Indonesia di potongan itu (bahasa Inggris, Jepang, dll.) yang akan salah diucapkan narator berbahasa Indonesia, beserta ejaan bunyinya dalam ejaan Indonesia, mis. {"tulis":"rice cooker","ucap":"rais kuker"}, {"tulis":"cosplay","ucap":"kosplei"}. Kata serapan yang sudah biasa dibaca Indonesia (HP, motor, senter, anime, wibu) tidak perlu. Kosongkan bila tidak ada.
Balas HANYA JSON: {"voice":[{"i":0,"delivery":"normal","pause":0.2,"lafal":[]}]} dengan satu entri untuk setiap potongan."""
DELIVERIES = {"normal", "tegang", "bisik", "dingin", "kaget", "lega"}


def main(slug):
    d = run_dir(slug)
    scenes = load(d / "scenes.json")
    got = {}
    for at in range(0, len(scenes), 40):
        part = [{"i": x["i"], "narasi": x["text"]} for x in scenes[at:at + 40]]
        for h in claude_json("sonnet", SYS, json.dumps(part, ensure_ascii=False)).get("highlights", []):
            got[h["i"]] = h
    n = 0
    for x in scenes:
        h = got.get(x["i"])
        ok = h and h.get("mood") in MOODS and " ".join(h.get("phrase", "").lower().split()) in " ".join(x["text"].lower().split())
        x["highlight"] = {"phrase": h["phrase"], "mood": h["mood"]} if ok else None
        n += bool(ok)
    voice = {}
    for at in range(0, len(scenes), 40):  # the whole story in each request, so the delivery follows its arc
        ctx = {"cerita": [{"i": x["i"], "narasi": x["text"]} for x in scenes],
               "potongan_yang_dinilai": [x["i"] for x in scenes[at:at + 40]]}
        for v in claude_json("sonnet", VOICE_SYS, json.dumps(ctx, ensure_ascii=False)).get("voice", []):
            voice[v.get("i")] = v
    for x in scenes:
        v = voice.get(x["i"]) or {}
        x["delivery"] = v.get("delivery") if v.get("delivery") in DELIVERIES else "normal"
        x["pause"] = v.get("pause", 0.2) if isinstance(v.get("pause"), (int, float)) else 0.2
        x["lafal"] = [a for a in v.get("lafal") or [] if isinstance(a, dict) and a.get("tulis") and a.get("ucap")]
    save(d / "scenes.json", scenes)
    log("highlights", n, "of", len(scenes), "| delivery",
        {k: sum(1 for x in scenes if x["delivery"] == k) for k in sorted(DELIVERIES)})


if __name__ == "__main__":
    main(sys.argv[1])
