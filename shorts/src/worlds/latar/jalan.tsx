import {useMemo} from 'react';
import {Box, Mat, Many, V3, rand} from '../../kit3d/core';
import {PROPS} from '../../kit3d/props';
import type {Latar} from './types';

// A city street at dusk: a four-lane road along X with a zebra crossing, raised pavements, shophouses, a traffic
// light, street lamps, and cars and scooters driving past. You stand on the near pavement beside your scooter,
// facing the road (+Z).

const SPOT: V3 = [-1.05, 0.95, 0.6];  // your scooter's handlebar and the phone on it

const Traffic: React.FC<{frame: number}> = ({frame}) => {
  const Car = PROPS.mobil, Bike = PROPS.motor, Truck = PROPS.truk;
  const lanes: [number, number, number, React.FC<{frame: number}>][] = [[3.2, 9, 0, Bike], [4.6, 7, 37, Car], [6.6, -6, 11, Car], [8.0, -5, 61, Truck]];
  return (
    <>
      {lanes.map(([z, v, off, V], i) => {
        const x = ((((off + frame * v / 30) % 120) + 120) % 120) - 60;  // loops along the road
        return <group key={i} position={[x, 0.02, z]} rotation={[0, v > 0 ? 0 : Math.PI, 0]}><V frame={frame} /></group>;
      })}
    </>
  );
};

const Scenery: React.FC<{frame: number; night: boolean}> = ({frame, night}) => {
  const Bike = PROPS.motor, Pole = PROPS.tiang;
  const shops = useMemo(() => Array.from({length: 14}, (_, i) => ({x: -32 + i * 5, h: 6 + rand(i) * 5, c: ['#e9d8b4', '#cfe0e8', '#f0c9a6', '#d8e6c8'][i % 4]})), []);
  const lamps = useMemo(() => [-18, -6, 6, 18].map((x) => ({p: [x, 3.2, 1.6] as V3})), []);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[300, 300]} /><Mat c="#6d8f3f" r={1} /></mesh>
      <Box p={[0, 0.01, 5.6]} s={[300, 0.02, 8]} c="#3b3b3f" r={0.95} shadow={false} />
      {Array.from({length: 30}, (_, i) => <Box key={i} p={[-60 + i * 4, 0.025, 5.6]} s={[2, 0.01, 0.15]} c="#f0f0f0" shadow={false} />)}
      {Array.from({length: 7}, (_, i) => <Box key={`z${i}`} p={[-3, 0.026, 2.3 + i * 1.1]} s={[2.4, 0.01, 0.55]} c="#f5f5f5" shadow={false} />)}
      <Box p={[0, 0.08, 0.3]} s={[300, 0.16, 3.2]} c="#b9b4aa" r={0.9} />
      <Box p={[0, 0.08, 11.8]} s={[300, 0.16, 4.4]} c="#b9b4aa" r={0.9} />
      {shops.map((s, i) => (
        <group key={i}>
          <Box p={[s.x, s.h / 2, -3.2]} s={[4.8, s.h, 4]} c={s.c} r={0.9} />
          <Box p={[s.x, 2.6, -1.1]} s={[4.6, 0.12, 0.8]} c={['#d62020', '#2b6cb0', '#2d6a4f'][i % 3]} />
          <Box p={[s.x, 1.2, -1.19]} s={[3.6, 2.2, 0.04]} c="#2a3440" e="#ffe2a0" ei={night ? 0.8 : 0.15} r={0.2} />
          <Box p={[s.x, s.h / 2 + 0.3, 15.6]} s={[4.8, s.h, 4]} c={s.c} r={0.9} />
        </group>
      ))}
      <Many at={lamps}><boxGeometry args={[0.12, 6.4, 0.12]} /><Mat c="#6b7178" m={0.5} /></Many>
      {[-18, -6, 6, 18].map((x) => <Box key={`b${x}`} p={[x, 6.3, 2.2]} s={[0.4, 0.12, 1.4]} c="#fff" e="#ffe8b0" ei={night ? 5 : 0.5} shadow={false} />)}
      {/* traffic light at the crossing */}
      <Box p={[-4.6, 1.8, 1.7]} s={[0.12, 3.6, 0.12]} c="#333" />
      <Box p={[-4.6, 3.8, 1.7]} s={[0.35, 1.0, 0.3]} c="#222" />
      {[['#ff2020', 4.1, Math.floor(frame / 90) % 2 === 0], ['#ffd400', 3.8, false], ['#20ff60', 3.5, Math.floor(frame / 90) % 2 === 1]].map(([c, y, on], i) => (
        <mesh key={i} position={[-4.6, y as number, 1.86]}><sphereGeometry args={[0.1, 10, 8]} /><Mat c="#111" e={c as string} ei={on ? 6 : 0.1} /></mesh>
      ))}
      <group position={[-1.6, 0.16, 0.6]}><Bike frame={frame} /></group>
      <group position={[8, 0.16, 1.4]}><Pole frame={frame} /></group>
      <Traffic frame={frame} />
    </group>
  );
};

export const jalan: Latar = {
  Scenery,
  hero: {p: [-0.2, 0.16, 0.4], ry: 0, pose: 'berdiri'},
  work: SPOT,
  wide: {cam: [3.0, 2.4, 12.0], at: [-0.6, 1.0, 0.8]},  // from across the road, traffic in between
  anchors: {
    trotoar_kiri: {p: [-3.6, 0.16, 0.6], ry: 0.3},
    trotoar_kanan: {p: [2.6, 0.16, 0.9], ry: -0.3},
    jalan_dekat: {p: [1.0, 0.02, 3.0], ry: 0.2},
    jalan_jauh: {p: [-1.0, 0.02, 6.8], ry: Math.PI},
  },
  efek: 'percikan',
  signature: 'motor',
};
