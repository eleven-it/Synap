import { createTheme, type ThemeOptions } from '@mui/material/styles'
import type { PaletteMode } from '@mui/material'
import { radius, shadows, typographyScale, transitionDuration } from './tokens'

const getDesignTokens = (mode: PaletteMode) => ({
  palette: {
    mode,
    primary: {
      main: mode === 'light' ? '#6B21A8' : '#A78BFA',
      light: mode === 'light' ? '#9333EA' : '#C4B5FD',
      dark: mode === 'light' ? '#581C87' : '#7C3AED',
      contrastText: '#fff',
    },
    secondary: {
      main: mode === 'light' ? '#4F46E5' : '#818CF8',
      light: mode === 'light' ? '#6366F1' : '#A5B4FC',
      dark: mode === 'light' ? '#3730A3' : '#6366F1',
      contrastText: '#fff',
    },
    error: { main: '#DC2626', light: '#FCA5A5', dark: '#B91C1C' },
    warning: { main: '#D97706', light: '#FCD34D', dark: '#B45309' },
    success: { main: '#059669', light: '#34D399', dark: '#047857' },
    info: { main: '#0284C7', light: '#38BDF8', dark: '#0369A1' },
    background: {
      default: mode === 'light' ? '#F8F9FB' : '#0F0F12',
      paper: mode === 'light' ? '#FFFFFF' : '#1A1A1F',
    },
    text: {
      primary: mode === 'light' ? '#111827' : '#F3F4F6',
      secondary: mode === 'light' ? '#6B7280' : '#9CA3AF',
      disabled: mode === 'light' ? '#9CA3AF' : '#6B7280',
    },
    divider: mode === 'light' ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)',
    action: {
      hover: mode === 'light' ? 'rgba(0,0,0,0.04)' : 'rgba(255,255,255,0.06)',
      selected: mode === 'light' ? 'rgba(107,33,168,0.12)' : 'rgba(167,139,250,0.16)',
    },
  },
  shape: { borderRadius: radius.md },
  shadows: [
    'none',
    shadows.sm,
    shadows.md,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
    shadows.lg,
  ] as ThemeOptions['shadows'],
  typography: {
    fontFamily: '"Inter", "Segoe UI", Roboto, sans-serif',
    h1: typographyScale.h1,
    h2: typographyScale.h2,
    h3: typographyScale.h3,
    h4: { ...typographyScale.h3, fontSize: '1rem' },
    h5: { ...typographyScale.body, fontWeight: 600 },
    h6: { ...typographyScale.body, fontWeight: 600 },
    body1: typographyScale.body,
    body2: typographyScale.small,
    caption: typographyScale.caption,
    button: { ...typographyScale.small, fontWeight: 600 },
  },
  transitions: {
    duration: {
      shortest: transitionDuration.short,
      shorter: transitionDuration.standard,
      short: transitionDuration.long,
      standard: 250,
      complex: 375,
      enteringScreen: 225,
      leavingScreen: 195,
    },
  },
})

/** Crea el tema MUI para un modo (light/dark). */
export function createAppTheme(mode: PaletteMode) {
  return createTheme({
    ...getDesignTokens(mode),
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            borderRadius: radius.md,
            transition: `all ${transitionDuration.standard}ms ease`,
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            borderRadius: radius.md,
            border: '1px solid',
            borderColor: mode === 'light' ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)',
            boxShadow: shadows.sm,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: radius.md,
            border: '1px solid',
            borderColor: mode === 'light' ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)',
            boxShadow: shadows.sm,
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { borderRadius: radius.sm },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: radius.md,
            transition: `background-color ${transitionDuration.short}ms ease`,
          },
        },
      },
    },
  })
}

/** Tema por defecto (para compatibilidad con imports existentes). */
export const theme = createAppTheme('light')
