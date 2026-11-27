import {ThreeCanvas} from '@remotion/three';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Lights, Rig} from './core';
import {EXPRS, HATS, POSES, Person} from './person';
import {PROPS} from './props';
import {EFFECTS} from './effects';

// Preview stills for checking the kit by eye: every pose, every expression, every hat.
const Stage: React.FC<{children: React.ReactNode; cam: [number, number, number]; at: [number, number, number]; fov: number; ground?: number}> = ({children, cam, at, fov, ground = 0}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <ThreeCanvas width={1080} height={1920} shadows gl={{antialias: true, preserveDrawingBuffer: true}}>
        <Rig look={{cam, at, fov}} frame={frame} night={false} />
        <Lights focus={[40, 0, 0]} night={false} />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, ground, 0]} receiveShadow><planeGeometry args={[100, 100]} /><meshStandardMaterial color="#6d8f3f" /></mesh>
        {children}
      </ThreeCanvas>
    </AbsoluteFill>
  );
};

export const PersonSheet: React.FC = () => {
  const frame = useCurrentFrame();
  const uniforms = ['#1d2b4a', '#e2711d', '#ffffff', '#2d6a4f', '#7b2d26'];
  return (
    <Stage cam={[0, 4.2, 26]} at={[0, 4.2, 0]} fov={24} ground={-6}>
      {POSES.map((p, i) => (
        <Person key={p} pose={p} expr={EXPRS[i % EXPRS.length]} frame={frame + 7} hero={{topi: HATS[i % HATS.length], seragam: uniforms[i % 5]}}
          position={[(i % 4) * 1.25 - 1.9, i < 4 ? 5.6 : 3.3, 0]} />
      ))}
      {EXPRS.map((e, i) => (
        <Person key={e} expr={e} frame={20} hero={{topi: HATS[i], seragam: uniforms[i]}} scale={1.9}
          position={[(i % 3) * 1.6 - 1.6, i < 3 ? -1.3 : -3.0, 0]} />
      ))}
    </Stage>
  );
};

export const PropSheet: React.FC = () => {
  const frame = useCurrentFrame();
  const names = Object.keys(PROPS);
  return (
    <Stage cam={[0, 30, 34]} at={[0, 0, -1]} fov={42}>
      {names.map((n, i) => {
        const Prop = PROPS[n];
        return <group key={n} position={[(i % 3) * 6 - 6, 0, Math.floor(i / 3) * 5.5 - 12]} rotation={[0, -0.5, 0]}><Prop frame={frame} /></group>;
      })}
      {[-9, 9].map((x) => <Person key={x} frame={frame} position={[x, 0, 10]} />)}
    </Stage>
  );
};

// The effects in a row (front) and the newest props (back), for checking by eye.
export const EffectSheet: React.FC = () => {
  const frame = useCurrentFrame();
  const fx = Object.keys(EFFECTS);
  const props = ['kompor', 'ban', 'jerigen', 'ember', 'apar', 'botol_oli'];
  return (
    <Stage cam={[0, 2.6, 9]} at={[0, 0.9, 0]} fov={40}>
      {fx.map((n, i) => { const F = EFFECTS[n]; return <F key={n} frame={frame} at={[(i % 3) * 1.6 - 1.6, 0.6 + Math.floor(i / 3) * 1.6, 0]} />; })}
      {props.map((n, i) => { const P = PROPS[n]; return <group key={n} position={[i * 0.75 - 1.9, 0, 2.2]}><P frame={frame} /></group>; })}
    </Stage>
  );
};
