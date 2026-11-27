import {Anchor, Box, Mat} from './core';
import {Person} from './person';

// Generic low-poly props a script may place on a shot's named anchors. Each stands on the ground at the origin, real
// size in metres, front towards +Z, long side along X. Keys are the names scripts use (and worlds.json lists).

export type PropSpec = {jenis: string; di: string};
type P = React.FC<{frame: number}>;

const Wheel: React.FC<{p: [number, number, number]; r: number; w?: number}> = ({p, r, w = 0.2}) => (
  <mesh position={p} rotation={[Math.PI / 2, 0, 0]} castShadow><cylinderGeometry args={[r, r, w, 16]} /><Mat c="#151515" /></mesh>
);

export const PROPS: Record<string, P> = {
  mobil: () => (
    <group>
      <Box p={[0, 0.75, 0]} s={[4.3, 0.85, 1.85]} c="#c2272d" m={0.3} r={0.35} />
      <Box p={[-0.2, 1.45, 0]} s={[2.3, 0.65, 1.7]} c="#1d2633" m={0.2} r={0.15} />
      {[[-1.4, 0.95], [1.4, 0.95], [-1.4, -0.95], [1.4, -0.95]].map(([x, z], i) => <Wheel key={i} p={[x, 0.36, z]} r={0.36} w={0.25} />)}
      {[0.75, -0.75].map((z) => <Box key={z} p={[-2.16, 0.95, z]} s={[0.05, 0.15, 0.3]} c="#530" e="#ffa000" ei={3} shadow={false} />)}
      {[0.65, -0.65].map((z) => <Box key={`h${z}`} p={[2.16, 0.85, z]} s={[0.05, 0.15, 0.35]} c="#fff" e="#fff6d0" ei={2} shadow={false} />)}
    </group>
  ),
  motor: () => (
    <group>
      <Wheel p={[0.65, 0.28, 0]} r={0.28} w={0.12} />
      <Wheel p={[-0.6, 0.28, 0]} r={0.28} w={0.12} />
      <Box p={[-0.15, 0.5, 0]} s={[1.0, 0.35, 0.38]} c="#e8e8e8" m={0.2} r={0.4} />
      <Box p={[-0.3, 0.78, 0]} s={[0.65, 0.12, 0.32]} c="#1c1c1c" />
      <Box p={[0.55, 0.72, 0]} s={[0.18, 0.75, 0.3]} c="#2b6cb0" r={0.4} />
      <Box p={[0.58, 1.12, 0]} s={[0.06, 0.06, 0.7]} c="#222" m={0.6} />
      <Box p={[0.66, 0.95, 0]} s={[0.06, 0.14, 0.18]} c="#fff" e="#fff6d0" ei={2} shadow={false} />
    </group>
  ),
  truk: () => (
    <group>
      <Box p={[2.4, 1.45, 0]} s={[1.8, 2.0, 2.3]} c="#f2c214" r={0.4} />
      <Box p={[3.31, 1.85, 0]} s={[0.02, 0.8, 2.0]} c="#1d2633" r={0.1} />
      <Box p={[-0.9, 1.75, 0]} s={[4.6, 2.5, 2.4]} c="#3a7d44" r={0.6} />
      <Box p={[0.3, 0.55, 0]} s={[7.0, 0.3, 1.8]} c="#2a2a2a" />
      {[2.5, -0.4, -1.8].flatMap((x) => [1.05, -1.05].map((z) => <Wheel key={`${x}${z}`} p={[x, 0.48, z]} r={0.48} w={0.35} />))}
    </group>
  ),
  orang: ({frame}) => <Person frame={frame + 31} hero={{seragam: '#6c757d', celana: '#3b3b3b'}} />,
  kotak: () => <Box p={[0, 0.3, 0]} s={[0.6, 0.6, 0.6]} c="#b8864b" r={0.9} />,
  tabung_gas: () => (
    <group>
      <mesh position={[0, 0.2, 0]} castShadow><cylinderGeometry args={[0.16, 0.16, 0.36, 18]} /><Mat c="#3a9d3a" r={0.4} /></mesh>
      <mesh position={[0, 0.39, 0]}><sphereGeometry args={[0.16, 18, 8, 0, Math.PI * 2, 0, Math.PI / 2]} /><Mat c="#3a9d3a" r={0.4} /></mesh>
      <mesh position={[0, 0.58, 0]}><cylinderGeometry args={[0.04, 0.05, 0.08, 10]} /><Mat c="#c0c0c0" m={0.8} r={0.3} /></mesh>
    </group>
  ),
  pohon: () => (
    <group>
      <mesh position={[0, 1.5, 0]} castShadow><cylinderGeometry args={[0.15, 0.22, 3, 8]} /><Mat c="#6b4a2b" r={0.9} /></mesh>
      {[[0, 3.6, 0, 1.4], [0.8, 3.2, 0.3, 1.0], [-0.7, 3.3, -0.2, 1.0]].map(([x, y, z, r], i) => (
        <mesh key={i} position={[x, y, z]} castShadow><icosahedronGeometry args={[r, 0]} /><Mat c="#3f7d2c" r={0.9} /></mesh>
      ))}
    </group>
  ),
  rumah: () => (
    <group>
      <Box p={[0, 1.5, 0]} s={[5, 3, 4]} c="#f1e3c6" r={0.9} />
      <mesh position={[0, 4.0, 0]} rotation={[0, Math.PI / 4, 0]} castShadow><coneGeometry args={[3.9, 2, 4]} /><Mat c="#a8432a" r={0.8} /></mesh>
      <Box p={[0.9, 1.0, 2.01]} s={[0.9, 2.0, 0.05]} c="#6b4a2b" />
      <Box p={[-1.2, 1.7, 2.01]} s={[1.1, 0.9, 0.05]} c="#bcd7ea" e="#ffe2a0" ei={0.2} r={0.1} />
    </group>
  ),
  lampu_peringatan: ({frame}) => (
    <group>
      <mesh position={[0, 1.1, 0]} castShadow><cylinderGeometry args={[0.05, 0.05, 2.2, 8]} /><Mat c="#888" m={0.5} /></mesh>
      <mesh position={[0, 2.3, 0]}><sphereGeometry args={[0.16, 14, 10]} /><Mat c="#552" e="#ffb000" ei={Math.floor(frame / 8) % 2 ? 7 : 0.3} /></mesh>
    </group>
  ),
  tiang: () => (
    <group>
      <mesh position={[0, 4.5, 0]} castShadow><cylinderGeometry args={[0.14, 0.18, 9, 8]} /><Mat c="#7a5a3a" r={0.9} /></mesh>
      <Box p={[0, 8.3, 0]} s={[0.12, 0.12, 2.2]} c="#7a5a3a" />
    </group>
  ),
  panel_layar: ({frame}) => (
    <group>
      <Box p={[0, 0.6, 0]} s={[1.2, 1.2, 0.6]} c="#3a3f47" m={0.3} />
      <Box p={[0, 1.2, 0.05]} s={[1.1, 0.7, 0.5]} c="#2b2f36" rot={[-0.35, 0, 0]} />
      <Box p={[0, 1.28, 0.31]} s={[0.9, 0.45, 0.02]} rot={[-0.35, 0, 0]} c="#0b2033" e="#3fd0ff" ei={0.8 + 0.2 * Math.sin(frame * 0.3)} shadow={false} />
      {[-0.3, 0, 0.3].map((x, i) => <Box key={x} p={[x, 0.95, 0.31]} s={[0.12, 0.06, 0.04]} c="#222" e={['#ff3030', '#30ff60', '#ffd400'][i]} ei={1.5} shadow={false} />)}
    </group>
  ),
  kerucut_lalu_lintas: () => (
    <group>
      <Box p={[0, 0.02, 0]} s={[0.4, 0.04, 0.4]} c="#e2611d" />
      <mesh position={[0, 0.37, 0]} castShadow><coneGeometry args={[0.15, 0.7, 14]} /><Mat c="#ff6a1a" r={0.5} /></mesh>
      <mesh position={[0, 0.4, 0]}><cylinderGeometry args={[0.072, 0.092, 0.1, 14]} /><Mat c="#ffffff" /></mesh>
    </group>
  ),
  sapi: () => (
    <group>
      <Box p={[0, 1.05, 0]} s={[1.8, 0.85, 0.8]} c="#f4f1ea" r={0.8} />
      {[[0.3, 0.42], [-0.45, -0.42], [0.1, -0.42]].map(([x, z], i) => <Box key={i} p={[x, 1.15, z]} s={[0.5, 0.45, 0.02]} c="#1d1d1d" shadow={false} />)}
      <Box p={[1.05, 1.35, 0]} s={[0.55, 0.45, 0.45]} c="#f4f1ea" r={0.8} />
      <Box p={[1.36, 1.25, 0]} s={[0.1, 0.25, 0.35]} c="#e8a5a5" />
      {[0.17, -0.17].map((z) => <Box key={z} p={[1.0, 1.65, z]} s={[0.06, 0.18, 0.06]} c="#d8cfb8" />)}
      {[[0.7, 0.28], [0.7, -0.28], [-0.7, 0.28], [-0.7, -0.28]].map(([x, z], i) => <Box key={`l${i}`} p={[x, 0.32, z]} s={[0.16, 0.64, 0.16]} c="#e8e4da" />)}
    </group>
  ),
  gerobak: () => (
    <group>
      <Box p={[0, 0.85, 0]} s={[1.6, 0.8, 0.8]} c="#2b6cb0" r={0.5} />
      <Box p={[0, 1.5, 0]} s={[1.5, 0.5, 0.7]} c="#cfe8f5" e="#fff1c0" ei={0.15} r={0.1} />
      {[[-0.75, 0.38], [0.75, 0.38], [-0.75, -0.38], [0.75, -0.38]].map(([x, z], i) => <Box key={i} p={[x, 1.9, z]} s={[0.04, 0.8, 0.04]} c="#888" m={0.5} />)}
      <Box p={[0, 2.32, 0]} s={[1.8, 0.06, 1.0]} c="#d62020" />
      <Wheel p={[0.3, 0.32, 0.45]} r={0.32} w={0.06} />
      <Wheel p={[0.3, 0.32, -0.45]} r={0.32} w={0.06} />
    </group>
  ),
  koper: () => (
    <group>
      <Box p={[0, 0.38, 0]} s={[0.42, 0.62, 0.25]} c="#7b2d26" r={0.5} />
      <Box p={[0, 0.85, 0]} s={[0.25, 0.03, 0.03]} c="#222" />
      {[0.12, -0.12].map((x) => <Box key={x} p={[x, 0.76, 0]} s={[0.025, 0.18, 0.025]} c="#222" />)}
    </group>
  ),
};

// The script's props on this shot's anchors: unknown names and missing anchors are skipped, one prop per anchor, at most 3.
export const PlacedProps: React.FC<{props?: PropSpec[]; anchors: Record<string, Anchor>; frame: number}> = ({props = [], anchors, frame}) => {
  const used = new Set<string>();
  const keep = props.filter((x) => PROPS[x.jenis] && anchors[x.di] && !used.has(x.di) && used.add(x.di)).slice(0, 3);
  return (
    <>
      {keep.map((x) => {
        const a = anchors[x.di], Prop = PROPS[x.jenis];
        return <group key={x.di} position={a.p} rotation={[0, a.ry ?? 0, 0]} scale={a.s ?? 1}><Prop frame={frame} /></group>;
      })}
    </>
  );
};
