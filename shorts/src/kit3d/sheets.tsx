import {ThreeCanvas} from '@remotion/three';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Lights, Rig} from './core';
import {EXPRS, HATS, POSES, Person} from './person';

// Preview stills for checking the kit by eye: every pose, every expression, every hat.
const Stage: React.FC<{children: React.ReactNode; cam: [number, number, number]; at: [number, number, number]; fov: number}> = ({children, cam, at, fov}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <ThreeCanvas width={1080} height={1920} shadows gl={{antialias: true, preserveDrawingBuffer: true}}>
        <Rig look={{cam, at, fov}} frame={frame} night={false} />
        <Lights focus={[40, 0, 0]} night={false} />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -6, 0]} receiveShadow><planeGeometry args={[100, 100]} /><meshStandardMaterial color="#6d8f3f" /></mesh>
        {children}
      </ThreeCanvas>
    </AbsoluteFill>
  );
};

export const PersonSheet: React.FC = () => {
  const frame = useCurrentFrame();
  const uniforms = ['#1d2b4a', '#e2711d', '#ffffff', '#2d6a4f', '#7b2d26'];
  return (
    <Stage cam={[0, 4.2, 26]} at={[0, 4.2, 0]} fov={24}>
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
