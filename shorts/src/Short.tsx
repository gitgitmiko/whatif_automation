import {
  AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile,
  useCurrentFrame, useVideoConfig,
} from 'remotion';
import {Captions} from './Captions';
import {Stars, VISUALS, Visual, Word, cueFrame} from './visuals';
import {Hero, HeroContext, Pov, PovOutro, THEMES} from './hero';
import {HOOK_FRAMES, HookCard, ImageScene, Label, TopTag, XFADE} from './scene3d';

export type Scene = {
  text: string; visual: Visual; cue?: string; sfx?: string; audio?: string; audioFrom?: number;
  from: number; frames: number; words: Word[]; image?: string; camera?: string; label?: string;
};
// narration: one voice track for the whole video (Gemini); without it each scene plays its own audio (edge-tts).
export type ShortProps = {title: string; hook?: string; fps: number; frames: number; scenes: Scene[]; hero?: Hero; theme?: string; style?: string; narration?: string};

const SceneView: React.FC<{scene: Scene; pov: boolean}> = ({scene, pov}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = scene.visual.type;
  const V = t === 'pov' ? Pov : t === 'outro' && pov ? PovOutro : VISUALS[t] ?? VISUALS.icon;
  // Every scene punches in, then drifts slowly closer: the camera never sits still.
  // The opening scene is already on screen at frame 0: the first frame is what decides the swipe.
  const enter = scene.from === 0 ? 1 : spring({frame, fps, config: {damping: 14, stiffness: 160}});
  const scale = interpolate(enter, [0, 1], [1.25, 1]) * interpolate(frame, [0, scene.frames], [1, 1.06]);
  const exit = interpolate(frame, [scene.frames - 6, scene.frames], [1, 0], {extrapolateLeft: 'clamp'});
  return (
    <AbsoluteFill style={{opacity: Math.min(enter * 1.5, 1) * exit}}>
      <AbsoluteFill style={{transform: `scale(${scale})`}}>
        <V scene={scene} />
      </AbsoluteFill>
      <Captions words={scene.words} />
    </AbsoluteFill>
  );
};

const Header: React.FC<{title: string; total: number}> = ({title, total}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', top: 0, left: 0, height: 14, background: '#FFD400',
        width: `${(frame / total) * 100}%`}} />
      <div style={{position: 'absolute', top: 110, width: '100%', textAlign: 'center'}}>
        <span style={{fontFamily: 'Anton', fontSize: 64, color: '#111', background: '#FFD400',
          padding: '6px 34px', borderRadius: 16, letterSpacing: 2, transform: 'rotate(-2deg)',
          display: 'inline-block', boxShadow: '0 10px 0 #B38F00'}}>GIMANA JADINYA?</span>
        <div style={{fontFamily: 'Anton', fontSize: 50, color: 'white', marginTop: 28, padding: '0 80px',
          lineHeight: 1.15, textShadow: '0 4px 12px rgba(0,0,0,.6)'}}>{title.toUpperCase()}</div>
      </div>
    </AbsoluteFill>
  );
};

const Short3D: React.FC<ShortProps> = ({title, hook, scenes, narration}) => (
  <AbsoluteFill style={{background: '#000'}}>
    {narration && <Audio src={staticFile(narration)} />}
    {scenes.map((s, i) => {
      const lead = i ? XFADE : 0;  // each picture dissolves in over the end of the one before
      return (
        <Sequence key={`img${i}`} from={s.from - lead} durationInFrames={s.frames + lead + (i < scenes.length - 1 ? 0 : 30)}>
          <ImageScene scene={s} frames={s.frames + lead} lead={lead} />
        </Sequence>
      );
    })}
    {scenes.map((s, i) => (
      <Sequence key={i} from={s.from} durationInFrames={s.frames} name={`${i} ${s.camera ?? ''}`}>
        <Label scene={s} />
        <Captions words={s.words} top={1150} />
        {s.audio && <Audio src={staticFile(s.audio)} startFrom={s.audioFrom} />}
        {i > 0 && <Audio src={staticFile('sfx/whoosh.wav')} volume={0.15} />}
        {s.sfx && (
          <Sequence from={Math.max(cueFrame(s.words, s.cue) - 2, 0)}>
            <Audio src={staticFile(`sfx/${s.sfx}.wav`)} volume={0.4} />
          </Sequence>
        )}
      </Sequence>
    ))}
    <TopTag title={title} from={hook ? HOOK_FRAMES : 0} />
    <HookCard text={hook ?? ''} />
  </AbsoluteFill>
);

export const Short: React.FC<ShortProps> = (props) => {
  const {title, scenes, frames, hero, theme} = props;
  if (props.style === '3d') return <Short3D {...props} />;
  const pov = Boolean(hero?.emoji);
  return (
    <HeroContext.Provider value={hero ?? {}}>
    <AbsoluteFill style={{background: pov ? THEMES[theme ?? ''] ?? THEMES.kota
      : 'radial-gradient(circle at 50% 40%, #1d2b64 0%, #0b0f2a 60%, #05060f 100%)'}}>
      {props.narration && <Audio src={staticFile(props.narration)} />}
      {pov ? <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 70%, rgba(255,255,255,.12), transparent 55%)'}} /> : <Stars />}
      {scenes.map((s, i) => (
        <Sequence key={i} from={s.from} durationInFrames={s.frames} name={`${i} ${s.visual.type}`}>
          <SceneView scene={s} pov={pov} />
          {s.audio && <Audio src={staticFile(s.audio)} startFrom={s.audioFrom} />}
          {i > 0 && <Audio src={staticFile('sfx/whoosh.wav')} volume={0.35} />}
          {s.sfx && (
            <Sequence from={Math.max(cueFrame(s.words, s.cue) - 2, 0)}>
              <Audio src={staticFile(`sfx/${s.sfx}.wav`)} volume={0.5} />
            </Sequence>
          )}
        </Sequence>
      ))}
      <Header title={title} total={frames} />
    </AbsoluteFill>
    </HeroContext.Provider>
  );
};
