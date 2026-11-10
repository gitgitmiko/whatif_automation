"""Step 3: cut the verified narration into scenes (verbatim, by code) and have Sonnet draw each one in words."""
import re, sys
from common import *

# Dark graphic-novel look for "Jangan Sendirian": real people in full, lit scenes, drawn gritty rather than cute.
MASCOT = ("Gitgit, the main character who IS the 'kamu' of the story: a slim young Indonesian man in his twenties with curly "
          "black hair parted in the middle")
# Flow serves this account its agent-only composer, where gflow cannot attach a reference image or a character, so
# Gitgit stays the same by being described word for word in every scene he appears in (see assets/mascot/gitgit.jpg).
# What he wears is not part of his identity: the storyboard picks clothes that fit each story.
MASCOT_LOOK = ("Gitgit always looks exactly like this: a slim young Indonesian man in his twenties, warm tan skin, thick CURLY "
               "wavy black hair parted exactly in the MIDDLE with curls falling to both sides of the forehead down to the ears; "
               "exactly one small dark MOLE on his RIGHT cheek just below his right eye, close to the side of the nose (on the "
               "left side of the picture when he faces us); a plain BLACK wristwatch on his LEFT wrist; no glasses, no beard, "
               "no hat covering the hair.")
BIKE_LOOK = ("Gitgit's motorbike is always the same small automatic scooter in the style of a Honda BeAT: clean WHITE body "
             "with bright BLUE striping and blue accents, black seat, no logos or text on it.")
STYLE = ("Dark horror graphic novel illustration, moody gritty ink drawing with heavy black shadows and cross-hatching, "
         "muted desaturated colors, realistic human proportions and realistic faces, rich fully drawn background with "
         "every part of the frame filled with environment details, eerie cinematic horror lighting (cold moonlight, a "
         "single flickering lamp, flashlight beams, fog, rain), deep blue, green-grey and black shadows with small warm "
         "light sources, depth with foreground and background. Other people are ordinary Indonesians in everyday clothes "
         "(shirts, jackets, sarongs, hijab). Ghosts and creatures are deeply unsettling but not gory: no blood, no wounds. "
         "Not cute, not funny, not anime. Wide cinematic 16:9 composition. Absolutely no text, no letters, no words, no "
         "numbers, no captions. Scene: ")

VISUAL_SYS = """Kamu storyboard artist untuk video cerita horor POV bergaya novel grafis horor yang gelap dan serius: setiap gambar adalah ADEGAN LENGKAP yang mencekam dengan latar penuh. Untuk setiap potongan narasi, tulis satu deskripsi gambar dalam BAHASA INGGRIS (maks 45 kata) yang menggambarkan isi potongan itu secara konkret dan visual.
Wajib di tiap deskripsi: (1) TEMPAT yang spesifik dan detail dengan suasana Indonesia (kamar kos, lorong kos, gang kampung malam, warung tutup, musala, kebun bambu, sawah malam, jalur pendakian, rumah Jawa tua, pasar sepi); sebutkan 3-4 benda latar; (2) WAKTU dan CAHAYA yang seram (malam, lampu berkedip, cahaya HP atau senter, bulan di balik kabut, hujan); (3) aksi tokoh yang jelas. Tokoh utama, yaitu "kamu" di narasi, SELALU digambarkan sebagai """ + MASCOT + """; sebut namanya "Gitgit" di setiap adegan yang menampilkan tokoh utama, dengan ekspresi yang sesuai (waspada, takut, panik, terpaku, lega). Jangan deskripsikan rambut, wajah, atau jam tangannya (ditambahkan otomatis), dan jangan sebut pakaiannya di tiap adegan (lihat "outfit"). Bila ia naik atau membawa motor, tulis "Gitgit's scooter" (motornya selalu sama, ditambahkan otomatis). Sesekali boleh sudut pandang orang pertama (first-person view: tangan kiri berjam tangan hitam memegang HP atau senter), tapi sebagian besar adegan menampilkan Gitgit. Tokoh lain orang Indonesia biasa dengan pakaian sehari-hari. Tidak ada unsur lucu, imut, atau anime.
"outfit": pakaian Gitgit untuk cerita INI dalam BAHASA INGGRIS (maks 20 kata), mengikuti latar dan situasi cerita (mis. jaket ojek polos dan celana panjang; baju koko dan sarung; jaket gunung dan ransel; kaus oblong dan celana pendek di kos), polos tanpa tulisan atau logo. Satu pakaian untuk seluruh cerita; bila pesan sudah memuat "outfit", pakai itu persis.
Hantu dan sosok: tunjukkan sebagian saja agar seram (siluet di ujung lorong, rambut panjang dari balik pintu, mata di kegelapan, bayangan di jendela), tanpa darah, luka, atau gore. Variasikan sudut kamera (close-up wajah ketakutan, wide shot lorong panjang, dari atas, POV), dan aksi, agar penonton tidak bosan.
Aturan: tanpa teks, huruf, angka, atau logo; tanpa tokoh nyata, merek, atau karakter terkenal; tanpa konten seksual; simbol agama hanya bila perlu dan digambarkan dengan hormat.

Pilih juga efek suara dari katalog untuk potongan yang memang terbantu olehnya. Patokan: sekitar sepertiga potongan diberi efek, jangan dua potongan berurutan memakai efek yang sama; simpan efek kejut (stinger) untuk momen kaget yang benar-benar penting. "sfx_word" adalah SATU kata persis dari narasi potongan itu, tempat efek dibunyikan; null jika efek di awal potongan.
Katalog efek: {catalog}

Balas HANYA JSON: {{"outfit":"...","visuals":[{{"i":0,"visual":"...","sfx":"id-dari-katalog atau null","sfx_word":"kata atau null"}}]}} dengan satu entri untuk setiap potongan."""

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
    outfit = ""
    # 40 at a time: a long storyboard in one reply is where JSON breaks.
    for at in range(0, len(ch), 40):
        part = scenes[at:at + 40]
        ctx = {"judul": s["title"], "potongan": [{"i": x["i"], "narasi": x["text"]} for x in part]}
        if outfit:
            ctx["outfit"] = outfit
        reply = claude_json("sonnet", VISUAL_SYS.format(catalog=catalog), json.dumps(ctx, ensure_ascii=False))
        got = {v["i"]: v for v in reply["visuals"]}
        outfit = outfit or " ".join(str(reply.get("outfit") or "plain dark t-shirt and jeans").split())
        for x in part:
            v = got[x["i"]]
            x["visual"] = v["visual"]
            x["prompt"] = STYLE + " ".join(v["visual"].split())
            low = v["visual"].lower()
            if "gitgit" in low:
                x["prompt"] += f" {MASCOT_LOOK} In this story he wears: {outfit.rstrip('.')}."
            if re.search(r"scooter|motorbike|motorcycle", low):
                x["prompt"] += " " + BIKE_LOOK
            x["sfx"] = v.get("sfx") if v.get("sfx") in ids else None
            x["sfx_word"] = v.get("sfx_word") if x["sfx"] else None
        log("storyboard", at + len(part), "/", len(ch))
    save(d / "scenes.json", scenes)
    log("outfit:", outfit)
    log("scenes with sfx", sum(1 for x in scenes if x["sfx"]))


if __name__ == "__main__":
    main(sys.argv[1])
