"""Salinan MySQL "Gimana Jadinya?" (db gitgit_whatif): tabel runs (riwayat produksi & unggahan) dan bank_naskah,
supaya bisa di-query bersama konten lain. data/whatif.db (SQLite) dan data/bank/*.json tetap sumber kebenaran:
tabel di sini dibangun ulang dari sana tiap 5 menit oleh pipeline/server.py. MySQL mati atau belum dibuat = dilewati,
produksi tidak pernah terganggu.

Kredensial di .env: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS. Database dibuat sekali: sudo mysql < (berkas SQL).

    .venv/bin/python pipeline/mirror.py
"""
import sqlite3
import sys

from bank import rows as bank_rows
from common import ROOT, log

ENV = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().split() if "=" in l) if (ROOT / ".env").exists() else {}
DB = ROOT / "data" / "whatif.db"

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS runs (id VARCHAR(64) PRIMARY KEY, slot VARCHAR(32), topic TEXT, title TEXT,
       status VARCHAR(32), stage VARCHAR(64), error TEXT, started_at VARCHAR(40), finished_at VARCHAR(40),
       youtube_id VARCHAR(32), data MEDIUMTEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bank_naskah (tanggal VARCHAR(10), idx INT, judul TEXT, topik VARCHAR(191), mode VARCHAR(16),
       nilai INT, dipakai VARCHAR(191), siap_darurat TINYINT, alasan TEXT, PRIMARY KEY (tanggal, idx))
       ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]
RUN_COLS = ("id", "slot", "topic", "title", "status", "stage", "error", "started_at", "finished_at", "youtube_id", "data")


def sync():
    if not ENV.get("DB_USER"):
        log("mirror: DB_USER belum diatur di .env, dilewati")
        return None
    import pymysql
    with sqlite3.connect(DB, timeout=30) as c:
        runs = c.execute(f"SELECT {', '.join(RUN_COLS)} FROM runs").fetchall()
    bank = bank_rows()
    con = pymysql.connect(host=ENV.get("DB_HOST", "127.0.0.1"), port=int(ENV.get("DB_PORT", "3306")), user=ENV["DB_USER"],
                          password=ENV.get("DB_PASS", ""), database=ENV.get("DB_NAME", "gitgit_whatif"), charset="utf8mb4")
    try:
        with con.cursor() as cur:
            for ddl in SCHEMA:
                cur.execute(ddl)
            cur.execute("DELETE FROM runs")
            cur.executemany(f"INSERT INTO runs VALUES ({', '.join(['%s'] * len(RUN_COLS))})", runs)
            cur.execute("DELETE FROM bank_naskah")
            cur.executemany("INSERT INTO bank_naskah VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", bank)
        con.commit()
    finally:
        con.close()
    return len(runs), len(bank)


if __name__ == "__main__":
    try:
        n = sync()
    except Exception as e:  # noqa: BLE001 - dicoba lagi 5 menit kemudian
        log(f"mirror gagal: {e}")
        sys.exit(1)
    if n:
        log(f"mirror: {n[0]} run, {n[1]} naskah bank ke MySQL")
