# Remotion 3D Fase 1 (fondasi + dunia kereta) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slot yang idenya bertopik kereta diproduksi otomatis sebagai video 3D real-time Remotion (seperti `runs/sample-kereta-3d`), dengan fallback ke Flow 3D lalu kartun.

**Architecture:** `shorts/src/train3d.tsx` dipecah menjadi kit bersama (`kit3d/`) dan dunia pertama (`worlds/kereta.tsx`) di belakang satu registry. `shorts/worlds.json` adalah katalog yang dibaca penulis naskah, riset ide dan validasi Python. `produce.py --style remotion3d` menulis naskah per shot, membuat suara seperti sekarang, merender dengan `--gl=swangle`, lalu menolak render yang framenya gelap atau datar. server.py mencoba remotion3d dulu untuk ide yang punya `world`.

**Tech Stack:** Remotion 4.0.543, @remotion/three 4.0.543, @react-three/fiber 9.8.2, three 0.183.0 (sudah terpasang), Python 3.12 di `.venv`, ffmpeg, numpy.

**Spec:** `docs/superpowers/specs/2026-11-27-remotion-3d-worlds-design.md`

Fase berikutnya (dunia tubuh, rumah, jalan, industri) masing-masing mendapat rencana sendiri. Fase-fase itu hanya menambah `worlds/<nama>.tsx`, entri katalog, dan benda baru.

## Global Constraints

- Render 3D selalu dengan `--gl=swangle`. Server tanpa GPU.
- Frame deterministik: tanpa `Math.random`, `Date`, atau state antar-frame. Acak memakai `rand(i)` dari kit.
- Satu satuan: meter. Rel sepanjang +X, perlintasan di x = 0 (dari sampel).
- AI tidak pernah memberi koordinat. Tokoh dan benda hanya ditaruh di anchor bernama milik shot.
- Produksi 3D harus selesai jauh di bawah `timeout=2700` server.py. Render memakai `--concurrency=6`.
- Aset luar hanya CC0 dan disimpan di repo. Fase 1 tidak memakai aset luar.
- Slot horor (`mode == "horor"`) memakai pencahayaan malam di semua shot.
- Tes Python berupa skrip assert biasa: `.venv/bin/python shorts/test_remotion3d.py` (pytest tidak terpasang). Setiap fungsi `test_*` dipanggil dari `__main__`.
- Komentar kode dan pesan log mengikuti gaya file yang disentuh (Inggris di kode, Indonesia di prompt).

## Review Focus

1. Naskah dari AI menyebut shot, anchor, pose atau benda yang tidak ada. Yang diharapkan: diganti default aman, video tetap jadi (tes di Task 5).
2. Ide berbasis dunia yang render 3D-nya gagal, padahal naskah 19:00 tidak punya prompt gambar. Yang diharapkan: fallback Flow menulis naskahnya sendiri, `--script` tidak diteruskan (tes di Task 7).
3. Shot yang lebih pendek atau lebih panjang dari 4–5 detik. Yang diharapkan: kereta tetap di frame dan gerak tidak meloncat (still di awal/akhir shot pada Task 4).
4. Slot horor di dunia kereta. Yang diharapkan: semua shot gelap/malam dan lampu tetap terlihat, tapi tidak lolos sebagai "frame gelap" palsu (tes ambang di Task 5 memakai still malam asli).
5. `worlds.json` dan shot di TS tidak sinkron setelah ada yang diedit. Yang diharapkan: tes gagal dengan nama shot yang hilang (Task 4).

---

### Task 1: Pecah sampel jadi kit + registry dunia, tanpa mengubah tampilan

**Files:**
- Create: `shorts/src/kit3d/core.tsx` (Box, Mat, Many, Rig, Sparks, Meter, Vignette, `rand`, tipe `V3`, `Look`, `brake`)
- Create: `shorts/src/worlds/kereta.tsx` (Track, Barrier, Car, Crossing, Coach, Train, Dash, `shots`)
- Create: `shorts/src/worlds/index.tsx` (registry + `WorldShot`)
- Modify: `shorts/src/Short.tsx` (Scene/ShortProps, Short3D)
- Delete: `shorts/src/train3d.tsx`

**Interfaces:**
- Produces:
  - `type Look = {front?: number; braking?: number; cam: V3; at: V3; fov?: number; night?: boolean; shake?: number; [k: string]: unknown}`. `cam`/`at`/`fov`/`night`/`shake` dipakai `Rig`, sisanya milik dunia.
  - `type World = {shots: Record<string, (t: number, T: number) => Look>; View: React.FC<WorldViewProps>; overlay?: Record<string, React.FC<{frames: number}>>}`
  - `type WorldViewProps = {look: Look; frame: number; shot: string; night: boolean; hero?: Hero3D; heroPose?: string; heroExpr?: string; props?: PropSpec[]}` (hero/props baru diisi di Task 2–3)
  - `WORLDS: Record<string, World>` dengan kunci `kereta`
  - `WorldShot: React.FC<{world: string; shot: string; frames: number; lead: number; night: boolean; scene: Scene; hero?: Hero3D}>`. Shot yang tidak dikenal memakai shot pertama dunia itu.
  - `Scene` mendapat `shot?`, `hero_pose?`, `hero_expr?`, `props?: PropSpec[]`. `ShortProps` mendapat `world?: string`, `hero3d?: Hero3D`.
  - Short3D: kalau `props.world` ada, setiap adegan memakai `WorldShot` (night = `mode === 'horor'`). Kalau tidak ada, tetap `ImageScene`.

- [ ] **Step 1:** Pindahkan kode sesuai daftar file. Perilaku setiap shot harus identik dengan `train3d.tsx` saat ini. `Meter` menjadi `overlay.distance` milik dunia kereta.
- [ ] **Step 2:** Tambahkan `"world": "kereta"` ke `runs/sample-kereta-3d/props.json` (kolom `shot` per adegan sudah ada).
- [ ] **Step 3:** Typecheck: `cd shorts && npx tsc --noEmit -p .` → tanpa output.
- [ ] **Step 4:** Render still di tengah tiap adegan sampel (`npx remotion still Short <out> --frame=<f> --props=../runs/sample-kereta-3d/props.json --public-dir=../runs/sample-kereta-3d/public --gl=swangle --scale=0.5`), lalu bandingkan dengan `runs/sample-kereta-3d/f_*.png` dari `final.mp4`. Expected: komposisi sama.
- [ ] **Step 5:** Pastikan video Flow lama tetap jalan: render satu still dari `runs/test-horor-01/props.json` (tanpa `world`). Expected: gambar Flow tampil seperti biasa.
- [ ] **Step 6:** Commit `shorts/src shorts/package.json shorts/package-lock.json` dengan pesan "Split the 3D train sample into a shared kit and a kereta world".

### Task 2: Tokoh orang low-poly

**Files:**
- Create: `shorts/src/kit3d/person.tsx`
- Modify: `shorts/src/Root.tsx` (Still `PersonSheet` 1080x1920 untuk pratinjau)

**Interfaces:**
- Produces:
  - `type Hero3D = {seragam?: string; celana?: string; kulit?: string; topi?: 'none' | 'masinis' | 'helm' | 'pet' | 'perawat'; rambut?: string}`. Default: seragam `#1d2b4a`, kulit `#c68a5e`, rambut `#1a1a1a`, topi `none`.
  - `POSES = ['berdiri','duduk','lari','menunjuk','panik','memegang','menoleh'] as const`
  - `EXPRS = ['biasa','kaget','takut','lega','fokus'] as const`
  - `Person: React.FC<{hero?: Hero3D; pose?: string; expr?: string; frame: number; position?: V3; rotationY?: number; scale?: number}>`. Tinggi 1.7 m. Pose atau ekspresi yang tidak dikenal memakai `berdiri`/`biasa`. Ada gerak idle kecil (napas, kedip setiap ±90 frame) dari `frame`.
- Wajah: mata, alis dan mulut berupa mesh datar di depan kepala. Ekspresi mengubah bentuk dan sudutnya. Proporsi bergaya (kepala besar, sekitar 3.5 kepala tinggi) agar wajah terbaca di layar ponsel.

- [ ] **Step 1:** Buat `PersonSheet`: grid 7 pose × (ekspresi bergilir), plus satu baris close-up wajah kelima ekspresi, dengan semua varian topi.
- [ ] **Step 2:** `npx tsc --noEmit -p .` → tanpa output.
- [ ] **Step 3:** `npx remotion still PersonSheet /tmp/.../person.png --gl=swangle --scale=0.5`, lalu periksa gambarnya: setiap pose bisa dibedakan, setiap ekspresi terbaca, tidak ada anggota tubuh yang lepas atau tembus.
- [ ] **Step 4:** Commit "Add a low-poly person with poses and drawn expressions".

### Task 3: Benda generik + anchor

**Files:**
- Create: `shorts/src/kit3d/props.tsx`
- Modify: `shorts/src/kit3d/core.tsx` (tipe `Anchor`), `shorts/src/Root.tsx` (Still `PropSheet`)

**Interfaces:**
- Produces:
  - `type PropSpec = {jenis: string; di: string}`
  - `type Anchor = {p: V3; ry?: number; s?: number}`. Tiap dunia menyediakan `anchors(shot: string, look: Look): Record<string, Anchor>`, ditambahkan ke `World` sebagai `anchors`.
  - `PROPS: Record<string, React.FC<{frame: number}>>` dengan 15 benda awal: `mobil`, `motor`, `truk`, `orang` (pejalan, memakai `Person`), `kotak`, `tabung_gas`, `pohon`, `rumah`, `lampu_peringatan`, `tiang`, `panel_layar`, `kerucut_lalu_lintas`, `sapi`, `gerobak`, `koper`. Benda lain menyusul di rencana dunia berikutnya (penyimpangan sadar dari "sekitar 30" di spec: tidak membuat benda yang belum dipakai dunia mana pun).
  - `PlacedProps: React.FC<{props?: PropSpec[]; anchors: Record<string, Anchor>; frame: number}>`. Benda dengan `jenis` atau `di` yang tidak dikenal dilewati. Satu anchor hanya diisi satu benda. Maksimal 3 benda per adegan.

- [ ] **Step 1:** Buat `PropSheet` yang menampilkan ke-15 benda berjajar di samping `Person` sebagai pembanding skala.
- [ ] **Step 2:** `npx tsc --noEmit -p .` → tanpa output. Render `PropSheet` dengan swangle, lalu periksa: skala masuk akal terhadap orang 1.7 m dan setiap benda bisa dikenali.
- [ ] **Step 3:** Commit "Add generic low-poly props placed on named anchors".

### Task 4: Dunia kereta lengkap + katalog

**Files:**
- Modify: `shorts/src/worlds/kereta.tsx`
- Create: `shorts/worlds.json`
- Create: `shorts/test_remotion3d.py`

**Interfaces:**
- Consumes: `Person`, `Hero3D`, `PlacedProps`, `Anchor` (Task 2–3).
- Produces:
  - `shots` kereta = 8 shot sampel (`cab, top, distance, wheel, crossing, stop, cabin, night`) + `masinis` (close-up tokoh di kursi kabin, wajah dan tangan di tuas, jendela menampilkan rel yang bergerak), `peron` (stasiun: peron, atap, kereta masuk atau berhenti, tokoh dan orang di peron), `gerbong` (interior KRL: kursi panjang, pegangan, penumpang berdiri, jendela dengan pemandangan bergerak).
  - Tokoh (`hero`) tampil di `masinis`, `cabin` (kaki dan tangan memakai warna seragamnya), `peron`. Di shot lain tokoh tidak tampil.
  - Anchor: `crossing`/`stop`/`cab`/`top` → `rel` (di perlintasan, menggantikan mobil bawaan bila diisi), `jalan_kiri`, `jalan_kanan`; `peron` → `peron_kiri`, `peron_kanan`; `gerbong` → `lantai`, `kursi`. Shot lain tanpa anchor.
  - Malam: `night` dari props memaksa langit/kabut malam dan lampu kereta menyala di semua shot.
  - `shorts/worlds.json`:
    ```json
    {"kereta": {"cocok": "masinis, penjaga palang pintu, petugas stasiun/KRL, teknisi rel, kondektur, kereta barang/cepat",
                "shots": {"cab": {"arti": "...", "anchors": ["rel", "jalan_kiri", "jalan_kanan"], "tokoh": false}, ...},
                "props": ["mobil", "motor", ...], "poses": [...], "exprs": [...], "topi": [...]}}
    ```
    `arti` adalah satu kalimat bahasa Indonesia tentang apa yang terlihat. Kalimat inilah yang dibaca penulis naskah.

- [ ] **Step 1: Tulis tes katalog yang gagal** di `shorts/test_remotion3d.py`:
  ```python
  def test_catalog_matches_ts():
      cat = json.loads((HERE / "worlds.json").read_text())
      for name, w in cat.items():
          src = (HERE / "src" / "worlds" / f"{name}.tsx").read_text()
          ts = set(re.findall(r"^\s{2}(\w+): \(t", src.split("export const shots", 1)[1], re.M))
          assert set(w["shots"]) == ts, (name, set(w["shots"]) ^ ts)
          for s in w["shots"].values():
              assert s["arti"] and isinstance(s["anchors"], list)
      props_src = (HERE / "src" / "kit3d" / "props.tsx").read_text()
      for p in cat["kereta"]["props"]:
          assert re.search(rf"^\s{{2}}{p}:", props_src, re.M), p
  ```
  (Bentuk `shots` di TS dibuat agar cocok dengan regex ini: objek literal, satu shot per baris `  nama: (t, T) => ...`.)
- [ ] **Step 2:** `.venv/bin/python shorts/test_remotion3d.py` → FAIL (worlds.json belum ada).
- [ ] **Step 3:** Bangun shot baru, tokoh, anchor dan malam. Isi `worlds.json`.
- [ ] **Step 4:** Tes → PASS.
- [ ] **Step 5:** Buat `props.json` uji dengan 11 adegan (satu per shot, masing-masing 120 dan 180 frame), `world: kereta`, tokoh bertopi masinis, dan benda di setiap anchor. Render still di frame 5 dan frame terakhir tiap adegan, siang dan `mode: horor`. Periksa: subjek di frame, wajah tokoh terbaca, benda di tempatnya, malam tidak hitam total.
- [ ] **Step 6:** Commit "Kereta world: driver close-up, platform, carriage interior, hero, anchors, night; catalog".

### Task 5: produce.py: naskah, validasi, render, cek frame

**Files:**
- Modify: `shorts/produce.py`
- Modify: `shorts/test_remotion3d.py`

**Interfaces:**
- Consumes: `shorts/worlds.json`.
- Produces:
  - `WORLDS = load(HERE / "worlds.json")`
  - `prompts_remotion(world: str, ending: str, mode: str) -> tuple[str, str]`: writer dan checker. Turunan dari WRITER_3D/CHECK_3D. Aturan `image`/`camera`/`hero_look` diganti dengan daftar shot dunia itu (nama + `arti` + anchor + boleh tokoh), daftar benda, pose, ekspresi, topi; `hero` {seragam hex, topi}; aturan: shot yang sama tidak boleh dua kali berturut-turut, minimal 5 shot berbeda per video, benda hanya di anchor shot-nya (maksimal 3). Format JSON balasan: `{"world": ..., "hero": {...}, "scenes": [{"text","shot","hero_pose","hero_expr","props":[{"jenis","di"}],"label","cue","sfx","emosi"}], ...}` ditambah kolom lain yang sama dengan WRITER_3D.
  - `tidy_remotion(s: dict) -> dict`: `style = "remotion3d"`. `world` yang tidak ada di WORLDS → ValueError. Shot tak dikenal diganti shot katalog yang tidak sama dengan adegan sebelumnya. Pose/ekspresi tak dikenal dihapus. Benda dengan jenis atau anchor yang tidak valid untuk shot itu dibuang, dan maksimal 3 disisakan. `hero.topi` tak dikenal → `none`. Seragam yang bukan hex → dihapus. Sisanya (label, cue, sfx, emosi, seri, hook_text, title, yt_title, minimal 4 adegan) sama dengan `tidy3d`.
  - `write_draft(..., world=None)` dan `check_draft(..., world=None)`: kalau `world` ada, memakai `prompts_remotion` dan `tidy_remotion`.
  - `props_from` meneruskan `world` dan `hero3d` (= `s["hero"]` bila style remotion3d).
  - `render(d, pub, gl=None)`: menambah `--gl=swangle` untuk remotion3d.
  - `frame_check(video: Path, scenes: list, fps=30) -> list[str]`: ambil satu frame di tengah tiap adegan lewat ffmpeg (gray, 54x96, rawvideo ke numpy). Kembalikan masalah `"adegan {i}: gelap"` bila mean < 10, atau `"adegan {i}: datar"` bila std < 5. Simpan lembar kontak `contact.jpg` di run (ffmpeg `tile`).
  - `main(..., world=None)`: `style == "remotion3d"` mewajibkan world (dari argumen `--world` atau `idea["world"]`), melewati `pictures()`, render dengan swangle, lalu `frame_check`. Bila ada masalah → `RuntimeError` agar server.py fallback.
  - CLI: `--world <nama>`.

- [ ] **Step 1: Tulis tes yang gagal:**
  ```python
  def test_tidy_remotion_repairs():
      s = {"world": "kereta", "title": "Kalau Kamu Jadi Masinis?", "hero": {"seragam": "biru", "topi": "koki"},
           "scenes": [{"text": "Satu dua tiga.", "shot": "cab", "props": [{"jenis": "mobil", "di": "rel"}, {"jenis": "ufo", "di": "rel"}]},
                      {"text": "Empat lima.", "shot": "cab"},
                      {"text": "Enam tujuh.", "shot": "terbang", "hero_pose": "salto"},
                      {"text": "Delapan.", "shot": "peron", "props": [{"jenis": "koper", "di": "rel"}]}]}
      t = produce.tidy_remotion(s)
      sh = [x["shot"] for x in t["scenes"]]
      assert t["style"] == "remotion3d" and sh[0] == "cab" and sh[1] != "cab" and sh[2] in produce.WORLDS["kereta"]["shots"]
      assert t["scenes"][0]["props"] == [{"jenis": "mobil", "di": "rel"}]
      assert "hero_pose" not in t["scenes"][2] and t["scenes"][3].get("props", []) == []
      assert t["hero"].get("topi") == "none" and "seragam" not in t["hero"]

  def test_tidy_remotion_unknown_world():
      try: produce.tidy_remotion({"world": "bulan", "scenes": []}); assert False
      except ValueError: pass

  def test_frame_check():
      # a real day still and a real horror-night still pass; a black clip and a flat clip fail
      ...build 3 one-second clips with ffmpeg: from the Task 4 day and night stills, color=black, color=0x6d8f3f
      assert produce.frame_check(day, [{"from": 0, "frames": 30}]) == []
      assert produce.frame_check(night, [{"from": 0, "frames": 30}]) == []
      assert produce.frame_check(black, [{"from": 0, "frames": 30}]) == ["adegan 0: gelap"]
      assert produce.frame_check(flat, [{"from": 0, "frames": 30}]) == ["adegan 0: datar"]
  ```
- [ ] **Step 2:** `.venv/bin/python shorts/test_remotion3d.py` → FAIL (`tidy_remotion` tidak ada).
- [ ] **Step 3:** Implementasikan semua yang ada di Interfaces.
- [ ] **Step 4:** Tes → PASS. Kalau ambang terlalu ketat untuk still malam, sesuaikan ambangnya, bukan stillnya.
- [ ] **Step 5:** Uji ujung ke ujung tanpa server: `cd shorts && ../.venv/bin/python produce.py test-remotion-kereta --topic "penjaga palang pintu kereta" --style remotion3d --world kereta`. Expected: log `done: ... final.mp4`, ada `contact.jpg`, durasi total produksi tercatat (target < 25 menit). Lihat `contact.jpg`.
- [ ] **Step 6:** Commit "produce.py: remotion3d style with per-shot scripts, repair, swangle render and a frame check".

### Task 6: Riset ide 19:00 memilih dunia

**Files:**
- Modify: `shorts/ideas.py`
- Modify: `shorts/test_remotion3d.py`

**Interfaces:**
- Consumes: `produce.WORLDS`, `write_draft(..., world=)`, `check_draft(..., world=)`.
- Produces:
  - SYS mendapat blok `DUNIA 3D YANG TERSEDIA` (nama + `cocok` dari katalog). Setiap ide wajib punya `"world"`: nama dunia, atau `"flow"` kalau tidak ada yang cocok. Utamakan dunia yang tersedia. Selama data kereta paling kuat, kereta mendapat porsi besar, tanpa kuota pasti (keputusan user: tidak ada jumlah khusus).
  - `world_of(idea: dict) -> str | None`: nama dunia valid, atau None untuk `flow`/kosong/tidak dikenal.
  - Draf memakai `write_draft(..., world=world_of(i))`. `pick` memanggil `check_draft(..., world=world_of(x["idea"]))`. Ide dan naskah yang disimpan tetap membawa `world`.

- [ ] **Step 1: Tes gagal:** `assert ideas.world_of({"world": "kereta"}) == "kereta"`, `world_of({"world": "flow"}) is None`, `world_of({"world": "bulan"}) is None`, `world_of({}) is None`.
- [ ] **Step 2:** Jalankan → FAIL.
- [ ] **Step 3:** Implementasikan.
- [ ] **Step 4:** Jalankan → PASS. Lalu `python -c "import ideas; print(ideas.SYS)"` dari `shorts/` dan pastikan blok dunia muncul dengan teks dari katalog.
- [ ] **Step 5:** Commit "19:00 research picks a 3D world for each idea".

### Task 7: server.py: urutan fallback

**Files:**
- Modify: `pipeline/server.py:33,98-120`
- Modify: `shorts/test_remotion3d.py`

**Interfaces:**
- Produces:
  - `STYLE_REMOTION_FROM = "2099-01-01"` (diubah ke tanggal nyata di Task 8 setelah user menyetujui sampel).
  - `attempts(idea: dict | None, today: str, research_script: Path | None) -> list[list]`: daftar argumen tambahan untuk produce.py, dicoba berurutan. Bila `today >= STYLE_REMOTION_FROM` dan `world_of(idea)` valid: `["--style","remotion3d","--world",w] + (["--script", research_script] bila naskahnya bergaya remotion3d)`. Lalu Flow 3D: `["--style","3d"]` + `--script` hanya bila naskah risetnya bukan remotion3d. Lalu kartun `[]`. Tanpa world, perilakunya sama seperti sekarang.
  - Loop produksi menjalankan `cmd + a` untuk tiap `a` sampai ada yang berhasil, dengan log "… failed; falling back to …" di run.log. Timeout: remotion3d dan 3d 2700 detik, kartun 3600 detik.

- [ ] **Step 1: Tes gagal:** dengan `STYLE_REMOTION_FROM` di-patch ke `"2000-01-01"`:
  - ide `{"world":"kereta"}` + naskah remotion3d → 3 percobaan. Yang pertama memuat `--style remotion3d --world kereta --script`, yang kedua `["--style","3d"]` tanpa `--script`, yang ketiga `[]`.
  - ide tanpa world + naskah 3d → `[["--style","3d","--script",p], []]`.
  - tanggal sebelum `STYLE_REMOTION_FROM` + ide kereta → percobaan pertama `--style 3d`.
- [ ] **Step 2:** Jalankan → FAIL.
- [ ] **Step 3:** Implementasikan `attempts` dan loop-nya, dengan penanganan error dan `update(...)` yang sama seperti sekarang.
- [ ] **Step 4:** Tes → PASS. `systemctl --user restart whatif.service`, lalu `journalctl --user -u whatif.service -n 20` → tanpa traceback.
- [ ] **Step 5:** Commit "Server tries the Remotion 3D world first, then Flow 3D, then cartoon".

### Task 8: Sampel untuk user, lalu aktifkan

- [ ] **Step 1:** Kirim path `runs/test-remotion-kereta/final.mp4` (dari Task 5) dan `contact.jpg` ke user. Tunggu penilaiannya.
- [ ] **Step 2:** Setelah disetujui: set `STYLE_REMOTION_FROM` ke tanggal produksi berikutnya, restart `whatif.service`, commit "Remotion 3D on from <tanggal>".
- [ ] **Step 3:** Hari berikutnya: cek `data/ideas/<tanggal>.json` (ada ide dengan `world: kereta`) dan run.log slot terkait (render remotion3d berhasil atau fallback tercatat).
- [ ] **Step 4:** Perbarui memori `channel-strategy` dengan status baru.
