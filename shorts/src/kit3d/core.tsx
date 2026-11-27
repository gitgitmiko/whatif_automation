import {useLayoutEffect, useRef} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {useThree} from '@react-three/fiber';

// Shared pieces of every real-time 3D world: materials, boxes, instancing, the camera rig, sky and light, particles
// and overlays. Worlds (src/worlds) build their scenery from these. Units are metres; frames must be deterministic.

export type V3 = [number, number, number];
// What a shot decides for one frame. cam/at/fov/night/shake/light belong to the kit; anything else is the world's own.
export type Look = {cam: V3; at: V3; fov?: number; night?: boolean; shake?: number; light?: V3; sky?: string; [k: string]: unknown};
// A named spot in a shot where a prop or a person may stand (the AI never gives coordinates).
export type Anchor = {p: V3; ry?: number; s?: number};

export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const rand = (i: number) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
export const smooth = (x: number) => x * x * (3 - 2 * x);
// Constant deceleration over the whole span T: position after time t, having covered dist when t = T.
export const brake = (x0: number, dist: number, t: number, T: number) => x0 + dist * (1 - (1 - Math.min(t / T, 1)) ** 2);

export const Mat: React.FC<{c: string; e?: string; ei?: number; m?: number; r?: number}> = ({c, e, ei = 0, m = 0, r = 0.6}) =>
  <meshStandardMaterial color={c} emissive={e ?? '#000'} emissiveIntensity={ei} metalness={m} roughness={r} />;

export const Box: React.FC<{p: V3; s: V3; c: string; e?: string; ei?: number; m?: number; r?: number; shadow?: boolean; rot?: V3}> =
  ({p, s, shadow = true, rot, ...mat}) => (
    <mesh position={p} rotation={rot} castShadow={shadow} receiveShadow>
      <boxGeometry args={s} />
      <Mat {...mat} />
    </mesh>
  );

// Many copies of one mesh at the given positions (sleepers, trees, poles).
export const Many: React.FC<{at: {p: V3; s?: V3; ry?: number}[]; children: React.ReactNode; shadow?: boolean}> = ({at, children, shadow}) => {
  const ref = useRef<THREE.InstancedMesh>(null);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4(), q = new THREE.Quaternion();
    at.forEach((a, i) => {
      q.setFromEuler(new THREE.Euler(0, a.ry ?? 0, 0));
      m.compose(new THREE.Vector3(...a.p), q, new THREE.Vector3(...(a.s ?? [1, 1, 1])));
      ref.current!.setMatrixAt(i, m);
    });
    ref.current!.instanceMatrix.needsUpdate = true;
  }, [at]);
  return <instancedMesh ref={ref} args={[undefined, undefined, at.length]} castShadow={shadow} receiveShadow>{children}</instancedMesh>;
};

// Camera, sky and fog for the frame. A little hand-held shake when the shot asks for it.
export const Rig: React.FC<{look: Look; frame: number; night: boolean}> = ({look, frame, night}) => {
  const {camera, scene} = useThree();
  const k = look.shake ?? 0;
  const j = (i: number) => (Math.sin(frame * 1.9 + i) + Math.sin(frame * 3.7 + i * 2)) * k;
  const cam = camera as THREE.PerspectiveCamera;
  cam.position.set(look.cam[0] + j(1), look.cam[1] + j(2), look.cam[2] + j(3));
  cam.lookAt(...look.at);
  cam.fov = look.fov ?? 50;
  cam.near = 0.1;
  cam.far = 2000;
  cam.updateProjectionMatrix();
  // a world may paint its own sky (inside the body); otherwise dusk, or night
  const sky = look.sky && !night ? look.sky : undefined;  // night (horror) always wins over a set's own sky
  scene.background = new THREE.Color(sky ?? (night ? '#0b1024' : '#f0a25a'));
  scene.fog = new THREE.Fog(sky ?? (night ? '#0b1024' : '#f3b77a'), 60, night ? 380 : 650);
  return null;
};

// Dusk sun with shadows centred on `focus`, or a cold moon at night.
export const Lights: React.FC<{focus: V3; night: boolean}> = ({focus, night}) => (
  <>
    <hemisphereLight args={[night ? '#3a4a80' : '#ffd9b0', night ? '#101418' : '#4a5a30', night ? 0.35 : 1.3]} />
    <directionalLight position={[focus[0] - 60, 80, 70]} intensity={night ? 0.3 : 2.6} color={night ? '#8fa8ff' : '#ffc890'}
      castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-70} shadow-camera-right={70}
      shadow-camera-top={70} shadow-camera-bottom={-70} shadow-camera-far={300} shadow-bias={-0.0004}
      target-position={[focus[0] - 40, 0, 0]} />
  </>
);

// Sparks flung back and up from points along x (wheels, a grinder): deterministic, each born, flying, fading.
export const Sparks: React.FC<{x: number; y: number; zs: number[]; offsets?: number[]; frame: number; on: boolean}> =
  ({x, y, zs, offsets = [0], frame, on}) => {
    const ref = useRef<THREE.InstancedMesh>(null);
    const N = 140;
    useLayoutEffect(() => {
      const m = new THREE.Matrix4();
      for (let i = 0; i < N; i++) {
        const life = 9, age = (frame + i * 7.3) % life, k = age / 30;
        const vx = -(4 + rand(i) * 6), vy = 1.5 + rand(i + 1) * 3, vz = (rand(i + 2) - 0.5) * 3;
        const z = zs[i % zs.length] + vz * k, off = offsets[Math.floor(i / 2) % offsets.length];
        const s = on ? 0.05 * (1 - age / life) : 0;
        m.makeScale(s * 4, s, s);
        m.setPosition(x + off + vx * k, y + vy * k - 4.9 * k * k, z);
        ref.current!.setMatrixAt(i, m);
      }
      ref.current!.instanceMatrix.needsUpdate = true;
    }, [frame, x, y, on, zs, offsets]);
    return (
      <>
        {on && <pointLight position={[x, y + 0.6, 1.6]} intensity={6 + 3 * Math.sin(frame * 2.3)} distance={7} color="#ffb050" />}
        <instancedMesh ref={ref} args={[undefined, undefined, N]}>
          <boxGeometry args={[1, 1, 1]} />
          <meshBasicMaterial color="#ffc04a" toneMapped={false} />
        </instancedMesh>
      </>
    );
  };

// A number counted up along a bar over the first `share` of the shot, eased like brake().
export const Meter: React.FC<{frames: number; total: number; unit: string; share?: number}> = ({frames, total, unit, share = 0.92}) => {
  const frame = useCurrentFrame();
  const u = Math.min(frame / (frames * share), 1);
  const v = Math.round(total * (1 - (1 - u) ** 2));
  return (
    <div style={{position: 'absolute', top: 500, left: 90, right: 90}}>
      <div style={{height: 26, borderRadius: 13, background: 'rgba(0,0,0,.55)', border: '4px solid white', overflow: 'hidden'}}>
        <div style={{height: '100%', width: `${(v / total) * 100}%`, background: 'linear-gradient(90deg,#FFD400,#ff5a1f)'}} />
      </div>
      <div style={{marginTop: 14, textAlign: 'center', fontFamily: 'Anton', fontSize: 130, color: '#FFD400',
        WebkitTextStroke: '12px #000', paintOrder: 'stroke fill', textShadow: '0 10px 0 rgba(0,0,0,.45)'}}>{v} {unit}</div>
    </div>
  );
};

export const Vignette: React.FC = () =>
  <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,.45) 100%)'}} />;
