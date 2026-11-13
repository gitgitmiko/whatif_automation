import {AbsoluteFill, random} from 'remotion';
import {Earth} from './visuals';

// Channel art for "Gimana Jadinya?", in the Shorts' own look: navy space, Anton, yellow, a globe.
const YELLOW = '#FFD400';
const SPACE = 'radial-gradient(circle at 50% 45%, #1d2b64 0%, #0b0f2a 60%, #05060f 100%)';

const StaticStars: React.FC<{w: number; h: number; n: number}> = ({w, h, n}) => (
  <svg width={w} height={h} style={{position: 'absolute'}}>
    {Array.from({length: n}).map((_, i) => (
      <circle key={i} cx={random(`bx${i}`) * w} cy={random(`by${i}`) * h} r={1 + random(`br${i}`) * 3}
        fill="white" opacity={0.25 + random(`bo${i}`) * 0.6} />
    ))}
  </svg>
);

// The mark: a question mark whose dot is the Earth.
export const Mark: React.FC<{size: number}> = ({size}) => (
  <div style={{position: 'relative', width: size * 0.72, height: size}}>
    <svg width={size * 0.72} height={size} viewBox="0 0 100 140" style={{position: 'absolute', overflow: 'visible'}}>
      <path d="M20,42 C20,16 38,6 52,6 C70,6 82,19 82,36 C82,53 66,59 58,67 C54,71 52,77 52,88"
        stroke="#000" strokeWidth={30} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M20,42 C20,16 38,6 52,6 C70,6 82,19 82,36 C82,53 66,59 58,67 C54,71 52,77 52,88"
        stroke={YELLOW} strokeWidth={19} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
    <div style={{position: 'absolute', left: size * 0.72 * 0.52 - size * 0.12, top: size * 0.765}}>
      <div style={{borderRadius: '50%', boxShadow: `0 0 0 ${size * 0.025}px #000`, width: size * 0.24, height: size * 0.24,
        display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <Earth rot={40} size={size * 0.24 / 0.9} />
      </div>
    </div>
  </div>
);

export const Profile: React.FC = () => (
  <AbsoluteFill style={{background: SPACE, alignItems: 'center', justifyContent: 'center'}}>
    <StaticStars w={800} h={800} n={60} />
    <Mark size={560} />
  </AbsoluteFill>
);

export const Watermark: React.FC = () => (
  <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
    <Mark size={140} />
  </AbsoluteFill>
);

const Speed: React.FC = () => (
  <svg width={420} height={420} viewBox="-120 -120 240 240">
    <path d="M-90.1,52 A104,104 0 1 1 90.1,52" stroke="#1f2a55" strokeWidth={18} fill="none" strokeLinecap="round" />
    <path d="M-90.1,52 A104,104 0 1 1 90.1,52" stroke={YELLOW} strokeWidth={18} fill="none" strokeLinecap="round"
      pathLength={1} strokeDasharray="0.83 1" />
    <g transform="rotate(79)"><path d="M-5,0 L0,-86 L5,0Z" fill="#ff3b3b" /></g>
    <circle r={11} fill="white" />
  </svg>
);

const Wave: React.FC = () => {
  let d = 'M0,300 L0,120';
  for (let x = 0; x <= 600; x += 20) d += ` L${x},${120 + Math.sin(x / 60) * 40 - x * 0.1}`;
  return (
    <svg width={600} height={300}>
      <path d={d + ' L600,300Z'} fill="#1e7fd9" />
      <path d={d.replace('M0,300 L', 'M')} stroke="white" strokeWidth={8} fill="none" opacity={0.8} />
    </svg>
  );
};

// 2560x1440; everything that must be read sits in YouTube's 1546x423 centre, the rest only shows on wide screens.
export const Banner: React.FC = () => (
  <AbsoluteFill style={{background: SPACE}}>
    <StaticStars w={2560} h={1440} n={260} />
    <div style={{position: 'absolute', left: 30, top: 480}}><Earth rot={90} size={440} /></div>
    <div style={{position: 'absolute', right: 40, top: 500, transform: 'rotate(8deg)'}}><Speed /></div>
    <div style={{position: 'absolute', right: 0, bottom: 0}}><Wave /></div>
    <div style={{position: 'absolute', left: 0, bottom: 0, transform: 'scaleX(-1)'}}><Wave /></div>
    <div style={{position: 'absolute', left: 507, top: 508, width: 1546, height: 423, display: 'flex',
      alignItems: 'center', justifyContent: 'center', gap: 56}}>
      <Mark size={340} />
      <div>
        <div style={{fontFamily: 'Anton', fontSize: 168, lineHeight: 1, color: YELLOW, letterSpacing: 3,
          WebkitTextStroke: '16px #000', paintOrder: 'stroke fill', textShadow: '0 14px 0 rgba(0,0,0,.45)'}}>
          GIMANA JADINYA?
        </div>
        <div style={{fontFamily: 'Anton', fontSize: 62, color: 'white', marginTop: 22, letterSpacing: 2}}>
          PERTANYAAN GILA. JAWABAN ILMIAH.
        </div>
      </div>
    </div>
  </AbsoluteFill>
);
