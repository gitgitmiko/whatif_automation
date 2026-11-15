import {continueRender, delayRender, staticFile} from 'remotion';

// Anton (bold display) and Montserrat (the 3D style's captions), loaded once before the first frame is taken. A run
// whose public dir lacks a font still renders, with a fallback face.
for (const [family, file, weight] of [['Anton', 'Anton-Regular.ttf', '400'], ['Montserrat', 'Montserrat.ttf', '100 900']]) {
  const handle = delayRender(family);
  new FontFace(family, `url(${staticFile(file)})`, {weight}).load()
    .then((f) => document.fonts.add(f))
    .catch(() => undefined)
    .finally(() => continueRender(handle));
}
