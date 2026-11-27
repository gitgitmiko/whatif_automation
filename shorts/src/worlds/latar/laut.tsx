import {useLayoutEffect, useMemo, useRef} from 'react';
import * as THREE from 'three';
import {Box, Mat, V3, rand} from '../../kit3d/core';
import type {Latar} from './types';

// An offshore rig deck at sea: a steel deck on legs 15 m above rolling waves, yellow railings, pipes with a red
// valve wheel, a crane, a flare stack burning at the far end, a supply boat. You stand at the valve facing the open
// side of the deck (+Z).

const D = 15;  // deck height above the sea
const VALVE: V3 = [-0.7, D + 1.1, -0.3];

// Low-poly waves: instanced flattened boxes bobbing deterministically.
const Waves: React.FC<{frame: number}> = ({frame}) => {
  const ref = useRef<THREE.InstancedMesh>(null);
  const spots = useMemo(() => Array.from({length: 400}, (_, i) => [(rand(i) - 0.5) * 240, (rand(i + 1) - 0.5) * 240] as [number, number]), []);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4(), q = new THREE.Quaternion();
    spots.forEach(([x, z], i) => {
      const y = Math.sin(frame * 0.05 + x * 0.1 + z * 0.07) * 0.35;
      q.setFromEuler(new THREE.Euler(0, rand(i + 2) * 3, 0));
      m.compose(new THREE.Vector3(x, y, z), q, new THREE.Vector3(3 + rand(i + 3) * 3, 0.15, 0.8));
      ref.current!.setMatrixAt(i, m);
    });
    ref.current!.instanceMatrix.needsUpdate = true;
  }, [frame, spots]);
  return <instancedMesh ref={ref} args={[undefined, undefined, spots.length]}><boxGeometry args={[1, 1, 1]} /><Mat c="#2f7fb0" m={0.2} r={0.3} /></instancedMesh>;
};

const Scenery: React.FC<{frame: number; night: boolean}> = ({frame}) => {
  const flare = 1 + 0.15 * Math.sin(frame * 0.6);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.2, 0]} receiveShadow><planeGeometry args={[800, 800]} /><Mat c="#1f6a96" m={0.3} r={0.25} /></mesh>
      <Waves frame={frame} />
      {/* legs and deck */}
      {[[-6, -6], [6, -6], [-6, 4], [6, 4]].map(([x, z], i) => (
        <mesh key={i} position={[x, D / 2 - 1, z]} castShadow><cylinderGeometry args={[0.6, 0.7, D + 2, 12]} /><Mat c="#f2c214" r={0.5} /></mesh>
      ))}
      <Box p={[0, D - 0.15, -1]} s={[14, 0.3, 12]} c="#7d838a" m={0.5} r={0.6} />
      {[4.95, -6.95].map((z) => <Box key={z} p={[0, D + 0.55, z]} s={[14, 0.06, 0.06]} c="#f2c214" />)}
      {[-6.95, 6.95].map((x) => <Box key={x} p={[x, D + 0.55, -1]} s={[0.06, 0.06, 12]} c="#f2c214" />)}
      {Array.from({length: 8}, (_, i) => <Box key={`p${i}`} p={[-7 + i * 2, D + 0.28, 4.95]} s={[0.06, 0.56, 0.06]} c="#f2c214" />)}
      {/* pipes and the valve */}
      {[0.6, 1.1].map((y) => <mesh key={y} position={[-0.7, D + y, -0.75]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.14, 0.14, 8, 12]} /><Mat c="#9aa3ab" m={0.6} r={0.4} /></mesh>)}
      <mesh position={[-0.7, D + 1.1, -0.48]}><cylinderGeometry args={[0.06, 0.06, 0.4, 8]} /><Mat c="#9aa3ab" m={0.6} /></mesh>
      <mesh position={VALVE} rotation={[Math.PI / 2, 0, 0]}><torusGeometry args={[0.25, 0.035, 8, 20]} /><Mat c="#d62020" r={0.4} /></mesh>
      {/* tanks, crane, living quarters */}
      {[-4.5, -3.0].map((x) => <mesh key={x} position={[x, D + 1.0, -4.5]} castShadow><cylinderGeometry args={[0.65, 0.65, 2.0, 16]} /><Mat c="#e8e8e8" r={0.5} /></mesh>)}
      <Box p={[3.8, D + 1.6, -4.6]} s={[3.6, 3.2, 3]} c="#f2f2ef" r={0.8} />
      {Array.from({length: 4}, (_, i) => <Box key={`w${i}`} p={[2.4 + i * 0.9, D + 2.2, -3.09]} s={[0.5, 0.4, 0.02]} c="#2a3440" e="#ffe2a0" ei={0.3} shadow={false} />)}
      <Box p={[5.5, D + 3.5, 2.5]} s={[0.5, 7, 0.5]} c="#f2c214" />
      <Box p={[3.3, D + 6.6, 2.5]} s={[5, 0.35, 0.35]} c="#f2c214" rot={[0, 0, 0.25]} />
      {/* flare boom with its flame */}
      <Box p={[-10, D + 3, -6]} s={[8, 0.3, 0.3]} c="#9aa3ab" rot={[0, 0.3, 0.35]} />
      <group position={[-13.6, D + 4.4, -7.2]} scale={[flare, flare * 1.3, flare]}>
        <mesh><coneGeometry args={[0.6, 2.2, 10]} /><meshBasicMaterial color="#ff8a20" toneMapped={false} /></mesh>
        <mesh position={[0, -0.3, 0]}><coneGeometry args={[0.35, 1.2, 10]} /><meshBasicMaterial color="#ffe060" toneMapped={false} /></mesh>
      </group>
      <pointLight position={[-13.6, D + 4.5, -7.2]} intensity={40} distance={30} color="#ff9a40" />
      {/* supply boat */}
      <group position={[18, 0, 14]} rotation={[0, 0.6, 0]}>
        <Box p={[0, 0.8, 0]} s={[12, 1.6, 3.6]} c="#d62020" />
        <Box p={[3, 2.6, 0]} s={[3.5, 2.2, 3]} c="#f2f2ef" />
      </group>
    </group>
  );
};

export const laut: Latar = {
  Scenery,
  hero: {p: [-0.7, D, 0.15], ry: 0, pose: 'memegang'},
  work: VALVE,
  wide: {cam: [4.8, D + 3.0, 8.5], at: [-1.0, D + 1.0, -1.2]},
  anchors: {
    dek_kiri: {p: [-3.5, D, 1.8], ry: 0.4},
    dek_kanan: {p: [2.5, D, 2.2], ry: -0.4},
  },
  efek: 'api',
  signature: 'jerigen',
};
