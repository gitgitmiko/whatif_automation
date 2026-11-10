"""Step 1-2: Sonnet researches and writes the narration, Opus verifies it independently."""
import sys
from common import *

WRITER_SYS = """Kamu penulis naskah channel YouTube edukasi berbahasa Indonesia, seri "Apa yang terjadi jika ...".
Gunakan WebSearch dan WebFetch untuk riset dari sumber kredibel (jurnal, universitas, lembaga resmi, ensiklopedia ilmiah). Buka halamannya; jangan mengutip sumber yang tidak kamu baca.

Judul dan thumbnail sudah ditetapkan dari riset (lihat "paket" di pesan). Naskah WAJIB menepati "promise" paket itu; penonton yang mengklik harus mendapat persis yang dijanjikan.

Aturan naskah:
- Panjang {min_words}-{max_words} kata narasi lisan, setara {minutes} menit.
- Bahasa Indonesia santai, jelas, enak didengar, menyapa penonton dengan "kamu". Seperti teman pintar yang bercerita, bukan buku pelajaran.
- 15 DETIK PERTAMA (sekitar 40 kata) menentukan penonton bertahan: langsung masuk ke momen paling dramatis dari janji judul, dalam situasi konkret yang bisa dibayangkan penonton. Jangan buka dengan disclaimer, definisi, "menurut NASA", atau "di video ini kita akan". Lalu satu kalimat kenapa ini penting bagi penonton, dan satu kalimat peta singkat ("dari detik pertama sampai seribu tahun kemudian").
- Disclaimer bahwa ini skenario hipotetis cukup satu kalimat pendek, SETELAH pembuka (sekitar kalimat ke-5 sampai ke-8), bukan di awal.
- Jaga penonton sampai akhir: setiap 60-90 detik buka "pertanyaan menggantung" yang baru dijawab nanti ("tapi itu belum yang paling aneh..."). Taruh momen paling mengejutkan ("peak" di paket) sekitar dua pertiga video. Hindari bagian panjang yang datar.
- Alur per fase waktu atau sebab-akibat yang runtut, dengan detail konkret dan angka yang bisa dibayangkan (bandingkan dengan benda sehari-hari, tempat di Indonesia bila cocok).
- Penutup harus terasa memuaskan, bukan antiklimaks: rangkum perubahan terbesar dengan kalimat yang berkesan, lalu satu pertanyaan spesifik untuk dijawab di komentar.
- Pisahkan tegas fakta dan spekulasi. Skenario hipotetis harus diucapkan sebagai perkiraan ("kemungkinan", "para peneliti memperkirakan", "kalau kita berasumsi").
- Tulis untuk didengar: tanpa markdown, tanpa daftar, tanpa URL, tanpa sebutan "[1]" di dalam narasi.
- Jangan ada konten seksual, grafis, kebencian, atau merendahkan gender atau kelompok mana pun. Reproduksi dibahas secara ilmiah dan sopan.
- Topik yang menyentuh kematian atau cedera: fokus pada sains, kecelakaan, dan penyelamatan, tanpa detail luka yang grafis, tanpa petunjuk, tanpa kesan bahwa melukai diri itu cepat atau tidak sakit.
- Jangan menyalin kalimat dari sumber.
- Jangan menutup dengan ajakan like, subscribe, atau lonceng: itu ditambahkan otomatis di akhir video. Boleh menutup dengan pertanyaan untuk dijawab penonton di komentar.

Balas HANYA JSON:
{{"title":"judul dari paket, persis","description":"deskripsi 2-3 paragraf; kalimat pertama memuat kata kunci pencarian dari paket dan langsung memancing rasa ingin tahu","tags":["kata kunci pencarian dari paket", "..."],
"narration":"seluruh narasi, paragraf dipisah \\n\\n",
"sources":[{{"id":"S1","title":"...","url":"https://..."}}],
"claims":[{{"claim":"klaim faktual penting apa adanya dari narasi","source":"S1"}}],
"assumptions":["asumsi skenario yang dipakai"]}}"""

VERIFIER_SYS = """Kamu pemeriksa fakta independen dan skeptis untuk naskah video edukasi. Kamu tidak menulis naskah ini dan tidak boleh menganggapnya benar.
Periksa dengan WebSearch dan WebFetch. Buka setiap URL sumber yang dipakai klaim penting, dan cek apakah sumber itu benar-benar mendukung klaimnya.
Periksa juga: apakah judul menjanjikan sesuatu yang tidak dijawab narasi (clickbait palsu = major); angka dan tanggal; spekulasi yang diucapkan seolah fakta; sumber yang tidak ada atau tidak mendukung; kutipan ilmuwan yang salah atribusi; konten seksual, grafis, atau merendahkan kelompok tertentu.

severity "major" = klaim salah, tidak didukung sumber, spekulasi disajikan sebagai fakta, atau melanggar batas konten. "minor" = kurang tepat tapi tidak menyesatkan.
verdict "pass" hanya jika tidak ada issue major.

Balas HANYA JSON:
{"verdict":"pass|revise","checked":[{"claim":"...","source_id":"S1","url_opened":true,"status":"supported|partly|unsupported|wrong|source_unavailable","note":"..."}],
"issues":[{"severity":"major|minor","quote":"kutipan persis dari narasi","problem":"...","fix":"saran perbaikan"}]}"""

REVISER_SYS = """Perbaiki naskah sesuai temuan pemeriksa fakta. Judul tetap, kecuali pemeriksa menandai judul itu sendiri sebagai major: ubah seminimal mungkin agar jujur, kata kunci pencarian tetap di depan, maks 60 karakter; naskah harus tetap menepati "promise" di paket, dengan pembuka yang langsung dramatis dan penutup yang memuaskan. Riset ulang dengan WebSearch dan WebFetch bila perlu. Hapus klaim yang tidak bisa didukung. Pertahankan gaya dan panjang {min_words}-{max_words} kata. Balas HANYA JSON dengan bentuk yang sama seperti input (title, description, tags, narration, sources, claims, assumptions)."""


def words(s):
    return len(s["narration"].split())


def main(slug, topic, minutes=6.5, rounds=6):
    d = run_dir(slug)
    pack = load(d / "plan.json") if (d / "plan.json").exists() else {}
    pack = {k: pack[k] for k in ("title", "query", "hook", "promise", "angle", "peak") if k in pack}
    # Measured: edge-tts Ardi at +5% reads about 157 words a minute. Videos run 5-8 minutes.
    lo, hi = int(minutes * 140), int(minutes * 165)
    floor = int(5.2 * 157)  # under this the video runs short of 5 minutes
    fmt = dict(min_words=lo, max_words=hi, minutes=minutes)
    if (d / "script.draft.json").exists():
        s = load(d / "script.draft.json")
        log("resuming from existing draft, words", words(s))
    else:
        log("writer: sonnet researching", topic)
        s = claude_json("sonnet", WRITER_SYS.format(**fmt), f"Topik: {topic}\n\npaket: " + json.dumps(pack, ensure_ascii=False),
                        web=True)
        if pack.get("title"):  # the researched title stands; the writer only delivers on it
            s["title"] = pack["title"]
        save(d / "script.draft.json", s)
        log("draft words", words(s), "sources", len(s["sources"]))
    for r in range(1, rounds + 1):
        f = d / f"verify.{r}.json"
        if f.exists():
            report = load(f)
            log(f"verifier round {r}: reusing saved report")
        else:
            log(f"verifier round {r}: opus")
            report = claude_json("opus", VERIFIER_SYS, json.dumps(
                {**{k: s[k] for k in ("title", "narration", "sources", "claims", "assumptions")},
                 "thumbnail_hook": pack.get("hook")}, ensure_ascii=False), web=True)
            save(f, report)
        issues = report.get("issues", [])
        major = [i for i in issues if i.get("severity") == "major"]
        log("verdict", report["verdict"], "major", len(major), "minor", len(issues) - len(major), "words", words(s))
        short = words(s) < floor
        if not major and not short:  # the rule is "no major issues"; the verifier sometimes says revise over minors
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
        ask = {"script": s, "issues": issues, "paket": pack}
        if short:
            ask["panjang"] = (f"Narasi sekarang {words(s)} kata, terlalu pendek. Tambah materi baru yang benar-benar "
                              f"berisi dan bersumber sampai {lo}-{hi} kata.")
        reply = claude_json("sonnet", REVISER_SYS.format(**fmt), json.dumps(ask, ensure_ascii=False), web=True)
        s = reply.get("script", reply)  # the reply may mirror the input's wrapper
        if pack.get("title") and not any(i.get("quote") == pack["title"] for i in major):
            s["title"] = pack["title"]  # the researched title stands unless the verifier flagged the title itself
        save(d / f"script.rev{r}.json", s)
        log("revised words", words(s))
    save(d / "script.rejected.json", s)
    sys.exit("REJECTED: verifier still reports major issues or the script is too short; nothing proceeds")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 6.5)
