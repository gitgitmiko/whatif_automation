import {AbsoluteFill, Easing, interpolate, random, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene} from './Short';

// The scene library. Every scene picks one visual by `type` and fills its fields (shorts/produce.py documents them
// for the writer); `scene.cue` is the spoken word its main action, stamp and sound effect land on. Emoji (Noto Color
// Emoji) are the vocabulary for things, so any topic can be drawn.

export type Word = {w: string; s: number; e: number};
export type Visual = {type: string; stamp?: string; [k: string]: any};

// The frame (within its scene) where the first word starting with `key` is spoken.
export const cueFrame = (words: Word[], key?: string, fallback = 0) => {
  if (!key) return fallback;
  const k = key.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
  const hit = words.find((w) => w.w.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '').startsWith(k));
  return hit ? hit.s : fallback;
};
const cueOf = (scene: Scene) => cueFrame(scene.words, scene.cue, Math.round(scene.frames * 0.3));

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const YELLOW = '#FFD400';
const FONT = 'Anton';
const EMOJI = 'Noto Color Emoji';
const PALETTE = ['#5ab8ff', '#ff7ad9', '#7dff9a', '#ff9f43'];
const fmt = (v: number) => v.toLocaleString('id-ID', {maximumFractionDigits: v < 10 ? 1 : 0});

const usePop = (at: number, damping = 10) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: frame - at, fps, config: {damping, stiffness: 180}});
};

const Emoji: React.FC<{e: string; size: number; style?: React.CSSProperties}> = ({e, size, style}) => (
  <span style={{fontFamily: EMOJI, fontSize: size, lineHeight: 1, display: 'inline-block', ...style}}>{e}</span>
);

// A word slammed onto the screen at frame `at`.
export const Stamp: React.FC<{at: number; text?: string; color?: string; top: number; rotate?: number; size?: number}> = (
  {at, text, color = YELLOW, top, rotate = -5, size = 116}) => {
  const p = usePop(at, 9);
  if (!text || p <= 0.001) return null;
  return (
    <div style={{position: 'absolute', top, width: '100%', textAlign: 'center', padding: '0 50px', boxSizing: 'border-box',
      transform: `scale(${interpolate(p, [0, 1], [2.6, 1])}) rotate(${rotate}deg)`, opacity: Math.min(p * 2, 1)}}>
      <span style={{fontFamily: FONT, fontSize: text.length > 16 ? size * 0.8 : size, lineHeight: 1.1, color,
        WebkitTextStroke: '12px #000', paintOrder: 'stroke fill', textShadow: '0 10px 0 rgba(0,0,0,.5)',
        letterSpacing: 2, textTransform: 'uppercase'}}>{text}</span>
    </div>
  );
};

export const Stars: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <svg width={1080} height={1920}>
        {Array.from({length: 90}).map((_, i) => (
          <circle key={i} cx={random(`x${i}`) * 1080} cy={random(`y${i}`) * 1920} r={1 + random(`r${i}`) * 2.5}
            fill="white" opacity={(0.4 + 0.6 * Math.abs(Math.sin(frame / 20 + i))) * 0.7} />
        ))}
      </svg>
    </AbsoluteFill>
  );
};

const Center: React.FC<{y?: number; children: React.ReactNode}> = ({y = 860, children}) => (
  <div style={{position: 'absolute', left: 0, right: 0, top: y, display: 'flex', justifyContent: 'center',
    transform: 'translateY(-50%)'}}>{children}</div>
);

const Flash: React.FC<{at: number}> = ({at}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: 'white', opacity: interpolate(frame - at, [0, 1, 10], [0, 0.75, 0], clamp)}} />;
};

const shakeAt = (frame: number, at: number, amp = 30) =>
  frame >= at ? Math.sin((frame - at) * 2.2) * amp * Math.exp(-(frame - at) / 8) : 0;

// Rough continents on a 200-unit strip scrolling behind a round mask: a spinning globe.
const LAND = [
  'M20,-50 C35,-72 62,-62 55,-35 C50,-15 30,-20 25,-5 C15,-10 5,-35 20,-50Z',
  'M40,0 C55,-5 62,20 50,45 C45,62 38,55 37,35 C35,20 32,8 40,0Z',
  'M95,-55 C120,-68 155,-58 165,-40 C152,-25 132,-30 122,-20 C106,-25 90,-40 95,-55Z',
  'M100,-15 C116,-20 126,-5 122,15 C118,36 108,46 102,30 C98,15 92,0 100,-15Z',
  'M160,22 C176,16 188,26 181,37 C170,42 157,33 160,22Z',
  'M138,2 C146,-2 152,4 148,9 C142,10 135,6 138,2Z M152,6 C158,4 162,9 158,12 C154,13 150,10 152,6Z',
  'M60,-85 C80,-92 120,-92 140,-84 C120,-78 80,-78 60,-85Z',
];

export const Earth: React.FC<{rot: number; size: number; night?: boolean; tint?: string; tintOpacity?: number}> = (
  {rot, size, night, tint, tintOpacity = 0}) => {
  const off = ((rot % 200) + 200) % 200;
  return (
    <svg width={size} height={size} viewBox="-100 -100 200 200" style={{overflow: 'visible'}}>
      <defs>
        <radialGradient id="sea" cx="35%" cy="30%">
          <stop offset="0%" stopColor="#4fc3ff" /><stop offset="100%" stopColor="#0b3d91" />
        </radialGradient>
        <radialGradient id="shade" cx="35%" cy="30%">
          <stop offset="55%" stopColor="black" stopOpacity="0" /><stop offset="100%" stopColor="black" stopOpacity=".55" />
        </radialGradient>
        <linearGradient id="term" x1="0" x2="1">
          <stop offset="48%" stopColor="#020414" stopOpacity="0" /><stop offset="56%" stopColor="#020414" stopOpacity=".88" />
        </linearGradient>
        <clipPath id="globe"><circle r={90} /></clipPath>
      </defs>
      <circle r={98} fill={tint ?? '#5ab8ff'} opacity={0.18 + tintOpacity * 0.2} />
      <circle r={90} fill="url(#sea)" />
      <g clipPath="url(#globe)">
        {[-1, 0, 1].map((k) => (
          <g key={k} transform={`translate(${k * 200 - off - 100},0)`}>
            {LAND.map((d, i) => <path key={i} d={d} fill="#3bb36b" stroke="#2a8a50" strokeWidth={1.5} />)}
          </g>
        ))}
      </g>
      {tint && <circle r={90} fill={tint} opacity={tintOpacity} />}
      <circle r={90} fill="url(#shade)" />
      {night && <circle r={90} fill="url(#term)" />}
    </svg>
  );
};

// globe: {mode: spin|stop|night|hot|frozen, stamp}
const Globe: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const at = cueOf(scene);
  const mode = v.mode ?? 'spin';
  const rot = mode === 'stop' ? Math.min(frame, at) * 7 : mode === 'night' ? 30 : frame * 1.6;
  const change = interpolate(frame, [at - 4, at + 20], [0, 1], clamp);
  const tint = mode === 'hot' ? '#ff4d00' : mode === 'frozen' ? '#e8f7ff' : undefined;
  const pulse = mode === 'hot' ? 1 + Math.sin(frame / 4) * 0.015 * change : 1;
  return (
    <AbsoluteFill>
      {mode === 'night' && (
        <div style={{position: 'absolute', left: -170, top: 690, width: 340, height: 340, borderRadius: '50%',
          background: 'radial-gradient(#fff6b0, #ffb300 60%, rgba(255,140,0,0) 72%)',
          transform: `scale(${1 + Math.sin(frame / 8) * 0.04})`, boxShadow: '0 0 160px 60px rgba(255,190,0,.45)'}} />
      )}
      <Center>
        <div style={{transform: `translateX(${mode === 'stop' ? shakeAt(frame, at) : 0}px) scale(${pulse})`, position: 'relative'}}>
          {mode === 'stop' && frame < at && [0, 1, 2].map((i) => (
            <svg key={i} width={760} height={760} viewBox="-100 -100 200 200"
              style={{position: 'absolute', left: -60, top: -60, transform: `rotate(${-frame * 9 + i * 120}deg)`}}>
              <path d="M0,-97 A97,97 0 0 1 84,-48" stroke="white" strokeWidth={2.5} fill="none" opacity={0.5} strokeLinecap="round" />
            </svg>
          ))}
          <Earth rot={rot} size={640} night={mode === 'night'} tint={tint} tintOpacity={change * 0.6} />
        </div>
      </Center>
      <Stamp at={at} text={v.stamp} color={mode === 'stop' ? '#ff3b3b' : YELLOW} top={1180} />
      {mode === 'stop' && <Flash at={at} />}
    </AbsoluteFill>
  );
};

// icon: {emoji, motion: pop|shake|float|spin|grow|shrink|explode, stamp}
const Icon: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const at = cueOf(scene);
  const motion = v.motion ?? 'pop';
  const enter = usePop(0, 9);
  let scale = enter, rotate = 0, x = 0, opacity = 1;
  const y = Math.sin(frame / 12) * 14;
  if (motion === 'shake') x = shakeAt(frame, at, 40);
  if (motion === 'spin') rotate = interpolate(frame, [at, at + 40], [0, 720], {...clamp, easing: Easing.out(Easing.cubic)});
  if (motion === 'grow') scale *= interpolate(frame, [0, at + 15], [0.45, 1.5], {...clamp, easing: Easing.inOut(Easing.cubic)});
  if (motion === 'shrink') scale *= interpolate(frame, [0, at + 15], [1.4, 0.25], {...clamp, easing: Easing.inOut(Easing.cubic)});
  if (motion === 'explode') {
    scale *= interpolate(frame, [at - 3, at, at + 6], [1, 1.25, 1.9], clamp);
    opacity = interpolate(frame, [at + 2, at + 9], [1, 0], clamp);
    x = frame < at ? Math.sin(frame * 1.9) * interpolate(frame, [0, at], [0, 14], clamp) : 0;
  }
  const since = frame - at;
  return (
    <AbsoluteFill>
      {motion === 'explode' && since >= 0 && (
        <>
          {[0, 1, 2].map((i) => {
            const r = Math.max(since - i * 4, 0) * 34;
            return <div key={i} style={{position: 'absolute', left: 540 - r, top: 840 - r, width: r * 2, height: r * 2,
              borderRadius: '50%', border: `${24 - i * 6}px solid rgba(255,${200 - i * 60},0,${Math.max(0, 0.9 - since / 30)})`}} />;
          })}
          {Array.from({length: 10}).map((_, i) => {
            const a = (i / 10) * Math.PI * 2 + random(`a${i}`);
            const d = since * (18 + random(`d${i}`) * 14);
            return <Emoji key={i} e={i % 2 ? '💥' : '🔥'} size={110}
              style={{position: 'absolute', left: 485 + Math.cos(a) * d, top: 785 + Math.sin(a) * d + since * since * 0.4,
                opacity: Math.max(0, 1 - since / 35)}} />;
          })}
        </>
      )}
      <Center>
        <Emoji e={v.emoji ?? '🤔'} size={420} style={{opacity,
          transform: `translate(${x}px, ${y}px) scale(${scale}) rotate(${rotate}deg)`,
          filter: 'drop-shadow(0 30px 40px rgba(0,0,0,.45))'}} />
      </Center>
      <Stamp at={at} text={v.stamp} top={1180} />
      {motion === 'explode' && <Flash at={at} />}
    </AbsoluteFill>
  );
};

// gauge: {value, unit, label, max}
const Gauge: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const at = cueOf(scene);
  const target = Number(v.value) || 0;
  const max = Number(v.max) || Math.max(target * 1.25, 1);
  const val = interpolate(frame, [0, at + 6], [0, target], {...clamp, easing: Easing.out(Easing.cubic)});
  const jitter = frame > at + 6 ? Math.sin(frame * 1.7) * max * 0.003 : 0;
  const angle = interpolate(val + jitter, [0, max], [-120, 120], clamp);
  const pill = usePop(at + 4);
  return (
    <AbsoluteFill>
      <Center y={880}>
        <svg width={860} height={860} viewBox="-120 -120 240 240">
          <path d="M-90.1,52 A104,104 0 1 1 90.1,52" stroke="#1f2a55" strokeWidth={18} fill="none" strokeLinecap="round" />
          <path d="M-90.1,52 A104,104 0 1 1 90.1,52" stroke={YELLOW} strokeWidth={18} fill="none" strokeLinecap="round"
            pathLength={1} strokeDasharray={`${Math.min(val / max, 1)} 1`} />
          {Array.from({length: 11}).map((_, i) => {
            const a = ((-120 + i * 24) * Math.PI) / 180;
            return <line key={i} x1={Math.sin(a) * 82} y1={-Math.cos(a) * 82} x2={Math.sin(a) * 90} y2={-Math.cos(a) * 90}
              stroke="white" strokeWidth={2} opacity={0.6} />;
          })}
          <g transform={`rotate(${angle})`}><path d="M-5,0 L0,-86 L5,0Z" fill="#ff3b3b" /></g>
          <circle r={11} fill="white" />
          <text y={52} textAnchor="middle" fontFamily={FONT} fontSize={fmt(target).length > 7 ? 32 : 44} fill="white">{fmt(val)}</text>
          <text y={76} textAnchor="middle" fontFamily={FONT} fontSize={18} fill={YELLOW} letterSpacing={2}>
            {String(v.unit ?? '').toUpperCase()}</text>
        </svg>
      </Center>
      {v.label && (
        <div style={{position: 'absolute', top: 1220, width: '100%', textAlign: 'center', opacity: pill,
          transform: `translateY(${(1 - pill) * 60}px)`}}>
          <span style={{fontFamily: FONT, fontSize: 60, color: 'white', background: '#ff3b3b', padding: '4px 30px',
            borderRadius: 14, textTransform: 'uppercase'}}>{v.label}</span>
        </div>
      )}
      <Stamp at={at} text={v.stamp} top={420} />
    </AbsoluteFill>
  );
};

// bars: {unit, items: [{label, value, emoji, at, highlight}]}
const Bars: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const items: any[] = (v.items ?? []).slice(0, 4);
  const max = Math.max(...items.map((x) => Number(x.value) || 0), 1);
  const gap = items.length > 3 ? 205 : 250;
  return (
    <AbsoluteFill>
      {items.map((it, i) => {
        const at = cueFrame(scene.words, it.at, i * 10);
        const p = interpolate(frame, [at, at + 14], [0, 1], {...clamp, easing: Easing.out(Easing.back(1.4))});
        const color = it.highlight ? YELLOW : PALETTE[i % PALETTE.length];
        const value = Number(it.value) || 0;
        return (
          <div key={i} style={{position: 'absolute', top: 440 + i * gap, left: 90, right: 60, opacity: Math.min(p * 3, 1)}}>
            <div style={{fontFamily: FONT, fontSize: 52, color: 'white', marginBottom: 8, textTransform: 'uppercase',
              whiteSpace: 'nowrap'}}>{it.emoji && <Emoji e={it.emoji} size={52} style={{marginRight: 14}} />}{it.label}</div>
            <div style={{display: 'flex', alignItems: 'center', gap: 22}}>
              <div style={{height: 80, width: Math.max((value / max) * 620, 14) * p, background: color, borderRadius: 18,
                boxShadow: '0 8px 0 rgba(0,0,0,.35)'}} />
              <span style={{fontFamily: FONT, fontSize: 50, color, whiteSpace: 'nowrap'}}>
                {fmt(value * Math.min(p, 1))} <span style={{fontSize: 30}}>{String(v.unit ?? '').toUpperCase()}</span></span>
            </div>
          </div>
        );
      })}
      <Stamp at={cueOf(scene)} text={v.stamp} top={1190} />
    </AbsoluteFill>
  );
};

// versus: {left: {emoji, label}, right: {emoji, label}, stamp}
const Versus: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const at = cueOf(scene);
  const l = usePop(0), r = usePop(at, 8);
  const side = (s: any, p: number, x: number, color: string) => (
    <div style={{position: 'absolute', top: 560, left: x, width: 480, textAlign: 'center', opacity: Math.min(p * 2, 1),
      transform: `scale(${p}) translateY(${Math.sin(frame / 10 + x) * 10}px)`}}>
      <Emoji e={s?.emoji ?? '❓'} size={250} />
      <div style={{fontFamily: FONT, fontSize: 58, color, marginTop: 30, lineHeight: 1.1, textTransform: 'uppercase',
        WebkitTextStroke: '8px #000', paintOrder: 'stroke fill'}}>{s?.label}</div>
    </div>
  );
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 538, top: 470, width: 4, height: 760, background: 'rgba(255,255,255,.25)'}} />
      {side(v.left, l, 30, 'white')}
      {side(v.right, r, 570, YELLOW)}
      <div style={{position: 'absolute', left: 470, top: 680, width: 140, height: 140, borderRadius: '50%',
        background: '#ff3b3b', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT,
        fontSize: 64, color: 'white', boxShadow: '0 8px 0 rgba(0,0,0,.4)', transform: `scale(${l})`}}>VS</div>
      <Stamp at={at + 6} text={v.stamp} top={1190} />
    </AbsoluteFill>
  );
};

// fly: {emojis: [..], direction: right|left|up|down, ground, stamp}
const Fly: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const at = cueOf(scene);
  const t = Math.max(frame - at, 0);
  const emojis: string[] = (v.emojis ?? ['🏠', '🚗', '🧍']).slice(0, 4);
  const dir = v.direction ?? 'right';
  const ground = v.ground !== false;
  const [dx, dy] = ({right: [1, -0.15], left: [-1, -0.15], up: [0, -1], down: [0, 1]} as Record<string, number[]>)[dir] ?? [1, 0];
  const base = ground ? 1130 : 860;
  return (
    <AbsoluteFill style={{transform: `translateY(${ground ? shakeAt(frame, at, 14) : 0}px)`}}>
      {ground && <div style={{position: 'absolute', top: 1130, left: 0, right: 0, height: 260,
        background: 'linear-gradient(#3bb36b, #2a8a50 30%, #6b4a2b 30%, #4a3020)'}} />}
      {emojis.map((e, i) => {
        const u = Math.max(t - i * 2, 0);
        const d = u * u * 1.5 + u * 8;
        const x = (1080 / (emojis.length + 1)) * (i + 1);
        return <Emoji key={i} e={e} size={200} style={{position: 'absolute', left: x - 100, top: base - 200,
          transform: `translate(${dx * d}px, ${dy * d}px) rotate(${u * (6 + i * 3) * (dx || 1)}deg)`,
          transformOrigin: 'center bottom'}} />;
      })}
      {t > 0 && Array.from({length: 14}).map((_, i) => {
        const horizontal = Math.abs(dx) > 0.5;
        const pos = ((random(`s${i}`) * 1600 + t * 70) % 1700) - 300;
        return <div key={i} style={{position: 'absolute', borderRadius: 4, background: 'rgba(255,255,255,.5)',
          ...(horizontal
            ? {top: 500 + random(`l${i}`) * 600, height: 8, width: 160 + random(`w${i}`) * 240, left: dx > 0 ? pos : 1080 - pos}
            : {left: 80 + random(`l${i}`) * 920, width: 8, height: 160 + random(`w${i}`) * 240, top: dy > 0 ? pos : 1700 - pos})}} />;
      })}
      <Stamp at={at} text={v.stamp} top={480} />
    </AbsoluteFill>
  );
};

// rise: {fluid: water|lava|ice|sand, stamp}: a city drowning
const FLUIDS: Record<string, [string, string, string]> = {
  water: ['#0b3d91', '#1e7fd9', 'white'], lava: ['#7a1500', '#ff5a00', '#ffd27a'],
  ice: ['#6fb7d6', '#dff6ff', 'white'], sand: ['#8a5a2b', '#e0b56a', '#fff1c9'],
};
const Rise: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const at = cueOf(scene);
  const [deep, body, foam] = FLUIDS[v.fluid] ?? FLUIDS.water;
  const level = interpolate(frame, [0, at + 8], [1500, 1010], {...clamp, easing: Easing.in(Easing.quad)});
  const wave = (amp: number, phase: number, y: number, open = false) => {
    let d = open ? `M0,${y}` : `M0,1920 L0,${y}`;
    for (let x = 0; x <= 1080; x += 30) d += ` L${x},${y + Math.sin(x / 90 + frame / 4 + phase) * amp - (x / 1080) * amp * 2.5}`;
    return open ? d : d + ' L1080,1920Z';
  };
  return (
    <AbsoluteFill>
      <svg width={1080} height={1920} style={{position: 'absolute'}}>
        <path d={wave(90, 1, level - 90)} fill={deep} opacity={0.55} />
        {[[80, 260], [200, 380], [330, 300], [470, 460], [610, 340], [760, 420], [900, 280]].map(([x, h], i) => (
          <g key={i}>
            <rect x={x} y={1300 - h} width={110} height={h} fill="#26305e" />
            {Array.from({length: Math.floor(h / 60)}).map((_, j) => (
              <rect key={j} x={x + 20} y={1300 - h + 25 + j * 60} width={22} height={26} fill="#ffd96a" opacity={0.8} />
            ))}
          </g>
        ))}
        <path d={wave(70, 0, level + 40)} fill={body} opacity={0.92} />
        <path d={wave(70, 0, level + 40, true)} fill="none" stroke={foam} strokeWidth={12} opacity={0.8} />
        {frame > at - 4 && Array.from({length: 40}).map((_, i) => {
          const u = frame - at + 4;
          return <circle key={i} cx={random(`sx${i}`) * 1080} r={6 + random(`sr${i}`) * 14} fill={foam}
            opacity={Math.max(0, 0.9 - u / 40)} cy={level - 40 - u * (8 + random(`sv${i}`) * 14) + u * u * 0.35} />;
        })}
      </svg>
      <Stamp at={at} text={v.stamp} top={460} />
    </AbsoluteFill>
  );
};

// swarm: {emoji, count_label, stamp}: one becomes many
const Swarm: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const at = cueOf(scene);
  const n = Math.round(interpolate(frame, [0, at + 12], [1, 64], {...clamp, easing: Easing.in(Easing.quad)}));
  const label = usePop(at, 8);
  return (
    <AbsoluteFill>
      {Array.from({length: n}).map((_, i) => {
        const col = i % 8, row = Math.floor(i / 8);
        const x = i === 0 ? 440 : 30 + col * 130 + random(`jx${i}`) * 30;
        const y = i === 0 ? 700 : 420 + row * 115 + random(`jy${i}`) * 30;
        const born = i === 0 ? 0 : (i / 64) * (at + 12);
        const p = interpolate(frame, [born, born + 6], [0, 1], clamp);
        return <Emoji key={i} e={v.emoji ?? '🧍'} size={i === 0 && n === 1 ? 200 : 100}
          style={{position: 'absolute', left: x, top: y + Math.sin(frame / 6 + i) * 6, transform: `scale(${p})`}} />;
      })}
      {v.count_label && (
        <div style={{position: 'absolute', top: 760, width: '100%', textAlign: 'center', opacity: label,
          transform: `scale(${interpolate(label, [0, 1], [2.4, 1])})`}}>
          <span style={{fontFamily: FONT, fontSize: 150, color: YELLOW, WebkitTextStroke: '14px #000',
            paintOrder: 'stroke fill', textTransform: 'uppercase'}}>{v.count_label}</span>
        </div>
      )}
      <Stamp at={at + 8} text={v.stamp} top={1190} />
    </AbsoluteFill>
  );
};

// timeline: {steps: [{time, emoji, label, at}]}
const Step: React.FC<{s: any; at: number; top: number}> = ({s, at, top}) => {
  const p = usePop(at, 11);
  return (
    <div style={{position: 'absolute', top, left: 60, right: 50, display: 'flex', alignItems: 'center', gap: 28,
      opacity: Math.min(p * 2, 1), transform: `translateX(${(1 - p) * -200}px)`}}>
      <div style={{width: 190, height: 100, borderRadius: 20, background: YELLOW, display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontFamily: FONT, fontSize: String(s.time ?? '').length > 8 ? 34 : 44, color: '#111',
        textAlign: 'center', lineHeight: 1, textTransform: 'uppercase', flexShrink: 0}}>{s.time}</div>
      {s.emoji && <Emoji e={s.emoji} size={110} />}
      <div style={{fontFamily: FONT, fontSize: 54, color: 'white', lineHeight: 1.1, textTransform: 'uppercase'}}>{s.label}</div>
    </div>
  );
};
const Timeline: React.FC<{scene: Scene}> = ({scene}) => {
  const steps: any[] = (scene.visual.steps ?? []).slice(0, 4);
  const gap = 760 / Math.max(steps.length, 1);
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 150, top: 470, width: 8, height: gap * Math.max(steps.length - 1, 0) + 20,
        background: 'rgba(255,255,255,.25)', borderRadius: 4}} />
      {steps.map((s, i) => (
        <Step key={i} s={s} top={430 + i * gap}
          at={cueFrame(scene.words, s.at, Math.round((scene.frames * 0.8 * i) / steps.length))} />
      ))}
    </AbsoluteFill>
  );
};

// thermo: {value, unit, min, max, label, stamp}
const Thermo: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const at = cueOf(scene);
  const target = Number(v.value) || 0;
  const lo = Number(v.min ?? Math.min(0, target - 20)), hi = Number(v.max ?? Math.max(target * 1.2, lo + 50));
  const val = interpolate(frame, [0, at + 8], [lo + (hi - lo) * 0.3, target], {...clamp, easing: Easing.out(Easing.cubic)});
  const f = Math.min(Math.max((val - lo) / (hi - lo), 0.02), 1);
  const color = target >= 40 ? '#ff3b1f' : target <= 0 ? '#5ab8ff' : '#ffb300';
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 190, top: 430, width: 120, height: 700, borderRadius: 60,
        background: '#1f2a55', border: '10px solid white', overflow: 'hidden'}}>
        <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: `${f * 100}%`, background: color}} />
      </div>
      <div style={{position: 'absolute', left: 150, top: 1080, width: 200, height: 200, borderRadius: '50%',
        background: color, border: '10px solid white'}} />
      <div style={{position: 'absolute', left: 400, top: 620, fontFamily: FONT, fontSize: 170, color: 'white',
        WebkitTextStroke: '12px #000', paintOrder: 'stroke fill', whiteSpace: 'nowrap'}}>
        {fmt(val)}<span style={{fontSize: 90, color}}>{v.unit ?? '°C'}</span></div>
      {v.label && <div style={{position: 'absolute', left: 410, top: 870, right: 40, fontFamily: FONT, fontSize: 56, color: YELLOW,
        textTransform: 'uppercase', lineHeight: 1.1}}>{v.label}</div>}
      <Stamp at={at + 6} text={v.stamp} top={1190} />
    </AbsoluteFill>
  );
};

// number: {value, unit, label, emoji, stamp}: one big figure counting up
const BigNumber: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const at = cueOf(scene);
  const target = Number(v.value) || 0;
  const val = interpolate(frame, [0, at + 8], [0, target], {...clamp, easing: Easing.out(Easing.cubic)});
  const e = usePop(0, 9);
  const text = fmt(val);
  return (
    <AbsoluteFill>
      {v.emoji && <Center y={580}><Emoji e={v.emoji} size={260} style={{transform: `scale(${e}) translateY(${Math.sin(frame / 10) * 10}px)`}} /></Center>}
      <div style={{position: 'absolute', top: v.emoji ? 760 : 640, width: '100%', textAlign: 'center', fontFamily: FONT,
        fontSize: fmt(target).length > 9 ? 150 : 210, color: YELLOW, WebkitTextStroke: '14px #000', paintOrder: 'stroke fill',
        lineHeight: 1}}>{text}</div>
      <div style={{position: 'absolute', top: v.emoji ? 990 : 870, width: '100%', textAlign: 'center', fontFamily: FONT,
        fontSize: 70, color: 'white', textTransform: 'uppercase'}}>{v.unit}</div>
      {v.label && <div style={{position: 'absolute', top: v.emoji ? 1090 : 970, width: '100%', textAlign: 'center',
        fontFamily: FONT, fontSize: 48, color: 'rgba(255,255,255,.75)', textTransform: 'uppercase', padding: '0 60px',
        boxSizing: 'border-box'}}>{v.label}</div>}
      <Stamp at={at + 8} text={v.stamp} top={1190} />
    </AbsoluteFill>
  );
};

// wind: {emoji, stamp}: a gale bending something
const Wind: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const v = scene.visual;
  const at = cueOf(scene);
  const power = interpolate(frame, [at - 6, at + 10], [0.25, 1], clamp);
  return (
    <AbsoluteFill>
      {Array.from({length: 46}).map((_, i) => {
        const speed = (40 + random(`v${i}`) * 50) * power;
        return <div key={i} style={{position: 'absolute', top: 330 + random(`y${i}`) * 1100, height: 5 + random(`h${i}`) * 6,
          width: 120 + random(`w${i}`) * 380, borderRadius: 6, background: `rgba(180,220,255,${0.25 + power * 0.4})`,
          left: ((random(`x${i}`) * 1600 + frame * speed) % 1700) - 400}} />;
      })}
      <Center y={850}>
        <Emoji e={v.emoji ?? '🌴'} size={380} style={{transformOrigin: 'center bottom',
          transform: `rotate(${power * 35 + Math.sin(frame / 2) * 5 * power}deg) translateX(${power * 30}px)`}} />
      </Center>
      <Stamp at={at} text={v.stamp} top={1180} />
    </AbsoluteFill>
  );
};

// outro: the question back to the viewer
const Outro: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const q = usePop(0, 7);
  const c = usePop(cueFrame(scene.words, 'tulis', Math.round(scene.frames * 0.5)));
  return (
    <AbsoluteFill>
      <Center y={560}><Earth rot={frame * 1.5} size={320} /></Center>
      <div style={{position: 'absolute', top: 700, width: '100%', textAlign: 'center', fontFamily: FONT, fontSize: 300,
        color: YELLOW, WebkitTextStroke: '14px #000', paintOrder: 'stroke fill',
        transform: `scale(${q}) rotate(${Math.sin(frame / 6) * 8}deg)`, opacity: q}}>?</div>
      <div style={{position: 'absolute', top: 1180, width: '100%', textAlign: 'center', opacity: c,
        transform: `translateY(${Math.sin(frame / 5) * 10}px)`}}>
        <span style={{fontFamily: FONT, fontSize: 70, background: '#ff3b3b', color: 'white', padding: '8px 36px',
          borderRadius: 18}}>TULIS DI KOMENTAR ↓</span>
      </div>
    </AbsoluteFill>
  );
};

export const VISUALS: Record<string, React.FC<{scene: Scene}>> = {
  globe: Globe, icon: Icon, gauge: Gauge, bars: Bars, versus: Versus, fly: Fly, rise: Rise, swarm: Swarm,
  timeline: Timeline, thermo: Thermo, number: BigNumber, wind: Wind, outro: Outro,
};
