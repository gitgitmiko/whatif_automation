import {useMemo} from 'react';
import {Box, Mat, Many, V3, rand} from '../../kit3d/core';
import {Person} from '../../kit3d/person';
import type {Latar} from './types';

// An airliner cockpit cut open as a stage: the nose shell, a glass windscreen, a dashboard of glowing screens, two
// yokes, a centre console with throttles, the captain's seat (yours, left) and the first officer beside you. Clouds
// stream past below. You sit facing forward (+Z).

const PANEL: V3 = [-0.3, 1.05, 0.75];

const Clouds: React.FC<{frame: number}> = ({frame}) => {
  const puffs = useMemo(() => Array.from({length: 70}, (_, i) => ({x: (rand(i) - 0.5) * 120, y: -6 - rand(i + 1) * 10, z0: rand(i + 2) * 200, s: 3 + rand(i + 3) * 5})), []);
  const at = puffs.map((c) => ({p: [c.x, c.y, 120 - ((c.z0 + frame * 1.2) % 200)] as V3, s: [c.s * 1.6, c.s * 0.6, c.s] as V3}));
  return <Many at={at}><icosahedronGeometry args={[1, 1]} /><Mat c="#ffffff" r={1} /></Many>;
};

const Scenery: React.FC<{frame: number; night: boolean}> = ({frame, night}) => {
  const screens = [[-0.75, 1.2], [-0.25, 1.2], [0.25, 1.2], [0.75, 1.2]];
  return (
    <group>
      <Clouds frame={frame} />
      {/* floor, side walls, roof of the nose */}
      <Box p={[0, 0.1, -0.2]} s={[2.6, 0.2, 3.4]} c="#3a3f47" />
      {[-1.35, 1.35].map((x) => <Box key={x} p={[x, 1.2, -0.6]} s={[0.1, 2.2, 2.6]} c="#d8dade" r={0.8} />)}
      <Box p={[0, 2.35, -0.4]} s={[2.8, 0.12, 3.0]} c="#c9ccd2" r={0.8} />
      <Box p={[0, 2.15, 0.85]} s={[2.4, 0.15, 0.5]} c="#2b2f36" rot={[0.5, 0, 0]} />
      {/* windscreen glass and frames */}
      <mesh position={[0, 1.7, 1.15]} rotation={[0.35, 0, 0]}><planeGeometry args={[2.5, 1.0]} /><meshStandardMaterial color="#a8d8ff" transparent opacity={0.15} side={2} roughness={0.05} /></mesh>
      {[-1.2, 0, 1.2].map((x) => <Box key={`f${x}`} p={[x, 1.7, 1.15]} s={[0.07, 1.0, 0.07]} c="#2b2f36" rot={[0.35, 0, 0]} />)}
      {/* dashboard with screens */}
      <Box p={[0, 0.95, 0.85]} s={[2.4, 0.55, 0.5]} c="#2b2f36" />
      {screens.map(([x, y], i) => (
        <Box key={i} p={[x, y, 0.62]} s={[0.4, 0.3, 0.02]} c="#06101c" e={['#30a0ff', '#20c060', '#30a0ff', '#ffb020'][i]} ei={0.6 + 0.2 * Math.sin(frame * 0.08 + i)} shadow={false} />
      ))}
      <mesh position={[0, 1.38, 0.62]}><boxGeometry args={[0.5, 0.08, 0.04]} /><Mat c="#300" e="#ff2020" ei={Math.floor(frame / 12) % 2 ? 0.2 : 1.5} /></mesh>
      {/* yokes and throttles */}
      {[-0.45, 0.45].map((x) => (
        <group key={`y${x}`} position={[x, 0.8, 0.48]}>
          <mesh rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.03, 0.03, 0.35, 8]} /><Mat c="#222" /></mesh>
          <Box p={[0, 0.08, -0.18]} s={[0.32, 0.05, 0.05]} c="#222" />
        </group>
      ))}
      <Box p={[0, 0.55, 0.15]} s={[0.4, 0.5, 0.7]} c="#3a3f47" />
      {[-0.08, 0.08].map((x) => <Box key={`t${x}`} p={[x, 0.88, 0.2]} s={[0.05, 0.18, 0.05]} c="#c0c4c8" m={0.6} />)}
      {/* seats */}
      {[-0.45, 0.45].map((x) => (
        <group key={`s${x}`}>
          <Box p={[x, 0.5, -0.35]} s={[0.55, 0.12, 0.55]} c="#2a3a5a" />
          <Box p={[x, 0.95, -0.65]} s={[0.55, 0.9, 0.12]} c="#2a3a5a" />
        </group>
      ))}
      <Person frame={frame + 19} pose="duduk" expr="fokus" hero={{seragam: '#f2f2ef', celana: '#1d2b4a', topi: 'masinis'}} position={[0.45, 0.25, -0.3]} />
      <pointLight position={[0, 2.0, 0]} intensity={night ? 5 : 4} distance={5} color="#dfe9ff" />
    </group>
  );
};

export const kokpit: Latar = {
  Scenery,
  hero: {p: [-0.45, 0.25, -0.3], ry: 0, pose: 'duduk', eye: 1.22},
  work: PANEL,
  wide: {cam: [1.1, 1.9, -2.2], at: [-0.1, 1.2, 0.6]},
  anchors: {
    kursi_kanan: {p: [1.0, 0.2, -1.2], ry: 0.4, s: 0.8},
  },
  efek: 'alarm',
  signature: 'panel_layar',
  sky: '#7fb8e8',
  cams: {bahaya: {cam: [0.3, 1.75, 0.8], at: [-0.45, 1.45, -0.3]}},  // between the seats, looking back at you
};
