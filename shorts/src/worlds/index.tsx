import {ThreeCanvas} from '@remotion/three';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Anchor, Lights, Look, Rig, Vignette, clamp} from '../kit3d/core';
import type {Hero3D} from '../kit3d/person';
import type {PropSpec} from '../kit3d/props';
import {kereta} from './kereta';
import {profesi} from './profesi';

// Every real-time 3D world, by the name the script's "world" uses (and shorts/worlds.json lists).
export type WorldViewProps = {look: Look; frame: number; shot: string; night: boolean;
  hero?: Hero3D; heroPose?: string; heroExpr?: string; props?: PropSpec[]; latar?: string; efek?: string};
// What a shot may know about its scene besides time: the latar (set) of worlds built from several sets.
export type ShotCtx = {latar?: string};
export type World = {
  shots: Record<string, (t: number, T: number, ctx: ShotCtx) => Look>;
  View: React.FC<WorldViewProps>;
  overlay?: Record<string, React.FC<{frames: number}>>;
  // named spots where the script may put props in this shot (none: the shot takes no props)
  anchors?: (shot: string, look: Look) => Record<string, Anchor>;
  // anchors whose prop, once placed in any scene, stays for the whole video (the car stalled on the rails)
  sticky?: string[];
};

// Each scene's props, with a sticky anchor's first prop carried into every scene that does not set that anchor itself.
export const sceneProps = (world: string, all: (PropSpec[] | undefined)[]): PropSpec[][] => {
  const sticky = (WORLDS[world] ?? WORLDS.kereta).sticky ?? [];
  const kept = sticky.map((a) => all.flat().find((x) => x?.di === a)).filter((x): x is PropSpec => !!x);
  return all.map((own = []) => [...own, ...kept.filter((k) => !own.some((x) => x.di === k.di))]);
};

export const WORLDS: Record<string, World> = {kereta, profesi};

// One scene of a world: the shot's camera over the world's scenery, fading in over the previous scene for `lead` frames.
export const WorldShot: React.FC<{world: string; shot: string; frames: number; lead: number; night: boolean;
  hero?: Hero3D; heroPose?: string; heroExpr?: string; props?: PropSpec[]; latar?: string; efek?: string}> =
  ({world, shot, frames, lead, night, hero, heroPose, heroExpr, props, latar, efek}) => {
    const frame = useCurrentFrame();
    const {width, height, fps} = useVideoConfig();
    const w = WORLDS[world] ?? WORLDS.kereta;
    const name = w.shots[shot] ? shot : Object.keys(w.shots)[0];
    const look = w.shots[name](frame / fps, frames / fps, {latar});
    const dark = night || !!look.night;
    const fade = lead ? interpolate(frame, [0, lead], [0, 1], clamp) : 1;
    const Overlay = w.overlay?.[name];
    return (
      <AbsoluteFill style={{opacity: fade, background: '#000'}}>
        <ThreeCanvas width={width} height={height} shadows gl={{antialias: true, preserveDrawingBuffer: true}}
          camera={{fov: 50, position: [0, 5, 10]}}>
          <Rig look={look} frame={frame} night={dark} />
          <Lights focus={look.light ?? look.at} night={dark} />
          <w.View look={look} frame={frame} shot={name} night={dark} hero={hero} heroPose={heroPose} heroExpr={heroExpr} props={props} latar={latar} efek={efek} />
        </ThreeCanvas>
        {Overlay && <Overlay frames={frames} />}
        <Vignette />
      </AbsoluteFill>
    );
  };
