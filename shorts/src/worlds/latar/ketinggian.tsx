import {useMemo} from 'react';
import {Box, Mat, Many, V3, rand} from '../../kit3d/core';
import type {Latar} from './types';

// High up a telecom tower: a lattice mast rising from a town far below, a small railed platform at 40 m with an
// antenna box, a red aviation light on top, wind. You stand on the platform, clipped to the mast, facing out (+Z).

const H = 40;  // platform height
const BOX: V3 = [0.65, H + 1.2, -0.25];

const Scenery: React.FC<{frame: number; night: boolean}> = ({frame, night}) => {
  const town = useMemo(() => Array.from({length: 160}, (_, i) => {
    const a = rand(i) * Math.PI * 2, r = 25 + rand(i + 1) * 140, h = 4 + rand(i + 2) * 12;
    return {p: [Math.cos(a) * r, h / 2, Math.sin(a) * r] as V3, s: [6 + rand(i + 3) * 6, h, 6 + rand(i + 4) * 6] as V3};
  }), []);
  const trees = useMemo(() => Array.from({length: 120}, (_, i) => ({p: [(rand(i + 9) - 0.5) * 300, 3, (rand(i + 11) - 0.5) * 300] as V3})), []);
  // lattice: four legs and cross braces every 4 m
  const braces = useMemo(() => Array.from({length: 13}, (_, i) => i * 4), []);
  const sway = Math.sin(frame * 0.05) * 0.02;
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[800, 800]} /><Mat c="#6d8f3f" r={1} /></mesh>
      <Many at={town}><boxGeometry args={[1, 1, 1]} /><Mat c="#e2d6c0" r={0.9} /></Many>
      <Many at={trees}><icosahedronGeometry args={[3, 0]} /><Mat c="#3f7d2c" r={0.9} /></Many>
      <group rotation={[sway, 0, sway * 0.5]}>
        {[[-0.8, -0.8], [0.8, -0.8], [-0.8, -2.4], [0.8, -2.4]].map(([x, z], i) => (
          <Box key={i} p={[x, (H + 6) / 2, z]} s={[0.12, H + 6, 0.12]} c="#c9ccd2" m={0.6} r={0.4} />
        ))}
        {braces.map((y) => (
          <group key={y}>
            <Box p={[0, y + 2, -0.8]} s={[1.6, 0.06, 0.06]} c="#c9ccd2" m={0.6} rot={[0, 0, (y / 4) % 2 ? 0.45 : -0.45]} />
            <Box p={[0, y + 2, -2.4]} s={[1.6, 0.06, 0.06]} c="#c9ccd2" m={0.6} rot={[0, 0, (y / 4) % 2 ? -0.45 : 0.45]} />
            <Box p={[-0.8, y + 2, -1.6]} s={[0.06, 0.06, 1.6]} c="#c9ccd2" m={0.6} />
            <Box p={[0.8, y + 2, -1.6]} s={[0.06, 0.06, 1.6]} c="#c9ccd2" m={0.6} />
          </group>
        ))}
        {/* platform with railing */}
        <Box p={[0, H - 0.05, -0.6]} s={[2.4, 0.1, 2.2]} c="#8d9298" m={0.5} />
        {[[0, 0.5], [-1.2, -0.6], [1.2, -0.6]].map(([x, z], i) => (
          <Box key={`r${i}`} p={[x, H + 0.55, z]} s={i ? [0.05, 0.05, 2.2] : [2.4, 0.05, 0.05]} c="#f2c214" />
        ))}
        {[-1.2, 0, 1.2].map((x) => <Box key={`p${x}`} p={[x, H + 0.28, 0.5]} s={[0.05, 0.56, 0.05]} c="#f2c214" />)}
        <Box p={BOX} s={[0.5, 0.7, 0.3]} c="#e6e8ea" />
        {[-0.6, 0.6].map((x) => <Box key={`a${x}`} p={[x, H + 3.4, -1.6]} s={[0.35, 1.8, 0.15]} c="#f4f4f4" />)}
        <mesh position={[0, H + 6.1, -1.6]}><sphereGeometry args={[0.15, 12, 8]} /><Mat c="#400" e="#ff2020" ei={Math.floor(frame / 20) % 2 ? 8 : 0.5} /></mesh>
        {/* safety line from your harness to the mast */}
        <mesh position={[0.1, H + 1.1, -0.55]} rotation={[0.9, 0, 0]}><cylinderGeometry args={[0.012, 0.012, 0.6, 6]} /><Mat c="#ff6a1a" /></mesh>
      </group>
      {night && <pointLight position={[0.5, H + 2.5, 1]} intensity={6} distance={6} color="#fff2d8" />}
    </group>
  );
};

export const ketinggian: Latar = {
  Scenery,
  hero: {p: [0.0, H, -0.1], ry: 0, pose: 'memegang'},
  work: BOX,
  wide: {cam: [5.5, H + 2.2, 7.0], at: [0, H + 0.6, -0.8]},
  anchors: {
    platform: {p: [-0.75, H, 0.1], s: 0.8},
  },
  efek: 'percikan',
  signature: 'lampu_peringatan',
};
