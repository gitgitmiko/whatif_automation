import {createContext, useContext} from 'react';
import {AbsoluteFill, Easing, interpolate, random, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene} from './Short';
import {Stamp, YELLOW, cueFrame} from './visuals';

// The POV hero: the thing "kamu" has become, drawn the same way in every scene of a video. A machine or object is a
// box body (its colour, a screen face, an emoji badge on the chest); anything else is its emoji with a face on it.
export type Hero = {name?: string; emoji?: string; body?: 'box' | 'emoji'; color?: string; face?: boolean};
export const HeroContext = createContext<Hero>({});

const FONT = 'Anton';
const EMOJI = 'Noto Color Emoji';
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const REACTION: Record<string, string> = {happy: '😄', shock: '😱', tired: '😴', angry: '😤', sad: '😢', dizzy: '😵‍💫',
  love: '😍', smug: '😏', scared: '😨', proud: '😎'};
export const MOODS = ['happy', 'shock', 'tired', 'angry', 'sad', 'dizzy', 'love', 'smug', 'scared', 'proud'];

const shade = (hex: string, k: number) => {
  const n = parseInt(hex.replace('#', '').padEnd(6, '0').slice(0, 6), 16);
  const f = (c: number) => Math.max(0, Math.min(255, Math.round(k < 0 ? c * (1 + k) : c + (255 - c) * k)));
  return `rgb(${f(n >> 16)},${f((n >> 8) & 255)},${f(n & 255)})`;
};

// A face drawn on a 200x120 box centred at 0,0. `ink` is the line colour.
const Face: React.FC<{mood: string; ink: string; frame: number}> = ({mood, ink, frame}) => {
  const blink = frame % 70 > 66 && !['shock', 'dizzy', 'love', 'tired'].includes(mood);
  const s = {stroke: ink, strokeWidth: 9, strokeLinecap: 'round' as const, fill: 'none'};
  const eyes = (x: number) => {
    if (blink) return <path d={`M${x - 16},0 L${x + 16},0`} {...s} />;
    switch (mood) {
      case 'happy': case 'proud': return <path d={`M${x - 18},6 Q${x},-18 ${x + 18},6`} {...s} />;
      case 'shock': return <><circle cx={x} cy={-2} r={22} fill="white" stroke={ink} strokeWidth={6} /><circle cx={x} cy={-2} r={8} fill={ink} /></>;
      case 'tired': return <><path d={`M${x - 20},-2 L${x + 20},-2`} {...s} /><path d={`M${x - 16},-2 Q${x},12 ${x + 16},-2`} {...s} strokeWidth={6} /></>;
      case 'angry': return <><path d={`M${x - 22},${x < 0 ? -26 : -14} L${x + 22},${x < 0 ? -14 : -26}`} {...s} /><circle cx={x} cy={4} r={9} fill={ink} /></>;
      case 'sad': return <><path d={`M${x - 20},${x < 0 ? -14 : -24} L${x + 20},${x < 0 ? -24 : -14}`} {...s} strokeWidth={7} /><circle cx={x} cy={4} r={9} fill={ink} /></>;
      case 'dizzy': {
        const r = frame * 12;
        return <g transform={`translate(${x},0) rotate(${x < 0 ? r : -r})`}><path d="M0,0 m-4,0 a4,4 0 1,1 8,0 a9,9 0 1,1 -16,0 a14,14 0 1,1 26,0" {...s} strokeWidth={5} /></g>;
      }
      case 'love': {
        const k = 1 + Math.sin(frame / 4) * 0.12;
        return <path transform={`translate(${x},0) scale(${k})`} d="M0,14 C-26,-4 -18,-24 0,-12 C18,-24 26,-4 0,14Z" fill="#ff3b6b" />;
      }
      case 'smug': return x < 0 ? <path d={`M${x - 18},0 L${x + 18},0`} {...s} /> : <><path d={`M${x - 18},-24 L${x + 18},-30`} {...s} strokeWidth={6} /><circle cx={x} cy={2} r={9} fill={ink} /></>;
      case 'scared': {
        const j = Math.sin(frame * 2.3) * 2;
        return <><circle cx={x + j} cy={0} r={16} fill="white" stroke={ink} strokeWidth={5} /><circle cx={x + j} cy={0} r={5} fill={ink} /></>;
      }
      default: return <circle cx={x} cy={0} r={10} fill={ink} />;
    }
  };
  const mouth = (() => {
    switch (mood) {
      case 'happy': return <path d="M-26,34 Q0,60 26,34" {...s} />;
      case 'proud': return <path d="M-30,32 Q0,66 30,32 Z" fill={ink} stroke={ink} strokeWidth={6} strokeLinejoin="round" />;
      case 'shock': return <ellipse cx={0} cy={44} rx={14} ry={18 + Math.sin(frame / 3) * 2} fill={ink} />;
      case 'tired': return <path d="M-16,42 L16,42" {...s} />;
      case 'angry': return <path d="M-24,50 Q0,30 24,50" {...s} />;
      case 'sad': return <path d="M-22,50 Q0,32 22,50" {...s} />;
      case 'dizzy': case 'scared': return <path d="M-28,42 q7,-10 14,0 t14,0 t14,0 t14,0" {...s} strokeWidth={6} />;
      case 'love': return <path d="M-18,36 Q0,52 18,36" {...s} />;
      case 'smug': return <path d="M-20,42 Q8,48 26,30" {...s} />;
      default: return <path d="M-20,40 Q0,52 20,40" {...s} />;
    }
  })();
  return (
    <g>
      {eyes(-46)}{eyes(46)}{mouth}
      {mood === 'sad' && <ellipse cx={46} cy={24 + ((frame * 3) % 50)} rx={7} ry={11} fill="#6ad0ff" opacity={1 - ((frame * 3) % 50) / 50} />}
      {(mood === 'scared' || mood === 'tired') && <path d="M86,-40 q8,16 0,22 q-8,-6 0,-22Z" fill="#6ad0ff" />}
      {(mood === 'happy' || mood === 'love' || mood === 'proud') && <><ellipse cx={-78} cy={30} rx={16} ry={9} fill="#ff7a9a" opacity={0.6} /><ellipse cx={78} cy={30} rx={16} ry={9} fill="#ff7a9a" opacity={0.6} /></>}
    </g>
  );
};

// The hero itself, about 460 px wide, its feet at the bottom of its box.
export const HeroFigure: React.FC<{hero: Hero; mood: string; size?: number}> = ({hero, mood, size = 1}) => {
  const frame = useCurrentFrame();
  const color = hero.color && /^#[0-9a-f]{6}$/i.test(hero.color) ? hero.color : '#2f7de1';
  if (hero.body === 'emoji') {
    return (
      <div style={{position: 'relative', width: 480 * size, height: 480 * size}}>
        <span style={{fontFamily: EMOJI, fontSize: 440 * size, lineHeight: 1, position: 'absolute', left: 0, top: 0,
          filter: 'drop-shadow(0 26px 30px rgba(0,0,0,.45))'}}>{hero.emoji ?? '🙂'}</span>
        {hero.face === false && (
          <span style={{position: 'absolute', right: -40 * size, top: -30 * size, fontFamily: EMOJI, fontSize: 150 * size,
            transform: `scale(${spring({frame, fps: 30, config: {damping: 8, stiffness: 200}})}) rotate(${Math.sin(frame / 7) * 10}deg)`,
            filter: 'drop-shadow(0 10px 12px rgba(0,0,0,.4))'}}>{REACTION[mood] ?? '🙂'}</span>
        )}
        {hero.face !== false && (
          <svg width={480 * size} height={480 * size} viewBox="-240 -240 480 480" style={{position: 'absolute', left: 0, top: 0}}>
            <g transform="translate(0,0) scale(1.15)">
              <ellipse cx={-46} cy={0} rx={34} ry={34} fill="white" opacity={0.0} />
              <Face mood={mood} ink="#111" frame={frame} />
            </g>
          </svg>
        )}
      </div>
    );
  }
  const W = 460, H = 620;
  return (
    <svg width={W * size} height={(H + 60) * size} viewBox={`${-W / 2 - 60} -20 ${W + 120} ${H + 60}`} style={{overflow: 'visible'}}>
      <ellipse cx={0} cy={H + 18} rx={W * 0.55} ry={26} fill="black" opacity={0.35} />
      <rect x={-W / 2 + 70} y={H - 10} width={60} height={34} rx={10} fill={shade(color, -0.55)} />
      <rect x={W / 2 - 130} y={H - 10} width={60} height={34} rx={10} fill={shade(color, -0.55)} />
      <path d={`M${-W / 2 + 6},${H * 0.55} q-60,${40 + Math.sin(frame / 8) * 16} -46,110`} stroke={shade(color, -0.35)} strokeWidth={26} strokeLinecap="round" fill="none" />
      <path d={`M${W / 2 - 6},${H * 0.55} q60,${40 + Math.cos(frame / 8) * 16} 46,110`} stroke={shade(color, -0.35)} strokeWidth={26} strokeLinecap="round" fill="none" />
      <rect x={-W / 2} y={0} width={W} height={H} rx={46} fill={shade(color, -0.3)} />
      <rect x={-W / 2} y={0} width={W - 26} height={H - 18} rx={44} fill={color} />
      <rect x={-W / 2 + 26} y={22} width={W - 120} height={26} rx={13} fill="white" opacity={0.22} />
      <rect x={-170} y={70} width={314} height={210} rx={30} fill="#0c1d2e" stroke={shade(color, -0.45)} strokeWidth={12} />
      <rect x={-158} y={82} width={290} height={186} rx={22} fill="#123e57" opacity={0.6} />
      <g transform="translate(-13,170)"><Face mood={mood} ink="#7dfcff" frame={frame} /></g>
      <circle cx={-13} cy={400} r={92} fill="white" opacity={0.92} />
      <text x={-13} y={438} textAnchor="middle" fontFamily={EMOJI} fontSize={110}>{hero.emoji ?? '❔'}</text>
      <rect x={-130} y={526} width={234} height={22} rx={11} fill={shade(color, -0.5)} />
    </svg>
  );
};

// pov: {mood, say, motion: idle|shake|jump|spin|shiver|tilt, props: [emoji], props_motion: around|rain|queue|burst, stamp}
const PropLayer: React.FC<{props: string[]; mode: string; at: number; ready?: boolean}> = ({props, mode, at, ready}) => {
  const frame = useCurrentFrame() + (ready ? 30 : 0);
  return (
    <>
      {props.slice(0, 4).flatMap((e, i) => {
        if (mode === 'in' || mode === 'hit') {
          // in: flies from off-screen into the hero's chest and vanishes there; hit: strikes its side at the cue.
          const side = i % 2 ? 1 : -1;
          const start = at - (mode === 'hit' ? 8 : 12) + i * 4;
          const u = interpolate(frame, [start, start + (mode === 'hit' ? 8 : 12)], [0, 1], {...clamp, easing: Easing.in(Easing.quad)});
          const tx = 485 + side * (mode === 'hit' ? 170 : 0), ty = mode === 'hit' ? 820 : 900;
          const x0 = side < 0 ? -260 : 1200, y0 = mode === 'hit' ? 760 : 520 + i * 60;
          const after = frame - (start + (mode === 'hit' ? 8 : 12));
          const gone = mode === 'in' ? interpolate(after, [0, 4], [1, 0], clamp) : interpolate(after, [6, 16], [1, 0], clamp);
          const bounce = mode === 'hit' && after > 0 ? -side * after * 9 : 0;
          return [<span key={i} style={{position: 'absolute', left: x0 + (tx - x0) * u + bounce, top: y0 + (ty - y0) * u - (mode === 'hit' && after > 0 ? after * 6 - after * after * 0.6 : 0),
            fontFamily: EMOJI, fontSize: 170, opacity: frame < start ? 0 : gone,
            transform: `scale(${mode === 'in' ? 1 - Math.max(after, 0) * 0.2 : 1}) rotate(${mode === 'hit' ? side * -30 + Math.max(after, 0) * side * 20 : 0}deg)`,
            filter: 'drop-shadow(0 12px 14px rgba(0,0,0,.4))'}}>{e}</span>,
            ...(mode === 'hit' && i === 0 && after >= 0 && after < 10 ? [<span key="boom" style={{position: 'absolute', left: tx - 110, top: ty - 60,
              fontFamily: EMOJI, fontSize: 200, opacity: 1 - after / 10, transform: `scale(${0.6 + after * 0.12})`}}>💥</span>] : [])];
        }
        if (mode === 'rain' || mode === 'burst') {
          return Array.from({length: 4}).map((_, k) => {
            const id = `${i}-${k}`;
            const born = (mode === 'burst' ? at : 0) + (i * 4 + k) * 3;
            const u = frame - born;
            if (u < 0) return null;
            let x, y;
            if (mode === 'rain') {
              x = 60 + random(`rx${id}`) * 900;
              y = -150 + ((u * (12 + random(`rv${id}`) * 8)) % 1500);
            } else {
              const a = -Math.PI / 2 + (random(`ba${id}`) - 0.5) * 2.2;
              const v = 16 + random(`bv${id}`) * 10;
              x = 485 + Math.cos(a) * v * u;
              y = 900 + Math.sin(a) * v * u + u * u * 0.55;
            }
            return <span key={id} style={{position: 'absolute', left: x, top: y, fontFamily: EMOJI, fontSize: 110,
              transform: `rotate(${u * (k % 2 ? 7 : -7)}deg)`}}>{e}</span>;
          });
        }
        const born = mode === 'queue' ? i * 6 : i * 5;
        const p = spring({frame: frame - born, fps: 30, config: {damping: 10, stiffness: 160}});
        const spots = mode === 'queue'
          ? [[20, 1110], [190, 1150], [-20, 960], [150, 990]]
          : [[40, 560], [850, 600], [20, 1050], [860, 1030]];
        const [x, y] = spots[i];
        return [<span key={i} style={{position: 'absolute', left: x, top: y + Math.sin(frame / 8 + i * 2) * 14, fontFamily: EMOJI,
          fontSize: mode === 'queue' ? 170 : 150, transform: `scale(${p})`, filter: 'drop-shadow(0 12px 14px rgba(0,0,0,.4))'}}>{e}</span>];
      })}
    </>
  );
};

const Bubble: React.FC<{text?: string; at: number}> = ({text, at}) => {
  const frame = useCurrentFrame();
  const p = spring({frame: frame - at, fps: 30, config: {damping: 9, stiffness: 200}});
  if (!text || p <= 0.001) return null;
  return (
    <div style={{position: 'absolute', top: 360, left: 0, right: 0, display: 'flex', justifyContent: 'center',
      transform: `scale(${p}) rotate(${Math.sin(frame / 14) * 1.5}deg)`, transformOrigin: '50% 100%'}}>
      <div style={{position: 'relative', background: 'white', borderRadius: 40, padding: '18px 40px', maxWidth: 820,
        border: '8px solid #111', boxShadow: '0 12px 0 rgba(0,0,0,.35)'}}>
        <span style={{fontFamily: FONT, fontSize: text.length > 22 ? 62 : 76, color: '#111', lineHeight: 1.1,
          textTransform: 'uppercase', textAlign: 'center', display: 'block'}}>{text}</span>
        <div style={{position: 'absolute', bottom: -40, left: '50%', marginLeft: -20, width: 0, height: 0,
          borderLeft: '22px solid transparent', borderRight: '22px solid transparent', borderTop: '40px solid #111'}} />
      </div>
    </div>
  );
};

export const Pov: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const hero = useContext(HeroContext);
  const v = scene.visual;
  const at = cueFrame(scene.words, scene.cue, Math.round(scene.frames * 0.3));
  const mood = MOODS.includes(v.mood) ? v.mood : 'happy';
  const motion = v.motion ?? 'idle';
  const since = frame - at;
  let x = 0, y = 0, rot = 0, sx = 1, sy = 1;
  const breathe = Math.sin(frame / 9);
  sx = 1 + breathe * 0.015; sy = 1 - breathe * 0.015;
  if (v.props_motion === 'hit' && since >= 0) x += Math.sin(since * 2.4) * 40 * Math.exp(-since / 8);
  if (motion === 'shake' && since >= 0) x = Math.sin(since * 2.2) * 34 * Math.exp(-since / 10);
  if (motion === 'shiver') x = Math.sin(frame * 3.1) * 7;
  if (motion === 'jump' && since >= 0) {
    const j = spring({frame: since, fps, config: {damping: 7, stiffness: 120}});
    y = -Math.sin(Math.min(since / 14, 1) * Math.PI) * 220;
    sy *= since < 3 ? 0.85 : 1 + (1 - j) * 0.08;
  }
  if (motion === 'spin') rot = interpolate(frame, [at, at + 30], [0, 360], {...clamp, easing: Easing.out(Easing.cubic)});
  if (motion === 'tilt') rot = interpolate(frame, [at, at + 20], [0, -14], clamp) + Math.sin(frame / 12) * 2;
  if (mood === 'angry' && motion === 'idle') x = Math.sin(frame * 1.5) * 3;
  return (
    <AbsoluteFill>
      {mood === 'angry' && <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 55%, rgba(255,40,0,.35), transparent 60%)'}} />}
      {mood === 'love' && <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 55%, rgba(255,90,160,.3), transparent 60%)'}} />}
      {!['burst', 'in', 'hit'].includes(v.props_motion ?? 'around') && <PropLayer props={v.props ?? []} mode={v.props_motion ?? 'around'} at={at} ready={scene.from === 0} />}
      <div style={{position: 'absolute', left: 0, right: 0, top: 540, display: 'flex', justifyContent: 'center'}}>
        <div style={{transform: `translate(${x}px, ${y}px) rotate(${rot}deg) scale(${sx}, ${sy})`, transformOrigin: '50% 100%'}}>
          <HeroFigure hero={hero} mood={mood} size={hero.body === 'emoji' ? 1.25 : 1.15} />
        </div>
      </div>
      {mood === 'tired' && [0, 1, 2].map((i) => {
        const u = (frame + i * 20) % 60;
        return <span key={i} style={{position: 'absolute', left: 760 + u * 2, top: 600 - u * 4, fontFamily: FONT, fontSize: 60 + i * 10,
          color: 'white', opacity: 1 - u / 60}}>Z</span>;
      })}
      {['burst', 'in', 'hit'].includes(v.props_motion) && <PropLayer props={v.props ?? []} mode={v.props_motion} at={at} />}
      <Bubble text={v.say} at={scene.from === 0 ? -20 : 6} />
      <Stamp at={at} text={v.stamp} top={1200} color={mood === 'angry' || mood === 'shock' ? '#ff3b3b' : YELLOW} />
    </AbsoluteFill>
  );
};

// The closing scene with the hero waving next to the question for the comments.
export const PovOutro: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const hero = useContext(HeroContext);
  const q = spring({frame, fps: 30, config: {damping: 7, stiffness: 180}});
  const c = spring({frame: frame - cueFrame(scene.words, 'tulis', Math.round(scene.frames * 0.5)), fps: 30,
    config: {damping: 10, stiffness: 180}});
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 0, right: 0, top: 470, display: 'flex', justifyContent: 'center',
        transform: `rotate(${Math.sin(frame / 5) * 4}deg)`, transformOrigin: '50% 100%'}}>
        <HeroFigure hero={hero} mood={scene.visual.mood ?? 'happy'} size={hero.body === 'emoji' ? 1.05 : 0.85} />
      </div>
      <div style={{position: 'absolute', top: 420, right: 70, fontFamily: FONT, fontSize: 240, color: YELLOW,
        WebkitTextStroke: '14px #000', paintOrder: 'stroke fill',
        transform: `scale(${q}) rotate(${12 + Math.sin(frame / 6) * 8}deg)`, opacity: q}}>?</div>
      <div style={{position: 'absolute', top: 1200, width: '100%', textAlign: 'center', opacity: c,
        transform: `translateY(${Math.sin(frame / 5) * 10}px)`}}>
        <span style={{fontFamily: FONT, fontSize: 70, background: '#ff3b3b', color: 'white', padding: '8px 36px',
          borderRadius: 18}}>TULIS DI KOMENTAR ↓</span>
      </div>
    </AbsoluteFill>
  );
};

// Backdrops by place; the hero's world rather than outer space.
export const THEMES: Record<string, string> = {
  kota: 'linear-gradient(#1b2b5e 0%, #3a3f8f 55%, #f08a5d 100%)',
  malam: 'radial-gradient(circle at 50% 30%, #1d2b64 0%, #0b0f2a 60%, #05060f 100%)',
  ruangan: 'linear-gradient(#5b3a8c 0%, #8a4fa0 55%, #f2a65a 100%)',
  alam: 'linear-gradient(#0f5e5a 0%, #2a9d8f 55%, #e9c46a 100%)',
  dapur: 'linear-gradient(#7a2e3a 0%, #c0504d 55%, #ffd166 100%)',
  laut: 'linear-gradient(#03396c 0%, #005b96 55%, #6497b1 100%)',
};
