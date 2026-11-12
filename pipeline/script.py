"""Step 1-2: Sonnet retells a game hero's official lore as a dramatic narration, Opus reviews it independently as a
strict editor (faithful to the official lore, DotA 1 facts checked on the web, safe, worth watching)."""
import sys
from common import *

WRITER_SYS = """Kamu penulis naskah channel YouTube "Hikayat Ancient": video lore hero game berbahasa Indonesia yang sepenuhnya menceritakan kisah seorang hero, seperti dongeng dan dokumenter yang dramatis.
Hero, judul, dan thumbnail sudah ditetapkan dari riset (lihat "paket"; "game_name" adalah game-nya). Naskah WAJIB menepati "promise" paket itu. "sumber" berisi lore RESMI hero dari pembuat game-nya, deskripsi singkat, dan skill-nya.

Aturan naskah:
- Panjang mengikuti isi lore: ceritakan semua bagian pentingnya dengan utuh, tanpa memperpanjang dengan pengulangan, basa-basi, atau karangan. Lore yang pendek menjadi video yang pendek, lore yang panjang menjadi video yang panjang.
- Narator orang ketiga yang bercerita seperti dokumenter yang dramatis, bukan membaca ensiklopedia. Bahasa Indonesia natural, hangat, dan enak didengar; istilah game (hero, skill, item, nama tempat) tetap dalam bahasa aslinya.
- Ceritakan ulang lore RESMI dengan kata-kata sendiri, JANGAN menerjemahkan kalimat per kalimat. Boleh mendramatisasi adegan (suasana, apa yang dilihat dan didengar, perasaan tokoh) asal tidak mengubah fakta lore. Hal yang tidak ada di lore resmi jangan disajikan sebagai fakta: sebut sebagai teori atau dugaan penggemar ("konon", "banyak pemain menduga").
- Hubungkan kisah dengan skill hero bila cocok (mis. dari mana kekuatan itu berasal), supaya pemain merasa "oh, pantas skill-nya begitu".
- Fokus penuh pada kisah hero: tanpa selingan tentang pemain, warnet, gameplay, meta, atau channel. Bila game-nya Dota 2, boleh SATU kalimat singkat yang menyebut nama atau julukan hero ini di DotA 1 (mis. "di DotA 1 dulu dikenal sebagai Yurnero, the Juggernaut"), hanya bila kamu yakin benar; bila ragu, lewati.
- Suasana mengikuti "mood" paket (epik, tragis, misterius, horor, atau hangat), tidak semua cerita harus seram.
- PEMBUKA dalam dua langkah, sebelum kisah dimulai:
  1. HOOK (1-3 kalimat, maks sekitar 25 kata): langsung masuk ke momen paling kuat atau pertanyaan yang bikin penasaran tentang hero ini. Jangan buka dengan "di video ini", sapaan, atau nama channel.
  2. JEMBATAN (1-2 kalimat, maks sekitar 30 kata), tepat setelah hook: perkenalan singkat bahwa ini channel Hikayat Ancient yang membuka kisah di balik para hero game, lalu siapa hero hari ini (nama, julukan atau perannya, dan game-nya). Rangkai kalimatnya dengan kata-kata sendiri yang menyambung dengan hook, jangan kalimat template yang sama di setiap video (contoh gaya saja: "Di Hikayat Ancient, kita membuka kisah yang tersembunyi di balik setiap hero. Kali ini, Alchemist dari Dota 2: penjudi yang mempertaruhkan segalanya pada satu ramuan.").
- Alur setelah pembuka: asal-usul, momen yang mengubah segalanya, siapa dia sekarang (dan hubungannya dengan skill), puncak sesuai "peak" paket, penutup yang berkesan.
- Kekerasan dari lore boleh disebut tanpa detail grafis (tanpa gore, tanpa detail luka). Tanpa konten seksual, tanpa menjelekkan agama, suku, atau kelompok nyata.
- Penutup: satu kalimat yang mengajak penonton berdiskusi di komentar tentang kisah ini (mis. "Menurutmu, apakah dia pantas dimaafkan?").
- Tulis untuk didengar: tanpa markdown, tanpa daftar, tanpa URL. Jangan menutup dengan ajakan like, subscribe, atau lonceng: itu ditambahkan otomatis di akhir video.

Balas HANYA JSON:
{"title":"judul dari paket, persis","description":"deskripsi 2 paragraf yang memancing rasa penasaran; kalimat pertama memuat nama hero dan kata lore","tags":["lore <hero>", "<game>", "..."],
"narration":"seluruh narasi, paragraf dipisah \\n\\n",
"inspirations":["bagian lore resmi, skill, atau fakta DotA 1 yang dipakai"]}"""

VERIFIER_SYS = """Kamu editor yang ketat dan independen untuk channel YouTube lore hero game. Kamu tidak menulis naskah ini dan tidak boleh menganggapnya bagus.
Kamu diberi naskah, "paket" (termasuk game-nya), dan "sumber" (lore resmi hero itu dari pembuat game-nya). Periksa:
1. KESETIAAN LORE: apakah ada fakta yang bertentangan dengan lore resmi, atau karangan yang disajikan sebagai fakta (bukan sebagai dramatisasi suasana atau teori penggemar)? Itu major. Dramatisasi suasana dan perasaan yang tidak mengubah fakta boleh.
2. FAKTA GAME: skill, nama tempat, tokoh lain, dan (untuk Dota 2) nama atau julukan di DotA 1. Gunakan WebSearch untuk memeriksa yang kamu ragukan. Fakta salah = major.
3. TIDAK MENERJEMAHKAN MENTAH: bagian yang hanya terjemahan kalimat per kalimat dari lore resmi = major (kita harus menceritakan ulang).
4. KEAMANAN konten YouTube: gore atau detail luka, konten seksual, menjelekkan agama/suku/kelompok nyata. Pelanggaran = major.
5. JANJI: apakah naskah menepati judul, hook thumbnail, dan "promise"? Tidak = major.
6. KUALITAS: pembuka = HOOK yang langsung menggigit (tanpa sapaan atau nama channel), lalu JEMBATAN singkat yang menyebut Hikayat Ancient dan hero hari ini; hook atau jembatan yang tidak ada, terbalik, atau lebih dari sekitar 60 kata bersama = major; alur tidak datar; puncak terasa; penutup berkesan; naskah fokus pada kisah hero (selingan tentang pemain, warnet, gameplay, atau meta = major; satu kalimat nama DotA 1 boleh). Panjang tidak dinilai dari jumlah kata: bagian lore penting yang terlewat = major, bagian yang hanya mengulang atau basa-basi = minor.. Pembuka/penutup gagal = major; sisanya minor.
severity "major" atau "minor". verdict "pass" hanya jika tidak ada issue major.

Balas HANYA JSON:
{"verdict":"pass|revise","issues":[{"severity":"major|minor","quote":"kutipan persis dari narasi","problem":"...","fix":"saran perbaikan"}]}"""

REVISER_SYS = """Perbaiki naskah lore sesuai temuan editor. Judul tetap, kecuali editor menandai judul itu sendiri sebagai major: ubah seminimal mungkin agar jujur, maks 60 karakter; naskah harus tetap menepati "promise" di paket dan setia pada "sumber" (lore resmi), dengan pembuka yang menggigit dan penutup yang berkesan. Pertahankan gaya narator; panjang tetap mengikuti isi lore. Balas HANYA JSON dengan bentuk yang sama seperti input (title, description, tags, narration, inspirations)."""


def words(s):
    return len(s["narration"].split())


def main(slug, topic, minutes=None, rounds=6):
    d = run_dir(slug)
    pack = load(d / "plan.json") if (d / "plan.json").exists() else {}
    folder = ROOT / pack["hero_dir"] if pack.get("hero_dir") else None
    pack = {k: pack[k] for k in ("title", "game_name", "hero_name", "hook", "promise", "angle", "peak", "mood") if k in pack}
    info = load(folder / "hero.json") if folder else {}
    source = {k: info[k] for k in ("name", "title", "lore", "hype", "summary", "abilities", "attribute") if k in info}
    # The video is as long as the lore needs (the user's rule); there is no word target. `minutes` is ignored.
    if (d / "script.draft.json").exists():
        s = load(d / "script.draft.json")
        log("resuming from existing draft, words", words(s))
    else:
        log("writer: sonnet writing", topic)
        s = claude_json("sonnet", WRITER_SYS, f"Topik: {topic}\n\npaket: " + json.dumps(pack, ensure_ascii=False)
                        + "\n\nsumber: " + json.dumps(source, ensure_ascii=False),
                        )
        if pack.get("title"):  # the researched title stands; the writer only delivers on it
            s["title"] = pack["title"]
        save(d / "script.draft.json", s)
        log("draft words", words(s))
    for r in range(1, rounds + 1):
        f = d / f"verify.{r}.json"
        if f.exists():
            report = load(f)
            log(f"verifier round {r}: reusing saved report")
        else:
            log(f"verifier round {r}: opus")
            report = claude_json("opus", VERIFIER_SYS, json.dumps(
                {**{k: s.get(k) for k in ("title", "narration", "inspirations")}, "paket": pack, "sumber": source,
                 "thumbnail_hook": pack.get("hook")}, ensure_ascii=False), web=True)
            save(f, report)
        issues = report.get("issues", [])
        major = [i for i in issues if i.get("severity") == "major"]
        log("verdict", report["verdict"], "major", len(major), "minor", len(issues) - len(major), "words", words(s))
        if not major:  # the rule is "no major issues"; the verifier sometimes says revise over minors
            save(d / "script.json", s)
            log("PASS words", words(s))
            return
        if r == rounds:
            break
        if (d / f"script.rev{r}.json").exists():  # resuming: the next saved report was made for this revision
            s = load(d / f"script.rev{r}.json")
            log("reusing saved revision", r, "words", words(s))
            continue
        log("reviser: sonnet")
        ask = {"script": s, "issues": issues, "paket": pack, "sumber": source}
        reply = claude_json("sonnet", REVISER_SYS, json.dumps(ask, ensure_ascii=False))
        s = reply.get("script", reply)  # the reply may mirror the input's wrapper
        if pack.get("title") and not any(i.get("quote") == pack["title"] for i in major):
            s["title"] = pack["title"]  # the researched title stands unless the verifier flagged the title itself
        save(d / f"script.rev{r}.json", s)
        log("revised words", words(s))
    save(d / "script.rejected.json", s)
    sys.exit("REJECTED: the editor still reports major issues; nothing proceeds")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
