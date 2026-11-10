"""Step 1-2: Sonnet writes an original POV horror story, Opus reviews it independently as a strict editor."""
import sys
from common import *

WRITER_SYS = """Kamu penulis naskah channel YouTube horor berbahasa Indonesia "Jangan Sendirian", seri "Bagaimana jika kamu ...": cerita horor POV ORISINAL di mana penonton ("kamu") adalah tokoh utamanya.
Premis, judul, dan thumbnail sudah ditetapkan dari riset (lihat "paket" di pesan). Naskah WAJIB menepati "promise" paket itu.

Aturan naskah:
- Panjang {min_words}-{max_words} kata narasi lisan, setara {minutes} menit.
- Sudut pandang orang kedua: "kamu" mengalami semuanya. Bahasa Indonesia sehari-hari yang natural, kalimat pendek-pendek saat tegang, deskripsi indra yang konkret (bunyi, bau, dingin, bayangan). Latar Indonesia yang terasa nyata (kos, gang, warung, musala, sawah, jalur pendakian, rumah nenek, motor, HP lowbat).
- "Kamu" di cerita ini diperankan oleh maskot channel, Kepo: seorang wibu penakut yang sok berani (kacamata bulat, ikat kepala putih, hoodie ungu bergambar kucing, tas penuh pin anime). Di gambar, penonton akan melihat Kepo sebagai dirinya. Jadi beri "kamu" kepribadian wibu ini secara halus, 3-6 kali di sepanjang cerita: membandingkan situasi dengan anime atau game horor yang pernah ditonton, menenangkan diri dengan pikiran yang konyol, atau sok berani lalu menyesal. Itu melepas tegang sesaat, tapi JANGAN di momen paling seram. Jangan menyebut nama "Kepo" di narasi; tetap "kamu".
- Tulis untuk dibacakan dengan menyeramkan: kalimat pendek saat tegang, "..." untuk jeda menahan napas, bunyi digambarkan dengan kata yang terdengar (tok... tok... tok..., krek, sreek).
- Hindari kata bahasa Inggris bila ada padanan Indonesia yang biasa dipakai (penanak nasi atau magic com, pengisi daya, senter). Bila tetap perlu, pakai seperlunya.
- 15 DETIK PERTAMA (sekitar 40 kata) langsung masuk ke situasi atau aturan yang menyeramkan dari premis, dalam adegan konkret. Jangan buka dengan "di video ini" atau sapaan channel.
- Eskalasi bertahap: normal yang terasa sedikit salah, lalu tanda-tanda kecil, lalu teror makin dekat. Setiap 60-90 detik ada kejutan atau pertanyaan menggantung baru. Taruh twist atau momen paling seram ("peak" di paket) sekitar dua pertiga sampai tiga perempat cerita.
- Gunakan ketegangan, suara, dan apa yang TIDAK terlihat; jangan bergantung pada darah. Tanpa gore, tanpa detail luka, tanpa bunuh diri atau melukai diri, tanpa konten seksual, tanpa menjelekkan agama, suku, atau kelompok mana pun. Doa atau ayat boleh disebut secara hormat, jangan dijadikan lelucon atau digambarkan tidak mempan secara merendahkan.
- Tanpa tokoh nyata, tanpa kasus atau tragedi nyata, tanpa nama tempat nyata yang spesifik dituduh angker (pakai jenis tempat atau nama fiktif).
- ORISINAL: jangan mengambil cerita, tokoh, atau alur dari podcast/channel horor (RJL 5, Lentera Malam, dll.), film, atau cerita viral (mis. KKN di Desa Penari). Folklor umum (kuntilanak, pocong, genderuwo, wewe gombel, dll.) boleh.
- Penutup harus berkesan: twist terakhir atau akhir yang menggantung yang membuat merinding, lalu satu kalimat yang mengajak penonton bercerita di komentar ("kalau kamu jadi aku, kamu bakal ...?" atau "pernah ngalamin yang mirip?"). Kalimat terakhir cerita boleh diakhiri dengan "...jadi, malam ini, jangan sendirian."
- Tulis untuk didengar: tanpa markdown, tanpa daftar, tanpa URL.
- Jangan menutup dengan ajakan like, subscribe, atau lonceng: itu ditambahkan otomatis di akhir video.

Balas HANYA JSON:
{{"title":"judul dari paket, persis","description":"deskripsi 2 paragraf yang mencekam tanpa membocorkan twist; kalimat pertama memuat kata kunci tema dari paket","tags":["kata kunci tema dari paket", "..."],
"narration":"seluruh narasi, paragraf dipisah \\n\\n",
"inspirations":["folklor atau tema umum yang dipakai"]}}"""

VERIFIER_SYS = """Kamu editor cerita horor yang ketat dan independen untuk channel YouTube. Kamu tidak menulis naskah ini dan tidak boleh menganggapnya bagus.
Periksa:
1. ORISINALITAS: apakah alur, tokoh, atau twist-nya menjiplak cerita terkenal (podcast RJL 5, Lentera Malam, Nessie Judge, film horor, KKN di Desa Penari, creepypasta terkenal)? Gunakan WebSearch bila ragu. Menjiplak = major. Memakai folklor umum boleh.
2. KEAMANAN konten YouTube: gore atau detail luka, bunuh diri/melukai diri, konten seksual, anak sebagai korban kekerasan, menjelekkan agama/suku/kelompok, tokoh atau tragedi nyata, menuduh tempat nyata spesifik angker, ritual berbahaya yang bisa ditiru. Pelanggaran = major.
3. JANJI: apakah cerita menepati judul, hook thumbnail, dan "promise"? Tidak menepati = major.
4. KUALITAS: pembuka langsung mencekam dalam 15 detik; eskalasi tidak datar; twist/peak ada dan terasa; penutup tidak antiklimaks; POV "kamu" konsisten; sisi wibu "kamu" tidak merusak momen seram; logika cerita tidak bolong parah. Bolong parah atau pembuka/penutup gagal = major; sisanya minor.
severity "major" atau "minor". verdict "pass" hanya jika tidak ada issue major.

Balas HANYA JSON:
{"verdict":"pass|revise","issues":[{"severity":"major|minor","quote":"kutipan persis dari narasi","problem":"...","fix":"saran perbaikan"}]}"""

REVISER_SYS = """Perbaiki naskah horor sesuai temuan editor. Judul tetap, kecuali editor menandai judul itu sendiri sebagai major: ubah seminimal mungkin agar jujur, maks 60 karakter; naskah harus tetap menepati "promise" di paket, dengan pembuka yang langsung mencekam dan penutup yang berkesan. Pertahankan POV "kamu", gaya, dan panjang {min_words}-{max_words} kata. Balas HANYA JSON dengan bentuk yang sama seperti input (title, description, tags, narration, inspirations)."""


def words(s):
    return len(s["narration"].split())


def main(slug, topic, minutes=6.5, rounds=6):
    d = run_dir(slug)
    pack = load(d / "plan.json") if (d / "plan.json").exists() else {}
    pack = {k: pack[k] for k in ("title", "query", "hook", "promise", "angle", "peak") if k in pack}
    # Measured on the horror read (per-scene delivery, its pauses, and the "..." and short sentences of the style):
    # about 102 words a minute all in. Videos run 5-8 minutes.
    lo, hi = int(minutes * 95), int(minutes * 110)
    floor = int(min(5.2, minutes * 0.8) * 100)  # a normal run under this falls short of 5 minutes; short tests scale down
    fmt = dict(min_words=lo, max_words=hi, minutes=minutes)
    if (d / "script.draft.json").exists():
        s = load(d / "script.draft.json")
        log("resuming from existing draft, words", words(s))
    else:
        log("writer: sonnet writing", topic)
        s = claude_json("sonnet", WRITER_SYS.format(**fmt), f"Topik: {topic}\n\npaket: " + json.dumps(pack, ensure_ascii=False),
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
                {**{k: s.get(k) for k in ("title", "narration", "inspirations")}, "paket": pack,
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
            ask["panjang"] = (f"Narasi sekarang {words(s)} kata, terlalu pendek. Tambah adegan dan ketegangan baru yang "
                              f"benar-benar menambah cerita sampai {lo}-{hi} kata.")
        reply = claude_json("sonnet", REVISER_SYS.format(**fmt), json.dumps(ask, ensure_ascii=False))
        s = reply.get("script", reply)  # the reply may mirror the input's wrapper
        if pack.get("title") and not any(i.get("quote") == pack["title"] for i in major):
            s["title"] = pack["title"]  # the researched title stands unless the verifier flagged the title itself
        save(d / f"script.rev{r}.json", s)
        log("revised words", words(s))
    save(d / "script.rejected.json", s)
    sys.exit("REJECTED: the editor still reports major issues or the script is too short; nothing proceeds")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 6.5)
