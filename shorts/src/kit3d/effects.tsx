import {useLayoutEffect, useRef} from 'react';
import * as THREE from 'three';
import {Mat, Sparks, V3, rand} from './core';

// Effects a scene can switch on at a point (a wok, an engine, a panel): fire, smoke, sparks, water, an alarm light.
// All deterministic: every particle's life is a function of the frame and its index.

type FX = React.FC<{frame: number; at: V3}>;

// Instanced particles: pos(i, age 0..1) and size(i, age) decide each one; age loops over `life` frames.
const Particles: React.FC<{n: number; life: number; frame: number; at: V3; color: string; opacity?: number; basic?: boolean;
  pos: (i: number, a: number) => V3; size: (i: number, a: number) => number}> = ({n, life, frame, at, color, opacity = 1, basic, pos, size}) => {
  const ref = useRef<THREE.InstancedMesh>(null);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    for (let i = 0; i < n; i++) {
      const a = ((frame + i * (life / n) * 3.7) % life) / life;
      const p = pos(i, a), s = size(i, a);
      m.makeScale(s, s, s);
      m.setPosition(at[0] + p[0], at[1] + p[1], at[2] + p[2]);
      ref.current!.setMatrixAt(i, m);
    }
    ref.current!.instanceMatrix.needsUpdate = true;
  }, [frame, at, n, life, pos, size]);
  return (
    <instancedMesh ref={ref} args={[undefined, undefined, n]}>
      <icosahedronGeometry args={[1, 1]} />
      {basic ? <meshBasicMaterial color={color} toneMapped={false} transparent={opacity < 1} opacity={opacity} />
        : <meshStandardMaterial color={color} transparent={opacity < 1} opacity={opacity} roughness={1} depthWrite={false} />}
    </instancedMesh>
  );
};

const firePos = (i: number, a: number): V3 => [(rand(i) - 0.5) * 0.35 * (1 - a), a * (0.5 + rand(i + 5) * 0.4), (rand(i + 2) - 0.5) * 0.35 * (1 - a)];
const fireSize = (i: number, a: number) => 0.09 * (1 - a) * (0.7 + rand(i + 9) * 0.6);
const smokePos = (i: number, a: number): V3 => [(rand(i) - 0.5) * 0.4 + a * 0.3, 0.2 + a * 1.6, (rand(i + 3) - 0.5) * 0.3];
const smokeSize = (i: number, a: number) => 0.07 + a * 0.28 * (0.7 + rand(i + 1) * 0.6);
const waterPos = (i: number, a: number): V3 => {
  const k = a * 0.6, ang = rand(i) * Math.PI * 2, v = 1.2 + rand(i + 4);
  return [Math.cos(ang) * v * k, 0.1 + 2.4 * k - 4.9 * k * k, Math.sin(ang) * v * k];
};
const waterSize = (i: number, a: number) => 0.035 * (1 - a * 0.5);

export const EFFECTS: Record<string, FX> = {
  api: ({frame, at}) => (
    <group>
      <Particles n={90} life={14} frame={frame} at={at} color="#ffb020" basic pos={firePos} size={fireSize} />
      <Particles n={40} life={10} frame={frame + 3} at={at} color="#ff4a10" basic pos={firePos} size={(i, a) => fireSize(i, a) * 1.5} />
      <pointLight position={[at[0], at[1] + 0.5, at[2]]} intensity={14 + 5 * Math.sin(frame * 1.3) + 3 * Math.sin(frame * 3.1)} distance={8} color="#ff8a30" />
    </group>
  ),
  asap: ({frame, at}) => <Particles n={36} life={70} frame={frame} at={at} color="#8a8a8a" opacity={0.55} pos={smokePos} size={smokeSize} />,
  percikan: ({frame, at}) => <Sparks x={at[0]} y={at[1]} zs={[at[2] - 0.05, at[2] + 0.05]} offsets={[0]} frame={frame} on />,
  air: ({frame, at}) => (
    <group>
      <Particles n={120} life={18} frame={frame} at={at} color="#7fd0ff" basic pos={waterPos} size={waterSize} />
      <mesh position={[at[0], 0.02, at[2]]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.9, 24]} /><Mat c="#4aa3d8" m={0.3} r={0.1} /></mesh>
    </group>
  ),
  alarm: ({frame, at}) => {
    const on = Math.floor(frame / 6) % 2 === 0;
    return (
      <group position={[at[0], at[1] + 0.9, at[2]]}>
        <mesh><cylinderGeometry args={[0.12, 0.14, 0.2, 16]} /><Mat c="#400" e="#ff1a1a" ei={on ? 10 : 0.4} /></mesh>
        <pointLight intensity={on ? 30 : 2} distance={12} color="#ff2020" />
      </group>
    );
  },
};
