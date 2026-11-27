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
        ts = set(re.findall(r"^\s{2}(\w+): \(t", src.split("export const shots", 1)[1], re.M))
        assert set(w["shots"]) == ts, (name, set(w["shots"]) ^ ts)
        for s in w["shots"].values():
            assert s["arti"] and isinstance(s["anchors"], list) and isinstance(s["tokoh"], bool)
    props_src = (HERE / "src" / "kit3d" / "props.tsx").read_text()
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
