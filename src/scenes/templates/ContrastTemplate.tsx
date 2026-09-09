import React from 'react';
import { COLORS } from '../../lib/constants';
import { useFadeIn, overlayContainerStyle, bodyStyle, labelStyle } from './sceneStyles';

export const ContrastTemplate: React.FC<{ params: Record<string, unknown> }> = ({ params }) => {
  const beforeLabel = (params.beforeLabel as string) || 'Before';
  const afterLabel = (params.afterLabel as string) || 'After';
  const before = (params.before as string) || '';
  const after = (params.after as string) || '';
  const opacity = useFadeIn();

  const columnStyle: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 12,
    padding: '24px 16px',
    borderRadius: 20,
  };

  return (
    <div style={overlayContainerStyle}>
      <div style={{ opacity, display: 'flex', width: '100%', gap: 20, alignItems: 'stretch' }}>
        <div style={{ ...columnStyle, background: 'rgba(232, 68, 90, 0.15)', border: `1px solid ${COLORS.red}` }}>
          <div style={{ ...labelStyle, color: COLORS.red }}>{beforeLabel}</div>
          <div style={bodyStyle}>{before}</div>
        </div>
        <div style={{ ...columnStyle, background: 'rgba(46, 204, 154, 0.15)', border: `1px solid ${COLORS.green}` }}>
          <div style={{ ...labelStyle, color: COLORS.green }}>{afterLabel}</div>
          <div style={bodyStyle}>{after}</div>
        </div>
      </div>
    </div>
  );
};
