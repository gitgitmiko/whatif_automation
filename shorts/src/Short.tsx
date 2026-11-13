import {
  AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile,
  useCurrentFrame, useVideoConfig,
} from 'remotion';
import {Captions} from './Captions';
import {Stars, VISUALS, Visual, Word, cueFrame} from './visuals';

export type Scene = {
  text: string; visual: Visual; cue?: string; sfx?: string; audio: string; audioFrom: number;
  from: number; frames: number; words: Word[];
};
export type ShortProps = {title: string; fps: number; frames: number; scenes: Scene[]};

const SceneView: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const V = VISUALS[scene.visual.type] ?? VISUALS.icon;
  // Every scene punches in, then drifts slowly closer: the camera never sits still.
  const enter = spring({frame, fps, config: {damping: 14, stiffness: 160}});
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

export const Short: React.FC<ShortProps> = ({title, scenes, frames}) => {
  return (
    <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 40%, #1d2b64 0%, #0b0f2a 60%, #05060f 100%)'}}>
      <Stars />
      {scenes.map((s, i) => (
        <Sequence key={i} from={s.from} durationInFrames={s.frames} name={`${i} ${s.visual.type}`}>
          <SceneView scene={s} />
          <Audio src={staticFile(s.audio)} startFrom={s.audioFrom} />
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
  );
};
