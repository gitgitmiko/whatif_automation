"""Bank naskah "Gimana Jadinya?": naskah yang lolos juri DAN cek fakta tapi tidak dapat slot malam itu (ideas.py
menyimpan 2 terbaik per malam). Dipakai slot cadangan (stok video) dan slot yang tidak punya naskah riset malam,
jadi tidak perlu AI menulis. Sumber kebenaran: data/bank/<tanggal>.json; tabel bank_naskah di data/whatif.db hanya
indeks untuk menu Database dashboard.
"""
import datetime as dt
import json
import sqlite3

from common import ROOT, load, log, save

BANK = ROOT / "data" / "bank"
DB = ROOT / "data" / "whatif.db"
MIN_NILAI = 5


def add(day, entries):
    """entries: [{"idea": {...}, "nilai", "alasan", "script"}] -> data/bank/<day>.json (menimpa malam yang sama)."""
    if not entries:
        return
    BANK.mkdir(parents=True, exist_ok=True)
    save(BANK / f"{day}.json", {"dibuat": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                                "naskah": [{**e, "dipakai": None} for e in entries]})
    log(f"bank naskah: {len(entries)} naskah disimpan untuk {day}")
    sync_index()


def next_entry():
    """(berkas, indeks, naskah) terbaik yang belum dipakai: malam terbaru dulu, lalu nilai juri tertinggi."""
    for f in sorted(BANK.glob("*.json"), reverse=True) if BANK.exists() else []:
        items = load(f).get("naskah", [])
        for i, e in sorted(enumerate(items), key=lambda p: -(p[1].get("nilai") or 0)):
            if e.get("dipakai") is None and (e.get("nilai") or 0) >= MIN_NILAI and e.get("script"):
                return f, i, e
    return None


def mark(f, i, status):
    data = load(f)
    data["naskah"][i]["dipakai"] = status
    save(f, data)
    sync_index()


def rows():
    out = []
    for f in sorted(BANK.glob("*.json")) if BANK.exists() else []:
        for i, e in enumerate(load(f).get("naskah", [])):
            s = e.get("script") or {}
            ready = e.get("dipakai") is None and (e.get("nilai") or 0) >= MIN_NILAI and bool(s)
            out.append((f.stem, i, s.get("yt_title") or s.get("title") or "", (e.get("idea") or {}).get("topic", ""),
                        s.get("mode") or (e.get("idea") or {}).get("mode", ""), e.get("nilai"), e.get("dipakai"), int(ready),
                        e.get("alasan", "")))
    return out


def sync_index():
    """Bangun ulang tabel indeks; gagal hanya dicatat."""
    try:
        with sqlite3.connect(DB, timeout=30) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS bank_naskah (tanggal TEXT, idx INTEGER, judul TEXT, topik TEXT, mode TEXT,
                nilai INTEGER, dipakai TEXT, siap_darurat INTEGER, alasan TEXT, PRIMARY KEY (tanggal, idx))""")
            c.execute("DELETE FROM bank_naskah")
            c.executemany("INSERT INTO bank_naskah VALUES (?,?,?,?,?,?,?,?,?)", rows())
    except Exception as e:  # noqa: BLE001
        log(f"indeks bank naskah gagal (diabaikan): {e}")


if __name__ == "__main__":  # self-check di folder sementara
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp())
    BANK, DB = tmp / "bank", tmp / "w.db"
    sc = {"title": "x", "yt_title": "Jadi Tukang Tes", "mode": "fakta", "scenes": []}
    add("2026-11-28", [{"idea": {"topic": "a"}, "nilai": 6, "script": sc}, {"idea": {"topic": "b"}, "nilai": 4, "script": sc}])
    add("2026-11-29", [{"idea": {"topic": "c"}, "nilai": 5, "script": sc}, {"idea": {"topic": "d"}, "nilai": 8, "script": sc}])
    f, i, e = next_entry()
    assert (f.stem, e["idea"]["topic"]) == ("2026-11-29", "d"), e
    mark(f, i, "produksi tes")
    assert next_entry()[2]["idea"]["topic"] == "c"
    mark(*next_entry()[:2], "produksi tes")
    assert next_entry()[2]["idea"]["topic"] == "a"  # topik b nilainya di bawah MIN_NILAI
    with sqlite3.connect(DB) as c:
        assert c.execute("SELECT SUM(siap_darurat), COUNT(*) FROM bank_naskah").fetchone() == (1, 4)
    print("ok")
