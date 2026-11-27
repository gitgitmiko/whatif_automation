import {ThreeCanvas} from '@remotion/three';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Lights, Look, Rig, Vignette, clamp} from '../kit3d/core';
import {kereta} from './kereta';

// Every real-time 3D world, by the name the script's "world" uses (and shorts/worlds.json lists).
export type WorldViewProps = {look: Look; frame: number; shot: string; night: boolean};
export type World = {
  shots: Record<string, (t: number, T: number) => Look>;
  View: React.FC<WorldViewProps>;
  overlay?: Record<string, React.FC<{frames: number}>>;
};

export const WORLDS: Record<string, World> = {kereta};

// One scene of a world: the shot's camera over the world's scenery, fading in over the previous scene for `lead` frames.
export const WorldShot: React.FC<{world: string; shot: string; frames: number; lead: number; night: boolean}> =
  ({world, shot, frames, lead, night}) => {
    const frame = useCurrentFrame();
    const {width, height, fps} = useVideoConfig();
    const w = WORLDS[world] ?? WORLDS.kereta;
    const name = w.shots[shot] ? shot : Object.keys(w.shots)[0];
    const look = w.shots[name](frame / fps, frames / fps);
    const dark = night || !!look.night;
    const fade = lead ? interpolate(frame, [0, lead], [0, 1], clamp) : 1;
    const Overlay = w.overlay?.[name];
    return (
      <AbsoluteFill style={{opacity: fade, background: '#000'}}>
        <ThreeCanvas width={width} height={height} shadows gl={{antialias: true, preserveDrawingBuffer: true}}
          camera={{fov: 50, position: [0, 5, 10]}}>
          <Rig look={look} frame={frame} night={dark} />
          <Lights focus={look.light ?? look.at} night={dark} />
          <w.View look={look} frame={frame} shot={name} night={dark} />
        </ThreeCanvas>
        {Overlay && <Overlay frames={frames} />}
        <Vignette />
      </AbsoluteFill>
    );
  };
