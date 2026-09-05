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

      fontSize: {
        // The scale, named. These were 100 arbitrary `text-[Npx]` values across
        // 49 distinct shapes; DESIGN.md says "set a type scale and stay on it"
        // and the code had never written the scale down. Sizes only -- line
        // height stays with the element -- so adopting these changed nothing on
        // screen. Add a size here or do not use it.
        micro: '10px',    // legend ticks
        label: '11px',    // tracked caps: .cap, .tag, .meta
        fine: '12px',     // secondary meta
        small: '13px',    // dense table text
        ui: '14px',       // controls
        body: '15px',     // running text
        read: '17px',     // ledes
        lead: '19px',     // card titles
        intro: '21px',
        title: '22px',    // section titles, wordmark in the shell
        brand: '24px',    // wordmark on the landing
        head: '26px',
        prime: '28px',   // the one board numeral between head and display
        display: '30px',  // the smallest board numeral
      },

      maxWidth: {
        // the one content track; nine views typed 1140px by hand
        page: '1140px',
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
