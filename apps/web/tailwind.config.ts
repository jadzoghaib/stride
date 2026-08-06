import type { Config } from 'tailwindcss'

/** Stride design tokens — direction: "Timing Board".
 *
 *  Values live in index.css as RGB *channel triplets* (`--c-ink: 242 244 247`)
 *  so Tailwind can inject alpha: `text-ink/60` compiles to
 *  `rgb(var(--c-ink) / 0.6)`. Storing whole colours (`#f2f4f7`) would silently
 *  break every `/opacity` modifier already used across the views.
 *
 *  One vocabulary: ground/panel/raised/track, ink/ink-2/ink-3, accent, ok/warn/critical.
 */
const ch = (name: string) => `rgb(var(--c-${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // ── surfaces ──────────────────────────────────────────────────────
        ground: { DEFAULT: ch('ground'), deep: ch('ground-deep') },
        panel: ch('panel'),
        raised: ch('raised'),
        track: ch('track'),

        // ── text ──────────────────────────────────────────────────────────
        ink: { DEFAULT: ch('ink'), 2: ch('ink-2'), 3: ch('ink-3') },

        // ── accent + semantics ────────────────────────────────────────────
        // `on` is the foreground for text placed on the amber fill; it stays
        // dark in both themes because the fill itself never goes dark.
        accent: { DEFAULT: ch('accent'), ink: ch('accent-ink'), on: ch('accent-on') },
        ok: ch('ok'),
        warn: ch('warn'),
        critical: ch('critical'),

        // ── hairlines (alpha already baked; no /opacity modifiers on these) ─
        line: { DEFAULT: 'var(--line)', strong: 'var(--line-strong)' },
      },

      fontFamily: {
        // Barlow Condensed is the board face: numerals, labels, table heads.
        display: ['Barlow Condensed', 'Bahnschrift', 'DIN Alternate', 'Arial Narrow', 'ui-sans-serif', 'sans-serif'],
        sans: ['Barlow', 'ui-sans-serif', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['ui-monospace', 'Cascadia Mono', 'SF Mono', 'Consolas', 'monospace'],
      },

      letterSpacing: {
        micro: '0.13em', // uppercase utility labels
        board: '0.05em', // condensed display runs
      },

      boxShadow: {
        card: 'var(--shadow)',
        lift: 'var(--shadow-lift)',
      },

      borderRadius: {
        // the board register is rectilinear — small, consistent radii
        DEFAULT: '5px',
        card: '5px',
      },

      keyframes: {
        rise: {
          from: { opacity: '0', transform: 'translateY(9px)' },
          to: { opacity: '1', transform: 'none' },
        },
        wipe: {
          from: { transform: 'scaleX(0)' },
          to: { transform: 'scaleX(1)' },
        },
      },
      animation: {
        rise: 'rise .5s cubic-bezier(.16,1,.3,1) both',
        wipe: 'wipe 1s cubic-bezier(.16,1,.3,1) both',
      },

      transitionTimingFunction: {
        settle: 'cubic-bezier(.16,1,.3,1)',
      },
    },
  },
  plugins: [],
} satisfies Config
