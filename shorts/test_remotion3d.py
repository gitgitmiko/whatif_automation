"""Self-checks for the real-time 3D Shorts: the catalog, script repair, the frame check, idea routing and the
server's fallback order. Run: .venv/bin/python shorts/test_remotion3d.py"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
DATA = HERE / "test_data"  # a real day still and a real horror-night still of the kereta world


def test_catalog_matches_ts():
    cat = json.loads((HERE / "worlds.json").read_text())
    for name, w in cat.items():
        src = (HERE / "src" / "worlds" / f"{name}.tsx").read_text()
        ts = set(re.findall(r"^\s{2}(\w+): (?:\(t|own\()", src.split("export const shots", 1)[1].split("\n};", 1)[0], re.M))
        assert set(w["shots"]) == ts, (name, set(w["shots"]) ^ ts)
        for s in w["shots"].values():
            assert s["arti"] and isinstance(s["anchors"], list) and isinstance(s["tokoh"], bool)
        if "latar" in w:  # a world built from sets: catalog latar = TS LATAR registry, effects = EFFECTS
            reg = re.search(r"export const LATAR: Record<string, Latar> = \{([^}]*)\}", src).group(1)
            assert set(w["latar"]) == {x.strip() for x in reg.split(",")}, (name, w["latar"].keys(), reg)
            for k, l in w["latar"].items():
                lsrc = (HERE / "src" / "worlds" / "latar" / f"{k}.tsx").read_text()
                ts_anchors = set(re.findall(r"^\s{4}(\w+): \{p:", lsrc.split("anchors: {", 1)[1].split("},\n  efek", 1)[0], re.M))
                assert set(l["anchors"]) == ts_anchors and l["arti"], (k, set(l["anchors"]) ^ ts_anchors)
            fx_src = (HERE / "src" / "kit3d" / "effects.tsx").read_text()
            assert set(w["efek"]) == set(re.findall(r"^\s{2}(\w+): \(\{frame", fx_src, re.M)), w["efek"]
    props_src = (HERE / "src" / "kit3d" / "props.tsx").read_text()
    assert "profesi" in cat and all(isinstance(w.get("aktif"), bool) for w in cat.values())
    for w in cat.values():
        for p in w["props"]:
            assert re.search(rf"^\s{{2}}{p}:", props_src, re.M), p


def test_tidy_remotion_repairs():
    import produce
    s = {"world": "kereta", "title": "Kalau Kamu Jadi Masinis?", "hero": {"seragam": "biru", "topi": "koki"},
         "scenes": [{"text": "Satu dua tiga.", "shot": "cab", "props": [{"jenis": "mobil", "di": "rel"}, {"jenis": "ufo", "di": "rel"}]},
                    {"text": "Empat lima.", "shot": "cab"},
                    {"text": "Enam tujuh.", "shot": "terbang", "hero_pose": "salto"},
                    {"text": "Delapan.", "shot": "peron", "props": [{"jenis": "koper", "di": "rel"}]}]}
    t = produce.tidy_remotion(s)
    sh = [x["shot"] for x in t["scenes"]]
    assert t["style"] == "remotion3d" and sh[0] == "cab" and sh[1] != "cab", sh
    assert sh[2] in produce.WORLDS["kereta"]["shots"] and sh[2] != sh[1], sh
    assert t["scenes"][0]["props"] == [{"jenis": "mobil", "di": "rel"}]
    assert "hero_pose" not in t["scenes"][2] and t["scenes"][3].get("props", []) == []
    assert t["hero"].get("topi") == "none" and "seragam" not in t["hero"]


def test_tidy_remotion_keeps_good_fields():
    import produce
    s = {"world": "kereta", "title": "T", "hero": {"seragam": "#2b4c8c", "topi": "masinis"},
         "scenes": [{"text": f"Kalimat nomor {i} di sini.", "shot": sh, "hero_pose": "panik", "hero_expr": "kaget",
                     "props": [{"jenis": "koper", "di": "peron_kiri"}] if sh == "peron" else [], "label": "500 M", "cue": "nomor", "emosi": "panik"}
                    for i, sh in enumerate(["cab", "peron", "masinis", "wheel"])]}
    t = produce.tidy_remotion(s)
    assert t["hero"] == {"seragam": "#2b4c8c", "topi": "masinis"}
    assert [x["shot"] for x in t["scenes"]] == ["cab", "peron", "masinis", "wheel"]
    assert t["scenes"][1]["props"] == [{"jenis": "koper", "di": "peron_kiri"}]
    assert t["scenes"][2]["hero_pose"] == "panik" and t["scenes"][2]["hero_expr"] == "kaget"
    assert t["scenes"][0]["label"] == "500 M" and t["scenes"][0]["cue"] == "nomor"


def test_tidy_remotion_unknown_world():
    import produce
    try:
        produce.tidy_remotion({"world": "bulan", "scenes": []})
        raise AssertionError("no ValueError")
    except ValueError:
        pass


def test_prompts_remotion():
    import produce
    w, c = produce.prompts_remotion("kereta", "loop", "fakta")
    assert '"world" WAJIB "kereta"' in w and "   - masinis: " in w and "[TOKOH TAMPIL]" in w
    assert '"image" (prompt' not in w and '"hero_look":"..."' not in w and '"shot":"..."' in w
    assert 'setiap adegan punya "shot"' in c and '"image"' not in c and "   - gerbong: " in c
    wh, ch = produce.prompts_remotion("kereta", "loop", "horor")
    assert "MODE HOROR" in wh and "MODE HOROR" in ch


def test_props_from_remotion():
    import produce
    s = {"title": "T", "style": "remotion3d", "world": "kereta", "hero": {"topi": "masinis"}, "mode": "fakta"}
    p = produce.props_from(s, [], 30)
    assert p["world"] == "kereta" and p["hero3d"] == {"topi": "masinis"}
    assert "world" not in produce.props_from({"title": "T", "style": "3d"}, [], 30)


def test_world_of():
    import ideas
    ideas.ACTIVE = True
    assert ideas.world_of({"world": "kereta"}) == "kereta"
    assert ideas.world_of({"world": "flow"}) is None
    assert ideas.world_of({"world": "bulan"}) is None
    assert ideas.world_of({}) is None


def test_world_of_off_before_activation():
    import ideas
    ideas.ACTIVE = False
    try:
        assert ideas.world_of({"world": "kereta"}) is None
        assert "DUNIA 3D YANG TERSEDIA" not in ideas.research_sys()
    finally:
        ideas.ACTIVE = True


def test_ideas_prompt_lists_worlds():
    import ideas
    ideas.ACTIVE = True
    assert "- kereta: kereta api dan KRL" in ideas.research_sys() and '"world":' in ideas.research_sys()
    assert "TIDAK boleh memengaruhi pilihan topik" in ideas.research_sys() and "porsi besar" not in ideas.research_sys()


def test_server_attempts():
    import tempfile
    sys.path.insert(0, str(HERE.parent / "pipeline"))
    import server
    server.STYLE_REMOTION_FROM = "2000-01-01"
    tmp = Path(tempfile.mkdtemp())
    r3d, s3d = tmp / "r.json", tmp / "s.json"
    r3d.write_text(json.dumps({"style": "remotion3d", "world": "kereta"}))
    s3d.write_text(json.dumps({"style": "3d"}))
    a = server.attempts({"world": "kereta"}, "2026-12-01", r3d)
    assert a == [["--style", "remotion3d", "--world", "kereta", "--script", r3d], ["--style", "3d"], []], a
    assert server.attempts({"world": "kereta"}, "2026-12-01", None) == [["--style", "remotion3d", "--world", "kereta"], ["--style", "3d"], []]
    assert server.attempts({"world": "flow"}, "2026-12-01", s3d) == [["--style", "3d", "--script", s3d], []]
    assert server.attempts(None, "2026-12-01", None) == [["--style", "3d"], []]
    server.STYLE_REMOTION_FROM = "2099-01-01"
    assert server.attempts({"world": "kereta"}, "2026-12-01", s3d)[0] == ["--style", "3d", "--script", s3d]
    server.STYLE_REMOTION_FROM = "2000-01-01"
    bad = tmp / "broken.json"
    bad.write_text("{not json")
    server.WORLDS_FILE = bad  # a broken catalog costs the 3D world, never the slot
    assert server.attempts({"world": "kereta"}, "2026-12-01", None) == [["--style", "3d"], []]
    server.WORLDS_FILE = HERE / "worlds.json"
    server.STYLE_3D_FROM = "2099-01-01"
    server.STYLE_REMOTION_FROM = "2099-01-01"
    assert server.attempts(None, "2026-12-01", None) == [[]]


def test_shots_never_reach_the_crossing():
    """Whatever stands on the rails (the sticky "rel" prop at x = 0) is never driven through, for any scene length,
    including the 8-frame lead and the 30 frames the last scene plays past its end."""
    import subprocess
    out = subprocess.run(["npx", "esbuild", "src/worlds/kereta.tsx", "--bundle", "--platform=node", "--format=cjs",
                          "--log-level=error", "--outfile=/dev/stdout", "--jsx=automatic"], cwd=HERE, capture_output=True, text=True, check=True).stdout
    js = out + """
const SH = module.exports.shots; const bad = [];
for (const [n, f] of Object.entries(SH)) { if (n === 'peron') continue;  // the station lies beyond the crossing
  for (const T of [3, 4, 6, 8]) for (let t = 0; t <= T + 1.3; t += 0.05) if (f(t, T).front > -3) { bad.push(n + '@' + T); break; } }
console.log(JSON.stringify(bad));"""
    import tempfile
    f = Path(tempfile.mkdtemp()) / "shots.cjs"
    f.write_text(js)
    r = subprocess.run(["node", str(f)], cwd=HERE, capture_output=True, text=True, check=True)
    assert json.loads(r.stdout.strip().splitlines()[-1]) == [], r.stdout


def test_inactive_world_is_flow():
    import tempfile
    import ideas
    sys.path.insert(0, str(HERE.parent / "pipeline"))
    import server
    ideas.ACTIVE = True
    cat = json.loads((HERE / "worlds.json").read_text())
    assert cat["kereta"]["aktif"] is True
    w = ideas.WORLDS["kereta"]
    w["aktif"] = False
    try:
        assert ideas.world_of({"world": "kereta"}) is None
        assert "- kereta:" not in ideas.research_sys()
    finally:
        w["aktif"] = True
    off = Path(tempfile.mkdtemp()) / "worlds.json"
    off.write_text(json.dumps({"kereta": {**cat["kereta"], "aktif": False}}))
    server.STYLE_REMOTION_FROM, server.STYLE_3D_FROM, server.WORLDS_FILE = "2000-01-01", "2000-01-01", off
    try:
        assert server.attempts({"world": "kereta"}, "2026-12-01", None) == [["--style", "3d"], []]
    finally:
        server.WORLDS_FILE = HERE / "worlds.json"


def test_tidy_remotion_latar():
    import produce
    s = {"world": "profesi", "title": "Kalau Kamu Jadi Penjual Gorengan?", "hero": {"seragam": "#e2711d", "topi": "none"},
         "scenes": [{"text": "Minyakmu mulai berasap.", "shot": "lebar", "props": [{"jenis": "motor", "di": "jalan"}]},
                    {"text": "Api menyambar.", "shot": "bahaya", "latar": "kapal", "efek": "ledakan"},
                    {"text": "Kamu lari ke bengkel.", "shot": "wajah", "latar": "bengkel", "props": [{"jenis": "ban", "di": "jalan"}, {"jenis": "ban", "di": "rak"}]},
                    {"text": "Tabung gas tiga kilogram.", "shot": "penjelasan", "efek": "api", "props": [{"jenis": "tabung_gas", "di": "mana_saja"}]}]}
    t = produce.tidy_remotion(s)
    sc = t["scenes"]
    assert [x["latar"] for x in sc] == ["dapur", "dapur", "bengkel", "bengkel"], [x.get("latar") for x in sc]
    assert sc[0]["props"] == [{"jenis": "motor", "di": "jalan"}]
    assert "efek" not in sc[1] and sc[3]["efek"] == "api"
    assert sc[2]["props"] == [{"jenis": "ban", "di": "rak"}]
    assert sc[3]["props"] == [{"jenis": "tabung_gas", "di": "panggung"}]
    w, c = produce.prompts_remotion("profesi", "loop", "fakta")
    assert '"latar"' in w and "   - dapur: warung gorengan" in w and "efek" in w and "   - bengkel:" in c


def test_scene_can_cut_to_tubuh():
    import produce
    s = {"world": "profesi", "title": "T", "hero": {},
         "scenes": [{"text": "Satu dua.", "shot": "lebar", "latar": "dapur"},
                    {"text": "Paru-parumu terisi asap.", "world": "tubuh", "shot": "paru", "latar": "dapur", "props": [{"jenis": "kompor", "di": "meja"}]},
                    {"text": "Jantung berdebar.", "world": "tubuh", "shot": "terbang"},
                    {"text": "Kembali ke warung.", "world": "bulan", "shot": "wajah"}]}
    import copy
    produce.WORLDS["tubuh"]["aktif"] = False
    off = produce.tidy_remotion(copy.deepcopy(s))  # tubuh not yet approved: the cut becomes a normal scene
    assert all("world" not in x for x in off["scenes"]), [x.get("world") for x in off["scenes"]]
    produce.WORLDS["tubuh"]["aktif"] = True
    try:
        t = produce.tidy_remotion(s)
    finally:
        produce.WORLDS["tubuh"]["aktif"] = True
    sc = t["scenes"]
    assert sc[1]["world"] == "tubuh" and sc[1]["shot"] == "paru" and sc[1].get("props") == [] and "latar" not in sc[1]
    assert sc[2]["world"] == "tubuh" and sc[2]["shot"] in produce.WORLDS["tubuh"]["shots"]
    assert "world" not in sc[3] and sc[3]["shot"] == "wajah" and sc[3]["latar"] == "dapur"
    produce.WORLDS["tubuh"]["aktif"] = False
    assert '"world":"tubuh"' not in produce.prompts_remotion("profesi", "loop", "fakta")[0]  # inactive: not offered
    produce.WORLDS["tubuh"]["aktif"] = True
    try:
        w, _ = produce.prompts_remotion("profesi", "loop", "fakta")
        assert "   - jantung: jantung berdetak" in w and '"world":"tubuh"' in w
    finally:
        produce.WORLDS["tubuh"]["aktif"] = True


def test_tidy_remotion_odd_types():
    import produce
    s = {"world": "kereta", "title": "T", "scenes": [{"text": "Satu dua.", "shot": "cab", "world": ["tubuh"]},
         {"text": "Tiga.", "shot": "top"}, {"text": "Empat.", "shot": "wheel"}, {"text": "Lima.", "shot": "stop"}]}
    assert "world" not in produce.tidy_remotion(s)["scenes"][0]
    s = {"world": "profesi", "title": "T", "scenes": [{"text": "Satu.", "shot": "lebar", "latar": ["dapur"]},
         {"text": "Dua.", "shot": "wajah"}, {"text": "Tiga.", "shot": "pov"}, {"text": "Empat.", "shot": "detail"}]}
    assert produce.tidy_remotion(s)["scenes"][0]["latar"] == "dapur"


def test_catalog_without_props_still_imports():
    import subprocess, tempfile, shutil
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(HERE.parent / "pipeline", tmp / "pipeline")
    (tmp / "shorts").mkdir()
    shutil.copy(HERE / "produce.py", tmp / "shorts")
    cat = json.loads((HERE / "worlds.json").read_text())
    del cat["tubuh"]["props"]
    (tmp / "shorts" / "worlds.json").write_text(json.dumps(cat))
    r = subprocess.run([sys.executable, "-c", "import produce; print(sorted(produce.INSETS))"], cwd=tmp / "shorts", capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]


def test_inset_only_world_is_never_a_video_world():
    import ideas
    sys.path.insert(0, str(HERE.parent / "pipeline"))
    import server
    ideas.ACTIVE = True
    assert ideas.world_of({"world": "tubuh"}) is None and "- tubuh:" not in ideas.research_sys()
    server.STYLE_REMOTION_FROM, server.STYLE_3D_FROM, server.WORLDS_FILE = "2000-01-01", "2000-01-01", HERE / "worlds.json"
    assert server.attempts({"world": "tubuh"}, "2026-12-01", None)[0] == ["--style", "3d"]
    assert server.attempts({"world": "profesi"}, "2026-12-01", None)[0] == ["--style", "remotion3d", "--world", "profesi"]


def _clip(src, out):
    import subprocess
    subprocess.run(["ffmpeg", "-v", "error", "-y", *src, "-t", "1", "-r", "30", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def test_frame_check():
    import produce
    one = [{"from": 0, "frames": 30}]
    import tempfile
    WS = Path(tempfile.mkdtemp())
    day = _clip(["-loop", "1", "-i", str(DATA / "day.png")], WS / "c_day.mp4")
    night = _clip(["-loop", "1", "-i", str(DATA / "night.png")], WS / "c_night.mp4")
    black = _clip(["-f", "lavfi", "-i", "color=black:s=270x480"], WS / "c_black.mp4")
    flat = _clip(["-f", "lavfi", "-i", "color=0x6d8f3f:s=270x480"], WS / "c_flat.mp4")
    assert produce.frame_check(day, one) == [], produce.frame_check(day, one)
    assert produce.frame_check(night, one) == [], produce.frame_check(night, one)
    assert produce.frame_check(black, one) == ["adegan 0: gelap"]
    assert produce.frame_check(flat, one) == ["adegan 0: datar"]


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in tests:
        try:
            f()
            print("PASS", n)
        except Exception as e:  # noqa: BLE001 - report every test, then fail the run
            failed += 1
            print("FAIL", n, repr(e))
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
