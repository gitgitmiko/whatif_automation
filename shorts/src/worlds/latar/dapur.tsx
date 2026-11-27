import {useMemo} from 'react';
import {Box, Mat, Many, V3, rand} from '../../kit3d/core';
import {PROPS} from '../../kit3d/props';
import type {Latar} from './types';

// A street-side gorengan stall at dusk: a counter with a gas stove and a wok of hot oil, a glass display of fried
// snacks, the green 3 kg gas cylinder beside it, an orange tarp on poles with string lights, a bench for customers,
// the road in front and houses behind. You stand behind the counter facing the street (+Z).

const WOK: V3 = [-0.52, 1.3, 0.05];

const Snack: React.FC<{p: V3; i: number}> = ({p, i}) => (
  <Box p={p} s={[0.11, 0.05, 0.07]} rot={[0, rand(i) * 3, 0]} c={['#c7832f', '#b5651d', '#d9a441'][i % 3]} r={0.8} shadow={false} />
);

const Scenery: React.FC<{frame: number; night: boolean}> = ({frame, night}) => {
  const Gas = PROPS.tabung_gas, Stove = PROPS.kompor, House = PROPS.rumah, Tree = PROPS.pohon, Pole = PROPS.tiang;
  const bulbs = useMemo(() => Array.from({length: 9}, (_, i) => ({p: [-1.3 + i * 0.325, 2.32 - Math.sin((i / 8) * Math.PI) * 0.12, 1.05] as V3})), []);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[200, 200]} /><Mat c="#7a7a72" r={1} /></mesh>
      <Box p={[0, 0.01, 4.6]} s={[200, 0.02, 5]} c="#3b3b3f" r={0.95} shadow={false} />
      {[-6, -2, 2, 6, 10].map((x) => <Box key={x} p={[x, 0.025, 4.6]} s={[2, 0.01, 0.15]} c="#e8e8e8" shadow={false} />)}
      {/* the counter */}
      <Box p={[0, 0.5, 0]} s={[2.4, 1.0, 0.9]} c="#2b6cb0" r={0.6} />
      <Box p={[0, 1.005, 0]} s={[2.5, 0.03, 1.0]} c="#f2f2ef" r={0.4} />
      <Box p={[0, 0.55, 0.455]} s={[2.0, 0.35, 0.01]} c="#f2c214" shadow={false} />
      <group position={[-0.35, 1.02, 0.05]}><Stove frame={frame} /></group>
      {/* wok of hot oil with snacks frying */}
      <mesh position={WOK} rotation={[Math.PI, 0, 0]} castShadow>
        <sphereGeometry args={[0.3, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2]} /><meshStandardMaterial color="#2a2a2a" metalness={0.7} roughness={0.35} side={2} />
      </mesh>
      <mesh position={[WOK[0], WOK[1] - 0.05, WOK[2]]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.26, 20]} /><Mat c="#d89a2b" m={0.2} r={0.15} /></mesh>
      {[0, 1, 2, 3].map((i) => <Snack key={i} i={i} p={[WOK[0] + Math.cos(i * 1.7 + frame * 0.03) * 0.13, WOK[1] - 0.03, WOK[2] + Math.sin(i * 1.7 + frame * 0.03) * 0.13]} />)}
      {/* glass display */}
      <Box p={[0.55, 1.03, 0]} s={[0.95, 0.04, 0.6]} c="#c9ccd2" m={0.5} />
      <mesh position={[0.55, 1.29, 0]}><boxGeometry args={[0.95, 0.5, 0.6]} /><meshStandardMaterial color="#bfe3f5" transparent opacity={0.28} roughness={0.05} /></mesh>
      {Array.from({length: 12}, (_, i) => <Snack key={`d${i}`} i={i + 7} p={[0.2 + (i % 6) * 0.13, 1.08 + Math.floor(i / 6) * 0.06, -0.1 + (i % 2) * 0.18]} />)}
      {/* gas cylinder with its hose to the stove */}
      <group position={[-1.5, 0, -0.25]}><Gas frame={frame} /></group>
      <mesh position={[-1.0, 0.75, -0.2]} rotation={[0, 0, -1.0]}><cylinderGeometry args={[0.012, 0.012, 1.2, 6]} /><Mat c="#b8a07a" /></mesh>
      {/* tarp roof on four poles, string lights */}
      {[[-1.35, -0.65], [1.35, -0.65], [-1.35, 1.1], [1.35, 1.1]].map(([x, z], i) => (
        <mesh key={i} position={[x, 1.2, z]} castShadow><cylinderGeometry args={[0.03, 0.03, 2.4, 8]} /><Mat c="#8d8f93" m={0.6} /></mesh>
      ))}
      <Box p={[0, 2.43, 0.22]} s={[3.0, 0.05, 2.2]} c="#e2711d" r={0.7} />
      <Many at={bulbs}><sphereGeometry args={[0.035, 8, 6]} /><meshStandardMaterial color="#fff" emissive="#ffe08a" emissiveIntensity={night ? 6 : 2.5} /></Many>
      <pointLight position={[0, 2.1, 0.4]} intensity={night ? 10 : 4} distance={6} color="#ffe2a8" />
      {/* bench for customers */}
      <Box p={[0, 0.42, 1.35]} s={[2.0, 0.06, 0.35]} c="#8a5a33" r={0.8} />
      {[-0.85, 0.85].map((x) => <Box key={x} p={[x, 0.2, 1.35]} s={[0.06, 0.4, 0.3]} c="#6b4a2b" />)}
      {/* the street's other side */}
      {[-9, -3, 3, 9].map((x, i) => <group key={x} position={[x, 0, -6.5 - (i % 2)]}><House frame={frame} /></group>)}
      {[-5.8, 6.2].map((x) => <group key={`t${x}`} position={[x, 0, -3.2]}><Tree frame={frame} /></group>)}
      <group position={[4.2, 0, 2.0]}><Pole frame={frame} /></group>
    </group>
  );
};

export const dapur: Latar = {
  Scenery,
  hero: {p: [0, 0, -0.8], ry: 0, pose: 'memegang'},
  work: WOK,
  wide: {cam: [2.6, 2.1, 4.6], at: [-0.2, 1.15, 0]},
  anchors: {
    meja: {p: [0.95, 1.02, 0.28], s: 0.6},
    lantai_kiri: {p: [-2.0, 0, 1.0], ry: 0.4},
    lantai_kanan: {p: [2.0, 0, 1.3], ry: -0.5},
    jalan: {p: [0.8, 0, 4.4], ry: Math.PI / 2},
  },
  efek: 'api',
  signature: 'tabung_gas',
};
