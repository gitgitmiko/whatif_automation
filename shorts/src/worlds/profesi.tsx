import {useLayoutEffect, useRef} from 'react';
import * as THREE from 'three';
import {Look, Mat, V3} from '../kit3d/core';
import {EFFECTS} from '../kit3d/effects';
import {Person} from '../kit3d/person';
import {PROPS, PlacedProps} from '../kit3d/props';
import type {ShotCtx, World, WorldViewProps} from './index';
import {bengkel} from './latar/bengkel';
import {dapur} from './latar/dapur';
import type {Latar} from './latar/types';

// The profession template: every scene picks a latar (set) and one of the standard shots below. Each shot is worked
// out from the latar's data (where you stand, what you work on, the wide camera), so adding a latar is only scenery.

export const LATAR: Record<string, Latar> = {dapur, bengkel};
const STAGE: V3 = [1000, 0, 0];  // the explainer stage, far from every set

type PLook = Look & {latar: string; danger?: boolean; explain?: boolean; detail?: boolean};
const pick = (ctx: ShotCtx) => (ctx.latar && LATAR[ctx.latar] ? ctx.latar : Object.keys(LATAR)[0]);
const add = (a: V3, ...bs: V3[]): V3 => bs.reduce<V3>((s, b) => [s[0] + b[0], s[1] + b[1], s[2] + b[2]], a);
const mul = (a: V3, k: number): V3 => [a[0] * k, a[1] * k, a[2] * k];
const lerp = (a: V3, b: V3, u: number): V3 => [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u];
// facing (f) and right-hand (r) directions of the hero, and the eyes
const frame3 = (L: Latar) => {
  const f: V3 = [Math.sin(L.hero.ry), 0, Math.cos(L.hero.ry)], r: V3 = [Math.cos(L.hero.ry), 0, -Math.sin(L.hero.ry)];
  return {f, r, eye: add(L.hero.p, [0, 1.52, 0])};
};

export const shots: Record<string, (t: number, T: number, ctx: ShotCtx) => PLook> = {
  lebar: (t: number, T: number, ctx: ShotCtx): PLook => {
    const latar = pick(ctx), L = LATAR[latar], u = Math.min(t / T, 1);
    return {latar, cam: lerp(L.wide.cam, lerp(L.wide.cam, L.wide.at, 0.18), u), at: L.wide.at, fov: 50, light: [0, 0, 0]};
  },
  wajah: (t: number, T: number, ctx: ShotCtx): PLook => {
    const latar = pick(ctx), L = LATAR[latar], u = Math.min(t / T, 1), {f, r, eye} = frame3(L);
    return {latar, cam: add(eye, mul(f, 1.7 - 0.3 * u), mul(r, -0.28), [0, 0.04, 0]), at: add(eye, [0, -0.04, 0]), fov: 40, light: [0, 0, 0]};
  },
  bahu: (t: number, T: number, ctx: ShotCtx): PLook => {
    const latar = pick(ctx), L = LATAR[latar], u = Math.min(t / T, 1), {f, r} = frame3(L);
    // over the shoulder on the side the work is on, so the head never hides it
    const side = (L.work[0] - L.hero.p[0]) * r[0] + (L.work[2] - L.hero.p[2]) * r[2] < 0 ? -1 : 1;
    return {latar, cam: add(L.hero.p, mul(f, -0.9 + 0.15 * u), mul(r, 0.75 * side), [0, 2.0, 0]), at: L.work, fov: 55, light: [0, 0, 0]};
  },
  detail: (t: number, T: number, ctx: ShotCtx): PLook => {
    const latar = pick(ctx), L = LATAR[latar], u = Math.min(t / T, 1);
    const a = Math.atan2(L.wide.cam[0] - L.work[0], L.wide.cam[2] - L.work[2]) - 0.3 + 0.6 * u;
    return {latar, detail: true, cam: add(L.work, [Math.sin(a) * 0.9, 0.55, Math.cos(a) * 0.9]), at: L.work, fov: 45, light: [0, 0, 0]};
  },
  pov: (t: number, T: number, ctx: ShotCtx): PLook => {
    const latar = pick(ctx), L = LATAR[latar], {f, eye} = frame3(L);
    return {latar, cam: add(eye, mul(f, 0.3), [0, 0.02 + Math.sin(t * 5) * 0.01, 0]), at: L.work, fov: 62, light: [0, 0, 0]};
  },
  bahaya: (t: number, T: number, ctx: ShotCtx): PLook => {
    const latar = pick(ctx), L = LATAR[latar], u = Math.min(t / T, 1), {f, r} = frame3(L);
    return {latar, danger: true, cam: add(L.hero.p, mul(f, -0.25 + 0.2 * u), mul(r, 1.05), [0, 1.6, 0]), at: lerp(L.work, add(L.hero.p, [0, 1.3, 0]), 0.3),
      fov: 58, shake: 0.035, light: [0, 0, 0]};
  },
  penjelasan: (t: number, T: number, ctx: ShotCtx): PLook => {
    const latar = pick(ctx), u = Math.min(t / T, 1);
    return {latar, explain: true, cam: add(STAGE, [0.3 - 0.6 * u, 1.45, 3.4 - 0.4 * u]), at: add(STAGE, [0, 0.95, 0]), fov: 42, light: STAGE};
  },
  malam: (t: number, T: number, ctx: ShotCtx): PLook => {
    const latar = pick(ctx), L = LATAR[latar], u = Math.min(t / T, 1);
    const side = add(L.wide.cam, mul([L.wide.cam[2] - L.wide.at[2], 0, -(L.wide.cam[0] - L.wide.at[0])], 0.25 * (u - 0.5)));
    return {latar, night: true, cam: side, at: L.wide.at, fov: 52, light: [0, 0, 0]};
  },
};

// A plain coloured stage with the scene's main prop turning on a pedestal, sized to fit whatever it is.
const Explain: React.FC<{jenis: string; frame: number}> = ({jenis, frame}) => {
  const ref = useRef<THREE.Group>(null);
  const Prop = PROPS[jenis] ?? PROPS.kotak;
  useLayoutEffect(() => {
    const g = ref.current!;
    g.scale.setScalar(1);
    const box = new THREE.Box3().setFromObject(g), size = box.getSize(new THREE.Vector3());
    g.scale.setScalar(1.25 / Math.max(size.x, size.y, size.z, 0.01));
  }, [jenis]);
  return (
    <group position={STAGE}>
      <mesh position={[0, 3, -1]}><cylinderGeometry args={[9, 9, 12, 32, 1, true]} /><meshStandardMaterial color="#1f8a9a" side={1} roughness={1} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><circleGeometry args={[9, 32]} /><Mat c="#26a0b0" r={1} /></mesh>
      <mesh position={[0, 0.2, 0]} castShadow receiveShadow><cylinderGeometry args={[0.8, 0.9, 0.4, 32]} /><Mat c="#f2f2ef" r={0.5} /></mesh>
      <group position={[0, 0.4, 0]} rotation={[0, frame * 0.012, 0]}><group ref={ref}><Prop frame={frame} /></group></group>
      <pointLight position={[1.5, 3, 2.5]} intensity={18} distance={10} color="#fff6e8" />
    </group>
  );
};

const View: React.FC<WorldViewProps> = ({look, frame, night, hero, heroPose, heroExpr, props = [], efek}) => {
  const k = look as PLook, L = LATAR[k.latar];
  if (k.explain) return <Explain jenis={props[0]?.jenis ?? L.signature} frame={frame} />;
  const fx = EFFECTS[efek ?? ''] ?? (k.danger ? EFFECTS[L.efek] : undefined);
  const Scenery = L.Scenery;
  return (
    <>
      <Scenery frame={frame} night={night} />
      {!k.detail && <Person hero={hero} pose={heroPose ?? (k.danger ? 'panik' : L.hero.pose)} expr={heroExpr ?? (k.danger ? 'kaget' : 'fokus')}
        frame={frame} position={L.hero.p} rotationY={L.hero.ry} />}
      <PlacedProps props={props} anchors={L.anchors} frame={frame} />
      {fx && fx({frame, at: L.work})}
    </>
  );
};

export const profesi: World = {shots, View};
