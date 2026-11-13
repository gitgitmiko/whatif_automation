import {interpolate, useCurrentFrame} from 'remotion';
import type {Word} from './visuals';

// Words shown a few at a time, breaking at sentence ends; the word being spoken pops in yellow.
const groups = (words: Word[], max = 3) => {
  const out: Word[][] = [];
  let cur: Word[] = [];
  for (const w of words) {
    cur.push(w);
    if (cur.length >= max || /[.?!,]$/.test(w.w)) {
      out.push(cur);
      cur = [];
    }
  }
  if (cur.length) out.push(cur);
  return out;
};

export const Captions: React.FC<{words: Word[]}> = ({words}) => {
  const frame = useCurrentFrame();
  const gs = groups(words);
  const g = [...gs].reverse().find((x) => x[0].s <= frame) ?? gs[0];
  return (
    <div style={{position: 'absolute', top: 1390, width: '100%', display: 'flex', justifyContent: 'center',
      flexWrap: 'wrap', padding: '0 60px', boxSizing: 'border-box'}}>
      {g.map((w, i) => {
        const on = frame >= w.s && (i === g.length - 1 || frame < g[i + 1].s);
        const pop = interpolate(frame, [w.s, w.s + 4, w.s + 8], [1, 1.18, 1.08],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
        return (
          <span key={i} style={{fontFamily: 'Anton', fontSize: 104, lineHeight: 1.2, textTransform: 'uppercase',
            color: on ? '#FFD400' : 'white', transform: `scale(${frame >= w.s ? pop : 1})`, display: 'inline-block', margin: '0 26px',
            opacity: frame >= w.s - 1 ? 1 : 0.55,
            WebkitTextStroke: '10px #000', paintOrder: 'stroke fill',
            textShadow: '0 8px 0 rgba(0,0,0,.55)'}}>{w.w}</span>
        );
      })}
    </div>
  );
};
