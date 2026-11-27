# Gimana Jadinya? — Shorts dibuat sebagai 3D real-time di Remotion

Tanggal: 2026-11-27 · Status: draf, menunggu persetujuan

## Maksud dan alasan

Sampel `runs/sample-kereta-3d` (masinis KRL, mobil mogok di perlintasan) dibuat penuh dengan three.js di dalam
Remotion: setiap frame adalah kamera yang bergerak di dunia 3D, bukan gambar Flow yang di-zoom. User menontonnya,
menilai "bagus banget", lalu minta semua konten What If dibuat dengan cara ini. Alasannya: konten kereta paling
banyak ditonton (5.1K dan 4.1K views, sementara video lain 1–1.8K), dan user ingin video terasa seperti animasi
sungguhan, bukan slide.

## Tujuan

- Semua topik akhirnya dirender sebagai 3D Remotion dengan kualitas setara sampel kereta.
- Peralihan bertahap: jadwal 5 Shorts per hari (10/12/15/18/20 WIB) tidak pernah berhenti selama dunia-dunia baru dibangun.
- Penulis naskah dan riset ide 19:00 tetap otomatis dan memilih dunia serta sudut kamera sendiri.

## Bukan tujuan (untuk sekarang)

- Topik bebas yang disusun AI dari nol tanpa dunia (opsi B murni). Benda generik hanya ditaruh di dalam dunia yang sudah ada.
- Model karakter realistis, rig wajah lengkap, atau lip-sync.
- Render GPU atau layanan render di cloud.
- Juri gambar berbasis AI (vision) untuk tiap render.

## Yang membuatnya gagal walau secara teknis jalan

- Adegan berantakan atau tidak terbaca: benda bertumpuk, ukuran tidak masuk akal, kamera menatap tanah kosong.
- Video terasa seperti slide lagi (kamera diam, tidak ada gerak).
- Slot gagal upload karena render 3D error tanpa fallback.
- Semua video terlihat sama karena hanya memakai segelintir sudut kamera.

## Batasan

- Server tanpa GPU (8 core, 15 GB). Render lewat Chromium `--gl=swangle`. Sampel 32 detik selesai dalam sekitar 12 menit dengan concurrency 6.
  Lima video per hari ≈ 1 jam CPU, aman karena semua diproduksi setelah tengah malam.
- server.py memberi produksi 3D batas waktu 45 menit (`timeout=2700`). Render harus selesai jauh di bawahnya.
- Frame harus deterministik (tanpa `Math.random`, tanpa waktu nyata), karena Remotion merender frame secara paralel.
- Aset luar hanya boleh berlisensi CC0 dan disimpan di repo. Dasarnya tetap bentuk primitif seperti sampel.

## Pendekatan yang dipertimbangkan

- **A. Dunia tematik buatan tangan.** Kualitas konsisten, tapi topik terbatas pada dunia yang ada.
- **B. Kotak benda generik, adegan disusun AI.** Topik apa pun bisa, tapi kualitasnya tidak bisa dijamin setiap hari.
- **C. Gabungan (dipilih user).** Dunia tematik sebagai dasar. Benda generik ditaruh di titik-titik tetap di dalam
  dunia supaya video bervariasi. Topik yang belum punya dunia tetap memakai Flow sampai dunianya jadi.

## Desain

### 1. Kit bersama — `shorts/src/kit3d/`

Diambil dari `train3d.tsx`:
- `Box`, `Mat`, `Many` (instancing), `Rig` (kamera, langit, kabut), `Sparks`/partikel, vignette, dan `Meter` (overlay angka yang menghitung naik).
- Pencahayaan siang/senja/malam. Varian malam dipakai otomatis untuk slot horor.
- **Tokoh orang low-poly**: kepala, badan, tangan dan kaki dari bentuk primitif. Ada pose (`berdiri`, `duduk`,
  `lari`, `menunjuk`, `panik`, `memegang`, `menoleh`) dan ekspresi (`biasa`, `kaget`, `takut`, `lega`, `fokus`) dari
  mata, alis dan mulut yang digambar. Warna seragam dan topi/helm diatur lewat parameter, supaya satu tokoh bisa jadi
  masinis, montir atau perawat. Inilah "kamu" dalam format POV profesi.
- **Benda generik** (sekitar 30 di tahap awal, bertambah per dunia): kendaraan, kotak/peti, tabung, gelas, piring,
  kompor, panel/layar, lampu peringatan, pohon, rumah, dan sebagainya. Semuanya parametrik (warna, ukuran) dan memakai satu skala (meter).

### 2. Dunia — `shorts/src/worlds/<nama>.tsx`

Tiap dunia mengekspor:
- `shots`: nama → fungsi `(t, T) => Look` (posisi kamera, target, fov, keadaan benda yang bergerak), sama seperti `shot()` di sampel.
- komponen dunia yang menerima `Look`, frame, dan daftar benda tambahan.
- `anchors` per shot: 2–4 titik bernama (misalnya `meja`, `kiri`, `kanan`) tempat benda generik atau tokoh boleh
  ditaruh. AI tidak pernah memberi koordinat bebas. Inilah penjaga agar adegan tidak berantakan.

Urutan pembangunan mengikuti analytics:
1. **kereta**: pindahkan dunia sampel ke sini, tambah stasiun/peron, interior KRL, dan tokoh masinis.
2. **tubuh**: panggung organ bergaya (ginjal, lambung, jantung, paru, pembuluh) dengan aliran partikel (darah, asam, batu ginjal), tampak potong dan x-ray.
3. **rumah**: dapur dan ruangan (kompor, setrika, kulkas, wastafel, nasi, spons), tampak makro.
4. **jalan**: jalan raya dan bengkel (motor, mobil, mesin dengan tampak potong untuk busi/piston, ojol).
5. **industri**: ketinggian dan lepas pantai (tower, anjungan, crane, tambang).
Berikutnya: rumah sakit, laut, udara/pesawat, kantor/server.

### 3. Katalog — `shorts/worlds.json`

Satu berkas yang dibaca Python, berisi untuk tiap dunia yang sudah siap: nama, deskripsi topik yang cocok (bahasa
Indonesia), daftar shot beserta artinya, anchor per shot, dan benda yang tersedia. Prompt penulis dan validasi dibangun dari
katalog ini, jadi menambah dunia cukup dengan menambah kode dunia plus entrinya di katalog. Sebuah tes memastikan isi katalog sama
dengan shot yang benar-benar diekspor dunia TS.

### 4. Format naskah

Naskah 3D berubah dari `image`/`camera` per adegan menjadi:
```json
{"style": "remotion3d", "world": "kereta", "hero": {"seragam": "#1d2b4a", "topi": "masinis"},
 "scenes": [{"text": "...", "shot": "cab", "hero_pose": "panik", "hero_expr": "kaget",
             "props": [{"jenis": "mobil", "di": "rel"}], "label": "100 KM/JAM", "cue": "100", "sfx": "sub-drop", "emosi": "kaget"}]}
```
`tidy_remotion()` di produce.py membuang shot, anchor, pose dan benda yang tidak ada di katalog dan menggantinya
dengan default yang aman, seperti `tidy3d()` sekarang. Pemeriksa fakta (CHECK) memeriksa nama shot juga.

### 5. Riset ide dan penulis

- `ideas.py` menerima daftar dunia yang siap (dari katalog). Setiap ide wajib menyebut `world`. Kalau benar-benar tidak ada dunia yang cocok, ide itu menyebut `"flow"`.
  Aturannya: utamakan dunia yang ada, dan beri kereta porsi besar selama datanya masih paling kuat.
- `WRITER_REMOTION` (turunan WRITER_3D) menjelaskan dunia yang dipilih beserta shot dan anchor-nya. Shot yang sama tidak boleh dipakai dua kali berturut-turut.

### 6. Produksi dan fallback

- `produce.py --style remotion3d`: tanpa tahap gambar, suara Gemini seperti sekarang, render dengan `--gl=swangle`.
- server.py mencoba berurutan: remotion3d (kalau ide punya `world`) → Flow 3D → kartun. Slot tetap ter-upload apa pun yang gagal.
- Pemeriksaan murah setelah render: ambil satu frame di tengah tiap adegan. Kalau ada frame yang hampir hitam atau
  hampir satu warna (kamera menatap tanah, dunia tidak termuat), render dianggap gagal dan fallback berjalan. Lembar kontaknya disimpan di run untuk dicek di dashboard.

### 7. Peralihan

- Mulai dari dunia kereta (pindahan sampel), lalu satu dunia baru per sesi kerja. Setiap dunia baru dicek dengan satu sampel yang dinilai user sebelum masuk jadwal.
- `STYLE_REMOTION_FROM` di server.py mengatur kapan slot mulai memakai jalur baru.

## Diputuskan oleh user

- Pendekatan C. Semua topik akhirnya 3D Remotion. Tidak ada kuota khusus jumlah video kereta.
- Tampilan sampel kereta disetujui sebagai patokan kualitas.

## Keputusan saya (bisa dikoreksi)

- Urutan dunia mengikuti analytics (kereta, tubuh, rumah, jalan, industri).
- Anchor bernama, bukan koordinat bebas, demi kerapian.
- Tokoh orang low-poly dengan wajah yang digambar, bukan model unduhan.
- Pemeriksaan otomatis hanya frame gelap/datar. Juri vision belum dipakai.
- Kanal horor memakai dunia yang sama dengan pencahayaan malam.

## Diserahkan ke pembangun

Detail geometri tiap dunia, gerak tiap shot, daftar persis benda generik, bentuk skema `worlds.json`, dan tes
kesesuaian katalog dengan TS.
