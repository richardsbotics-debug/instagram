import React from 'react';
import { COLORS } from '../../lib/constants';
import { useFadeIn, overlayContainerStyle, bodyStyle, labelStyle } from './sceneStyles';

interface Feature {
  label: string;
  icon?: string;
}

export const FeatureGridTemplate: React.FC<{ params: Record<string, unknown> }> = ({ params }) => {
  const features = (params.features as Feature[]) || [];
  const opacity = useFadeIn();

  return (
    <div style={overlayContainerStyle}>
      <div style={{
        opacity,
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: 24,
        width: '100%',
      }}>
        {features.map((feature, i) => (
          <div key={i} style={{
            background: 'rgba(255,255,255,0.08)',
            border: `1px solid ${COLORS.divider}`,
            borderRadius: 20,
            padding: '28px 20px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 8,
          }}>
            {feature.icon ? <div style={labelStyle}>{feature.icon}</div> : null}
            <div style={{ ...bodyStyle, fontSize: 32 }}>{feature.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
