import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { COLORS, FONT } from '../../lib/constants';
import { overlayContainerStyle, labelStyle } from './sceneStyles';

export const BigNumberTemplate: React.FC<{ params: Record<string, unknown> }> = ({ params }) => {
  const number = (params.number as string) || '';
  const label = (params.label as string) || '';
  const frame = useCurrentFrame();

  const scale = interpolate(frame, [0, 10], [0.6, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div style={overlayContainerStyle}>
      <div style={{ transform: `scale(${scale})`, opacity, textAlign: 'center' }}>
        <div style={{
          color: COLORS.accent,
          fontFamily: FONT.family,
          fontSize: 160,
          fontWeight: 800,
          letterSpacing: '-0.04em',
          lineHeight: 1,
        }}>
          {number}
        </div>
        {label ? <div style={{ ...labelStyle, marginTop: 16 }}>{label}</div> : null}
      </div>
    </div>
  );
};
