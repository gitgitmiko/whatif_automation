import {interpolate} from 'remotion';
import {useMemo} from 'react';
import {Box, Look, Mat, Many, Sparks, Meter, V3, brake, clamp, rand, smooth} from '../kit3d/core';
import type {World, WorldViewProps} from './index';

// The railway: track along +X, a level crossing at x = 0 with a stalled car, a five-car commuter train whose front is
// at x = front, and the driver's cab for the dead-man shot. Each shot below is one line of the catalog (worlds.json).

const CAR_L = 20, CARS = 5, GAP = 0.8, RAIL_Z = 0.75, RAIL_Y = 0.42, WHEEL_R = 0.46;
type KLook = Look & {front: number; braking: number; gate?: number; dash?: boolean; foot?: number; alarm?: boolean};

export const shots: Record<string, (t: number, T: number) => KLook> = {
  cab: (t: number, T: number): KLook => {
    const u = Math.min(t / T, 1);
    // driver's view down the line, the stalled car growing ahead
    const front = -170 + 26 * t;
    return {light: [front, 0, 0], front, braking: 0, cam: [front + 1.2, 3.6, -0.5], at: [front + 80, 1.8, 0.3], fov: 60, shake: 0.05, gate: 1};
  },
  top: (t: number, T: number): KLook => {
    const u = Math.min(t / T, 1);
    // from above: the train locked between two rails, nowhere to swerve
    const front = brake(-110, 45, t, T * 1.6);
    return {light: [front, 0, 0], front, braking: 1, cam: [front + 30, 30, 8], at: [front - 4, 0, 0], fov: 62, gate: 1};
  },
  distance: (t: number, T: number): KLook => {
    const u = Math.min(t / T, 1);
    // the whole braking run seen from far away, counted in metres by the overlay
    const front = brake(-505, 500, t, T * 0.92);
    return {light: [front, 0, 0], front, braking: 1, cam: [front - 20, 38, 95], at: [front - 30, 0, 0], fov: 60, gate: 1};
  },
  wheel: (t: number, T: number): KLook => {
    const u = Math.min(t / T, 1);
    // the front bogie, steel on steel, sparks flying
    const front = brake(-80, 30, t, T * 1.8);
    const bx = front - 3.2;
    return {light: [front, 0, 0], front, braking: 1, cam: [bx + interpolate(u, [0, 1], [4, 2]), 1.0, 4.6], at: [bx, 0.8, RAIL_Z], fov: 55, shake: 0.02, gate: 1};
  },
  crossing: (t: number, T: number): KLook => {
    const u = Math.min(t / T, 1);
    // road level at the crossing: barriers down, lamps flashing, headlights coming
    const front = brake(-160, 110, t, T * 1.5);
    return {light: [front, 0, 0], front, braking: 1, cam: [14, 1.8, 9], at: [-10, 2.2, 0], fov: 62, gate: interpolate(u, [0, 0.35], [0, 1], clamp)};
  },
  stop: (t: number, T: number): KLook => {
    const u = Math.min(t / T, 1);
    // the nose halts a few metres from the car
    const front = brake(-40, 34, t, T * 0.85);
    return {light: [front, 0, 0], front, braking: 1, cam: [interpolate(u, [0, 1], [10, 6]), 1.3, interpolate(u, [0, 1], [11, 8])], at: [-5, 2.0, 0], fov: 58, gate: 1};
  },
  cabin: (t: number, T: number): KLook => {
    const u = Math.min(t / T, 1);
    // inside the cab: the dead-man pedal, the foot lifting, the alarm
    const front = -400 + 20 * t;
    const down = interpolate(u, [0.15, 0.32], [0, 1], {...clamp, easing: smooth});
    const at: V3 = [front + interpolate(down, [0, 1], [40, -0.9]), interpolate(down, [0, 1], [1.5, 1.8]), interpolate(down, [0, 1], [0, 0.35])];
    return {light: [front, 0, 0], front, braking: 0, cam: [front - 2.9, 3.4, -0.9], at, fov: 70, dash: true,
      foot: interpolate(u, [0.35, 0.55], [0, 1], clamp), alarm: u > 0.55, gate: 0};
  },
  night: (t: number, T: number): KLook => {
    const u = Math.min(t / T, 1);
    // the loop: the same train rushing into the next night
    const front = -260 + 30 * t;
    return {light: [front, 0, 0], front, braking: 0, cam: [front + 14 - 6 * u, 5 + 2 * u, 12 - 4 * u], at: [front - 8, 2.5, 0], fov: 60, night: true, gate: 0};
  },
};

const Track: React.FC = () => {
  const sleepers = useMemo(() => Array.from({length: 1500}, (_, i) => ({p: [-700 + i * 0.65, 0.28, 0] as V3})), []);
  const trees = useMemo(() => Array.from({length: 420}, (_, i) => {
    const side = i % 2 ? 1 : -1, x = -720 + rand(i) * 900, z = side * (14 + rand(i + 9) * 70), h = 5 + rand(i + 3) * 7;
    return {p: [x, h / 2, z] as V3, s: [h / 7, h / 7, h / 7] as V3};
  }).filter((t) => Math.abs(t.p[0]) > 14), []);
  const poles = useMemo(() => Array.from({length: 20}, (_, i) => ({p: [-700 + i * 45, 3.6, -3.4] as V3})), []);
  const arms = useMemo(() => poles.map((x) => ({p: [x.p[0], 6.9, -1.9] as V3})), [poles]);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[2400, 800]} /><Mat c="#6d8f3f" r={1} /></mesh>
      <Box p={[-150, 0.12, 0]} s={[1300, 0.24, 4.4]} c="#8a8178" r={1} shadow={false} />
      <Many at={sleepers}><boxGeometry args={[0.25, 0.14, 2.5]} /><Mat c="#6b6f75" r={0.9} /></Many>
      {[-RAIL_Z, RAIL_Z].map((z) => <Box key={z} p={[-150, 0.38, z]} s={[1300, 0.14, 0.09]} c="#c9ccd2" m={0.9} r={0.3} shadow={false} />)}
      <Many at={trees} shadow><coneGeometry args={[2.2, 7, 7]} /><Mat c="#2f5d2a" r={0.9} /></Many>
      <Many at={poles}><boxGeometry args={[0.3, 7.2, 0.3]} /><Mat c="#9aa0a6" m={0.5} /></Many>
      <Many at={arms}><boxGeometry args={[0.15, 0.15, 3.3]} /><Mat c="#9aa0a6" m={0.5} /></Many>
      <Box p={[-150, 6.2, 0]} s={[1300, 0.04, 0.04]} c="#333" shadow={false} />
    </group>
  );
};

// Red-white barrier arm on a post, `down` 0 = up, 1 = across the road.
const Barrier: React.FC<{x: number; z: number; dir: number; down: number; blink: boolean}> = ({x, z, dir, down, blink}) => (
  <group position={[x, 0, z]}>
    <Box p={[0, 0.9, 0]} s={[0.3, 1.8, 0.3]} c="#eeeeee" />
    <Box p={[0, 2.4, 0]} s={[0.25, 0.9, 0.9]} c="#222" />
    <mesh position={[0.16, 2.6, -0.22]}><sphereGeometry args={[0.16, 16, 16]} /><Mat c="#300" e="#ff2010" ei={blink ? 6 : 0.2} /></mesh>
    <mesh position={[0.16, 2.6, 0.22]}><sphereGeometry args={[0.16, 16, 16]} /><Mat c="#300" e="#ff2010" ei={blink ? 0.2 : 6} /></mesh>
    <group position={[0, 1.4, 0]} rotation={[dir * (1 - down) * (Math.PI / 2 - 0.05), 0, 0]}>
      {Array.from({length: 8}, (_, i) => (
        <Box key={i} p={[0, 0, dir * -(0.4 + i * 0.75)]} s={[0.14, 0.18, 0.75]} c={i % 2 ? '#fff' : '#d62020'} />
      ))}
    </group>
  </group>
);

const Car: React.FC = () => (
  <group position={[0, 0.42, 0]} rotation={[0, Math.PI / 2 - 0.25, 0]}>
    <Box p={[0, 0.75, 0]} s={[4.3, 0.85, 1.85]} c="#c2272d" m={0.3} r={0.35} />
    <Box p={[-0.2, 1.45, 0]} s={[2.3, 0.65, 1.7]} c="#1d2633" m={0.2} r={0.15} />
    {[[-1.4, 0.95], [1.4, 0.95], [-1.4, -0.95], [1.4, -0.95]].map(([x, z], i) => (
      <mesh key={i} position={[x, 0.36, z]} rotation={[Math.PI / 2, 0, 0]} castShadow>
        <cylinderGeometry args={[0.36, 0.36, 0.25, 18]} /><Mat c="#151515" />
      </mesh>
    ))}
    {/* hazard lights */}
    {[0.75, -0.75].map((z) => <Box key={z} p={[-2.16, 0.95, z]} s={[0.05, 0.15, 0.3]} c="#530" e="#ffa000" ei={3} shadow={false} />)}
  </group>
);

const Crossing: React.FC<{gate: number; blink: boolean}> = ({gate, blink}) => (
  <group>
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 0]} receiveShadow><planeGeometry args={[8, 400]} /><Mat c="#3b3b3f" r={0.95} /></mesh>
    <Box p={[0, 0.3, 0]} s={[8, 0.12, 3.2]} c="#4a4a4f" shadow={false} />
    <Barrier x={-5.5} z={-5.5} dir={-1} down={gate} blink={blink} />
    <Barrier x={5.5} z={5.5} dir={1} down={gate} blink={!blink} />
    <Car />
  </group>
);

// One commuter car: white body, red band, dark window strip, two bogies whose wheels turn with distance.
const Coach: React.FC<{x: number; lead: boolean; spin: number; lit: boolean}> = ({x, lead, spin, lit}) => (
  <group position={[x, 0, 0]}>
    <Box p={[0, 3.0, 0]} s={[CAR_L, 3.4, 3.0]} c="#f2f2ef" m={0.2} r={0.35} />
    <Box p={[0, 4.78, 0]} s={[CAR_L - 0.4, 0.2, 2.6]} c="#b8bcc2" m={0.5} />
    <Box p={[0, 2.15, 0]} s={[CAR_L + 0.02, 0.34, 3.04]} c="#d4202a" r={0.4} />
    <Box p={[0, 3.55, 0]} s={[CAR_L - 1.2, 0.95, 3.04]} c="#152030" e="#ffd88a" ei={lit ? 0.5 : 0.05} r={0.1} />
    {[-6, 0, 6].map((d) => <Box key={d} p={[d, 2.95, 0]} s={[1.3, 2.4, 3.06]} c="#9aa2ad" m={0.4} r={0.3} />)}
    <Box p={[0, 1.15, 0]} s={[CAR_L - 2, 0.5, 2.4]} c="#3a3d42" />
    {[CAR_L / 2 - 3.2, -(CAR_L / 2 - 3.2)].map((b) => (
      <group key={b} position={[b, 0, 0]}>
        <Box p={[0, 1.25, 0]} s={[3.2, 0.22, 2.0]} c="#2a2c30" m={0.4} />
        {[-1.1, 1.1].map((a) => [-RAIL_Z, RAIL_Z].map((z) => (
          <group key={`${a}${z}`} position={[a, RAIL_Y + WHEEL_R - 0.05, z]} rotation={[0, 0, -spin]}>
            <mesh rotation={[Math.PI / 2, 0, 0]} castShadow>
              <cylinderGeometry args={[WHEEL_R, WHEEL_R, 0.16, 20]} /><Mat c="#8d929a" m={0.8} r={0.35} />
            </mesh>
            <Box p={[0, WHEEL_R * 0.55, z > 0 ? 0.09 : -0.09]} s={[0.12, 0.3, 0.02]} c="#d8d8d8" shadow={false} />
          </group>
        )))}
      </group>
    ))}
    {lead && (
      <group position={[CAR_L / 2, 0, 0]}>
        <Box p={[0.15, 3.0, 0]} s={[0.3, 3.4, 3.0]} c="#d4202a" r={0.4} />
        <Box p={[0.32, 3.7, 0]} s={[0.05, 1.1, 2.5]} c="#0e1622" r={0.05} m={0.3} />
        <Box p={[0.32, 2.1, 0]} s={[0.05, 0.4, 3.0]} c="#f2f2ef" />
        {[-1.05, 1.05].map((z) => (
          <mesh key={z} position={[0.36, 2.55, z]}><sphereGeometry args={[0.22, 16, 16]} /><Mat c="#fff" e="#fff6d0" ei={8} /></mesh>
        ))}
        <pointLight position={[3, 2.6, 0]} intensity={lit ? 220 : 60} distance={40} color="#fff2c8" />
      </group>
    )}
  </group>
);

const Train: React.FC<{front: number; lit: boolean}> = ({front, lit}) => {
  const spin = front / WHEEL_R;
  return (
    <group>
      {Array.from({length: CARS}, (_, i) => (
        <Coach key={i} x={front - CAR_L / 2 - i * (CAR_L + GAP)} lead={i === 0} spin={spin} lit={lit} />
      ))}
    </group>
  );
};

// Cab interior for the dead-man shot: dashboard, gauges, the pedal and a boot that lifts off it, and the alarm lamp.
const Dash: React.FC<{x: number; foot: number; alarm: boolean; frame: number}> = ({x, foot, alarm, frame}) => {
  const flash = alarm && Math.floor(frame / 5) % 2 === 0;
  return (
    <group position={[x, 0, 0]}>
      <Box p={[-0.6, 2.55, 0]} s={[1.2, 0.9, 2.8]} c="#2b2f36" r={0.7} />
      <Box p={[-0.2, 3.05, 0]} s={[0.5, 0.1, 2.8]} c="#1c1f24" />
      {[-0.8, -0.2, 0.4].map((z, i) => (
        <mesh key={z} position={[0.02, 2.75, z]} rotation={[0, 0, Math.PI / 2 - 0.6]}>
          <cylinderGeometry args={[0.17, 0.17, 0.04, 24]} /><Mat c="#0b0f14" e={i === 1 ? '#3fd0ff' : '#ffffff'} ei={0.6} />
        </mesh>
      ))}
      <mesh position={[0.05, 3.15, 0.9]}><sphereGeometry args={[0.1, 16, 16]} /><Mat c="#400" e="#ff1a1a" ei={flash ? 10 : 0.3} /></mesh>
      {flash && <pointLight position={[-0.4, 3.0, 0.6]} intensity={15} distance={5} color="#ff2020" />}
      <Box p={[-1.0, 1.66, 0]} s={[2.2, 0.08, 3.0]} c="#4a4f57" r={0.8} />
      <pointLight position={[-1.4, 3.6, 0]} intensity={6} distance={6} color="#fff0d8" />
      <Box p={[-0.9, 1.75, 0.35]} s={[0.5, 0.06, 0.4]} c="#e8c32a" m={0.4} r={0.4} />
      <group position={[-1.15, 1.85 + foot * 0.25, 0.35]} rotation={[0, 0, foot * 0.25]}>
        <Box p={[0.15, 0.08, 0]} s={[0.62, 0.16, 0.26]} c="#1a1a1a" />
        <Box p={[-0.12, 0.45, 0]} s={[0.24, 0.6, 0.24]} c="#1d2b4a" />
      </group>
      {/* side walls and roof frame the windscreen */}
      <Box p={[-0.8, 3.2, 1.55]} s={[2, 3, 0.1]} c="#3a3f47" />
      <Box p={[-0.8, 3.2, -1.55]} s={[2, 3, 0.1]} c="#3a3f47" />
      <Box p={[-0.8, 4.5, 0]} s={[2, 0.3, 3.2]} c="#3a3f47" />
    </group>
  );
};


const View: React.FC<WorldViewProps> = ({look, frame, night}) => {
  const k = look as KLook;
  const blink = Math.floor(frame / 9) % 2 === 0;
  return (
    <>
      <Track />
      <Crossing gate={k.gate ?? 1} blink={blink} />
      {!k.dash && <Train front={k.front} lit={night} />}
      <Sparks x={k.front - 3.2} y={RAIL_Y + 0.05} zs={SPARK_Z} offsets={SPARK_X} frame={frame} on={k.braking > 0} />
      {k.dash && <Dash x={k.front - 0.2} foot={k.foot ?? 0} alarm={!!k.alarm} frame={frame} />}
    </>
  );
};
const SPARK_Z = [-RAIL_Z, RAIL_Z], SPARK_X = [1.1, -1.1];

export const kereta: World = {
  shots,
  View,
  overlay: {distance: ({frames}) => <Meter frames={frames} total={500} unit="METER" />},
};
