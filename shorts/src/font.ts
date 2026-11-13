import {continueRender, delayRender, staticFile} from 'remotion';

// Anton for every composition, loaded once before the first frame is taken.
const handle = delayRender('Anton');
new FontFace('Anton', `url(${staticFile('Anton-Regular.ttf')})`).load().then((f) => {
  document.fonts.add(f);
  continueRender(handle);
});
