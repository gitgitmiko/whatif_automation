# Dunia profesi (template) + dunia tubuh — desain

Tanggal: 2026-11-27 · Lanjutan dari `2026-11-27-remotion-3d-worlds-design.md` · Disetujui user ("Iya itu maksudnya, lanjut ya")

## Maksud

Format channel adalah POV profesi. Dunia buatan tangan per profesi (seperti kereta) tidak akan pernah mencakup semua
profesi, jadi user minta **template dunia profesi**: beberapa latar yang dibangun sekali dan berbagi sudut kamera
standar, supaya hampir semua profesi bisa dibuat 3D Remotion. Dunia **tubuh** dibangun terpisah untuk adegan penjelasan organ.

## Desain

- **Satu world `profesi`.** Tiap adegan memilih `latar` (dapur, bengkel, ... bertambah bertahap) dan `shot` standar:
  - `lebar` (suasana)
  - `wajah` (close-up emosi tokoh)
  - `bahu` (dari balik bahu saat bekerja)
  - `detail` (close-up alat/benda kerja)
  - `pov` (pandangan mata)
  - `bahaya` (goyang + efek menyala di titik kerja, tokoh panik)
  - `penjelasan` (panggung polos: benda utama berputar besar + label)
  - `malam`
- **Tiap latar** menyediakan pemandangan, posisi dan pose kerja tokoh, titik kerja, kamera lebar, anchor bernama, dan efek bawaan untuk shot bahaya.
  Sudut kamera dihitung dari data itu, jadi latar baru otomatis mendapat semua shot.
- **Efek** (`kit3d/effects.tsx`): `api`, `asap`, `percikan`, `air`, `alarm`. Adegan boleh memilih `efek`. Bila tidak dipilih, shot `bahaya` memakai efek bawaan latar.
- **Tokoh** tampil di semua shot latar kecuali `detail` dan `penjelasan`.
- **Benda baru:** `kompor`, `ban`, `jerigen`, `ember`, `apar`, `botol_oli` (ditambah lagi per latar).
- **Dunia `tubuh`** (world sendiri): panggung organ bergaya. Shot: `ginjal`, `lambung`, `jantung`, `paru`, `pembuluh`, `sel`, masing-masing dengan aliran partikel.
- **Aktivasi per dunia:** `worlds.json` mendapat `"aktif": true|false`. Riset 19:00 dan server hanya memakai dunia aktif.
  Dunia baru masuk dengan `aktif: false` sampai user menyetujui sampelnya. Kereta: `aktif: true`.
- **Naskah:** kolom per adegan `latar` dan `efek` (dunia dengan latar). `tidy_remotion` mengisi latar yang hilang dari adegan sebelumnya atau latar pertama.
  Anchor diambil dari latar adegan itu. Efek yang tidak dikenal dibuang.

## Urutan

1. Fondasi template + latar `dapur` (warung gorengan terbuka di pinggir jalan) + `bengkel` (bengkel motor terbuka) + efek + benda baru → sampel (penjual gorengan).
2. Dunia `tubuh` → sampel.
3. Latar berikutnya bertahap: jalan raya, rumah sakit, kantor/ruang kontrol, ruang server, ketinggian, laut/anjungan, kokpit.

## Keputusan saya

- Latar dibuat terbuka (warung, garasi) agar cahaya senja tetap masuk tanpa sistem lampu interior.
- Panggung penjelasan berada jauh dari latar (x = 1000), dengan latar belakang warna polos ala video penjelas.
- Kamera lebar dan titik kerja ditentukan tangan per latar. Shot lainnya dihitung otomatis.
