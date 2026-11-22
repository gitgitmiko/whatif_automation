import {AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame} from 'remotion';
import type {Scene} from './Short';
import {Word, cueFrame} from './visuals';

// The 3D style, after the explainer Shorts that pull tens of millions: one rendered picture per scene, a camera that
// never stops moving, soft dissolves instead of cuts, small clean captions and a floating label on the key number.

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const XFADE = 8;
const SANS = 'Montserrat';

// camera: push | pull | pan_left | pan_right | rise | fall
const move = (camera: string | undefined, t: number) => {
  const e = Easing.inOut(Easing.sin)(t);
  switch (camera) {
    case 'pull': return {s: interpolate(e, [0, 1], [1.32, 1.1]), x: 0, y: 0};
    case 'pan_left': return {s: 1.22, x: interpolate(e, [0, 1], [60, -60]), y: 0};
    case 'pan_right': return {s: 1.22, x: interpolate(e, [0, 1], [-60, 60]), y: 0};
    case 'rise': return {s: 1.2, x: 0, y: interpolate(e, [0, 1], [70, -70])};
    case 'fall': return {s: 1.2, x: 0, y: interpolate(e, [0, 1], [-70, 70])};
    default: return {s: interpolate(e, [0, 1], [1.08, 1.3]), x: 0, y: 0};
  }
};

export const ImageScene: React.FC<{scene: Scene; frames: number; lead: number}> = ({scene, frames, lead}) => {
  const frame = useCurrentFrame();
  const {s, x, y} = move(scene.camera, frame / frames);
  const fade = lead ? interpolate(frame, [0, lead], [0, 1], clamp) : 1;
  // A little jolt on the cue word keeps the eye awake through a long shot.
  const at = lead + cueFrame(scene.words, scene.cue, -999);
  const jolt = at > 0 ? spring({frame: frame - at, fps: 30, config: {damping: 12, stiffness: 200}}) : 1;
  const punch = at > 0 && frame >= at ? 1 + (1 - jolt) * 0.06 : 1;
  return (
    <AbsoluteFill style={{opacity: fade, overflow: 'hidden', background: '#000'}}>
      <Img src={staticFile(scene.image ?? '')} style={{width: '100%', height: '100%', objectFit: 'cover',
        transform: `translate(${x}px, ${y}px) scale(${s * punch})`}} />
    </AbsoluteFill>
  );
};

// A short word or number floating up beside the subject at the cue ("300 KG", "3×").
export const Label: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  if (!scene.label) return null;
  const at = cueFrame(scene.words, scene.cue, Math.round(scene.frames * 0.3));
  const p = spring({frame: frame - at, fps: 30, config: {damping: 11, stiffness: 150}});
  if (p <= 0.001) return null;
  return (
    <div style={{position: 'absolute', top: 640, width: '100%', textAlign: 'center', opacity: Math.min(p * 1.5, 1),
      transform: `translateY(${(1 - p) * 50 - frame * 0.4}px) scale(${interpolate(p, [0, 1], [0.7, 1])})`}}>
      <span style={{fontFamily: SANS, fontWeight: 800, fontSize: 120, color: '#7fe3ff', letterSpacing: 1,
        textShadow: '0 0 30px rgba(80,200,255,.75), 0 6px 18px rgba(0,0,0,.6)'}}>{scene.label}</span>
    </div>
  );
};

// Two or three words at a time, white, mid-screen, the spoken one slightly brighter: read without being looked at.
export const SoftCaptions: React.FC<{words: Word[]}> = ({words}) => {
  const frame = useCurrentFrame();
  const groups: Word[][] = [];
  let cur: Word[] = [];
  for (const w of words) {
    cur.push(w);
    if (cur.length >= 3 || /[.?!,]$/.test(w.w)) { groups.push(cur); cur = []; }
  }
  if (cur.length) groups.push(cur);
  const g = [...groups].reverse().find((x) => x[0].s <= frame) ?? groups[0];
  if (!g) return null;
  return (
    <div style={{position: 'absolute', top: 1180, width: '100%', textAlign: 'center', padding: '0 90px',
      boxSizing: 'border-box'}}>
      <span style={{fontFamily: SANS, fontWeight: 700, fontSize: 62, color: 'white', lineHeight: 1.25,
        textShadow: '0 3px 12px rgba(0,0,0,.85), 0 0 3px rgba(0,0,0,.9)'}}>
        {g.map((w) => w.w.replace(/[,;:]$/, '')).join(' ')}</span>
    </div>
  );
};

export const TopTag: React.FC<{title: string; from?: number}> = ({title, from = 0}) => {
  const frame = useCurrentFrame();
  const show = interpolate(frame, [from, from + 8], [0, 1], clamp);
  if (show <= 0) return null;
  return (
  <div style={{position: 'absolute', top: 150, width: '100%', textAlign: 'center', opacity: show}}>
    <span style={{fontFamily: SANS, fontWeight: 800, fontSize: 48, color: 'white', background: 'rgba(0,0,0,.55)',
      padding: '14px 34px', borderRadius: 44, letterSpacing: 0.5}}>
      <span style={{color: '#FFD400'}}>GIMANA JADINYA?</span> {title.replace(/^kalau\s+/i, '').replace(/\?$/, '')}</span>
  </div>
  );
};

// The first ~1.8 s: the crisis in four giant words, slamming in one by one over a darkened picture. The first frame
// already carries the first word, because that frame is what decides the swipe.
export const HOOK_FRAMES = 54;
export const HookCard: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  if (!text || frame >= HOOK_FRAMES) return null;
  const words = text.toUpperCase().split(/\s+/).filter(Boolean);
  const out = interpolate(frame, [HOOK_FRAMES - 8, HOOK_FRAMES], [1, 0], clamp);
  const shake = frame > words.length * 4 + 6 && frame < words.length * 4 + 14 ? Math.sin(frame * 2.7) * 9 : 0;
  return (
    <AbsoluteFill style={{opacity: out}}>
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(0,0,0,.72) 0%, rgba(0,0,0,.35) 45%, rgba(0,0,0,0) 70%)'}} />
      <div style={{position: 'absolute', top: 330, left: 60, right: 60, textAlign: 'center', transformOrigin: '50% 40%',
        transform: `translateX(${shake}px) scale(${interpolate(frame, [0, 7], [1.3, 1], {...clamp, easing: Easing.out(Easing.back(2.2))})})`}}>
        {words.map((w, i) => {
          // Whole line readable on frame 0, slammed in from big; each word then gets its own little kick.
          const kick = spring({frame: frame - 8 - i * 4, fps: 30, config: {damping: 9, stiffness: 260}});
          const bump = frame >= 8 + i * 4 ? 1 + (1 - kick) * 0.18 : 1;
          return (
            <span key={i} style={{display: 'inline-block', margin: '0 18px', fontFamily: 'Anton', fontSize: 168, lineHeight: 1.08,
              color: i % 2 ? 'white' : '#FFD400', transform: `scale(${bump})`,
              WebkitTextStroke: '14px #000', paintOrder: 'stroke fill', textShadow: '0 12px 0 rgba(0,0,0,.5)'}}>{w}</span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
