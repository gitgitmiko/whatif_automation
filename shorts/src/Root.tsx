import {Composition, Still} from 'remotion';
import {Short, ShortProps} from './Short';
import {Banner, Profile, Watermark} from './Brand';
import sample from './sample.json';

export const Root: React.FC = () => (
  <>
    <Composition
      id="Short"
      component={Short}
      durationInFrames={300}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={sample as unknown as ShortProps}
      calculateMetadata={({props}) => ({durationInFrames: props.frames, fps: props.fps})}
    />
    <Still id="Profile" component={Profile} width={800} height={800} />
    <Still id="Banner" component={Banner} width={2560} height={1440} />
    <Still id="Watermark" component={Watermark} width={150} height={150} />
  </>
);
