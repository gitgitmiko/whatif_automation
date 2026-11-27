import {Box, Mat, V3} from '../../kit3d/core';
import {PROPS} from '../../kit3d/props';
import type {Latar} from './types';

// An open-front motorcycle workshop: concrete floor, back and side walls, a tin roof with a tube light, a tool board,
// shelves of oil, a stack of tyres, a compressor, and a scooter in the middle. You stand behind the scooter facing the
// street (+Z), hands on the engine.

const ENGINE: V3 = [0.05, 0.5, -1.0];

const Scenery: React.FC<{frame: number; night: boolean}> = ({frame, night}) => {
  const Motor = PROPS.motor, Tyre = PROPS.ban, Oil = PROPS.botol_oli, Can = PROPS.jerigen, House = PROPS.rumah;
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[200, 200]} /><Mat c="#7a7a72" r={1} /></mesh>
      <Box p={[0, 0.01, 4.2]} s={[200, 0.02, 5]} c="#3b3b3f" r={0.95} shadow={false} />
      <Box p={[0, 0.03, -1.5]} s={[8, 0.06, 6]} c="#a3a39b" r={0.9} />
      {[-0.5, 1.6].map((z) => <Box key={z} p={[0, 0.065, z]} s={[8, 0.005, 0.03]} c="#6f6f68" shadow={false} />)}
      {/* walls and roof */}
      <Box p={[0, 1.75, -4.4]} s={[8, 3.5, 0.2]} c="#d9cfb8" r={0.9} />
      {[-4, 4].map((x) => <Box key={x} p={[x, 1.75, -1.7]} s={[0.2, 3.5, 5.6]} c="#cfc4ab" r={0.9} />)}
      <Box p={[0, 3.6, -1.5]} s={[8.6, 0.08, 6.4]} c="#9aa3ab" m={0.5} r={0.5} />
      <Box p={[0, 3.45, -1.4]} s={[1.4, 0.06, 0.12]} c="#fff" e="#f4fbff" ei={night ? 4 : 2} shadow={false} />
      <pointLight position={[0, 3.2, -1.2]} intensity={night ? 14 : 9} distance={9} color="#f2f8ff" />
      <Box p={[0, 2.9, 0.0]} s={[3.2, 0.5, 0.05]} c="#d62020" />
      {/* tool board with wrenches */}
      <Box p={[-1.9, 1.8, -4.28]} s={[2.6, 1.2, 0.04]} c="#5b6770" />
      {Array.from({length: 9}, (_, i) => (
        <Box key={i} p={[-3.0 + i * 0.27, 1.8 + (i % 2) * 0.1, -4.24]} s={[0.05, 0.45 + (i % 3) * 0.1, 0.02]} c="#d8dadd" m={0.8} r={0.3} shadow={false} />
      ))}
      {/* shelves of oil on the right wall */}
      {[0.9, 1.5].map((y) => <Box key={y} p={[3.65, y, -2.2]} s={[0.5, 0.04, 2.4]} c="#7a5a3a" />)}
      {Array.from({length: 12}, (_, i) => <group key={i} position={[3.62, 0.92 + Math.floor(i / 6) * 0.6, -3.2 + (i % 6) * 0.38]}><Oil frame={frame} /></group>)}
      {/* tyres, a jerry can, a compressor */}
      {[0, 1, 2].map((i) => <group key={i} position={[2.9, i * 0.18 - 0.14, -3.6]} rotation={[Math.PI / 2, 0, 0]}><Tyre frame={frame} /></group>)}
      <group position={[2.4, 0.05, -0.8]}><Can frame={frame} /></group>
      <mesh position={[-3.2, 0.4, -3.4]} rotation={[0, 0, Math.PI / 2]} castShadow><cylinderGeometry args={[0.28, 0.28, 0.9, 16]} /><Mat c="#d62020" r={0.4} /></mesh>
      <Box p={[-3.2, 0.82, -3.4]} s={[0.3, 0.2, 0.3]} c="#333" />
      {/* the scooter being fixed */}
      <group position={[0, 0.06, -1.0]}><Motor frame={frame} /></group>
      {/* the street's other side */}
      {[-9, -3, 3, 9].map((x, i) => <group key={x} position={[x, 0, 9 + (i % 2)]} rotation={[0, Math.PI, 0]}><House frame={frame} /></group>)}
    </group>
  );
};

export const bengkel: Latar = {
  Scenery,
  hero: {p: [0.2, 0.06, -1.85], ry: 0, pose: 'memegang'},
  work: ENGINE,
  wide: {cam: [2.9, 2.2, 3.8], at: [-0.1, 0.9, -1.3]},
  anchors: {
    lantai_kiri: {p: [-2.2, 0.06, -0.5], ry: 0.5},
    lantai_kanan: {p: [1.9, 0.06, 0.3], ry: -0.4},
    rak: {p: [3.0, 0.06, -2.0], ry: -Math.PI / 2},
    depan: {p: [0.6, 0, 2.4], ry: Math.PI / 2},
  },
  efek: 'asap',
  signature: 'motor',
};
