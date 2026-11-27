import {Box, Mat, V3} from '../../kit3d/core';
import type {Latar} from './types';

// A control room (CCTV, air traffic, dam, power grid): a wall of screens behind you, a desk with monitors and a
// keyboard, a chair you sit on facing the room's open side (+Z), a red phone and a warning lamp.

const SCREEN: V3 = [0.55, 1.15, 0.55];  // the monitor you watch, on your right

const Screen: React.FC<{p: V3; ry?: number; w: number; h: number; i: number; frame: number}> = ({p, ry = 0, w, h, i, frame}) => {
  const hue = ['#2a8cff', '#20c060', '#ffb020', '#30d0ff', '#ff5050'][i % 5];
  const pulse = 0.5 + 0.35 * Math.sin(frame * 0.07 + i * 1.3);
  return (
    <group position={p} rotation={[0, ry, 0]}>
      <Box p={[0, 0, 0]} s={[w + 0.06, h + 0.06, 0.06]} c="#1c1f24" />
      <Box p={[0, 0, 0.032]} s={[w, h, 0.005]} c="#06101c" e={hue} ei={pulse} shadow={false} />
      <Box p={[-w * 0.2, h * 0.15, 0.036]} s={[w * 0.45, h * 0.08, 0.004]} c="#000" e="#ffffff" ei={0.8} shadow={false} />
    </group>
  );
};

const Scenery: React.FC<{frame: number; night: boolean}> = ({frame, night}) => (
  <group>
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[200, 200]} /><Mat c="#5a6068" r={1} /></mesh>
    <Box p={[0, 0.01, -0.5]} s={[7, 0.02, 6]} c="#3d434b" r={0.8} shadow={false} />
    <Box p={[0, 1.7, -2.6]} s={[7, 3.4, 0.15]} c="#2a2f36" r={0.9} />
    {[-3.5, 3.5].map((x) => <Box key={x} p={[x, 1.7, -0.5]} s={[0.15, 3.4, 4.4]} c="#30363e" r={0.9} />)}
    {/* the video wall behind you */}
    {Array.from({length: 12}, (_, i) => <Screen key={i} p={[-1.65 + (i % 4) * 1.1, 1.3 + Math.floor(i / 4) * 0.68, -2.5]} w={1.0} h={0.6} i={i} frame={frame} />)}
    {/* desk, monitors, keyboard, phone */}
    <Box p={[0.1, 0.74, 0.45]} s={[2.2, 0.05, 0.75]} c="#8a9097" m={0.3} />
    {[-0.9, 1.1].map((x) => <Box key={x} p={[x, 0.37, 0.45]} s={[0.05, 0.74, 0.7]} c="#5a6068" />)}
    <Screen p={SCREEN} ry={Math.PI - 0.5} w={0.55} h={0.34} i={7} frame={frame} />
    <Screen p={[-0.45, 1.12, 0.6]} ry={Math.PI + 0.5} w={0.55} h={0.34} i={3} frame={frame} />
    <Box p={[0.0, 0.78, 0.35]} s={[0.5, 0.02, 0.16]} c="#1c1f24" />
    <Box p={[0.9, 0.8, 0.25]} s={[0.22, 0.08, 0.16]} c="#c41f1f" />
    <mesh position={[-0.95, 1.2, 0.2]}><cylinderGeometry args={[0.07, 0.08, 0.14, 12]} /><Mat c="#300" e="#ff2020" ei={Math.floor(frame / 15) % 2 ? 0.2 : 2} /></mesh>
    {/* chair */}
    <Box p={[0.0, 0.48, -0.25]} s={[0.55, 0.08, 0.55]} c="#1c1f24" />
    <Box p={[0.0, 0.85, -0.52]} s={[0.55, 0.7, 0.08]} c="#1c1f24" />
    <mesh position={[0.0, 0.24, -0.25]}><cylinderGeometry args={[0.04, 0.04, 0.48, 8]} /><Mat c="#555" m={0.6} /></mesh>
    <Box p={[0, 3.3, -0.6]} s={[2.4, 0.05, 0.3]} c="#fff" e="#e8f2ff" ei={night ? 3 : 1.2} shadow={false} />
    <pointLight position={[0, 3.0, 0.2]} intensity={night ? 8 : 6} distance={8} color="#dfe9ff" />
  </group>
);

export const kantor: Latar = {
  Scenery,
  hero: {p: [0.0, 0.22, -0.3], ry: 0, pose: 'duduk', eye: 1.22},
  work: SCREEN,
  wide: {cam: [2.8, 2.2, 4.4], at: [-0.1, 1.2, -0.6]},
  anchors: {
    meja: {p: [-0.6, 0.77, 0.3], s: 0.5},
    lantai_kiri: {p: [-2.4, 0, 0.9], ry: 0.5},
    lantai_kanan: {p: [2.4, 0, 0.9], ry: -0.5},
  },
  efek: 'alarm',
  signature: 'panel_layar',
};
