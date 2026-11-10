"""Builds assets/sfx: CC0 sounds picked from the downloaded packs plus a few synthesised with ffmpeg,
all trimmed and peak-normalised, and catalog.json that the storyboard chooses from."""
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "assets" / "sfx-src", ROOT / "assets" / "sfx"
OGA100 = ("100-cc0-sfx/x", "CC0-1.0", "https://opengameart.org/content/100-cc0-sfx")
KENNEY = ("kenney-interface/x/Audio", "CC0-1.0", "https://opengameart.org/content/interface-sounds (Kenney)")

PICKED = [  # id, pack, file, what it sounds like (what the storyboard reads)
    ("boing", OGA100, "spring_01.ogg", "boing pegas kartun: lucu, memantul, sesuatu melompat atau gagal secara lucu"),
    ("boing-short", OGA100, "spring_03.ogg", "boing pendek: kejutan kecil yang lucu"),
    ("pop", OGA100, "plop_01.ogg", "pop/plop: sesuatu muncul tiba-tiba, ide kecil, gelembung"),
    ("pop2", OGA100, "plop_02.ogg", "pop kedua: objek muncul, angka atau fakta muncul"),
    ("bell", OGA100, "bell_01.ogg", "bunyi lonceng: pengumuman, fakta penting, momen 'ternyata'"),
    ("gong", OGA100, "gong_01.ogg", "gong dramatis: pernyataan besar, kesimpulan, momen serius"),
    ("hit", OGA100, "hit_01.ogg", "pukulan/benturan ringan: sesuatu jatuh atau mengenai"),
    ("slam", OGA100, "slam_01.ogg", "hantaman keras: pintu dibanting, keputusan tegas, kejutan berat"),
    ("splash", OGA100, "splash_01.ogg", "cipratan air: air, laut, cairan"),
    ("paper", OGA100, "paper_01.ogg", "kertas dibalik/diremas: dokumen, buku, penelitian, catatan"),
    ("boom", OGA100, "explosion.ogg", "ledakan kecil kartun: kehancuran, kekacauan, perubahan drastis"),
    ("glass", OGA100, "glass_01.ogg", "gelas/kaca berdenting: laboratorium, tabung, botol"),
    ("door-open", OGA100, "door_open.ogg", "pintu dibuka: memasuki tempat, peluang baru"),
    ("door-close", OGA100, "door_close_01.ogg", "pintu ditutup: akhir, sesuatu tertutup atau hilang"),
    ("machine", OGA100, "machine_01.ogg", "mesin bekerja: teknologi, pabrik, alat laboratorium"),
    ("weird", OGA100, "weird_03.ogg", "bunyi aneh/misterius: hal ganjil, tidak masuk akal"),
    ("metal", OGA100, "metal_01.ogg", "denting logam: alat, kunci, brankas, tangki"),
    ("click", OGA100, "switch_01.ogg", "klik saklar: menyalakan sesuatu, tombol"),
    ("correct", KENNEY, "confirmation_001.ogg", "ding benar: jawaban benar, berhasil, terbukti"),
    ("wrong", KENNEY, "error_006.ogg", "bunyi salah: gagal, tidak mungkin, mitos dipatahkan"),
    ("question", KENNEY, "question_001.ogg", "bunyi bertanya: pertanyaan, rasa penasaran, bingung"),
    ("drop", KENNEY, "drop_001.ogg", "tetesan/jatuh kecil: angka turun, sesuatu berkurang"),
    ("pluck", KENNEY, "pluck_001.ogg", "petikan kecil: detail kecil, poin ringan"),
    ("pop-up", KENNEY, "maximize_001.ogg", "pop-up naik: sesuatu membesar, angka naik, muncul di layar"),
]

# Made here from noise and tones, so no third party is involved at all.
SYNTH = {
    "whoosh-soft": ("anoisesrc=d=0.5:c=pink:a=0.5", "highpass=f=500,lowpass=f=2500,afade=t=in:d=0.22,afade=t=out:st=0.22:d=0.28",
                    "whoosh lembut: perpindahan adegan"),
    "whoosh-fast": ("anoisesrc=d=0.35:c=white:a=0.4", "bandpass=f=1800:width_type=o:w=2,afade=t=in:d=0.12,afade=t=out:st=0.12:d=0.23",
                    "whoosh cepat: gerakan cepat, sesuatu melesat"),
    "riser": ("anoisesrc=d=1.6:c=pink:a=0.4", "highpass=f=300,lowpass=f=6000,afade=t=in:d=1.5:curve=exp,afade=t=out:st=1.5:d=0.1",
              "riser: ketegangan naik sebelum pengungkapan besar"),
    "heartbeat": ("sine=f=55:d=1.1", "volume='if(lt(mod(t,0.55),0.09),1,if(lt(mod(t-0.18,0.55),0.07)*gte(t,0.18),0.7,0))':eval=frame,lowpass=f=120,volume=4",
                  "detak jantung: tegang, hidup dan mati, tubuh manusia"),
    "clock": ("sine=f=2400:d=1.6", "volume='if(lt(mod(t,0.4),0.02),1,0)':eval=frame,highpass=f=1500",
              "detak jam: waktu berjalan, tahun berlalu, linimasa"),
    "sparkle": ("sine=f=2093:d=0.7", "aecho=0.8:0.6:60|120:0.5|0.3,afade=t=out:st=0.05:d=0.65",
                "kilau/ting ajaib: penemuan, keajaiban sains, ide cemerlang"),
    "sub-drop": ("sine=f=90:d=0.9", "asetrate=48000*0.7,aresample=48000,afade=t=out:st=0.1:d=0.8,volume=3",
                 "dentuman rendah: fakta mengejutkan, suasana berat"),
}


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)


def finish(src, dst, trim=True):
    # Trim leading silence, peak to -3 dBFS, 48 kHz stereo like the rest of the timeline.
    peak = subprocess.run(["ffmpeg", "-nostats", "-i", str(src), "-af", "volumedetect", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    mx = float(peak.split("max_volume:")[1].split()[0])
    ff("-i", str(src), "-af", ("silenceremove=start_periods=1:start_threshold=-50dB," if trim else "") + f"volume={-3 - mx}dB",
       "-ar", "48000", "-ac", "2", str(dst))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cat = []
    for sid, (folder, lic, src), name, desc in PICKED:
        finish(SRC / folder / name, OUT / f"{sid}.wav")
        cat.append({"id": sid, "desc": desc, "license": lic, "source": f"{src} :: {name}"})
    for sid, (gen, fx, desc) in SYNTH.items():
        tmp = OUT / f".{sid}.wav"
        ff("-f", "lavfi", "-i", gen, "-af", fx, "-ar", "48000", str(tmp))
        finish(tmp, OUT / f"{sid}.wav", trim=False)  # a riser starts quiet on purpose
        tmp.unlink()
        cat.append({"id": sid, "desc": desc, "license": "own (synthesised)", "source": "pipeline/make_sfx.py"})
    for c in cat:
        c["duration"] = round(float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                             "-of", "csv=p=0", str(OUT / f"{c['id']}.wav")])), 3)
    (OUT / "catalog.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1))
    print(len(cat), "sounds")


if __name__ == "__main__":
    main()
