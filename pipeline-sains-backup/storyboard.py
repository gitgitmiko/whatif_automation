"""Step 3: cut the verified narration into scenes (verbatim, by code) and have Sonnet draw each one in words."""
import re, sys
from common import *

# Modelled on the big Indonesian story channels: full, detailed, lit scenes rather than stickmen on a flat colour.
MASCOT = ("the main character: a cheerful anime-fan (wibu) stickman with a plain WHITE round head, big round glasses, a white "
          "headband and a purple cat hoodie")
# Flow serves this account its agent-only composer, where gflow cannot attach a reference image or a character, so
# the mascot stays the same by being described word for word in every scene it appears in (see assets/mascot/kepo.jpg).
MASCOT_LOOK = ("The wibu stickman always looks exactly like this: perfectly round plain white head with a thick black outline, "
               "two black dot eyes behind big round black-framed glasses, no hair, no nose, no ears; a plain white headband tied "
               "around the forehead with the knot tails sticking out at the side; an oversized purple hoodie with a cute cartoon "
               "cat face on the chest; black track pants with a white side stripe; white sneakers; a small backpack covered in "
               "colorful round pins and keychains; thin black stick arms and legs. No text, no flags, no logos on him.")
STYLE = ("Detailed hand-drawn cartoon illustration, thick black ink outlines, rich textured and fully painted background, "
         "every part of the frame filled with environment details, cinematic lighting with strong mood (warm lamps, "
         "night glow, sunset, rain), saturated but natural colors, depth with foreground and background. Characters have "
         "plain white round heads with thick black outline and simple dot eyes, and clothed bodies (shirts, jackets, "
         "sarongs, hijab) with stick-thin arms and legs. Wide cinematic 16:9 composition. Absolutely no text, no letters, "
         "no words, no numbers, no captions. Scene: ")

VISUAL_SYS = """Kamu storyboard artist untuk video bergaya ilustrasi kartun detail seperti channel cerita YouTube Indonesia yang besar: setiap gambar adalah ADEGAN LENGKAP dengan latar penuh, bukan stickman di latar polos. Untuk setiap potongan narasi, tulis satu deskripsi gambar dalam BAHASA INGGRIS (maks 45 kata) yang menggambarkan isi potongan itu secara konkret dan visual.
Wajib di tiap deskripsi: (1) TEMPAT yang spesifik dan detail, utamakan suasana Indonesia bila cocok (gang kampung, ruko, kabel listrik semrawut, warung, puskesmas, sawah, pasar, rumah genteng merah, laboratorium, kota besar); sebutkan 3-4 benda latar; (2) WAKTU dan CAHAYA (pagi berkabut, siang terik, senja oranye, malam lampu jalan, hujan); (3) aksi tokoh yang jelas. Tokoh utama yang muncul berulang adalah """ + MASCOT + """; sebut "the wibu stickman" bila dia ada di adegan. Tokoh lain berkepala bulat putih yang sama dan memakai pakaian sehari-hari.
Aturan: tanpa teks, huruf, angka, grafik berlabel, atau logo; tanpa tokoh nyata, merek, atau karakter terkenal; sopan, tanpa konten seksual, bagian tubuh, kehamilan yang eksplisit, atau kekerasan dan darah. Buat tiap gambar berbeda: variasikan tempat, sudut kamera (close-up, wide shot, dari atas), dan aksi, agar penonton tidak bosan. Ide abstrak diubah jadi adegan nyata atau metafora visual yang tetap punya latar lengkap.

Pilih juga efek suara dari katalog untuk potongan yang memang terbantu olehnya, agar video tidak monoton. Patokan: sekitar setengah dari potongan diberi efek, jangan dua potongan berurutan memakai efek yang sama, dan hemat pada bagian yang serius atau sedih. Pilih efek yang cocok dengan isi gambar atau kata yang diucapkan. "sfx_word" adalah SATU kata persis dari narasi potongan itu, tempat efek dibunyikan; null jika efek di awal potongan.
Katalog efek: {catalog}

Balas HANYA JSON: {{"visuals":[{{"i":0,"visual":"...","sfx":"id-dari-katalog atau null","sfx_word":"kata atau null"}}]}} dengan satu entri untuk setiap potongan."""


def chunks(narration, lo=11, hi=20):
    """Sentences merged or split into runs of lo..hi words; every word kept in order."""
    out = []
    for para in narration.split("\n\n"):
        cur = []
        for sent in re.split(r"(?<=[.!?])\s+", para.strip()):
            ws = sent.split()
            while len(ws) > hi:
                # Prefer a comma near the middle of the allowed range.
                cut = next((i + 1 for i in range(hi - 1, lo - 1, -1) if ws[i].endswith((",", ";", ":"))), hi)
                out.append(" ".join(cur + ws[:cut]) if len(cur) + cut <= hi else " ".join(ws[:cut]))
                if len(cur) + cut > hi and cur:
                    out.insert(len(out) - 1, " ".join(cur))
                cur, ws = [], ws[cut:]
            if len(cur) + len(ws) > hi:
                out.append(" ".join(cur))
                cur = []
            cur += ws
            if len(cur) >= lo:
                out.append(" ".join(cur))
                cur = []
        if cur:
            # A tail too short to hold a picture joins the run before it.
            if out and len(cur) < lo // 2:
                out[-1] += " " + " ".join(cur)
            else:
                out.append(" ".join(cur))
    return out


def main(slug):
    d = run_dir(slug)
    s = load(d / "script.json")
    cat = load(ROOT / "assets" / "sfx" / "catalog.json")
    ids = {c["id"] for c in cat}
    catalog = json.dumps({c["id"]: c["desc"] for c in cat}, ensure_ascii=False)
    ch = chunks(s["narration"])
    assert " ".join(ch).split() == s["narration"].split(), "chunking changed the narration"
    log("scenes", len(ch))
    scenes = [{"i": i, "text": t} for i, t in enumerate(ch)]
    # 40 at a time: a long storyboard in one reply is where JSON breaks.
    for at in range(0, len(ch), 40):
        part = scenes[at:at + 40]
        ctx = {"judul": s["title"], "potongan": [{"i": x["i"], "narasi": x["text"]} for x in part]}
        reply = claude_json("sonnet", VISUAL_SYS.format(catalog=catalog), json.dumps(ctx, ensure_ascii=False))
        got = {v["i"]: v for v in reply["visuals"]}
        for x in part:
            v = got[x["i"]]
            x["visual"] = v["visual"]
            x["prompt"] = STYLE + " ".join(v["visual"].split())
            if "wibu stickman" in v["visual"].lower():
                x["prompt"] += " " + MASCOT_LOOK
            x["sfx"] = v.get("sfx") if v.get("sfx") in ids else None
            x["sfx_word"] = v.get("sfx_word") if x["sfx"] else None
        log("storyboard", at + len(part), "/", len(ch))
    save(d / "scenes.json", scenes)
    log("scenes with sfx", sum(1 for x in scenes if x["sfx"]))


if __name__ == "__main__":
    main(sys.argv[1])
