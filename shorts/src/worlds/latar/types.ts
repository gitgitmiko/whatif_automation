import type {Anchor, V3} from '../../kit3d/core';

// One set of the profession world. Shots are computed from this data, so a new latar gets every shot for free:
// where you stand and how (hero), what you work on (work), the establishing camera (wide), where props may go,
// the effect the "bahaya" shot switches on, and the prop shown on the explainer stage when the scene names none.
export type Latar = {
  Scenery: React.FC<{frame: number; night: boolean}>;
  hero: {p: V3; ry: number; pose: string};
  work: V3;
  wide: {cam: V3; at: V3};
  anchors: Record<string, Anchor>;
  efek: string;
  signature: string;
};
