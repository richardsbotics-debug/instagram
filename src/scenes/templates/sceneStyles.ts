import { useCurrentFrame, interpolate } from 'remotion';
import { COLORS, FONT } from '../../lib/constants';

export const useFadeIn = (durationInFrames = 8) => {
  const frame = useCurrentFrame();
  return interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
};

export const overlayContainerStyle: React.CSSProperties = {
  position: 'absolute',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '0 64px',
  background: 'rgba(8, 8, 8, 0.55)',
  boxSizing: 'border-box',
};

export const headlineStyle: React.CSSProperties = {
  color: COLORS.white,
  fontFamily: FONT.family,
  fontSize: FONT.headline.fontSize,
  fontWeight: FONT.headline.fontWeight,
  letterSpacing: FONT.headline.letterSpacing,
  lineHeight: FONT.headline.lineHeight,
  textAlign: 'center',
  textShadow: '0 2px 12px rgba(0,0,0,0.5)',
};

export const bodyStyle: React.CSSProperties = {
  color: COLORS.white,
  fontFamily: FONT.family,
  fontSize: FONT.body.fontSize,
  fontWeight: FONT.body.fontWeight,
  letterSpacing: FONT.body.letterSpacing,
  lineHeight: FONT.body.lineHeight,
  textAlign: 'center',
};

export const labelStyle: React.CSSProperties = {
  color: COLORS.accent,
  fontFamily: FONT.family,
  fontSize: FONT.label.fontSize,
  fontWeight: FONT.label.fontWeight,
  letterSpacing: FONT.label.letterSpacing,
  lineHeight: FONT.label.lineHeight,
  textTransform: 'uppercase',
};
