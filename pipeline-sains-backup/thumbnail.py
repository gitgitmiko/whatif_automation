"""Step 5b: a YouTube thumbnail that hooks: Sonnet picks a dramatic picture and a 2-4 word hook, gflow draws the
picture, and the hook is set over it in a thick comic face with one word in yellow."""
import shutil, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from common import *
from images import gflow

FONT = ROOT / "assets" / "fonts" / "Bangers-Regular.ttf"
# Channel mascot: the same stickman in every thumbnail, so viewers learn to spot the channel in their feed.
MASCOT = ("a cheerful anime-fan stickman (the channel mascot) with a perfectly round plain WHITE head, thick black outline, "
          "two black dot eyes behind big round black-framed glasses, no hair, a plain white headband tied around the forehead "
          "with knot tails sticking out, and an oversized purple hoodie with a cute cartoon cat face")
STYLE = ("YouTube thumbnail, bold detailed hand-drawn cartoon, vivid saturated colors, bright lighting, high contrast. "
         f"LEFT 40 percent of the frame: an extreme close-up of {MASCOT}, head and shoulders only, the head huge and "
         "filling the left side, SHOCKED and SCARED face (wide eyes, raised eyebrows, sweat drops, mouth open in a scream; "
         "not smiling, not happy). RIGHT 60 percent: a detailed, "
         "busy dramatic scene showing the threat or the consequence, many elements, clear conflict, set in Indonesia when "
         "it fits. Keep the TOP RIGHT corner fairly calm (sky or wall). Absolutely no text, no letters, no words, no numbers. "
         "Scene: ")
SYS = """Kamu desainer thumbnail YouTube untuk channel edukasi "Apa yang terjadi jika ...". Tujuan: penonton langsung paham premisnya dalam 1 detik di layar HP dan penasaran, tanpa clickbait palsu: harus sesuai isi video.
Contoh thumbnail yang sukses: wajah stickman kaget close-up besar di kiri, adegan stasiun penuh zombie di kanan, teks "90 HARI VS ZOMBIE".
Berikan:
- "visual": adegan untuk sisi KANAN thumbnail dalam BAHASA INGGRIS (maks 40 kata): momen paling dramatis dari topik, konkret dan ramai, dengan ancaman atau akibat yang terlihat jelas (kerumunan, skala besar, kota atau alam Indonesia bila cocok). Jangan deskripsikan stickman utamanya (sudah otomatis close-up di kiri). Tanpa teks, tanpa tokoh nyata, tanpa kekerasan, darah, atau konten seksual.
- "hook": 2-4 kata bahasa Indonesia, HURUF BESAR, berupa PREMIS KONKRET yang menyebut subjek topik, idealnya dengan angka, "VS", atau kontras (contoh gaya: "90 HARI VS ZOMBIE", "1 HARI TANPA NYAMUK", "TOBA VS DUNIA", "LAUT HILANG 1 JAM"). Jangan kalimat teka-teki yang tak bisa dipahami tanpa judul.
- "highlight": satu kata dari hook yang diberi warna merah (sisanya kuning).
Gambar dan hook harus saling cocok: adegan menunjukkan persis apa yang dikatakan hook, bukan kebalikannya.
Balas HANYA JSON: {"visual":"...","hook":"...","highlight":"..."}"""


def fit_lines(draw, words, font_path, box_w, max_lines=2, start=210):
    """The biggest size at which the hook fits the box in at most max_lines lines."""
    for size in range(start, 60, -6):
        font = ImageFont.truetype(str(font_path), size)
        lines, cur = [], []
        for w in words:
            trial = " ".join(cur + [w])
            if cur and draw.textlength(trial, font=font) > box_w:
                lines.append(cur)
                cur = [w]
            else:
                cur.append(w)
        lines.append(cur)
        if len(lines) <= max_lines and all(draw.textlength(" ".join(l), font=font) <= box_w for l in lines):
            return font, lines
    return ImageFont.truetype(str(font_path), 60), [words]


def compose(picture, hook, highlight, out):
    W, H = 1280, 720
    img = Image.open(picture).convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    draw = ImageDraw.Draw(img)
    # Hook top right over the scene, like the big story channels: yellow with one red word, heavy black outline.
    words = hook.upper().split()
    box_w, box_h, right = int(W * 0.50), int(H * 0.46), W - 36
    font, lines = fit_lines(draw, words, FONT, box_w)
    asc, desc = font.getmetrics()
    while (asc + desc) * 0.9 * len(lines) > box_h and font.size > 60:
        font, lines = fit_lines(draw, words, FONT, box_w, start=font.size - 6)
        asc, desc = font.getmetrics()
    lh = int((asc + desc) * 0.9)
    y = 24
    hl = highlight.upper().strip("?!.,")
    for line in lines:
        x = right - draw.textlength(" ".join(line), font=font)
        for w in line:
            colour = (235, 40, 35) if w.strip("?!.,") == hl else (255, 222, 0)
            draw.text((x + 6, y + 8), w, font=font, fill=(0, 0, 0), stroke_width=14, stroke_fill=(0, 0, 0))
            draw.text((x, y), w, font=font, fill=colour, stroke_width=12, stroke_fill=(0, 0, 0))
            x += draw.textlength(w + " ", font=font)
        y += lh
    img.save(out, "JPEG", quality=90)


def main(slug, fresh=False):
    d = run_dir(slug)
    s = load(d / "script.json")
    pack = load(d / "plan.json") if (d / "plan.json").exists() and not fresh else {}
    if all(pack.get(k) for k in ("hook", "visual")):  # fixed with the title during research
        idea = {k: pack.get(k, "") for k in ("visual", "hook", "highlight")}
    else:
        idea = claude_json("sonnet", SYS, json.dumps({"judul": s["title"], "ringkasan": s["description"],
                                                      "awal_narasi": s["narration"][:1500]}, ensure_ascii=False))
    log("thumbnail idea:", idea["hook"], "|", idea["visual"])
    tmp = d / "thumb-gen"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    r = gflow("image", "t2i", STYLE + " ".join(idea["visual"].split()), "--aspect", "16:9", "--ui-mode", "classic",
              "--project", (d / "gflow-project.txt").read_text().strip(), "--out", tmp, timeout=600)
    pics = sorted(tmp.glob("*.jpg"))
    if not pics:
        sys.exit("gflow made no thumbnail picture: " + (r.stdout + r.stderr)[-500:])
    shutil.move(pics[0], d / "thumbnail-picture.jpg")
    shutil.rmtree(tmp, ignore_errors=True)
    compose(d / "thumbnail-picture.jpg", idea["hook"], idea.get("highlight", ""), d / "thumbnail.jpg")
    save(d / "thumbnail.json", idea)
    log("thumbnail written")


if __name__ == "__main__":
    main(sys.argv[1], fresh="--fresh" in sys.argv)
