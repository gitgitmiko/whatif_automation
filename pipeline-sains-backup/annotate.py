"""Step 3b: Sonnet marks the moments the captions should colour: a short phrase from a scene and its mood."""
import sys
from common import *

SYS = """Kamu editor video YouTube edukasi. Dari potongan narasi berikut, pilih momen yang layak ditonjolkan di subtitle dengan warna: angka penting, istilah kunci, fakta mengejutkan, peringatan, atau kesimpulan. Patokan: sekitar sepertiga potongan, menyebar sepanjang video, tidak berurutan terus-menerus.
"phrase" adalah 1-4 kata PERSIS berurutan dari narasi potongan itu. "mood" salah satu: fakta (angka/data), bahaya (risiko, gagal, mati, masalah), positif (berhasil, harapan, solusi), ajaib (penemuan, keajaiban sains), tanya (pertanyaan, misteri).
Balas HANYA JSON: {"highlights":[{"i":0,"phrase":"...","mood":"fakta"}]}"""
MOODS = {"fakta", "bahaya", "positif", "ajaib", "tanya"}


def main(slug):
    d = run_dir(slug)
    scenes = load(d / "scenes.json")
    got = {}
    for at in range(0, len(scenes), 40):
        part = [{"i": x["i"], "narasi": x["text"]} for x in scenes[at:at + 40]]
        for h in claude_json("sonnet", SYS, json.dumps(part, ensure_ascii=False)).get("highlights", []):
            got[h["i"]] = h
    n = 0
    for x in scenes:
        h = got.get(x["i"])
        ok = h and h.get("mood") in MOODS and " ".join(h.get("phrase", "").lower().split()) in " ".join(x["text"].lower().split())
        x["highlight"] = {"phrase": h["phrase"], "mood": h["mood"]} if ok else None
        n += bool(ok)
    save(d / "scenes.json", scenes)
    log("highlights", n, "of", len(scenes))


if __name__ == "__main__":
    main(sys.argv[1])
