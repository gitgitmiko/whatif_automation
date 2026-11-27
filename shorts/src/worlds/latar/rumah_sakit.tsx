import {Box, Mat, V3} from '../../kit3d/core';
import {Person} from '../../kit3d/person';
import type {Latar} from './types';

// An emergency room bay, built as an open stage: pale walls on three sides, a bed with a patient, a heart monitor
// whose trace runs across the screen, an IV pole, a crash cart, a curtain rail and cold ceiling light. You stand at
// the bedside facing the room's open side (+Z), the patient on your left.

const CHEST: V3 = [-1.0, 1.05, -0.8];

const Monitor: React.FC<{frame: number}> = ({frame}) => {
  const x = ((frame * 0.03) % 1) * 0.8 - 0.4;
  const spike = (frame % 25) < 3;  // a heartbeat
  return (
    <group position={[-2.2, 1.7, -0.6]} rotation={[0, 0.7, 0]}>
      <Box p={[0, 0, 0]} s={[0.95, 0.65, 0.12]} c="#2b2f36" />
      <Box p={[0, 0, 0.065]} s={[0.85, 0.52, 0.01]} c="#05140c" e="#0a2a18" ei={0.6} shadow={false} />
      <Box p={[0, -0.05, 0.075]} s={[0.8, 0.012, 0.005]} c="#1a4a2a" shadow={false} />
      <mesh position={[x, spike ? 0.08 : -0.05, 0.08]}><sphereGeometry args={[0.025, 8, 6]} /><meshBasicMaterial color="#30ff70" toneMapped={false} /></mesh>
      <Box p={[0.3, 0.18, 0.075]} s={[0.16, 0.08, 0.005]} c="#000" e="#30ff70" ei={2} shadow={false} />
      <mesh position={[0, -0.6, 0]}><cylinderGeometry args={[0.03, 0.03, 1.0, 8]} /><Mat c="#9aa0a6" m={0.6} /></mesh>
    </group>
  );
};

const Scenery: React.FC<{frame: number; night: boolean}> = ({frame, night}) => (
  <group>
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[200, 200]} /><Mat c="#9ea7ad" r={1} /></mesh>
    <Box p={[0, 0.01, -0.5]} s={[7, 0.02, 6]} c="#dfe7ea" r={0.6} shadow={false} />
    <Box p={[0, 1.6, -3.5]} s={[7, 3.2, 0.15]} c="#e8f1f2" r={0.9} />
    {[-3.5, 3.5].map((x) => <Box key={x} p={[x, 1.6, -0.5]} s={[0.15, 3.2, 6]} c="#dbe8ea" r={0.9} />)}
    <Box p={[0, 0.5, -3.42]} s={[7, 1.0, 0.02]} c="#7fb8c4" shadow={false} />
    {/* bed and patient */}
    <Box p={[-1.0, 0.55, -0.6]} s={[1.0, 0.12, 2.1]} c="#c9ccd2" m={0.5} />
    <Box p={[-1.0, 0.68, -0.6]} s={[0.92, 0.14, 2.0]} c="#f4f6f7" r={0.8} />
    {[[-1.45, 0.4], [-0.55, 0.4], [-1.45, -1.6], [-0.55, -1.6]].map(([x, z], i) => <Box key={i} p={[x, 0.27, z]} s={[0.05, 0.54, 0.05]} c="#9aa0a6" m={0.6} />)}
    <Box p={[-1.0, 0.82, -1.35]} s={[0.7, 0.12, 0.45]} c="#ffffff" r={0.8} />
    <group position={[-1.0, 0.8, 0.35]} rotation={[-Math.PI / 2, 0, 0]}><Person frame={frame + 5} expr="takut" hero={{seragam: '#9fd3e0', celana: '#9fd3e0'}} /></group>
    <Monitor frame={frame} />
    {/* IV pole and drip */}
    <mesh position={[-1.9, 1.0, 0.4]}><cylinderGeometry args={[0.02, 0.02, 2.0, 8]} /><Mat c="#c0c4c8" m={0.7} /></mesh>
    <Box p={[-1.9, 1.85, 0.4]} s={[0.18, 0.28, 0.06]} c="#e8f4ff" e="#cfe8ff" ei={0.2} r={0.2} />
    {/* crash cart */}
    <Box p={[1.6, 0.5, -2.6]} s={[0.8, 1.0, 0.55]} c="#d62020" r={0.5} />
    {[0.25, 0.55, 0.85].map((y) => <Box key={y} p={[1.6, y, -2.32]} s={[0.7, 0.02, 0.01]} c="#7a1010" shadow={false} />)}
    <Box p={[2.6, 1.2, -3.35]} s={[1.2, 0.8, 0.1]} c="#ffffff" e="#ffffff" ei={0.1} />
    {/* curtain rail and curtain */}
    <Box p={[0.3, 3.0, -0.5]} s={[0.04, 0.04, 6]} c="#9aa0a6" m={0.6} />
    <Box p={[0.3, 1.9, -2.0]} s={[0.03, 2.1, 2.6]} c="#8fc1cf" r={0.9} />
    <Box p={[0, 3.15, -1.0]} s={[2.0, 0.05, 0.4]} c="#fff" e="#f2fbff" ei={night ? 4 : 2} shadow={false} />
    <pointLight position={[0, 2.9, -0.6]} intensity={night ? 14 : 10} distance={9} color="#eef8ff" />
  </group>
);

export const rumah_sakit: Latar = {
  Scenery,
  hero: {p: [0.0, 0, 0.3], ry: -0.35, pose: 'memegang'},
  work: CHEST,
  wide: {cam: [3.0, 2.4, 4.6], at: [-0.5, 1.0, -0.6]},
  anchors: {
    lantai_kiri: {p: [-2.6, 0, 1.4], ry: 0.5},
    lantai_kanan: {p: [2.3, 0, 0.6], ry: -0.6},
    meja: {p: [1.6, 1.0, -2.6], s: 0.6},
  },
  efek: 'alarm',
  signature: 'panel_layar',
};
