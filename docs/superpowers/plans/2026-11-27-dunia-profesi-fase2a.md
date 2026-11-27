# Dunia profesi fase 2a (template + dapur + bengkel) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** World `profesi` with standard shots computed from per-latar data, latar `dapur` and `bengkel`, effects, 6 new props, per-world activation; full pipeline support; one e2e sample.

**Spec:** `docs/superpowers/specs/2026-11-27-dunia-profesi-design.md` (and the phase 1 spec it extends).

## Global Constraints
- Same as phase 1: `--gl=swangle`, deterministic frames, metres, AI never gives coordinates, tests in `shorts/test_remotion3d.py` (`cd shorts && ../.venv/bin/python test_remotion3d.py`).
- `profesi` enters `worlds.json` with `"aktif": false`; nothing in production changes until the user approves the sample.

## Review Focus
1. Scene with a latar the world lacks / no latar at all → repaired to the previous or first latar.
2. Inactive world named by an idea → treated as `flow` by research and server.
3. Effects on for `bahaya` with no `efek` given → latar default effect appears.
4. Hero standing/working pose reads in `wajah`/`bahu`/`pov` for every latar (no camera inside the head or a wall).
5. Catalog latar/shots/efek out of sync with TS → test names the difference.

### Task 1: Shot context + activation flag
- `World.shots` signature becomes `(t, T, ctx: {latar?: string}) => Look`. WorldShot passes `{latar: scene.latar}`. Scene gets `latar?`, `efek?`; `WorldViewProps` gets `latar`, `efek`.
- `worlds.json` entries get `"aktif"`; kereta `true`.
- `ideas.research_sys`/`world_of` and `server.attempts` use only active worlds. Tests: `test_inactive_world_is_flow` (ideas + server).

### Task 2: Effects + new props
- `kit3d/effects.tsx`: `EFFECTS: Record<'api'|'asap'|'percikan'|'air'|'alarm', FC<{frame:number; at: V3}>>`, deterministic particles.
- `kit3d/props.tsx`: `kompor`, `ban`, `jerigen`, `ember`, `apar`, `botol_oli`.
- Check: sheet still render of effects and the new props.

### Task 3: World `profesi` + latar `dapur`, `bengkel`
- `worlds/profesi.tsx`: `type Latar = {Scenery; hero: {p: V3; ry: number; pose: string}; work: V3; wide: {cam: V3; at: V3}; anchors: Record<string, Anchor>; efek: string}`; `LATAR` registry; `shots` object literal (`lebar, wajah, bahu, detail, pov, bahaya, penjelasan, malam`) computed from the latar; View renders scenery, hero (not in detail/penjelasan), placed props on latar anchors, the scene effect (or latar default on bahaya), and the explainer stage at x = 1000.
- `worlds.json`: `profesi` with `latar` {name: {arti, anchors}}, `shots`, `efek`, `props`, poses/exprs/topi, `aktif: false`.
- Test: catalog test extended to latar keys and efek names; check stills of every shot × latar.

### Task 4: produce.py for latar worlds
- `tidy_remotion`: latar repair, anchors from the scene's latar, efek validation. `world_menu`/`prompts_remotion` describe latar and efek.
- Tests: `test_tidy_remotion_latar`.

### Task 5: Sample
- e2e `produce.py test-profesi-dapur --topic "penjual gorengan" --style remotion3d --world profesi`; contact sheet; show the user.
