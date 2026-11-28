"""Peran AI dari dashboard (dashboard_gitgit/lib/peran_ai.py): siapa yang meriset, menulis draf, menjuri, dan mengecek
fakta. Tanpa dashboard di server ini, tiap peran kembali ke Claude bawaannya (riset & penulis Sonnet, juri & cek Opus)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getenv("PERAN_AI_LIB", str(Path.home() / "github-repos" / "dashboard_gitgit" / "lib")))
try:
    from peran_ai import ask_json as _ask_json
except ImportError:  # dashboard tidak ada
    _ask_json = None
try:
    from cadangan import catat  # noqa: F401 - riwayat cadangan di dashboard (+ WA bila darurat)
except ImportError:
    def catat(channel, jenis, pesan, darurat=False):
        print(f"cadangan {channel}/{jenis}: {pesan}", flush=True)

MODELS = {"riset": "sonnet", "penulis": "sonnet", "juri": "opus", "cek": "opus"}


def ask_json(role, system, user, web=False, timeout=1500):
    """(jawaban JSON, AI yang menjawab) untuk channel Apa yang terjadi jika."""
    if _ask_json:
        return _ask_json("whatif", role, system, user, web=web, timeout=timeout)
    from common import claude_json
    return claude_json(MODELS[role], system, user, web=web, timeout=timeout), f"claude:{MODELS[role]}"


def asker(role, web=True):
    """ask(system, user) -> dict untuk produce.write_draft / check_draft."""
    return lambda system, user: ask_json(role, system, user, web=web)[0]
