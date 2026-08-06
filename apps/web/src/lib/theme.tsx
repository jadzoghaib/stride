/** Theme state. Dark is the default register; a stored choice wins.
 *
 *  The attribute is set pre-paint by the inline script in index.html — this
 *  hook only reads it back and writes changes, so there is no flash and no
 *  second source of truth. */

import { useCallback, useEffect, useState } from 'react'

export type Theme = 'dark' | 'light'

const KEY = 'stride-theme'

const read = (): Theme =>
  document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(read)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try {
      localStorage.setItem(KEY, theme)
    } catch {
      /* private mode — the in-memory choice still applies for this session */
    }
  }, [theme])

  const toggle = useCallback(() => setTheme((t) => (t === 'dark' ? 'light' : 'dark')), [])

  return { theme, setTheme, toggle }
}
