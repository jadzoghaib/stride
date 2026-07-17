import type { Config } from 'tailwindcss'

/** Stride design tokens — light, airy, premium (Passes-register).
 *  Token NAMES are semantic and stable; only values changed in the light reskin:
 *  `ink` = surface ramp (page → card → field → hover → track),
 *  `mist` = text ramp (100 darkest heading → 400 muted). */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#f7f6f2', // page
          900: '#ffffff', // card / panel
          850: '#f5f4ef', // field background
          800: '#edece5', // chips, hover washes
          700: '#e3e1d8', // meter tracks
          600: '#cfccc0', // muted bar fills
        },
        line: {
          DEFAULT: 'rgba(24, 22, 40, 0.09)',
          strong: 'rgba(24, 22, 40, 0.20)',
        },
        mist: {
          400: '#77748a', // muted labels
          300: '#565367',
          200: '#343146', // body text
          100: '#161426', // headings
        },
        pulse: {
          400: '#6d70f6',
          500: '#585ceb',
          600: '#4a4dd8',
        },
        wave: {
          violet: '#8b5cf6',
          indigo: '#6366f1',
          cyan: '#0891b2',
          teal: '#0d9488',
        },
        ok: '#0e9f6e',
        warn: '#b45309',
        danger: '#dc2626',
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      letterSpacing: {
        micro: '0.08em',
      },
      boxShadow: {
        card: '0 1px 2px rgba(22, 20, 38, 0.05), 0 10px 30px -14px rgba(22, 20, 38, 0.14)',
        lift: '0 2px 4px rgba(22, 20, 38, 0.06), 0 16px 40px -16px rgba(22, 20, 38, 0.22)',
      },
    },
  },
  plugins: [],
} satisfies Config
