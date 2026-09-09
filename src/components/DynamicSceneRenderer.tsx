import React from 'react';
import { Sequence } from 'remotion';
import { secToFrame } from '../lib/constants';
import type { SceneConfig, SceneType } from '../lib/dynamic-config';
import { HookTemplate } from '../scenes/templates/HookTemplate';
import { BulletsTemplate } from '../scenes/templates/BulletsTemplate';
import { FeatureGridTemplate } from '../scenes/templates/FeatureGridTemplate';
import { BigNumberTemplate } from '../scenes/templates/BigNumberTemplate';
import { ContrastTemplate } from '../scenes/templates/ContrastTemplate';
import { StrikethroughTemplate } from '../scenes/templates/StrikethroughTemplate';
import { LogoGridTemplate } from '../scenes/templates/LogoGridTemplate';
import { ClosingTemplate } from '../scenes/templates/ClosingTemplate';

type SceneComponent = React.FC<{ params: Record<string, unknown> }>;

const TEMPLATES: Record<SceneType, SceneComponent> = {
  hook: HookTemplate,
  bullets: BulletsTemplate,
  featureGrid: FeatureGridTemplate,
  bigNumber: BigNumberTemplate,
  contrast: ContrastTemplate,
  strikethrough: StrikethroughTemplate,
  logoGrid: LogoGridTemplate,
  closing: ClosingTemplate,
};

// Scene overlays are disabled by design (see README > Design Principles) -
// storyboard/assembly always emit an empty `scenes` array. This renderer
// exists so the templates stay wired up for anyone who wants to re-enable them.
export const DynamicSceneRenderer: React.FC<{ scenes: SceneConfig[] }> = ({ scenes }) => {
  return (
    <>
      {scenes.map((scene, i) => {
        const Template = TEMPLATES[scene.type];
        if (!Template) return null;

        const from = secToFrame(scene.startSec);
        const durationInFrames = secToFrame(scene.endSec) - from;
        if (durationInFrames <= 0) return null;

        return (
          <Sequence key={`scene-${i}`} from={from} durationInFrames={durationInFrames} layout="none">
            <Template params={scene.params} />
          </Sequence>
        );
      })}
    </>
  );
};
