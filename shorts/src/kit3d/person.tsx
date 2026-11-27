import {Box, Mat, V3} from './core';

// "Kamu": a stylised low-poly person, 1.7 m tall with a big head (about 3.5 heads) so the drawn face reads on a phone.
// Feet at the origin, facing +Z. The uniform and hat change per profession; poses and expressions come from the script.

export type Hero3D = {seragam?: string; celana?: string; kulit?: string; rambut?: string;
  topi?: 'none' | 'masinis' | 'helm' | 'pet' | 'perawat'};
export const POSES = ['berdiri', 'duduk', 'lari', 'menunjuk', 'panik', 'memegang', 'menoleh'] as const;
export const EXPRS = ['biasa', 'kaget', 'takut', 'lega', 'fokus'] as const;
export const HATS = ['none', 'masinis', 'helm', 'pet', 'perawat'] as const;

// Joint angles in radians. Shoulder x < 0 swings the arm forward, z > 0 lifts it out sideways; elbow < 0 bends forward;
// hip < 0 lifts the thigh forward; knee > 0 bends back. lean tips the body forward, y drops the pelvis (sitting).
type Pose = {sh: [V2, V2]; el: [number, number]; hip: [number, number]; knee: [number, number];
  lean?: number; yaw?: number; pitch?: number; y?: number};
type V2 = [number, number];
const POSE: Record<string, (f: number) => Pose> = {
  berdiri: () => ({sh: [[0, 0.12], [0, 0.12]], el: [-0.15, -0.15], hip: [0, 0], knee: [0, 0]}),
  duduk: () => ({sh: [[-0.7, 0.1], [-0.7, 0.1]], el: [-0.7, -0.7], hip: [-1.55, -1.55], knee: [1.55, 1.55], y: -0.3}),
  lari: (f) => {
    const s = Math.sin(f * 0.45);
    return {sh: [[s * 0.9, 0.1], [-s * 0.9, 0.1]], el: [-1.3, -1.3], hip: [-s * 0.8, s * 0.8],
      knee: [0.3 + Math.max(s, 0) * 1.1, 0.3 + Math.max(-s, 0) * 1.1], lean: 0.25, y: -0.04 + Math.abs(s) * 0.05};
  },
  menunjuk: () => ({sh: [[-1.45, 0.05], [0, 0.12]], el: [0, -0.15], hip: [0, 0], knee: [0, 0], yaw: -0.15}),
  panik: (f) => {
    const w = Math.sin(f * 1.7) * 0.06;
    return {sh: [[-0.4, 2.5 + w], [-0.4, 2.5 - w]], el: [-1.6, -1.6], hip: [0, 0], knee: [0.08, 0.08], pitch: -0.12};
  },
  memegang: () => ({sh: [[-1.15, 0.12], [-1.15, 0.12]], el: [-0.45, -0.45], hip: [0, 0], knee: [0, 0], lean: 0.05}),
  menoleh: () => ({sh: [[0.1, 0.1], [-0.2, 0.12]], el: [-0.15, -0.35], hip: [0, 0], knee: [0, 0], yaw: 0.95}),
};

const D = {seragam: '#2b4c8c', celana: '#2a2f38', kulit: '#c68a5e', rambut: '#1a1a1a'};

const Limb: React.FC<{len: number; r: number; c: string}> = ({len, r, c}) => (
  <mesh position={[0, -len / 2, 0]} castShadow><capsuleGeometry args={[r, len - 2 * r, 4, 10]} /><Mat c={c} r={0.7} /></mesh>
);

const Arm: React.FC<{side: 1 | -1; sh: V2; el: number; sleeve: string; skin: string}> = ({side, sh, el, sleeve, skin}) => (
  <group position={[side * 0.27, 1.22, 0]} rotation={[sh[0], 0, side * sh[1]]}>
    <Limb len={0.32} r={0.075} c={sleeve} />
    <group position={[0, -0.3, 0]} rotation={[el, 0, 0]}>
      <Limb len={0.3} r={0.06} c={skin} />
      <mesh position={[0, -0.32, 0]} castShadow><sphereGeometry args={[0.07, 10, 8]} /><Mat c={skin} /></mesh>
    </group>
  </group>
);

const Leg: React.FC<{side: 1 | -1; hip: number; knee: number; pants: string}> = ({side, hip, knee, pants}) => (
  <group position={[side * 0.11, 0.74, 0]} rotation={[hip, 0, 0]}>
    <Limb len={0.38} r={0.085} c={pants} />
    <group position={[0, -0.36, 0]} rotation={[knee, 0, 0]}>
      <Limb len={0.34} r={0.075} c={pants} />
      <Box p={[0, -0.34, 0.06]} s={[0.15, 0.09, 0.28]} c="#1b1b1b" />
    </group>
  </group>
);

// Eyes, brows and mouth drawn as flat shapes on the front of the head. Blinks every three seconds or so.
const Face: React.FC<{expr: string; frame: number}> = ({expr, frame}) => {
  const blink = frame % 93 < 4 ? 0.12 : 1;
  const eyeY = {kaget: 1.35, takut: 1.2, fokus: 0.55, lega: 0.8}[expr] ?? 1;
  const pupil = {kaget: 0.55, takut: 0.7}[expr] ?? 1;
  // brow: [height, tilt]; tilt > 0 raises the inner end (worry), < 0 lowers it (focus, anger)
  const [bh, bt] = ({kaget: [0.15, 0], takut: [0.13, 0.45], fokus: [0.085, -0.4], lega: [0.12, 0.1]} as Record<string, V2>)[expr] ?? [0.11, 0];
  return (
    <group position={[0, 0, 0.215]}>
      {[1, -1].map((s) => (
        <group key={s} position={[s * 0.09, 0.02, 0]}>
          <mesh scale={[1, eyeY * blink, 0.35]}><sphereGeometry args={[0.055, 14, 10]} /><Mat c="#ffffff" r={0.3} /></mesh>
          <mesh position={[0, -0.005, 0.02]} scale={[pupil, pupil * eyeY * blink, 0.3]}><sphereGeometry args={[0.03, 12, 8]} /><Mat c="#111" r={0.2} /></mesh>
          <Box p={[0, bh, 0.01]} s={[0.1, 0.022, 0.02]} rot={[0, 0, s * -bt]} c="#1a1a1a" shadow={false} />
        </group>
      ))}
      {expr === 'kaget' && <mesh position={[0, -0.12, 0]} scale={[0.75, 1.1, 0.3]}><sphereGeometry args={[0.05, 14, 10]} /><Mat c="#3a1010" /></mesh>}
      {expr === 'takut' && <Box p={[0, -0.12, 0]} s={[0.12, 0.04, 0.02]} c="#3a1010" shadow={false} />}
      {expr === 'lega' && (
        <mesh position={[0, -0.09, 0]} rotation={[0, 0, Math.PI]}><torusGeometry args={[0.055, 0.012, 6, 16, Math.PI]} /><Mat c="#3a1010" /></mesh>
      )}
      {(expr === 'fokus' || !['kaget', 'takut', 'lega'].includes(expr)) && (
        <Box p={[0, -0.11, 0]} s={[expr === 'fokus' ? 0.07 : 0.09, 0.016, 0.02]} c="#3a1010" shadow={false} />
      )}
    </group>
  );
};

const Hat: React.FC<{kind: string; hair: string; uniform: string}> = ({kind, hair, uniform}) => {
  switch (kind) {
    case 'masinis': return (
      <group position={[0, 0.17, 0]}>
        <mesh castShadow><cylinderGeometry args={[0.25, 0.24, 0.13, 20]} /><Mat c={uniform} /></mesh>
        <mesh position={[0, -0.04, 0]}><cylinderGeometry args={[0.245, 0.245, 0.03, 20]} /><Mat c="#d9a520" m={0.6} r={0.3} /></mesh>
        <Box p={[0, -0.06, 0.24]} s={[0.3, 0.02, 0.14]} c="#111" />
      </group>
    );
    case 'helm': return (
      <group position={[0, 0.05, 0]}>
        <mesh castShadow><sphereGeometry args={[0.27, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2]} /><Mat c="#f2c214" r={0.4} /></mesh>
        <mesh position={[0, 0.005, 0]} rotation={[-Math.PI / 2, 0, 0]}><ringGeometry args={[0.26, 0.32, 24]} /><meshStandardMaterial color="#e0b010" side={2} /></mesh>
      </group>
    );
    case 'pet': return (
      <group position={[0, 0.08, 0]}>
        <mesh castShadow><sphereGeometry args={[0.25, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2]} /><Mat c={uniform} /></mesh>
        <Box p={[0, 0.0, 0.26]} s={[0.26, 0.02, 0.16]} c={uniform} />
      </group>
    );
    case 'perawat': return (
      <group>
        <mesh position={[0, 0.06, 0]}><sphereGeometry args={[0.245, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2]} /><Mat c={hair} /></mesh>
        <Box p={[0, 0.22, 0.04]} s={[0.26, 0.08, 0.18]} c="#ffffff" />
      </group>
    );
    default: return (
      <mesh position={[0, 0.04, -0.015]} castShadow><sphereGeometry args={[0.25, 18, 10, 0, Math.PI * 2, 0, Math.PI / 1.9]} /><Mat c={hair} r={0.9} /></mesh>
    );
  }
};

export const Person: React.FC<{hero?: Hero3D; pose?: string; expr?: string; frame: number; position?: V3; rotationY?: number; scale?: number}> =
  ({hero = {}, pose = 'berdiri', expr = 'biasa', frame, position = [0, 0, 0], rotationY = 0, scale = 1}) => {
    const p = (POSE[pose] ?? POSE.berdiri)(frame);
    const c = {...D, ...Object.fromEntries(Object.entries(hero).filter(([, v]) => v))} as typeof D & Hero3D;
    const breath = 1 + Math.sin(frame * 0.12) * 0.012;
    return (
      <group position={position} rotation={[0, rotationY, 0]} scale={scale}>
        <group position={[0, p.y ?? 0, 0]}>
          <Leg side={1} hip={p.hip[0]} knee={p.knee[0]} pants={c.celana} />
          <Leg side={-1} hip={p.hip[1]} knee={p.knee[1]} pants={c.celana} />
          <Box p={[0, 0.8, 0]} s={[0.34, 0.16, 0.22]} c={c.celana} />
          <group position={[0, 0.8, 0]} rotation={[p.lean ?? 0, 0, 0]}>
            <group position={[0, -0.8, 0]}>
              <group scale={[1, breath, 1]} position={[0, 1.03, 0]}>
                <Box p={[0, 0, 0]} s={[0.46, 0.5, 0.26]} c={c.seragam} r={0.7} />
                <Box p={[0, 0.2, 0.135]} s={[0.18, 0.08, 0.01]} c="#ffffff" shadow={false} />
              </group>
              {/* left arm is +X (the person's left, the viewer's right) */}
              <Arm side={1} sh={p.sh[0]} el={p.el[0]} sleeve={c.seragam} skin={c.kulit} />
              <Arm side={-1} sh={p.sh[1]} el={p.el[1]} sleeve={c.seragam} skin={c.kulit} />
              <mesh position={[0, 1.31, 0]}><cylinderGeometry args={[0.06, 0.07, 0.1, 10]} /><Mat c={c.kulit} /></mesh>
              <group position={[0, 1.5, 0]} rotation={[p.pitch ?? 0, p.yaw ?? 0, 0]}>
                <mesh castShadow scale={[1, 1.05, 0.95]}><sphereGeometry args={[0.235, 20, 16]} /><Mat c={c.kulit} r={0.65} /></mesh>
                {[1, -1].map((s) => <mesh key={s} position={[s * 0.235, 0, 0]}><sphereGeometry args={[0.045, 8, 6]} /><Mat c={c.kulit} /></mesh>)}
                <mesh position={[0, -0.03, 0.225]}><sphereGeometry args={[0.03, 8, 6]} /><Mat c={c.kulit} /></mesh>
                <Face expr={expr} frame={frame} />
                <Hat kind={c.topi ?? 'none'} hair={c.rambut} uniform={c.seragam} />
              </group>
            </group>
          </group>
        </group>
      </group>
    );
  };
