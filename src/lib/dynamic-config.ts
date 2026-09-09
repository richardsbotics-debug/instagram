export interface BRollSegment {
  video?: string;       // Filename in public/broll/clips/
  image?: string;       // Filename in public/broll/ or public/broll/topics/
  startSec: number;
  endSec: number;
  objectPosition?: string;  // CSS object-position (default 'center center')
  scaleFrom?: number;       // Ken Burns start zoom (default 1.0)
  scaleTo?: number;         // Ken Burns end zoom (default 1.05)
  videoStartSec?: number;   // Skip into source video
  objectFit?: 'cover' | 'contain';
  _speech?: string;         // Annotation only, not rendered
}

export interface CaptionChunk {
  text: string;
  startSec: number;
  endSec: number;
}

export type SceneType = 'hook' | 'bullets' | 'featureGrid' | 'bigNumber' |
  'contrast' | 'strikethrough' | 'logoGrid' | 'closing';

export interface SceneConfig {
  type: SceneType;
  startSec: number;
  endSec: number;
  params: Record<string, unknown>;
}

export interface ReelConfig {
  id: string;
  duration: number;          // Frames at 25fps
  avatarSrc: string;         // In public/
  avatarMarginTop?: number;  // Vertical crop offset (default -280)
  brollSegments: BRollSegment[];
  captionChunks: CaptionChunk[];
  scenes: SceneConfig[];
  crossfadeFrames?: number;  // Transition frames (default 8)
}
