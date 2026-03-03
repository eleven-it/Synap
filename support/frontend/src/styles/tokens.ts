/**
 * Design system tokens – Kora-like premium admin.
 * Uso: theme/spacing desde MUI; colores y sombras desde theme.palette / theme.shadows.
 */

export const spacing = {
  0: 0,
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 24,
  6: 32,
  7: 40,
  8: 48,
} as const

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 9999,
} as const

/** Sombras suaves (Kora-like) */
export const shadows = {
  sm: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)',
  md: '0 2px 8px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.06)',
  lg: '0 4px 20px rgba(0,0,0,0.08), 0 8px 32px rgba(0,0,0,0.08)',
} as const

export const typographyScale = {
  h1: { fontSize: '1.75rem', fontWeight: 700, lineHeight: 1.3 },
  h2: { fontSize: '1.375rem', fontWeight: 600, lineHeight: 1.35 },
  h3: { fontSize: '1.125rem', fontWeight: 600, lineHeight: 1.4 },
  body: { fontSize: '0.9375rem', fontWeight: 400, lineHeight: 1.5 },
  small: { fontSize: '0.8125rem', fontWeight: 400, lineHeight: 1.45 },
  caption: { fontSize: '0.75rem', fontWeight: 400, lineHeight: 1.4 },
} as const

/** Duración estándar para microinteracciones */
export const transitionDuration = {
  short: 150,
  standard: 200,
  long: 250,
} as const

export const STORAGE_THEME_KEY = 'synap-support-theme-mode'
