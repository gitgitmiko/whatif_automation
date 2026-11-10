"""Step 3: cut the verified narration into scenes (verbatim, by code) and have Sonnet draw each one in words."""
import re, sys
from common import *

# Modelled on the big Indonesian story channels: full, detailed, lit scenes rather than stickmen on a flat colour,
# here in a dark horror mood for "Jangan Sendirian".
MASCOT = ("Kepo, the main character who IS the 'kamu' of the story: a nervous anime-fan (wibu) stickman with a plain WHITE round head, big round glasses, a white "
          "headband and a purple cat hoodie")
# Flow serves this account its agent-only composer, where gflow cannot attach a reference image or a character, so
# the mascot stays the same by being described word for word in every scene it appears in (see assets/mascot/kepo.jpg).
MASCOT_LOOK = ("The wibu stickman always looks exactly like this: perfectly round plain white head with a thick black outline, "
               "two black dot eyes behind big round black-framed glasses, no hair, no nose, no ears; a plain white headband tied "
               "around the forehead with the knot tails sticking out at the side; an oversized purple hoodie with a cute cartoon "
               "cat face on the chest; black track pants with a white side stripe; white sneakers; a small backpack covered in "
               "colorful round pins and keychains; thin black stick arms and legs. No text, no flags, no logos on him.")
STYLE = ("Detailed hand-drawn cartoon illustration, thick black ink outlines, rich textured and fully painted background, "
         "every part of the frame filled with environment details, eerie cinematic horror lighting (cold moonlight, a "
         "single flickering lamp, flashlight beams, fog, rain), deep blue, purple and black shadows with small warm light "
         "sources, slightly desaturated colors, depth with foreground and background. Characters have plain white round "
         "heads with thick black outline and simple dot eyes, and clothed bodies (shirts, jackets, sarongs, hijab) with "
         "stick-thin arms and legs. Ghosts and creatures are creepy but not gory: no blood, no wounds. Wide cinematic "
         "16:9 composition. Absolutely no text, no letters, no words, no numbers, no captions. Scene: ")

VISUAL_SYS = """Kamu storyboard artist untuk video cerita horor POV bergaya ilustrasi kartun detail: setiap gambar adalah ADEGAN LENGKAP yang mencekam dengan latar penuh, bukan stickman di latar polos. Untuk setiap potongan narasi, tulis satu deskripsi gambar dalam BAHASA INGGRIS (maks 45 kata) yang menggambarkan isi potongan itu secara konkret dan visual.
Wajib di tiap deskripsi: (1) TEMPAT yang spesifik dan detail dengan suasana Indonesia (kamar kos, lorong kos, gang kampung malam, warung tutup, musala, kebun bambu, sawah malam, jalur pendakian, rumah Jawa tua, pasar sepi); sebutkan 3-4 benda latar; (2) WAKTU dan CAHAYA yang seram (malam, lampu berkedip, cahaya HP atau senter, bulan di balik kabut, hujan); (3) aksi tokoh yang jelas. Tokoh utama, yaitu "kamu" di narasi, SELALU digambarkan sebagai """ + MASCOT + """; sebut "the wibu stickman" di setiap adegan yang menampilkan tokoh utama, dengan ekspresi yang sesuai (takut, gugup, sok berani, lega). Sesekali boleh sudut pandang orang pertama (first-person view: tangan berlengan hoodie ungu memegang HP atau senter), tapi sebagian besar adegan menampilkan the wibu stickman. Tokoh lain berkepala bulat putih yang sama dan memakai pakaian sehari-hari.
Hantu dan sosok: tunjukkan sebagian saja agar seram (siluet di ujung lorong, rambut panjang dari balik pintu, mata di kegelapan, bayangan di jendela), tanpa darah, luka, atau gore. Variasikan sudut kamera (close-up wajah ketakutan, wide shot lorong panjang, dari atas, POV), dan aksi, agar penonton tidak bosan.
Aturan: tanpa teks, huruf, angka, atau logo; tanpa tokoh nyata, merek, atau karakter terkenal; tanpa konten seksual; simbol agama hanya bila perlu dan digambarkan dengan hormat.

Pilih juga efek suara dari katalog untuk potongan yang memang terbantu olehnya. Patokan: sekitar sepertiga potongan diberi efek, jangan dua potongan berurutan memakai efek yang sama; simpan efek kejut (stinger) untuk momen kaget yang benar-benar penting. "sfx_word" adalah SATU kata persis dari narasi potongan itu, tempat efek dibunyikan; null jika efek di awal potongan.
Katalog efek: {catalog}

Balas HANYA JSON: {{"visuals":[{{"i":0,"visual":"...","sfx":"id-dari-katalog atau null","sfx_word":"kata atau null"}}]}} dengan satu entri untuk setiap potongan."""

# Content sounds that suit horror; the cartoon ones (boing, sparkle, ...) stay out of this channel.
HORROR_SFX = {"heartbeat", "door-open", "door-close", "clock", "riser", "sub-drop", "weird", "whoosh-soft", "glass",
              "slam", "metal", "drop", "hit", "paper", "boom", "splash"}


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
    cat = [c for c in load(ROOT / "assets" / "sfx" / "catalog.json") if c["id"] in HORROR_SFX]
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
