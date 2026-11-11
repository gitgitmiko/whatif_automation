"""Step 5b: a YouTube thumbnail that hooks: the hero's official render on the left, a scene from its lore drawn by gflow
on the right, and a 2-4 word hook set over it in a thick comic face with one word in red."""
import shutil, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from common import *
from images import gflow

FONT = ROOT / "assets" / "fonts" / "Bangers-Regular.ttf"
# The hero's official art (a cut-out render, or the splash art framed as a panel) stands on the left, so viewers see at once whose lore this is; the AI only
# draws the world behind it.
STYLE = ("YouTube thumbnail background for a game hero lore video, dark fantasy graphic novel illustration with bold ink "
         "lines, dramatic high contrast lighting with one bright light source so it pops on a phone. The LEFT 40 percent "
         "of the frame is open ground and sky with no figure (a hero render is placed there later). RIGHT 60 percent: a "
         "detailed, dramatic scene from the hero's world. No characters' faces, no blood, no gore. Keep the TOP RIGHT "
         "corner fairly calm (sky or wall). Absolutely no text, no letters, no words, no numbers, no logos. Scene: ")
SYS = """Kamu desainer thumbnail YouTube untuk channel lore hero game "Hikayat Ancient". Tujuan: penonton langsung tahu hero siapa dan penasaran dengan kisahnya dalam 1 detik di layar HP, tanpa clickbait palsu.
Potret resmi hero otomatis ada di kiri. Berikan:
- "visual": latar sisi KANAN dalam BAHASA INGGRIS (maks 40 kata): tempat atau momen paling kuat dari lore, tanpa menggambar heronya. Tanpa teks.
- "hook": 2-4 kata bahasa Indonesia, HURUF BESAR, konkret dan sesuai lore (contoh gaya: "DIA TAK BISA MATI", "JAGAL MEDAN PERANG").
- "highlight": satu kata dari hook yang diberi warna merah (sisanya kuning).
Balas HANYA JSON: {"visual":"...","hook":"...","highlight":"..."}"""


def with_hero(picture, render, out):
    """The official render on the left of the picture, tall, with a dark glow so it stands off the background."""
    W, H = 1280, 720
    img = Image.open(picture).convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    hero = Image.open(render).convert("RGBA")
    if hero.getextrema()[3][0] == 255:  # no transparency: a splash picture, shown as a framed panel
        k = H * 0.86 / hero.height
        panel = hero.resize((round(hero.width * k), round(hero.height * k)), Image.LANCZOS)
        side = min(panel.width, int(W * 0.40))
        panel = panel.crop(((panel.width - side) // 2, 0, (panel.width - side) // 2 + side, panel.height))
        framed = Image.new("RGBA", (panel.width + 16, panel.height + 16), (12, 12, 16, 255))
        framed.paste(panel, (8, 8))
        hero = framed
    hero = hero.crop(hero.getbbox())
    k = min(H * 1.02 / hero.height, W * 0.52 / hero.width)
    hero = hero.resize((round(hero.width * k), round(hero.height * k)), Image.LANCZOS)
    x, y = max(int(W * 0.24) - hero.width // 2, -20), H - hero.height + 10
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow.paste((0, 0, 0, 200), (x, y), hero.getchannel("A"))
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    base = img.convert("RGBA")
    base.alpha_composite(glow)
    base.alpha_composite(hero, (x, y))
    base.convert("RGB").save(out, "JPEG", quality=95)


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
    folder = (load(d / "plan.json") if (d / "plan.json").exists() else {}).get("hero_dir")
    info = load(ROOT / folder / "hero.json") if folder and (ROOT / folder / "hero.json").exists() else {}
    render = ROOT / str(folder) / info.get("reveal", "render.png")
    picture = d / "thumbnail-picture.jpg"
    if render.exists():
        with_hero(picture, render, d / "thumbnail-hero.jpg")
        picture = d / "thumbnail-hero.jpg"
    compose(picture, idea["hook"], idea.get("highlight", ""), d / "thumbnail.jpg")
    save(d / "thumbnail.json", idea)
    log("thumbnail written")


if __name__ == "__main__":
    main(sys.argv[1], fresh="--fresh" in sys.argv)
