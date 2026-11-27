"""One "Gimana Jadinya?" Short, start to finish, into runs/<id>/:

  naskah  Claude (with web search) picks a fresh "gimana jadinya kalau kamu jadi …" (a profession: pilot, ojol, SAR…) and
          writes a point-of-view narration, scene by scene: the hero (src/hero.tsx) with a mood and a speech bubble,
          or a fact visual from the Remotion library in src/visuals.tsx                        -> script.draft.json
  cek     a second Claude pass checks every claim and number on the web and fixes them        -> script.json
  suara   Gemini TTS reads the whole story in one take, each line in its scene's emotion; faster-whisper times
          the words (edge-tts Ardi per scene when Gemini is out of quota)                  -> voice.mp3, props.json
  render  Remotion draws the 1080x1920 video                                                   -> final.mp4

  .venv/bin/python shorts/produce.py <id> [--script file.json] [--topic "mesin ATM"] [--idea ideas.json slot] [--style 3d]
      --script skips naskah and cek; --topic fixes what "kamu" becomes instead of letting the writer pick;
      --mode fakta|horor overrides the slot's mode (slot5 = horor); --idea writes the slot's idea from the 06:00 research (shorts/ideas.py); --style 3d draws each scene as a Flow
      3D render moved by the camera (src/scene3d.tsx) instead of the cartoon hero
"""
import asyncio, json, re, shutil, sqlite3, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path
import edge_tts

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from common import RUNS, claude_json, load, log, save  # noqa: E402

VOICE, RATE = "id-ID-ArdiNeural", "+8%"
FPS, GAP = 30, 0.25  # a short breath between scenes
SFX = {
    "whoosh": "sapuan cepat", "pop": "sesuatu muncul", "pop-up": "muncul ceria", "boing": "memantul, lucu",
    "riser": "ketegangan naik", "boom": "ledakan besar", "sub-drop": "dentuman berat, kejutan", "slam": "hantaman",
    "hit": "pukulan", "splash": "air menerjang", "sparkle": "ajaib, berkilau", "question": "tanda tanya, penasaran",
    "correct": "benar", "wrong": "salah", "clock": "detak jam, waktu berjalan", "heartbeat": "detak jantung",
    "bell": "lonceng", "gong": "gong", "glass": "kaca pecah", "drop": "jatuh", "metal": "logam", "machine": "mesin",
    "weird": "aneh",
}
TYPES = {"pov", "globe", "icon", "gauge", "bars", "versus", "fly", "rise", "swarm", "timeline", "thermo", "number", "wind", "outro"}

MOODS = ["happy", "shock", "tired", "angry", "sad", "dizzy", "love", "smug", "scared", "proud"]
THEMES = ["kota", "malam", "ruangan", "alam", "dapur", "laut"]
# The emotion each line is read in. Gemini gets the English tag (it acts it out, never reads it); edge-tts, which has
# no speaking styles for Indonesian, only bends pace, pitch and loudness: (tag, rate, pitch, volume).
EMOSI = {
    "tegang": ("[tense]", "+6%", "-2Hz", "+0%"), "panik": ("[panicked]", "+14%", "+2Hz", "+6%"),
    "kaget": ("[shocked]", "+12%", "+4Hz", "+10%"), "serius": ("[serious]", "+4%", "-3Hz", "+0%"),
    "kagum": ("[amazed]", "+6%", "+2Hz", "+0%"), "senang": ("[excited]", "+12%", "+3Hz", "+4%"),
    "lega": ("[relieved]", "+4%", "+1Hz", "+0%"), "sedih": ("[sad]", "-4%", "-4Hz", "-6%"),
    "bisik": ("[whispering]", "-2%", "-5Hz", "-25%"), "takut": ("[scared]", "-2%", "-3Hz", "-8%"),
}
# Recurring series, so viewers come back for the next episode; the tag shows after the hook (TopTag).
SERIES = {
    "NIGHT SHIFT": "shift malam saat semua orang tidur (satpam, kasir 24 jam, petugas hotel, operator CCTV, teknisi server, masinis kereta terakhir)",
    "EMERGENCY": "darurat medis dan penyelamatan (dokter IGD, perawat, sopir ambulans, operator 112, tim SAR, pemadam kebakaran)",
    "PEKERJAAN EKSTREM": "ketinggian, bawah tanah, laut dalam, cuaca ganas (teknisi tower, penambang, penyelam, pekerja offshore, pilot saat badai)",
    "DI BALIK LAYAR": "profesi yang jarang terlihat tapi menjaga semua tetap jalan (petugas ATC, operator bendungan, teknisi lift, forensik)",
    "HARI TERBURUK": "satu hari saat semua yang bisa salah benar-benar salah, di profesi sehari-hari (ojol, kurir, montir, chef)",
}
# fakta: a true moment explained with checked facts. horor: original horror fiction set in a real job whose
# procedures and tools are true. The night slot is horror; the others stay factual.
MODE_BY_SLOT = {"slot1": "fakta", "slot2": "fakta", "slot3": "fakta", "slot4": "fakta", "slot5": "horor"}  # slot5 = 20:00

LIBRARY = """JENIS VISUAL (field "visual" tiap adegan; semua teks di layar HURUF BESAR otomatis, buat SINGKAT):
- {"type":"pov","mood":"happy|shock|tired|angry|sad|dizzy|love|smug|scared|proud","say":"...","motion":"idle|shake|jump|spin|shiver|tilt","props":["🧍","💳"],"props_motion":"around|rain|queue|burst|in|hit","stamp":"..."}  SANG TOKOH (benda yang kamu perankan, dari field "hero") digambar besar dengan wajah dan ekspresi mood. say = isi hati/ucapan tokoh di gelembung bicara, maks 5 kata, lucu, BUKAN pengulangan narasi (boleh kosong). motion terjadi di kata cue (shake = terguncang, jump = melompat kaget, spin = berputar, shiver = gemetar terus, tilt = miring lesu). props = 0-4 emoji: around = mengelilingi, queue = antre di depan, rain = berjatuhan dari atas, burst = menyembur keluar dari tokoh di kata cue (uang keluar dari ATM), in = melesat masuk ke tokoh di kata cue (kartu masuk, koin dimasukkan), hit = menghantam tokoh dari samping tepat di kata cue (tendangan, linggis, bola). Pilih props dan motion yang MEMPERAGAKAN kalimatnya, bukan hiasan.
- {"type":"globe","mode":"spin|stop|night|hot|frozen","stamp":"..."}  Bumi animasi. stop = berputar lalu berhenti mendadak di kata cue; night = setengah gelap dengan Matahari; hot = memerah membara; frozen = membeku putih.
- {"type":"icon","emoji":"🦖","motion":"pop|shake|float|spin|grow|shrink|explode","stamp":"..."}  satu emoji besar. explode = meledak di kata cue; grow/shrink = membesar/mengecil sampai kata cue.
- {"type":"gauge","value":1660,"unit":"km/jam","label":"Jakarta","max":2000}  speedometer naik ke value di kata cue.
- {"type":"bars","unit":"km/jam","items":[{"label":"Pesawat","value":900,"emoji":"✈️","at":"pesawat"},{"label":"Kamu","value":1660,"emoji":"🧍","highlight":true}]}  perbandingan 2-4 batang; tiap batang muncul saat kata "at" diucapkan (kosongkan "at" = muncul di awal). Nilai harus sebanding (rasio terbesar/terkecil < 50).
- {"type":"versus","left":{"emoji":"🌞","label":"Sekarang"},"right":{"emoji":"🥶","label":"Nanti"},"stamp":"..."}  dua sisi dibandingkan; sisi kanan muncul di kata cue.
- {"type":"fly","emojis":["🏠","🚗","🧍"],"direction":"right|left|up|down","ground":true,"stamp":"..."}  1-4 benda diam lalu terlempar ke arah itu di kata cue.
- {"type":"rise","fluid":"water|lava|ice|sand","stamp":"..."}  cairan naik menenggelamkan kota.
- {"type":"swarm","emoji":"🧍","count_label":"8 miliar","stamp":"..."}  satu emoji berlipat ganda memenuhi layar sampai kata cue.
- {"type":"timeline","steps":[{"time":"1 detik","emoji":"⚡","label":"Listrik padam","at":"detik"}]}  2-4 langkah waktu, tiap langkah muncul di kata "at"-nya.
- {"type":"thermo","value":60,"unit":"°C","min":0,"max":80,"label":"Suhu Jakarta","stamp":"..."}  termometer naik ke value di kata cue.
- {"type":"number","value":8000000000,"unit":"orang","label":"...","emoji":"🧍","stamp":"..."}  satu angka besar menghitung naik.
- {"type":"wind","emoji":"🌴","stamp":"..."}  angin kencang menerpa sesuatu.
"stamp" opsional, maks 3 kata / 18 huruf, menegaskan momen di kata cue (contoh "STOP!", "3× LEBIH KENCANG", "TSUNAMI RAKSASA"). Emoji harus emoji Unicode standar yang umum. Tokoh adalah bintangnya: kira-kira separuh adegan memakai "pov" (moodnya berganti-ganti mengikuti cerita), sisanya visual fakta yang mendukung angka. Jenis selain pov jangan dipakai lebih dari 2 kali."""

WRITER_SYS = f"""Kamu penulis naskah YouTube Shorts untuk channel "Gimana Jadinya?". Formatnya POINT OF VIEW: setiap video mengajak penonton membayangkan "gimana jadinya kalau KAMU jadi <profesi>", lalu menjalani SATU momen paling menegangkan dari pekerjaan itu, penuh fakta nyata yang mengejutkan, dalam animasi grafis 35-50 detik. Penonton: orang Indonesia umum, remaja sampai dewasa.

1. Pilih SATU profesi nyata yang dikenal orang Indonesia (sehari-hari seperti driver ojol, kasir minimarket, tukang parkir, satpam; berbahaya seperti pilot, pemadam kebakaran, penyelam, tim SAR, teknisi PLN; atau di balik layar seperti petugas menara ATC, dokter IGD, operator bendungan) dan SATU momen krisis atau keputusan sulit yang benar-benar bisa dialami profesi itu. Rumusnya: PROFESI + WAKTU ATAU KEADAAN EKSTREM + KEJADIAN TAK TERDUGA (contoh: dokter IGD saat malam tahun baru, kasir minimarket pukul 02.00, kurir saat banjir, teknisi server saat semua bank sedang tutup buku). Jam yang spesifik ("Pukul 03.17") membuat momen langsung terbayang dan bisa dipakai lagi di akhir untuk loop. Hormati profesinya: nada kagum dan empatik, BUKAN mengejek. Kalau ada "topik_wajib", pakai itu. Kalau ada "ide_dari_riset" (hasil riset Shorts yang sedang meledak), ikuti sudut ceritanya, kembangkan draf hook-nya (boleh dipertajam, tetap ikuti aturan hook di bawah), dan tetap cek ulang faktanya. Boleh terinspirasi dari saran pencarian YouTube yang diberikan. DILARANG mengulang atau sangat mirip dengan yang sudah pernah dibuat. Hindari politik, agama, SARA, tragedi nyata tertentu, polisi/tentara dalam konteks kontroversial, hal jorok, dan hal sadis.
2. Riset dengan pencarian web: cari 4-6 fakta NYATA dan mengejutkan tentang profesi itu dan momen krisisnya (prosedur resmi, alat, aturan keselamatan, angka, batas waktu, jam kerja atau penghasilan bila relevan, terutama di Indonesia). Setiap angka dan klaim harus benar menurut sumber tepercaya (bank sentral, produsen, lembaga resmi, jurnal, ensiklopedia, media besar). Kalau angka berupa perkiraan, katakan "sekitar" atau "diperkirakan".
3. Tulis narasi Bahasa Indonesia santai (pakai "kamu", sudut pandang orang yang menjalani profesi itu), total 70-100 kata (30-40 detik), dalam 6-8 adegan, tiap adegan 5-18 kata. Ikuti pola Shorts edukasi paling laris (Zack D. Films, median 10 juta views):
   a. KALIMAT PERTAMA LANGSUNG DI TENGAH AKSI. Judul "Kalau kamu jadi ..." sudah tampil di layar sejak detik pertama, jadi narasi TIDAK BOLEH membuka dengan "Gimana jadinya kalau", pertanyaan, salam, atau perkenalan. Buka dengan momen paling dramatis yang SEDANG terjadi padamu saat bekerja, maksimal 14 kata, konkret dan bisa digambar, dan HARUS mengandung taruhan nyata: nyawa (milikmu atau orang lain), uang, batas waktu, atau malu besar. Suasana biasa ("kamu berangkat kerja", "hari pertama kerja") BUKAN hook. Tulis dulu 5 kandidat di "hook_candidates", beri tiap kandidat nilai 1-10 di "hook_scores" (taruhan terbesar + paling mudah dibayangkan dalam 1 detik = nilai tertinggi), lalu WAJIB pakai kandidat bernilai tertinggi sebagai kalimat pertama dan bangun cerita dari situ. Contoh pola: "Ketinggian 300 meter, dan sesuatu baru saja menghantam kaca kokpitmu." / "Gagang pintu itu panas, dan asap hitam keluar dari celah bawahnya." / "Kamu terima selembar seratus ribu, dan teksturnya terasa aneh di jarimu."
   b. Lalu jelaskan KENAPA itu terjadi dengan fakta nyata ("Soalnya...", "Ternyata..."), satu rantai sebab-akibat, BUKAN daftar fakta yang dilompat-lompat. Setiap adegan menyambung ke adegan berikutnya dengan "Lalu", "Tapi", "Makanya", "Masalahnya".
   c. Di tengah, satu belokan: "Tapi ada satu masalah..." atau fakta yang membalik dugaan penonton.
   d. Tutup dengan punchline atau fakta paling mengejutkan, lalu BERHENTI. Tanpa ajakan komentar, tanpa "kamu mau jadi apa", tanpa kesimpulan. {{ENDING_RULE}}
   e. Boleh ada humor ringan dari situasi kerja khas Indonesia (tanggal gajian, macet, mudik, pelanggan rewel), tapi ketegangan tetap jadi tulang punggung; jangan mengejek profesi atau orang.
4. Angka ditulis dengan digit format Indonesia (1.660, 8 miliar, 3,5) supaya terbaca di caption; satuan ditulis seperti diucapkan: "kilogram", "derajat Celsius", "persen", "rupiah" (Rp 100 ribu ditulis "100 ribu rupiah"). Hindari kata bahasa Inggris dan singkatan yang sulit dibaca mesin suara.
5. "hero" menggambarkan tokohmu, sama di semua adegan: "name" (nama pendek benda), "body" ("box" untuk mesin/benda kotak seperti ATM, vending machine, kulkas, lift; "emoji" untuk lainnya), "emoji" (box: lambang di dada mesin, misalnya 💵 untuk ATM, 🥤 untuk vending machine; emoji: emoji standar yang paling mirip bendanya, misalnya 🦟 🪙 🍚), "color" (warna badan hex, misalnya "#1f8a4c"; hanya untuk box), Untuk profesi pakai body "emoji" dengan emoji profesi standar (👨‍✈️ 🧑‍🚒 🧑‍⚕️ 👷 🧑‍🔧 💂 🧑‍🍳) dan face false. "face" (true HANYA kalau emojinya menghadap depan dengan bidang polos di tengah untuk ditempeli mata dan mulut, misalnya 🪙 🍚 🥚 🧻 🎈 🍩 🧊; false untuk emoji yang tampak samping atau sudah punya wajah, misalnya 🐜 🦟 🪳 🦎 🚗, maka tokoh memakai emoji reaksi sesuai mood). "theme" adalah latar: {", ".join(THEMES)}.
6. Tiap adegan: "text" (narasi), "visual" (dari daftar di bawah, isinya harus sesuai dengan narasi dan angkanya sama persis), "cue" (SATU kata yang ada persis di text adegan itu, saat aksi utama/stamp terjadi), "sfx" (satu dari: {", ".join(f"{k} ({v})" for k, v in SFX.items())}; boleh kosong), "emosi" (nada suara narator di kalimat itu: {", ".join(EMOSI)}; ikuti perasaan orang yang mengalaminya dan buat BERGANTI mengikuti alur, misalnya kaget di hook, serius saat menjelaskan, panik di belokan, lega atau tegang di akhir).
7. "seri": pilih SATU seri yang paling cocok: {"; ".join(f"{k} = {v}" for k, v in SERIES.items())}.

{LIBRARY}

Balas HANYA JSON:
{{"title":"Kalau Kamu Jadi ...?" (maks 42 huruf, tampil di bawah label GIMANA JADINYA? sepanjang video),
 "hook_text":"..." (teks raksasa di layar pada detik 0-2: maks 4 kata + 1 emoji, merangkum krisisnya, huruf besar, contoh "PILOT VS BURUNG 💥", "GAGANG PINTU PANAS 🔥", "UANG PALSU? 😳"),
 "yt_title":"..." (maks 70 huruf: pernyataan yang memancing rasa penasaran, jujur, diawali "Kalau Kamu Jadi <profesi>," atau "Jadi <profesi>:", diakhiri satu emoji, contoh "Kalau Kamu Jadi Pilot, Burung Sekecil Ini Bisa Mematikan Mesinmu 😨"),
 "description":"2-3 kalimat ringkasan menarik",
 "tags":["8-12 tag"],
 "sources":["2-4 URL sumber yang benar-benar kamu pakai"],
 "hook_candidates":["5 kandidat kalimat pertama"],
 "hook_scores":[8,5,9,6,7],
 "seri":"NIGHT SHIFT",
 "hero":{{"name":"...","body":"box|emoji","emoji":"...","color":"#......","face":true}},
 "theme":"...",
 "scenes":[{{"text":"...","visual":{{...}},"cue":"...","sfx":"...","emosi":"tegang"}}]}}"""

CHECK_SYS = f"""Kamu pemeriksa fakta dan editor naskah YouTube Shorts "Gimana Jadinya?" (format point of view: "gimana jadinya kalau kamu jadi <sesuatu>"). Kamu menerima naskah JSON.
1. Periksa SETIAP klaim dan angka di narasi DAN di visual dengan pencarian web ke sumber tepercaya. Perbaiki yang salah atau berlebihan; samakan angka di visual dengan narasi. Klaim spekulatif harus ditandai "menurut perkiraan ilmuwan" atau sejenisnya.
2. Pastikan aturan: 6-8 adegan; total 70-100 kata; kalimat pertama langsung di tengah aksi dengan konflik (bahaya, sakit, serangan, keanehan; maks 14 kata, TIDAK diawali "Gimana jadinya", pertanyaan, atau perkenalan; kalau melanggar, tulis ulang kalimat pertamanya); kalimat pertama adalah kandidat dengan nilai tertinggi di "hook_scores" bila ada; adegan saling menyambung sebagai satu rantai sebab-akibat dengan satu belokan; penutup berhenti di punchline tanpa ajakan komentar atau pertanyaan ke penonton; kira-kira separuh adegan visual pov dengan mood yang berganti dan props yang memperagakan kalimat; "say" maks 5 kata dan tidak mengulang narasi; tiap "cue" adalah kata yang ada persis di text adegannya; angka pakai digit format Indonesia; stamp maks 18 huruf; {{ENDING_CHECK}}; "hook_text" maks 4 kata + 1 emoji dan sesuai krisis di kalimat pertama; nada menghormati profesi (perbaiki kalau terdengar mengejek); prosedur dan angka profesi sesuai sumber resmi; visual sesuai daftar berikut.

{LIBRARY}

3. Pertahankan "emosi" tiap adegan (perbaiki kalau tidak cocok dengan kalimatnya). Jangan mengubah topik, "hero", atau "theme". Pertahankan gaya santai dan lucu. Perbarui "sources" dengan URL yang kamu pakai untuk memeriksa.
Balas HANYA JSON: {{"issues":["daftar yang kamu perbaiki, kosong kalau tidak ada"],"script":{{...naskah lengkap yang sudah diperbaiki, format sama...}}}}"""


CAMERAS = ["push", "pull", "pan_left", "pan_right", "rise", "fall"]
IMAGE_STYLE = ("Stylized 3D CGI render, not a photograph, vertical 9:16 composition with the subject centred and room "
               "above and below. Clean studio lighting, soft shadows, smooth saturated colours, shallow depth of field, "
               "simple uncluttered background, high-end science explainer animation style. No text, no letters, no "
               "numbers, no logos, no watermark, no blood.")

_RULES_3D = """5. "hero_look" (bahasa Inggris): deskripsi fisik TOKOH "kamu" (orang Indonesia yang menjalani profesi itu) yang SAMA PERSIS dipakai di setiap prompt gambar yang menampilkannya, supaya wajah, rambut, dan seragamnya konsisten (contoh: "a young Indonesian male pilot with short black hair and a thin moustache, white shirt with four gold stripes on the epaulettes, black tie, aviator headset"). Tokoh digambar sebagai karakter 3D bergaya dengan wajah ekspresif yang menunjukkan emosi adegan.
6. Tiap adegan: "text" (narasi), "image" (prompt bahasa Inggris untuk SATU gambar render 3D yang MEMPERAGAKAN kalimat itu secara harfiah, 25-60 kata: subjek, aksi, sudut kamera, latar. Kalau tokohmu tampil, tulis hero_look apa adanya di dalamnya. Pakai variasi khas video penjelas: close-up dramatis wajah tokoh, tampak potongan/cutaway yang memperlihatkan isi alat atau mesin, x-ray, makro sampai skala molekul, sudut rendah. Latar polos warna solid (biru, teal, oranye) untuk adegan penjelasan, lokasi sederhana khas Indonesia untuk adegan cerita. Orang digambar sebagai karakter 3D bergaya, wajah ekspresif. Jangan menulis teks atau angka di gambar), "camera" (gerak kamera: push = maju pelan, pull = mundur, pan_left/pan_right = geser, rise/fall = naik/turun; variasikan), "label" (opsional, maks 12 huruf: angka/kata kunci yang melayang di layar saat kata cue, contoh "300 KG", "121°C", "3×"; pakai di 2-4 adegan yang punya angka), "cue" (SATU kata yang ada persis di text adegan itu, saat label muncul atau aksi terjadi), "sfx" (satu dari: {sfx}; boleh kosong), "emosi" (nada suara narator di kalimat itu: {emosi}; ikuti perasaan orang yang mengalaminya dan buat BERGANTI mengikuti alur, misalnya kaget di hook, serius saat menjelaskan, panik di belokan, lega atau tegang di akhir)."""

_RULES_3D_TEXT = _RULES_3D.format(sfx=", ".join(f"{k} ({v})" for k, v in SFX.items()), emosi=", ".join(EMOSI))
WRITER_3D = WRITER_SYS.replace(WRITER_SYS[WRITER_SYS.index("5. \"hero\" menggambarkan"):WRITER_SYS.index("Balas HANYA JSON:")],
                               _RULES_3D_TEXT
                               + "\n7. \"seri\": pilih SATU seri yang paling cocok: "
                               + "; ".join(f"{k} = {v}" for k, v in SERIES.items()) + ".\n\n")
WRITER_3D = WRITER_3D.replace("dalam animasi grafis 35-50 detik", "dalam animasi render 3D 30-40 detik")
_JSON_3D = """ "seri":"NIGHT SHIFT",
 "hero_look":"...",
 "scenes":[{"text":"...","image":"...","camera":"push","label":"","cue":"...","sfx":"...","emosi":"tegang"}]}"""
WRITER_3D = WRITER_3D.replace(""" "hero":{{"name":"...","body":"box|emoji","emoji":"...","color":"#......","face":true}},
 "theme":"...",
 "scenes":[{{"text":"...","visual":{{...}},"cue":"...","sfx":"...","emosi":"tegang"}}]}}""".replace("{{", "{").replace("}}", "}"),
 _JSON_3D)

CHECK_3D = CHECK_SYS[:CHECK_SYS.index("kira-kira separuh adegan visual pov")] + (
    "setiap adegan punya \"image\" (prompt bahasa Inggris yang memperagakan kalimatnya secara harfiah, memuat hero_look "
    "kalau tokohnya tampil, tanpa teks di gambar, tanpa darah), \"camera\" salah satu dari " + ", ".join(CAMERAS) +
    ", \"label\" maks 12 huruf dan angkanya sama dengan narasi; tiap \"cue\" adalah kata yang ada persis di text "
    "adegannya; angka pakai digit format Indonesia; {ENDING_CHECK}; \"hook_text\" "
    "maks 4 kata + 1 emoji dan sesuai krisis di kalimat pertama; nada menghormati profesi; prosedur dan angka profesi "
    "sesuai sumber resmi.\n\n3. Pertahankan \"emosi\" tiap adegan (perbaiki kalau tidak cocok). Jangan mengubah topik atau \"hero_look\". Pertahankan gaya "
    "santai dan menegangkan. Perbarui \"sources\" dengan URL yang kamu pakai untuk memeriksa.\nBalas HANYA JSON: "
    "{\"issues\":[\"daftar yang kamu perbaiki, kosong kalau tidak ada\"],\"script\":{...naskah lengkap yang sudah "
    "diperbaiki, format sama...}}")


# Real-time 3D worlds (shorts/src/worlds) and what the writer may use in each: shots, anchors, props, poses, hats.
try:
    WORLDS = load(HERE / "worlds.json")
except Exception as e:  # noqa: BLE001 - a broken catalog must not stop the Flow and cartoon styles
    log("worlds.json unreadable, no 3D worlds:", e)
    WORLDS = {}


def world_menu(world):
    """The chosen world as the writer and checker read it: every shot with its meaning, anchors and hero flag."""
    w = WORLDS[world]
    shots = "\n".join(f'   - {k}: {v["arti"]}' + (f' (anchor: {", ".join(v["anchors"])})' if v["anchors"] else "")
                      + (" [TOKOH TAMPIL]" if v["tokoh"] else "") for k, v in w["shots"].items())
    latar = "".join(f'\n   - {k}: {v["arti"]} (anchor: {", ".join(v["anchors"])})' for k, v in w.get("latar", {}).items())
    return (f'DUNIA 3D "{world}" (cocok untuk: {w["cocok"]}).' + (f' Latar yang tersedia (kolom "latar" tiap adegan):{latar}\n' if latar else "")
            + f' Shot yang tersedia:\n{shots}\n'
            f'   {w.get("catatan", "")}\n   Benda: {", ".join(w["props"])}. Pose tokoh: {", ".join(w["poses"])}. '
            f'Ekspresi: {", ".join(w["exprs"])}. Topi: {", ".join(w["topi"])}.'
            + (f' Efek: {", ".join(w["efek"])}.' if w.get("efek") else ""))


def prompts_remotion(world, ending, mode="fakta"):
    """Writer and checker for a script told as shots of a real-time 3D world instead of picture prompts."""
    writer, checker = prompts(True, ending, mode)
    rules = (f'5. Video ini animasi 3D real-time di dunia yang sudah jadi. "world" WAJIB "{world}". "hero" adalah tokoh "kamu": '
             '{"seragam":"#hex warna seragam profesi itu","topi":"salah satu topi di daftar"}; tokoh hanya tampil di shot bertanda TOKOH TAMPIL.\n'
             '6. Tiap adegan: "text" (narasi), "shot" (SATU nama shot dari daftar di bawah yang paling memperagakan kalimatnya; jangan pakai shot '
             'yang sama dua kali berturut-turut; minimal 5 shot berbeda dalam satu video), "hero_pose" dan "hero_expr" (hanya di shot bertanda '
             'TOKOH TAMPIL: pose dan ekspresi dari daftar, ekspresi mengikuti emosi kalimatnya), "props" (opsional, maks 3: '
             '[{"jenis":"nama benda dari daftar","di":"nama anchor milik shot itu"}], hanya untuk benda yang memang ada di cerita), '
             '"label" (opsional, maks 12 huruf: angka/kata kunci yang melayang di layar saat kata cue, contoh "300 KG", "121°C"; pakai di 2-4 '
             'adegan yang punya angka), "cue" (SATU kata yang ada persis di text adegan itu), "sfx" (satu dari: '
             + ", ".join(f"{k} ({v})" for k, v in SFX.items()) + '; boleh kosong), "emosi" (nada suara narator: ' + ", ".join(EMOSI)
             + '; buat BERGANTI mengikuti alur, misalnya kaget di hook, serius saat menjelaskan, panik di belokan, lega atau tegang di akhir).\n'
             + world_menu(world))
    if WORLDS[world].get("latar"):
        rules += ('\n   Dunia ini punya beberapa LATAR: tiap adegan WAJIB punya "latar" (nama dari daftar latar, pilih yang sesuai '
                  'tempat kejadian kalimatnya; boleh berganti antar adegan) dan boleh punya "efek" (salah satu efek di daftar, menyala '
                  'di benda kerja; shot "bahaya" tanpa efek memakai efek bawaan latar).')
    for inset in sorted(i for i in INSETS if i != world and WORLDS[i].get("aktif")):  # live insets only
        rules += (f'\n   Untuk menjelaskan sesuatu, satu adegan boleh pindah sebentar ke dunia "{inset}": tulis "world":"{inset}" di adegan '
                  f'itu dan pilih shot dari dunia {inset} (tanpa latar, benda, atau pose).\n' + world_menu(inset))
    extra = '"latar":"...","efek":"",' if WORLDS[world].get("latar") else ""
    writer = writer.replace(_RULES_3D_TEXT, rules).replace(_JSON_3D, """ "seri":"NIGHT SHIFT",
 "world":"%s",
 "hero":{"seragam":"#2b4c8c","topi":"none"},
 "scenes":[{"text":"...",%s"shot":"...","hero_pose":"","hero_expr":"","props":[],"label":"","cue":"...","sfx":"...","emosi":"tegang"}]}""" % (world, extra))
    a = checker.index('setiap adegan punya "image"')
    b = checker.index('"label" maks 12 huruf')
    checker = (checker[:a] + 'setiap adegan punya "shot" dari daftar dunia di bawah (tidak sama dengan adegan sebelumnya, minimal 5 shot berbeda), '
               '"hero_pose"/"hero_expr" hanya dari daftar dan hanya di shot TOKOH TAMPIL, "props" hanya benda dan anchor shot itu (maks 3), '
               + checker[b:]).replace('Jangan mengubah topik atau "hero_look"', 'Jangan mengubah topik, "world", atau "hero"')
    checker = checker.replace("\nBalas HANYA JSON:", "\n\n" + world_menu(world) + "\nBalas HANYA JSON:", 1)
    return writer, checker


HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


# Worlds a scene of any other world may cut to for one shot (no sets, props or hero of their own).
INSETS = {k for k, v in WORLDS.items() if not v.get("latar") and not v.get("props")}


def _tidy_common(x):
    """Fields every 3D scene shares: a short label, a cue word that is really spoken, a known sfx and emotion."""
    if not x.get("label") or len(str(x["label"])) > 14:
        x.pop("label", None)
    spoken = [t.lower().strip(".,?!;:") for t in x["text"].split()]
    cue = str(x.get("cue") or "").lower().strip(".,?!;:")
    if cue and not any(t.startswith(cue) for t in spoken):
        x.pop("cue", None)
    if x.get("sfx") not in SFX:
        x.pop("sfx", None)
    if x.get("emosi") not in EMOSI:
        x["emosi"] = "tegang"
    for k in ("image", "camera", "visual"):
        x.pop(k, None)


def tidy_remotion(s):
    """A script for a 3D world, repaired to what the world really has: unknown shots, poses, props and hats are
    replaced or dropped so the render never meets a name it does not know."""
    w = WORLDS.get(s.get("world"))
    if not w:
        raise ValueError(f"unknown 3D world {s.get('world')!r}")
    scenes = [x for x in s.get("scenes", []) if str(x.get("text", "")).strip()]
    if len(scenes) < 4:
        raise ValueError(f"script has only {len(scenes)} scenes")
    names = list(w["shots"])
    prev, place = None, None
    for i, x in enumerate(scenes):
        inset = x.get("world") if isinstance(x.get("world"), str) else None
        if inset in INSETS and inset != s["world"] and WORLDS[inset].get("aktif"):  # an unapproved world never renders  # a cut to a shared world (inside the body) for one scene
            x["shot"] = x.get("shot") if x.get("shot") in WORLDS[inset]["shots"] else next(iter(WORLDS[inset]["shots"]))
            x["props"] = []
            for k in ("latar", "efek", "hero_pose", "hero_expr"):
                x.pop(k, None)
            prev = None
            _tidy_common(x)
            continue
        x.pop("world", None)
        if w.get("latar"):  # a world of sets: a missing or unknown latar continues the previous one
            own = x.get("latar") if isinstance(x.get("latar"), str) else None
            place = x["latar"] = own if own in w["latar"] else place or next(iter(w["latar"]))
            if x.get("efek") not in w.get("efek", []):
                x.pop("efek", None)
        if x.get("shot") not in w["shots"] or x["shot"] == prev:
            x["shot"] = next(n for n in names[i % len(names):] + names if n != prev)
        prev = x["shot"]
        for k, allowed in (("hero_pose", w["poses"]), ("hero_expr", w["exprs"])):
            if x.get(k) not in allowed:
                x.pop(k, None)
        anchors = w["latar"][place]["anchors"] if place else w["shots"][x["shot"]]["anchors"]
        if x["shot"] == "penjelasan" and place:  # the explainer stage shows the first real prop, wherever the script put it
            shown = [p for p in x.get("props") or [] if isinstance(p, dict) and p.get("jenis") in w["props"]][:1]
            x["props"] = [{"jenis": p["jenis"], "di": "panggung"} for p in shown]
        else:
            props = [p for p in x.get("props") or [] if isinstance(p, dict) and p.get("jenis") in w["props"] and p.get("di") in anchors]
            x["props"] = [{"jenis": p["jenis"], "di": p["di"]} for p in props][:3]
        _tidy_common(x)
    hero = s.get("hero") if isinstance(s.get("hero"), dict) else {}
    s["hero"] = {"topi": hero.get("topi") if hero.get("topi") in w["topi"] else "none"}
    if HEX.match(str(hero.get("seragam") or "")):
        s["hero"] = {"seragam": hero["seragam"], **s["hero"]}
    s["scenes"], s["style"] = scenes, "remotion3d"
    if s.get("seri") not in SERIES:
        s.pop("seri", None)
    s["hook_text"] = str(s.get("hook_text") or "").strip()[:34]
    s["title"] = str(s.get("title") or "")[:60]
    s["yt_title"] = str(s.get("yt_title") or "Gimana Jadinya " + s["title"])[:90]
    log(f"script: {len(scenes)} scenes, {sum(len(x['text'].split()) for x in scenes)} words, world {s['world']}, "
        f"shots {' '.join(x['shot'] for x in scenes)}")
    return s


def frame_check(video, scenes, fps=FPS):
    """One frame from the middle of each scene: a near-black or near-flat one means the camera saw nothing (ground,
    a wall, a world that did not load). Returns the problems and leaves contact.jpg beside the video."""
    import numpy as np
    problems, tmp = [], Path(video).parent / "contact-tmp"
    tmp.mkdir(exist_ok=True)
    for i, x in enumerate(scenes):
        t = (x["from"] + x["frames"] / 2) / fps
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                              "-vf", "scale=54:96,format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
        g = np.frombuffer(raw, np.uint8).astype(float)
        if g.size == 0 or g.mean() < 10:
            problems.append(f"adegan {i}: gelap")
        elif g.std() < 5:
            problems.append(f"adegan {i}: datar")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=216:384", str(tmp / f"f{i:02}.jpg")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(tmp / "f%02d.jpg"), "-vf",
                    f"tile={len(scenes)}x1", "-frames:v", "1", str(Path(video).parent / "contact.jpg")], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return problems


# Ending: semua slot "loop" menggantung (keputusan 2026-11-22; uji A/B dibatalkan). Varian "tuntas" tetap ada
# lewat --ending tuntas. Tiap video dicatat di data/ab_ending.jsonl.
ENDINGS = {
    "tuntas": ('Cerita WAJIB TUNTAS: adegan terakhir memberi penyelesaian yang jelas (apa yang akhirnya terjadi atau apa yang dilakukan profesional sungguhan, plus fakta paling mengejutkan), berupa kalimat LENGKAP. DILARANG menggantung, cliffhanger, atau diakhiri "..." / "dan saat itulah". Setelah tuntas, susun kalimat penutup supaya maknanya menyambung ke kalimat pertama (loop alami), contoh: pembuka "Air yang kamu semprot ke langit-langit tidak menetes balik" dan penutup "Ingat aturannya: selama air itu masih menetes balik, kamu masih aman." Penonton merasa puas, lalu pembuka langsung terasa sebagai bahaya berikutnya.',
               'cerita tuntas di adegan terakhir dengan kalimat lengkap (tanpa "...", tanpa cliffhanger; kalau menggantung, '
               'tulis ulang jadi penyelesaian yang maknanya menyambung ke kalimat pertama)'),
    "loop": ('WAJIB loop menggantung: semua fakta penting sudah tersampaikan sebelum adegan terakhir; kalimat terakhir '
             'sengaja menggantung dan menyambung mulus ke kalimat pertama (misalnya diakhiri "...dan saat itulah"), '
             'sehingga saat Shorts berputar ulang, kalimat pembuka terdengar sebagai lanjutannya dan penonton menonton '
             'ulang tanpa sadar.',
             'kalimat terakhir menggantung dan menyambung mulus ke kalimat pertama (loop); semua fakta penting sudah '
             'disampaikan sebelumnya'),
}
ENDING_BY_SLOT = {s: "loop" for s in MODE_BY_SLOT}


HOROR_WRITER = """

MODE HOROR (aturan ini MENGALAHKAN aturan di atas yang bertentangan): video ini CERITA HOROR FIKSI orisinal dari sudut pandang profesi. Latarnya harus realistis: prosedur, alat, istilah, aturan, dan jam kerja profesi itu NYATA dan benar (cek dengan pencarian web, selipkan 2-3 fakta nyata secara alami), tapi kejadian janggalnya fiksi. Nada serius dan mencekam dari awal sampai akhir: TANPA humor, tanpa candaan, tanpa referensi anime/game. Ketakutan dibangun dari detail kecil yang tidak masuk akal (rekaman CCTV, jam, panggilan radio/telepon, pintu yang terkunci, angka di layar, suara dari tempat yang seharusnya kosong), BUKAN dari darah atau kekerasan. Dilarang: gore, sadis, bunuh diri, setan/ritual agama tertentu, tragedi nyata, tempat atau perusahaan nyata yang bisa dirugikan; jangan pernah menyebutnya kisah nyata. Hook tetap aturan 3a (kejadian janggal yang sedang terjadi, ada taruhan nyata). Belokan di tengah membuat penonton sadar ada yang salah; twist di akhir membalik dugaan penonton lalu menggantung kembali ke kalimat pertama (misalnya jam di CCTV ternyata sama dengan jam di kalimat pembuka). "emosi" kebanyakan tegang, bisik, takut, kaget. "description" diawali "Cerita fiksi." Visual/gambar: gelap, sinematik, mencekam, tanpa darah."""

HOROR_CHECK = """

MODE HOROR: naskah ini FIKSI horor. JANGAN menghapus atau "mengoreksi" kejadian janggal/supernaturalnya dan jangan menambahkan "menurut perkiraan ilmuwan". Periksa hanya detail profesinya (prosedur, alat, istilah, angka) yang harus nyata. Pastikan: tanpa humor, tanpa gore atau kekerasan sadis, tidak menyebut agama/ritual tertentu, tidak diklaim kisah nyata, "description" diawali "Cerita fiksi.", twist di akhir menggantung kembali ke kalimat pertama. Pertahankan "seri"."""


def prompts(three, ending, mode="fakta"):
    rule, check = ENDINGS[ending]
    writer = (WRITER_3D if three else WRITER_SYS).replace("{ENDING_RULE}", rule)
    checker = (CHECK_3D if three else CHECK_SYS).replace("{ENDING_CHECK}", check)
    if mode == "horor":
        writer = writer.replace("\n\nBalas HANYA JSON:", HOROR_WRITER + "\n\nBalas HANYA JSON:", 1)
        checker = checker.replace("\nBalas HANYA JSON:", HOROR_CHECK + "\nBalas HANYA JSON:", 1)
    return writer, checker


def episode(seri):
    """The next episode number of a series, from the log of every Short made."""
    f = ROOT / "data" / "series.jsonl"
    seen = [json.loads(l) for l in f.read_text().splitlines() if l.strip()] if f.exists() else []
    return 1 + sum(1 for x in seen if x.get("seri") == seri)


def cliffhanger(s):
    """The story must end resolved; a trailing "..." or "dan saat itulah" leaves viewers feeling it was cut off."""
    last = (s.get("scenes") or [{}])[-1].get("text", "").strip()
    return bool(re.search(r"(\.\.\.|…|saat itulah)\W*$", last, re.I))


def tidy3d(s):
    scenes = [x for x in s.get("scenes", []) if str(x.get("text", "")).strip() and str(x.get("image", "")).strip()]
    if len(scenes) < 4:
        raise ValueError(f"script has only {len(scenes)} scenes with a picture")
    for i, x in enumerate(scenes):
        if x.get("camera") not in CAMERAS:
            x["camera"] = CAMERAS[i % 2]
        if not x.get("label") or len(str(x["label"])) > 14:
            x.pop("label", None)
        spoken = [w.lower().strip(".,?!;:") for w in x["text"].split()]
        cue = str(x.get("cue") or "").lower().strip(".,?!;:")
        if cue and not any(w.startswith(cue) for w in spoken):
            x.pop("cue", None)
        if x.get("sfx") not in SFX:
            x.pop("sfx", None)
        if x.get("emosi") not in EMOSI:
            x["emosi"] = "tegang"
        x.pop("visual", None)
    s["scenes"] = scenes
    s["style"] = "3d"
    if s.get("seri") not in SERIES:
        s.pop("seri", None)
    s["hook_text"] = str(s.get("hook_text") or "").strip()[:34]
    s["title"] = str(s.get("title") or "")[:60]
    s["yt_title"] = str(s.get("yt_title") or "Gimana Jadinya " + s["title"])[:90]
    n = sum(len(x["text"].split()) for x in scenes)
    log(f"script: {len(scenes)} scenes, {n} words, title {s['title']!r} (3d)")
    return s


IMAGE_STYLE_HOROR = ("Stylized 3D CGI render, not a photograph, vertical 9:16 composition with the subject centred and "
                     "room above and below. Dark cinematic horror lighting, deep shadows, cold blue and sickly green tones, "
                     "thin fog, one harsh light source, eerie and tense, high-end animated film style. No text, no letters, "
                     "no numbers, no logos, no watermark, no blood, no gore.")


def pictures(s, d, pub):
    """One 9:16 render per scene through Google Flow (classic composer, the plan's daily image allowance)."""
    sys.path.insert(0, str(ROOT / "pipeline"))
    import images
    images.ensure_display()
    pf = d / "gflow-project.txt"
    if not pf.exists():
        r = images.gflow("project", "create", "--name", f"gimana-{d.name}", "--json", timeout=300)
        out = json.loads(r.stdout[r.stdout.index("{"):]) if "{" in r.stdout else {}
        if "project_id" not in out:
            raise RuntimeError(f"gflow project create failed: {r.stdout[-300:]} {r.stderr[-300:]}")
        pf.write_text(out["project_id"])
    for attempt in range(3):
        todo = [i for i in range(len(s["scenes"])) if not (pub / f"img{i:02}.jpg").exists()]
        if not todo:
            break
        tmp = d / "tmp-img"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        style = IMAGE_STYLE_HOROR if s.get("mode") == "horor" else IMAGE_STYLE
        (tmp / "p.txt").write_text("\n".join(f"{s['scenes'][i]['image'].strip()} {style}".replace("\n", " ")
                                             for i in todo) + "\n")
        r = images.gflow("image", "t2i", "--prompts-file", tmp / "p.txt", "--aspect", "9:16", "--project",
                         pf.read_text().strip(), "--out", tmp, timeout=1800)
        (d / "gflow.log").open("a").write(r.stdout[-3000:] + r.stderr[-1500:] + "\n")
        for n, i in enumerate(todo):
            if (tmp / f"prompt_{n}_0.jpg").exists():
                shutil.move(tmp / f"prompt_{n}_0.jpg", pub / f"img{i:02}.jpg")
        log(f"pictures: {len(s['scenes']) - len([i for i in todo if not (pub / f'img{i:02}.jpg').exists()])}/{len(s['scenes'])}")
    missing = [i for i in range(len(s["scenes"])) if not (pub / f"img{i:02}.jpg").exists()]
    if missing:
        raise RuntimeError(f"Flow made no picture for scenes {missing}; see {d / 'gflow.log'}")
    for i, x in enumerate(s["scenes"]):
        x["image"] = f"img{i:02}.jpg"


def suggestions():
    out = []
    for q in ("kalau kamu jadi", "pov jadi", "sehari jadi", "pov kamu jadi pilot"):
        try:
            u = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
                {"client": "firefox", "ds": "yt", "hl": "id", "gl": "ID", "q": q})
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            out += json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace"))[1]
        except Exception as e:  # noqa: BLE001 - inspiration only
            log("suggest failed:", q, e)
    return out


def previous_titles():
    db = ROOT / "data" / "whatif.db"
    if not db.exists():
        return []
    with sqlite3.connect(db) as c:
        return [r[0] for r in c.execute("SELECT title FROM runs WHERE title IS NOT NULL AND slot IN "
                                        "('slot1','slot2','slot3','slot4','slot5','pagi','sore','malam') ORDER BY started_at DESC LIMIT 300")]


def tidy(s):
    """Holds the script to what the template can draw; anything unusable falls back rather than fails."""
    scenes = [x for x in s.get("scenes", []) if str(x.get("text", "")).strip()]
    if len(scenes) < 4:
        raise ValueError(f"script has only {len(scenes)} scenes")
    for i, x in enumerate(scenes):
        v = x.get("visual") if isinstance(x.get("visual"), dict) else {}
        if v.get("type") == "pov":
            if v.get("mood") not in MOODS:
                v["mood"] = "happy"
            v["props"] = [str(e) for e in v.get("props") or []][:4]
            if v.get("say") and len(str(v["say"])) > 34:
                v.pop("say")
        if v.get("type") not in TYPES or v["type"] == "outro":
            v = {"type": "icon", "emoji": v.get("emoji") or "🤔", "motion": "pop", "stamp": v.get("stamp")}
        for k in ("value", "max", "min"):
            if k in v:
                try:
                    v[k] = float(str(v[k]).replace(",", "."))
                except ValueError:
                    v.pop(k)
        for it in v.get("items", []) + v.get("steps", []):
            if "value" in it:
                try:
                    it["value"] = float(str(it["value"]).replace(",", "."))
                except ValueError:
                    it["value"] = 0
        if v.get("stamp") and len(v["stamp"]) > 22:
            v.pop("stamp")
        x["visual"] = v
        spoken = [w.lower().strip(".,?!;:") for w in x["text"].split()]
        cue = str(x.get("cue") or "").lower().strip(".,?!;:")
        if cue and not any(w.startswith(cue) for w in spoken):
            log(f"scene {i}: cue {cue!r} not in its text, dropped")
            x.pop("cue", None)
        if x.get("sfx") not in SFX:
            x.pop("sfx", None)
        if x.get("emosi") not in EMOSI:
            x["emosi"] = "tegang"
    h = s.get("hero") if isinstance(s.get("hero"), dict) else {}
    if not h.get("emoji"):
        raise ValueError("script has no hero emoji")
    h["body"] = "box" if h.get("body") == "box" else "emoji"
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(h.get("color") or "")):
        h["color"] = "#2f7de1"
    s["hero"] = h
    if s.get("theme") not in THEMES:
        s["theme"] = "kota"
    s["scenes"] = scenes
    if s.get("seri") not in SERIES:
        s.pop("seri", None)
    s["hook_text"] = str(s.get("hook_text") or "").strip()[:34]
    s["title"] = str(s.get("title") or "")[:60]
    s["yt_title"] = str(s.get("yt_title") or "Gimana Jadinya " + s["title"])[:90]
    n = sum(len(x["text"].split()) for x in scenes)
    if scenes[0]["text"].lower().startswith(("gimana jadinya", "bagaimana jika", "apa jadinya")):
        log("warning: first scene opens with the question instead of the action")
    log(f"script: {len(scenes)} scenes, {n} words, title {s['title']!r}")
    return s


async def synth(text, mp3, rate=RATE, pitch="+0Hz", volume="+0%", tries=5):
    # Microsoft's server now and then stalls on one request; a moment later it answers.
    for attempt in range(tries):
        words = []
        try:
            with open(mp3, "wb") as f:
                async for c in edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch, volume=volume,
                                                    boundary="WordBoundary").stream():
                    if c["type"] == "audio":
                        f.write(c["data"])
                    elif c["type"] == "WordBoundary":
                        words.append({"w": c["text"], "s": c["offset"] / 1e7, "e": (c["offset"] + c["duration"]) / 1e7})
            if words:
                return words
            raise RuntimeError("no word timings")
        except Exception as e:  # noqa: BLE001 - aiohttp and edge-tts raise several kinds for the same hiccup
            if attempt == tries - 1:
                raise
            log(f"edge-tts failed ({type(e).__name__}: {str(e)[:100]}), retrying")
            await asyncio.sleep(10 * (attempt + 1))


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(path)]).strip())


# The loop: the last word is cut 0.08 s after it ends and the first starts at frame 0, so YouTube's replay lands
# straight on the opening line instead of after a second of silence.
TAIL = 0.08
# A take longer than this is sped up (pitch kept) toward FIT_TO, by at most MAX_TEMPO: horror reads slowly.
MAX_LEN, FIT_TO, MAX_TEMPO = 46.0, 44.0, 1.35
GEMINI_STYLE = ("Read aloud in Indonesian as a gripping, fast-paced YouTube Shorts storyteller, very expressive and "
                "natural: the emotion follows the tag at the start of each line (never read the tags). Quick pace, "
                "short pauses between lines.")
GEMINI_HOROR = ("Read aloud in Indonesian as a late-night horror storyteller at the brisk pace of a YouTube Short: low, close and tense, "
                "dropping to a whisper on the frightening lines; the emotion follows the tag at the start of each line "
                "(never read the tags). Short pauses between lines.")
GEMINI_LOOP = (" The last line is unfinished: keep the voice suspended at the end, as if the sentence goes on.")


def props_from(s, scenes, frames):
    return {"title": s["title"], "hook": s.get("hook_text") or "", "hero": s.get("hero"), "theme": s.get("theme"),
            "style": s.get("style"), "fps": FPS, "frames": frames, "scenes": scenes,
            "series": f"{s['seri']} · EP. {s['episode']}" if s.get("seri") and s.get("episode") else "",
            "mode": s.get("mode") or "fakta",
            **({"world": s["world"], "hero3d": s.get("hero") or {}} if s.get("style") == "remotion3d" else {})}


def voice_gemini(s, d, pub):
    """The whole story in one Gemini take, each line tagged with its scene's emotion, timed by faster-whisper.
    One take a video keeps the free tier's 10 requests a day per model enough for three Shorts and their retries."""
    import numpy as np
    import tts
    if not tts.ENV.get("GEMINI_API_KEY"):
        raise RuntimeError("no GEMINI_API_KEY in .env")
    style = (GEMINI_HOROR if s.get("mode") == "horor" else GEMINI_STYLE) + (GEMINI_LOOP if s.get("ending") == "loop" else "") + ":\n"
    lines = "\n".join(f"{EMOSI.get(x.get('emosi'), EMOSI['tegang'])[0]} {x['text']}" for x in s["scenes"])
    tokens = [w for x in s["scenes"] for w in x["text"].split()]
    (d / "tts").mkdir(exist_ok=True)
    err = None
    for model, styled in tts.GEMINI_MODELS:
        tts.model, tts.styled = model, styled
        f = d / "tts" / f"{model}.wav"
        try:
            spoken = tts.take((style if styled else "") + lines, tokens, f)
            break
        except Exception as e:  # noqa: BLE001 - quota or a bad take: the next model, then edge-tts
            err = e
            log(f"{model} failed: {str(e)[:300]}")
    else:
        raise RuntimeError(f"no Gemini take: {err}")
    raw = tts.pcm(f)
    total = len(raw) / 2 / tts.SR
    timed = tts.align(tokens, spoken)
    # Trim the take to the voice: from where it rises out of silence to just after the last sound.
    a = tts.onset(raw)
    rev = np.frombuffer(raw, np.int16)[::-1].tobytes()
    b = min(total - max(tts.onset(rev) - 0.03, 0) + TAIL, total)
    shift = a - timed[0]["s"]  # whisper may start the first word late; anchor it on the real onset
    tempo = min((b - a) / FIT_TO, MAX_TEMPO) if b - a > MAX_LEN else 1.0
    words = [{"w": w["w"], "s": min(max(w["s"] + shift - a, 0), b - a) / tempo,
              "e": min(max(w["e"] + shift - a, 0), b - a) / tempo} for w in timed]
    if tempo > 1:
        log(f"voice: take {b - a:.1f} s, sped up {tempo:.2f}x")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(f), "-af",
                    (f"atempo={tempo:.3f}," if tempo > 1 else "") + "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-b:a", "192k", str(pub / "voice.mp3")], check=True)
    length = duration(pub / "voice.mp3")
    starts, at = [], 0
    for x in s["scenes"]:
        starts.append(0.0 if not at else max(words[at]["s"] - 0.1, 0))  # the picture changes just before the line
        at += len(x["text"].split())
    starts.append(length)
    scenes, at = [], 0
    for i, x in enumerate(s["scenes"]):
        n = len(x["text"].split())
        f0 = round(starts[i] * FPS)
        scenes.append({**x, "from": f0, "frames": max(round(starts[i + 1] * FPS) - f0, 1),
                       "words": [{"w": w["w"], "s": round(w["s"] * FPS) - f0, "e": round(w["e"] * FPS) - f0}
                                 for w in words[at:at + n]]})
        at += n
    props = {**props_from(s, scenes, round(length * FPS)), "narration": "voice.mp3"}
    save(d / "props.json", props)
    log(f"voice: gemini {tts.model} {tts.GEMINI_VOICE}, {length:.1f} s")
    return props


def voice_edge(s, d, pub):
    t, scenes = 0.0, []
    last = len(s["scenes"]) - 1
    for i, x in enumerate(s["scenes"]):
        mp3 = pub / f"vo{i:02}.mp3"
        _, rate, pitch, vol = EMOSI.get(x.get("emosi"), ("", RATE, "+0Hz", "+0%"))
        words = asyncio.run(synth(x["text"], mp3, rate, pitch, vol))
        # Word boundaries drop punctuation; put back the mark after each word so captions break on sentences.
        at = 0
        for w in words:
            k = x["text"].find(w["w"], at)
            if k >= 0:
                at = k + len(w["w"])
                m = re.match(r"[.,?!;:]+", x["text"][at:])
                if m:
                    w["w"] += m.group()
        # edge-tts pads silence at both ends: the scene runs from the first word to just after the last.
        lead = max(words[0]["s"] - (0 if i == 0 else 0.05), 0)
        end = min(words[-1]["e"] + (TAIL if i == last else 0.2), duration(mp3))
        length = end - lead + (0 if i == last else GAP)
        scenes.append({**x, "audio": mp3.name, "audioFrom": round(lead * FPS), "from": round(t * FPS),
                       "frames": round(length * FPS),
                       "words": [{"w": w["w"], "s": round((w["s"] - lead) * FPS), "e": round((w["e"] - lead) * FPS)}
                                 for w in words]})
        t += length
    props = props_from(s, scenes, round(t * FPS))
    save(d / "props.json", props)
    log(f"voice: edge-tts {VOICE}, {t:.1f} s")
    return props


def voice(s, d, pub):
    try:
        return voice_gemini(s, d, pub)
    except Exception as e:  # noqa: BLE001 - the video still gets a voice
        log(f"Gemini voice failed, edge-tts reads it: {str(e)[:300]}")
        return voice_edge(s, d, pub)


def render(d, pub, gl=None):
    """gl="swangle" for the real-time 3D worlds: the server has no GPU, so WebGL runs in software."""
    subprocess.run(["npx", "remotion", "render", "Short", str(d / "final.mp4"), f"--props={d / 'props.json'}",
                    f"--public-dir={pub}", "--concurrency=6", "--crf=20", "--log=error"] + ([f"--gl={gl}"] if gl else []),
                   cwd=HERE, check=True, timeout=1800)


def brief_for(idea=None, topic=None):
    """What the writer gets: the research idea (or a forced topic) and the titles already made."""
    made = previous_titles()
    if idea:
        return {"topik_wajib": f"kamu jadi {idea['topic']}", "ide_dari_riset": {k: idea.get(k) for k in (
            "angle", "hook", "facts", "inspired_by", "seri")}, "judul_yang_sudah_pernah_dibuat": made}
    if topic:
        return {"topik_wajib": f"kamu jadi {topic}", "judul_yang_sudah_pernah_dibuat": made}
    return {"judul_yang_sudah_pernah_dibuat": made, "saran_pencarian_youtube": suggestions()}


def opus(system, user):
    return claude_json("opus", system, user, web=True)


def write_draft(brief, three, ending, mode, ask=opus, world=None):
    """One full draft script; ask(system, user) -> dict is the writer (Opus here, the Peran AI writer in the 19:00
    research). With a world, the script is told in that real-time 3D world's shots. Fails early when even the checker
    could not save it."""
    writer, _ = prompts_remotion(world, ending, mode) if world else prompts(three, ending, mode)
    draft = ask(writer, json.dumps(brief, ensure_ascii=False))
    if world:
        draft["world"] = world
    fixer(three, world)(json.loads(json.dumps(draft)))
    return draft


def fixer(three, world):
    return tidy_remotion if world else tidy3d if three else tidy


def check_draft(draft, three, ending, mode, ask=opus, world=None):
    """The checker (Opus, or the Peran AI checker) fact-checks and fixes a draft; a "tuntas" ending that still dangles
    gets one more pass."""
    _, checker = prompts_remotion(world, ending, mode) if world else prompts(three, ending, mode)
    fix = fixer(three, world)
    checked = ask(checker, json.dumps(draft, ensure_ascii=False))
    for issue in checked.get("issues", []):
        log("fixed:", issue)
    s = checked.get("script") or draft
    if world:
        s["world"] = world  # the checker may not move the story to another world
    s = fix(s)
    if ending == "tuntas" and cliffhanger(s):  # one more pass with the ending as the only job
        log("ending is a cliffhanger, asking the checker to resolve it:", s["scenes"][-1]["text"])
        again = ask(checker, json.dumps(
            {**s, "catatan_editor": "Adegan terakhir menggantung. Tulis ulang HANYA adegan terakhir jadi penyelesaian "
             "tuntas berupa kalimat lengkap yang maknanya menyambung ke kalimat pertama."}, ensure_ascii=False))
        s = fix(again.get("script") or s)
        if cliffhanger(s):
            raise RuntimeError(f"ending still a cliffhanger: {s['scenes'][-1]['text']!r}")
    return s


def main(rid, script_file=None, topic=None, idea=None, style=None, ending=None, mode=None, world=None):
    d = RUNS / rid
    slot = (idea or {}).get("slot") or next((x for x in rid.split("-") if x in ENDING_BY_SLOT), "")
    ending = ending if ending in ENDINGS else ENDING_BY_SLOT.get(slot, "tuntas")
    mode = mode if mode in ("fakta", "horor") else (idea or {}).get("mode") or MODE_BY_SLOT.get(slot, "fakta")
    d.mkdir(parents=True, exist_ok=True)
    real3d = style == "remotion3d"
    world = (world or (idea or {}).get("world")) if real3d else None
    if real3d and world not in WORLDS:
        raise ValueError(f"--style remotion3d needs a known --world, got {world!r}")
    three = style == "3d" or real3d
    if script_file:  # naskah jadi dari riset 19:00 (ditulis Sonnet, dijuri & dicek Opus)
        raw = load(script_file)
        if real3d:
            s = tidy_remotion({**raw, "world": raw.get("world") or world})
        else:
            s = tidy3d(raw) if three or raw.get("style") == "3d" else tidy(raw)
    else:
        print("STAGE naskah", flush=True)
        brief = brief_for(idea, topic)
        if idea:
            log(f"idea: kamu jadi {idea['topic']} | {idea.get('hook', '')}")
        log(f"ending: {ending}, mode: {mode}" + (f", world: {world}" if world else ""))
        draft = write_draft(brief, three, ending, mode, world=world)
        save(d / "script.draft.json", draft)
        print("STAGE cek", flush=True)
        s = check_draft(draft, three, ending, mode, world=world)
    s["ending"], s["mode"] = ending, mode
    if s.get("seri"):
        s["episode"] = episode(s["seri"])
        log(f"seri: {s['seri']} ep. {s['episode']}")
    with open(ROOT / "data" / "ab_ending.jsonl", "a") as fh:
        fh.write(json.dumps({"run": rid, "ending": ending, "title": s.get("yt_title")}, ensure_ascii=False) + "\n")
    save(d / "script.json", s)
    print("STAGE suara", flush=True)
    pub = d / "public"
    pub.mkdir(exist_ok=True)
    shutil.copy(HERE / "public" / "Anton-Regular.ttf", pub)
    shutil.copy(HERE / "public" / "Montserrat.ttf", pub)
    if s.get("style") == "3d":
        print("STAGE gambar", flush=True)
        pictures(s, d, pub)
        save(d / "script.json", s)
    shutil.copytree(HERE / "public" / "sfx", pub / "sfx", dirs_exist_ok=True)
    voice(s, d, pub)
    print("STAGE render", flush=True)
    t0 = time.time()
    render(d, pub, "swangle" if real3d else None)
    shutil.rmtree(pub / "sfx", ignore_errors=True)
    if real3d:
        log(f"render: {time.time() - t0:.0f} s")
        bad = frame_check(d / "final.mp4", load(d / "props.json")["scenes"])
        if bad:
            raise RuntimeError("3D render looks empty: " + "; ".join(bad))
    if s.get("seri") and s.get("episode") and slot:  # counted once the episode exists; test runs are not
        with open(ROOT / "data" / "series.jsonl", "a") as fh:
            fh.write(json.dumps({"run": rid, "seri": s["seri"], "episode": s["episode"], "mode": s.get("mode"),
                                 "title": s.get("yt_title")}, ensure_ascii=False) + "\n")
    log("done:", d / "final.mp4", f"{duration(d / 'final.mp4'):.1f} s")


if __name__ == "__main__":
    a = sys.argv[1:]
    idea = None
    if "--idea" in a:
        k = a.index("--idea")
        idea = next((i for i in load(a[k + 1])["ideas"] if i.get("slot") == a[k + 2]), None)
    main(a[0], a[a.index("--script") + 1] if "--script" in a else None,
         a[a.index("--topic") + 1] if "--topic" in a else None, idea, a[a.index("--style") + 1] if "--style" in a else None,
         a[a.index("--ending") + 1] if "--ending" in a else None, a[a.index("--mode") + 1] if "--mode" in a else None,
         a[a.index("--world") + 1] if "--world" in a else None)
