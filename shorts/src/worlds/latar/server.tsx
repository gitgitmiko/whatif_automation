import {useLayoutEffect, useMemo, useRef} from 'react';
import * as THREE from 'three';
import {Box, Mat, Many, V3, rand} from '../../kit3d/core';
import type {Latar} from './types';

// A data-centre aisle: two rows of black racks full of blinking lights on a raised tiled floor, cold blue light
// from the ceiling, cable trays overhead. You stand in the aisle facing its open end (+Z), a rack at your right.

const RACK: V3 = [1.13, 1.3, 0.5];

// Hundreds of status LEDs, each blinking on its own rhythm (deterministic per index and frame).
const Leds: React.FC<{frame: number}> = ({frame}) => {
  const ref = useRef<THREE.InstancedMesh>(null);
  const spots = useMemo(() => {
    const out: V3[] = [];
    for (const side of [-1, 1]) for (let r = 0; r < 7; r++) for (let u = 0; u < 14; u++) for (let k = 0; k < 3; k++)
      out.push([side * 1.14, 0.35 + u * 0.13, -4.4 + r * 0.8 + 0.15 + k * 0.18]);
    return out;
  }, []);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4(), c = new THREE.Color();
    spots.forEach((p, i) => {
      const on = Math.floor((frame + rand(i) * 40) / (6 + rand(i + 1) * 20)) % 3 !== 0;
      m.makeScale(on ? 1 : 0.001, 1, 1);
      m.setPosition(p[0], p[1], p[2]);
      ref.current!.setMatrixAt(i, m);
      ref.current!.setColorAt(i, c.set(rand(i + 2) > 0.85 ? '#ffb020' : '#30ff70'));
    });
    ref.current!.instanceMatrix.needsUpdate = true;
    if (ref.current!.instanceColor) ref.current!.instanceColor.needsUpdate = true;
  }, [frame, spots]);
  return (
    <instancedMesh ref={ref} args={[undefined, undefined, spots.length]}>
      <boxGeometry args={[0.02, 0.02, 0.03]} /><meshBasicMaterial toneMapped={false} />
    </instancedMesh>
  );
};

const Scenery: React.FC<{frame: number; night: boolean}> = ({frame, night}) => {
  const racks = useMemo(() => [-1, 1].flatMap((side) => Array.from({length: 7}, (_, r) => ({p: [side * 1.5, 1.1, -4.0 + r * 0.8] as V3}))), []);
  const tiles = useMemo(() => Array.from({length: 40}, (_, i) => ({p: [(i % 4) * 0.6 - 0.9, 0.205, -5 + Math.floor(i / 4) * 0.6 + 0.6] as V3})), []);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[200, 200]} /><Mat c="#2a2f36" r={1} /></mesh>
      <Box p={[0, 0.1, -1.6]} s={[5.4, 0.2, 7.6]} c="#c9ccd2" r={0.6} />
      <Many at={tiles}><boxGeometry args={[0.58, 0.01, 0.58]} /><Mat c="#dde1e5" r={0.5} /></Many>
      <Many at={racks} shadow><boxGeometry args={[0.7, 2.2, 0.78]} /><Mat c="#15181c" m={0.4} r={0.4} /></Many>
      <Leds frame={frame} />
      <Box p={[0, 1.6, -5.6]} s={[5.4, 3.2, 0.15]} c="#1f2429" />
      {[-2.7, 2.7].map((x) => <Box key={x} p={[x, 1.6, -1.6]} s={[0.12, 3.2, 7.8]} c="#22282e" />)}
      {[-1.5, 1.5].map((x) => <Box key={`t${x}`} p={[x, 2.7, -1.6]} s={[0.5, 0.06, 7.4]} c="#e2b714" m={0.4} />)}
      {[-3.5, -1.5, 0.5].map((z) => <Box key={`l${z}`} p={[0, 3.0, z]} s={[0.25, 0.05, 1.2]} c="#fff" e="#bfe2ff" ei={night ? 4 : 2.5} shadow={false} />)}
      <pointLight position={[0, 2.8, -1.0]} intensity={night ? 12 : 9} distance={9} color="#9fd4ff" />
      <pointLight position={[0, 2.8, -4.0]} intensity={8} distance={8} color="#9fd4ff" />
    </group>
  );
};

export const server: Latar = {
  Scenery,
  hero: {p: [0.15, 0.2, -0.5], ry: 0, pose: 'berdiri'},
  work: RACK,
  wide: {cam: [1.1, 2.2, 4.6], at: [0, 1.2, -1.2]},
  anchors: {
    lorong_depan: {p: [-0.5, 0.2, 1.6], ry: 0.3},
    lorong_belakang: {p: [0.2, 0.2, -2.6], ry: 0},
  },
  efek: 'asap',
  signature: 'panel_layar',
};
