import { createContext, useCallback, useMemo, useState } from 'react'
import { ThemeProvider as MuiThemeProvider, CssBaseline } from '@mui/material'
import { createAppTheme } from '@/styles/theme'
import type { PaletteMode } from '@mui/material'
import { STORAGE_THEME_KEY } from '@/styles/tokens'

export const ThemeModeContext = createContext<{
  mode: PaletteMode
  setMode: (mode: PaletteMode) => void
  toggleMode: () => void
}>({ mode: 'light', setMode: () => {}, toggleMode: () => {} })

function readStoredMode(): PaletteMode {
  if (typeof window === 'undefined') return 'light'
  const stored = localStorage.getItem(STORAGE_THEME_KEY)
  if (stored === 'dark' || stored === 'light') return stored
  return 'light'
}

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<PaletteMode>(readStoredMode)

  const setMode = useCallback((next: PaletteMode) => {
    setModeState(next)
    localStorage.setItem(STORAGE_THEME_KEY, next)
  }, [])

  const toggleMode = useCallback(() => {
    setModeState((prev: PaletteMode) => {
      const next: PaletteMode = prev === 'light' ? 'dark' : 'light'
      localStorage.setItem(STORAGE_THEME_KEY, next)
      return next
    })
  }, [])

  const theme = useMemo(() => createAppTheme(mode), [mode])
  const contextValue = useMemo(
    () => ({ mode, setMode, toggleMode }),
    [mode, setMode, toggleMode]
  )

  return (
    <ThemeModeContext.Provider value={contextValue}>
      <MuiThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </MuiThemeProvider>
    </ThemeModeContext.Provider>
  )
}
