import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { COLORS } from '../../lib/constants';
import { overlayContainerStyle, bodyStyle } from './sceneStyles';

export const BulletsTemplate: React.FC<{ params: Record<string, unknown> }> = ({ params }) => {
  const bullets = (params.bullets as string[]) || [];
  const frame = useCurrentFrame();

  return (
    <div style={overlayContainerStyle}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 28, width: '100%' }}>
        {bullets.map((bullet, i) => {
          const itemStart = i * 8;
          const opacity = interpolate(frame, [itemStart, itemStart + 8], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });
          const translateX = interpolate(frame, [itemStart, itemStart + 8], [-40, 0], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });
          return (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 20,
                opacity,
                transform: `translateX(${translateX}px)`,
              }}
            >
              <div style={{
                width: 12, height: 12, borderRadius: 6, background: COLORS.accent, flexShrink: 0,
              }} />
              <div style={{ ...bodyStyle, textAlign: 'left' }}>{bullet}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
