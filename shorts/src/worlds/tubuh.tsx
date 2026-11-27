import {useLayoutEffect, useRef} from 'react';
import * as THREE from 'three';
import {Look, Mat, V3, rand} from '../kit3d/core';
import type {ShotCtx, World, WorldViewProps} from './index';

// Inside the human body: stylised organs on a dark stage, each alive (a beating heart, breathing lungs, bubbling
// stomach acid, stones sliding down from the kidneys, sparks in the brain), a fly-through of a blood vessel, and a
// see-through body showing where each organ sits. One organ per shot, always at the origin.

const SKY = '#2a0c14';
const beat = (f: number) => Math.max(0, Math.sin(f * 0.25)) ** 4;  // about 72 beats a minute at 30 fps

// Small instanced dots moving along a path: p(i, a) with a in 0..1 looping over `life` frames.
const Flow: React.FC<{n: number; life: number; frame: number; color: string; r: number; glow?: boolean; p: (i: number, a: number) => V3}> =
  ({n, life, frame, color, r, glow, p}) => {
    const ref = useRef<THREE.InstancedMesh>(null);
    useLayoutEffect(() => {
      const m = new THREE.Matrix4();
      for (let i = 0; i < n; i++) {
        const a = ((frame + i * (life / n)) % life) / life, q = p(i, a);
        m.makeScale(r, r, r);
        m.setPosition(q[0], q[1], q[2]);
        ref.current!.setMatrixAt(i, m);
      }
      ref.current!.instanceMatrix.needsUpdate = true;
    }, [frame, n, life, r, p]);
    return (
      <instancedMesh ref={ref} args={[undefined, undefined, n]}>
        <sphereGeometry args={[1, 10, 8]} />
        {glow ? <meshBasicMaterial color={color} toneMapped={false} /> : <meshStandardMaterial color={color} roughness={0.5} />}
      </instancedMesh>
    );
  };

const Tube: React.FC<{from: V3; to: V3; r: number; c: string}> = ({from, to, r, c}) => {
  const a = new THREE.Vector3(...from), b = new THREE.Vector3(...to), mid = a.clone().add(b).multiplyScalar(0.5);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
  return <mesh position={mid} quaternion={q} castShadow><cylinderGeometry args={[r, r, a.distanceTo(b), 14]} /><Mat c={c} r={0.5} /></mesh>;
};

const aortaPath = (_: number, a: number): V3 => {
  const t = Math.PI * a;  // up the front, over the arch, down the back
  return [Math.cos(t) * 0.38 - 0.05, 0.75 + Math.sin(t) * 0.38, 0];
};

export const Heart: React.FC<{frame: number}> = ({frame}) => {
  const s = 1 + 0.09 * beat(frame);
  return (
    <group>
      <group scale={[s, s * 0.97, s]}>
        <mesh castShadow scale={[1, 1.1, 0.85]}><sphereGeometry args={[0.62, 28, 20]} /><Mat c="#c0392b" r={0.45} /></mesh>
        <mesh position={[0.08, -0.62, 0]} rotation={[0, 0, 0.25]} castShadow><coneGeometry args={[0.45, 0.75, 24]} /><Mat c="#b03024" r={0.45} /></mesh>
        <mesh position={[-0.28, 0.35, 0.42]} scale={[1, 1.1, 0.6]}><sphereGeometry args={[0.24, 16, 12]} /><Mat c="#d24a3c" r={0.45} /></mesh>
      </group>
      <mesh position={[-0.05, 0.75, 0]} rotation={[0, 0, 0]}><torusGeometry args={[0.38, 0.12, 12, 24, Math.PI]} /><Mat c="#e0473a" r={0.4} /></mesh>
      <Tube from={[0.33, 0.75, 0]} to={[0.33, -0.1, -0.1]} r={0.12} c="#e0473a" />
      <Tube from={[-0.25, 0.5, 0.25]} to={[-0.55, 1.15, 0.3]} r={0.11} c="#3b6fd1" />
      <Tube from={[0.25, 0.4, -0.3]} to={[0.75, 0.95, -0.4]} r={0.09} c="#3b6fd1" />
      {[-0.2, 0, 0.2].map((x) => <Tube key={x} from={[x - 0.05, 1.08, 0]} to={[x * 1.6 - 0.05, 1.5, 0]} r={0.05} c="#e0473a" />)}
      <Flow n={26} life={30} frame={frame} color="#ff2a2a" r={0.045} p={aortaPath} />
    </group>
  );
};

export const Lungs: React.FC<{frame: number}> = ({frame}) => {
  const s = 1 + 0.07 * Math.sin(frame * 0.1);
  return (
    <group>
      {[-1, 1].map((side) => (
        <group key={side} position={[side * 0.62, -0.2, 0]} scale={[s, s * 1.02, s]}>
          <mesh castShadow scale={[0.5, 1.0, 0.42]}><sphereGeometry args={[1, 24, 18]} /><Mat c="#e8909a" r={0.7} /></mesh>
          {[0.35, -0.05, -0.45].map((y) => <mesh key={y} position={[-side * 0.12, y, 0.4]} rotation={[0, 0, side * 0.5]}><torusGeometry args={[0.18, 0.02, 6, 12, Math.PI]} /><Mat c="#cf7280" /></mesh>)}
        </group>
      ))}
      <Tube from={[0, 1.55, 0]} to={[0, 0.7, 0]} r={0.09} c="#e8d0d4" />
      <Tube from={[0, 0.72, 0]} to={[-0.45, 0.3, 0]} r={0.07} c="#e8d0d4" />
      <Tube from={[0, 0.72, 0]} to={[0.45, 0.3, 0]} r={0.07} c="#e8d0d4" />
      <Flow n={30} life={40} frame={frame} color="#bfe9ff" r={0.035} glow p={(i, a) => {
        const side = i % 2 ? 1 : -1;
        return a < 0.5 ? [0, 1.55 - a * 1.7, 0] : [side * (a - 0.5) * 0.9, 0.7 - (a - 0.5) * 0.85, 0];
      }} />
    </group>
  );
};

export const Stomach: React.FC<{frame: number}> = ({frame}) => (
  <group rotation={[0, 0, -0.35]}>
    <mesh castShadow rotation={[0, 0, 0.6]}>
      <torusGeometry args={[0.62, 0.36, 18, 32, Math.PI * 1.25]} />
      <meshStandardMaterial color="#e59a8c" roughness={0.6} transparent opacity={0.55} depthWrite={false} side={2} />
    </mesh>
    <Tube from={[-0.35, 1.45, 0]} to={[-0.45, 0.65, 0]} r={0.12} c="#d98a7c" />
    <Flow n={60} life={60} frame={frame} color="#c8e04a" r={0.04} glow p={(i, a) => {
      const t = rand(i) * Math.PI * 1.1 + 0.4, R = 0.62 + (rand(i + 7) - 0.5) * 0.35;
      return [Math.cos(t) * R, -Math.abs(Math.sin(t)) * R * 0.5 + a * 0.35 - 0.15, (rand(i + 3) - 0.5) * 0.4];
    }} />
    <mesh position={[0.15, -0.35, 0]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.55, 24]} /><meshStandardMaterial color="#b6d33a" transparent opacity={0.6} /></mesh>
  </group>
);

export const Kidneys: React.FC<{frame: number}> = ({frame}) => (
  <group>
    <Tube from={[-0.15, 1.6, -0.2]} to={[-0.15, -1.5, -0.2]} r={0.11} c="#e0473a" />
    <Tube from={[0.15, 1.6, -0.2]} to={[0.15, -1.5, -0.2]} r={0.12} c="#3b6fd1" />
    {[-1, 1].map((side) => (
      <group key={side}>
        <group position={[side * 0.85, 0.35, 0]} rotation={[0, 0, side * 0.25]}>
          <mesh castShadow scale={[0.36, 0.62, 0.26]}><sphereGeometry args={[1, 24, 18]} /><Mat c="#8e3b46" r={0.55} /></mesh>
          <mesh position={[-side * 0.3, 0, 0.05]} scale={[0.12, 0.2, 0.15]}><sphereGeometry args={[1, 12, 10]} /><Mat c="#f0d9c4" /></mesh>
        </group>
        <Tube from={[side * 0.55, 0.35, -0.05]} to={[side * 0.15, 0.4, -0.2]} r={0.05} c="#e0473a" />
        <Tube from={[side * 0.55, 0.25, 0]} to={[side * 0.2, -1.45, 0.25]} r={0.035} c="#f0d9c4" />
      </group>
    ))}
    <mesh position={[0, -1.6, 0.3]} scale={[0.4, 0.32, 0.32]}><sphereGeometry args={[1, 20, 14]} /><Mat c="#e8b49c" r={0.6} /></mesh>
    <Flow n={8} life={90} frame={frame} color="#d8c98a" r={0.05} p={(i, a) => {
      const side = i % 2 ? 1 : -1;
      return [side * (0.55 - a * 0.35), 0.25 - a * 1.7, a * 0.25];
    }} />
  </group>
);

export const Brain: React.FC<{frame: number}> = ({frame}) => (
  <group>
    {[-1, 1].map((side) => (
      <mesh key={side} position={[side * 0.42, 0.1, 0]} scale={[0.5, 0.62, 0.95]} castShadow>
        <icosahedronGeometry args={[1, 2]} /><Mat c="#f1a7b5" r={0.75} />
      </mesh>
    ))}
    <mesh position={[0, -0.45, -0.55]} scale={[0.55, 0.32, 0.4]}><icosahedronGeometry args={[1, 2]} /><Mat c="#e391a1" r={0.75} /></mesh>
    <Tube from={[0, -0.45, -0.2]} to={[0, -1.6, -0.25]} r={0.12} c="#e8b0b8" />
    <Flow n={40} life={20} frame={frame} color="#7fe3ff" r={0.035} glow p={(i, a) => {
      const th = rand(i) * Math.PI * 2, ph = rand(i + 4) * Math.PI, side = i % 2 ? 1 : -1;
      const k = a < 0.5 ? 1 : 0;  // each spark lives half its loop
      return [side * 0.42 + Math.sin(ph) * Math.cos(th) * 0.52 * k, 0.1 + Math.cos(ph) * 0.64 * k, Math.sin(ph) * Math.sin(th) * 0.97 * k - (1 - k) * 50];
    }} />
  </group>
);

// Flying down a blood vessel: a red tunnel and red cells streaming past the camera.
const Vessel: React.FC<{frame: number}> = ({frame}) => {
  const ref = useRef<THREE.InstancedMesh>(null);
  const N = 70;
  useLayoutEffect(() => {
    const m = new THREE.Matrix4(), q = new THREE.Quaternion();
    for (let i = 0; i < N; i++) {
      const z = 6 - ((i * 0.43 + frame * 0.09) % 30), a = rand(i) * Math.PI * 2, r = rand(i + 1) * 0.9;
      q.setFromEuler(new THREE.Euler(rand(i + 2) * 3, rand(i + 3) * 3, 0));
      m.compose(new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r, z), q, new THREE.Vector3(1, 1, 1));
      ref.current!.setMatrixAt(i, m);
    }
    ref.current!.instanceMatrix.needsUpdate = true;
  }, [frame]);
  return (
    <group>
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, -10]}><cylinderGeometry args={[1.4, 1.4, 40, 32, 1, true]} /><meshStandardMaterial color="#8a1420" side={1} roughness={0.8} /></mesh>
      <instancedMesh ref={ref} args={[undefined, undefined, N]}>
        <torusGeometry args={[0.13, 0.07, 8, 16]} /><meshStandardMaterial color="#d61f2c" roughness={0.4} />
      </instancedMesh>
      <pointLight position={[0, 0.5, 3]} intensity={12} distance={20} color="#ffb0a0" />
    </group>
  );
};

// A see-through body with the organs glowing in place.
const Body: React.FC<{frame: number}> = ({frame}) => {
  const glass = <meshStandardMaterial color="#6fc3ff" transparent opacity={0.18} depthWrite={false} roughness={0.2} />;
  return (
    <group>
      <mesh position={[0, 3.3, 0]}><sphereGeometry args={[0.45, 24, 18]} />{glass}</mesh>
      <mesh position={[0, 1.9, 0]}><capsuleGeometry args={[0.55, 1.1, 8, 16]} />{glass}</mesh>
      {[-1, 1].map((s) => <mesh key={s} position={[s * 0.85, 2.0, 0]} rotation={[0, 0, s * 0.12]}><capsuleGeometry args={[0.16, 1.2, 6, 10]} />{glass}</mesh>)}
      {[-1, 1].map((s) => <mesh key={`l${s}`} position={[s * 0.28, 0.4, 0]}><capsuleGeometry args={[0.2, 1.1, 6, 10]} />{glass}</mesh>)}
      <group position={[0, 3.32, 0]} scale={0.28}><Brain frame={frame} /></group>
      <group position={[0, 2.35, 0.05]} scale={0.42}><Lungs frame={frame} /></group>
      <group position={[0.1, 2.25, 0.18]} scale={0.22}><Heart frame={frame} /></group>
      <group position={[0.15, 1.6, 0.12]} scale={0.3}><Stomach frame={frame} /></group>
      <group position={[0, 1.35, -0.12]} scale={0.3}><Kidneys frame={frame} /></group>
    </group>
  );
};

type TLook = Look & {organ: string};
const orbit = (organ: string, t: number, T: number, r = 3.3, y = 0.4): TLook => {
  const u = Math.min(t / T, 1), a = -0.45 + 0.9 * u;
  return {organ, cam: [Math.sin(a) * r, y, Math.cos(a) * r], at: [0, 0, 0], fov: 45, sky: SKY, light: [40, 0, 0]};
};

export const shots: Record<string, (t: number, T: number, ctx: ShotCtx) => TLook> = {
  siluet: (t: number, T: number): TLook => {
    const u = Math.min(t / T, 1);
    return {organ: 'siluet', cam: [0.4, 3.0 - 1.1 * u, 5.2 - 1.4 * u], at: [0, 2.9 - 1.0 * u, 0], fov: 42, sky: SKY, light: [40, 0, 0]};
  },
  otak: (t: number, T: number): TLook => orbit('otak', t, T, 4.6, 0.7),
  jantung: (t: number, T: number): TLook => orbit('jantung', t, T, 4.2, 0.5),
  paru: (t: number, T: number): TLook => orbit('paru', t, T, 4.0, 0.4),
  lambung: (t: number, T: number): TLook => orbit('lambung', t, T, 3.4, 0.6),
  ginjal: (t: number, T: number): TLook => orbit('ginjal', t, T, 4.4, 0.2),
  pembuluh: (t: number, T: number): TLook => ({organ: 'pembuluh', cam: [0.15, 0.1, 4.5], at: [0, 0, -10], fov: 70, sky: SKY, shake: 0.02, light: [40, 0, 0]}),
};

const ORGANS: Record<string, React.FC<{frame: number}>> = {siluet: Body, otak: Brain, jantung: Heart, paru: Lungs, lambung: Stomach, ginjal: Kidneys, pembuluh: Vessel};

const View: React.FC<WorldViewProps> = ({look, frame}) => {
  const O = ORGANS[(look as TLook).organ] ?? Heart;
  return (
    <>
      <O frame={frame} />
      <pointLight position={[2.5, 2.5, 3]} intensity={20} distance={14} color="#ffd6dc" />
      <pointLight position={[-3, -1, 2]} intensity={8} distance={12} color="#ff6a80" />
    </>
  );
};

export const tubuh: World = {shots, View};
