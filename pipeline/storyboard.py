"""Step 3: cut the verified narration into scenes (verbatim, by code) and have Sonnet draw each one in words."""
import re, sys
from common import *

# Hero lore videos: the hero's world drawn in one recognisable ink graphic-novel look, coloured and lit by the story's
# mood. Heroes are the publishers' designs and come out wrong when drawn, so they appear only as silhouettes, shadows or a hand
# and a weapon; the official render is laid over one reveal scene by edit.py. No mascot: every scene is the lore's world.
MOOD_LOOK = {
    "epik": "heroic epic lighting: storm clouds split by golden sunbeams, warm gold and deep blue, vast scale",
    "tragis": "melancholic lighting: cold grey-blue light, rain or ash in the air, muted desaturated colours, long shadows",
    "misterius": "arcane mysterious lighting: deep teal and violet shadows, glowing runes and magical light, drifting mist",
    "horor": "dark horror lighting: sickly green and cold blue, fog, pale moonlight, heavy black shadows",
    "hangat": "warm gentle lighting: soft amber sunlight, lush greens, hopeful and calm",
}
STYLE = ("Dark fantasy graphic novel illustration, bold ink drawing with heavy black shadows and cross-hatching, rich "
         "fully drawn background with every part of the frame filled with environment details, cinematic depth with "
         "foreground and background, {mood}. Heroes and creatures shown as silhouettes, shadows or partial views, never a "
         "clear face. No blood, no gore, no wounds. Not cute, not anime. Wide cinematic 16:9 composition. Absolutely no "
         "text, no letters, no words, no numbers, no captions, no logos, no UI. Scene: ")

VISUAL_SYS = """Kamu storyboard artist untuk video lore hero game bergaya novel grafis fantasi bertinta: setiap gambar adalah ADEGAN LENGKAP dengan latar penuh dari dunia hero itu. Suasana gambar mengikuti mood cerita: {mood}. Untuk setiap potongan narasi, tulis satu deskripsi gambar dalam BAHASA INGGRIS (maks 45 kata) yang menggambarkan isi potongan itu secara konkret dan visual.
Wajib di tiap deskripsi: (1) TEMPAT yang spesifik dari lore (medan perang, kuil kuno, hutan, kota, gua, lautan, dan sebagainya) dengan 3-4 benda latar; (2) WAKTU dan CAHAYA yang sesuai mood; (3) aksi yang jelas.
Hero dan tokoh lain dari game itu: JANGAN gambar wajah atau desainnya secara utuh (desain resminya akan salah). Tunjukkan sebagai siluet, bayangan, dari belakang dan jauh, atau close-up tangan dan senjatanya, dan sebut ciri umumnya saja (mis. "a huge hulking silhouette dragging a meat hook on a chain"). Jangan pernah menulis nama hero di deskripsi; tulis bentuknya.
SEMUA adegan berada di dunia hero itu; bila narasi menyebut game lama atau versi sebelumnya, gambar tetap adegan dari kisah hero (tanpa komputer, pemain, atau dunia nyata).
Variasikan sudut kamera (wide shot dunia yang luas, close-up tangan atau senjata, dari bawah yang megah, dari atas) agar penonton tidak bosan.
Aturan: tanpa teks, huruf, angka, logo, atau antarmuka game; tanpa tokoh nyata atau merek; tanpa darah, gore, atau konten seksual; simbol agama hanya bila perlu dan dengan hormat.
"reveal": nomor potongan (i) di 45 detik pertama tempat hero ini paling pas diperkenalkan dengan jelas (potret resminya akan ditampilkan di atas gambar potongan itu); gambar latarnya cukup tempat hero itu berada, tanpa sosok di tengah.

"ambience": suara latar yang terdengar di tempat potongan itu, salah satu: sea (laut, pantai, kapal), rain (hujan, badai), wind (gunung, padang, salju, ketinggian), cave (gua, ruang bawah tanah, kuil sunyi), fire (api, kota terbakar, tungku), forest (hutan, alam yang tenang), battle (medan perang, pasukan), magic (sihir, dimensi lain, ritual), dark (kegelapan, kehampaan, ancaman tanpa tempat jelas). Biarkan sama untuk potongan berurutan di tempat yang sama.

Pilih juga efek suara dari katalog untuk potongan yang memang terbantu olehnya. Patokan: sekitar sepertiga potongan diberi efek, jangan dua potongan berurutan memakai efek yang sama; simpan efek besar (gong, boom, sub-drop) untuk momen yang benar-benar penting. "sfx_word" adalah SATU kata persis dari narasi potongan itu, tempat efek dibunyikan; null jika efek di awal potongan.
Katalog efek: {catalog}

Balas HANYA JSON: {{"reveal":0,"visuals":[{{"i":0,"visual":"...","ambience":"wind","sfx":"id-dari-katalog atau null","sfx_word":"kata atau null"}}]}} dengan satu entri untuk setiap potongan."""

AMBIENCES = {"sea", "rain", "wind", "cave", "fire", "forest", "battle", "magic", "dark"}
# Content sounds for lore; the cartoon ones (boing, pop, correct, ...) stay out of this channel.
LORE_SFX = {"heartbeat", "door-open", "door-close", "clock", "riser", "sub-drop", "weird", "whoosh-soft", "whoosh-fast",
            "glass", "slam", "metal", "drop", "hit", "paper", "boom", "splash", "gong", "bell", "sparkle"}


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
    plan = load(d / "plan.json") if (d / "plan.json").exists() else {}
    mood = plan.get("mood") if plan.get("mood") in MOOD_LOOK else "misterius"
    cat = [c for c in load(ROOT / "assets" / "sfx" / "catalog.json") if c["id"] in LORE_SFX]
    ids = {c["id"] for c in cat}
    catalog = json.dumps({c["id"]: c["desc"] for c in cat}, ensure_ascii=False)
    ch = chunks(s["narration"])
    assert " ".join(ch).split() == s["narration"].split(), "chunking changed the narration"
    log("scenes", len(ch))
    scenes = [{"i": i, "text": t} for i, t in enumerate(ch)]
    reveal = None
    # 40 at a time: a long storyboard in one reply is where JSON breaks.
    for at in range(0, len(ch), 40):
        part = scenes[at:at + 40]
        ctx = {"judul": s["title"], "potongan": [{"i": x["i"], "narasi": x["text"]} for x in part]}
        reply = claude_json("sonnet", VISUAL_SYS.format(catalog=catalog, mood=f"{mood} ({MOOD_LOOK[mood]})"),
                            json.dumps(ctx, ensure_ascii=False))
        got = {v["i"]: v for v in reply["visuals"]}
        if reveal is None and isinstance(reply.get("reveal"), int) and 0 <= reply["reveal"] < len(scenes):
            reveal = reply["reveal"]
        for x in part:
            v = got[x["i"]]
            x["visual"] = v["visual"]
            x["prompt"] = STYLE.format(mood=MOOD_LOOK[mood]) + " ".join(v["visual"].split())
            x["ambience"] = v.get("ambience") if v.get("ambience") in AMBIENCES else "dark"
            x["sfx"] = v.get("sfx") if v.get("sfx") in ids else None
            x["sfx_word"] = v.get("sfx_word") if x["sfx"] else None
        log("storyboard", at + len(part), "/", len(ch))
    for x in scenes:
        x["reveal"] = x["i"] == (reveal if reveal is not None else min(2, len(scenes) - 1))
    save(d / "scenes.json", scenes)
    log("mood:", mood, "| hero reveal at scene", next(x["i"] for x in scenes if x["reveal"]))
    log("scenes with sfx", sum(1 for x in scenes if x["sfx"]))


if __name__ == "__main__":
    main(sys.argv[1])
