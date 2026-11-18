# Design and engineering rules

## Scope
- Live location tracking logic (geolocation watcher, socket/API updates, hooks,
  state) is working. Never rewrite or change it. Only restyle and restructure UI.
- Do not add a new map library. Use the one already in the project.

## Visual direction (must look like a shipped product, not AI-generated)
- One neutral palette plus ONE accent color.
- Banned: purple/blue gradients, glassmorphism, neon glows, emoji as icons,
  decorative blobs, oversized hero cards, lorem ipsum, "Welcome to your dashboard!".
- Flat surfaces, 1px subtle borders, small soft shadows, 8px spacing grid.
- Inter or system font stack, clear type scale, tabular-nums for all numbers.
- Icons: lucide-react only, one stroke width.
- Real, specific microcopy ("Driver is 4 min away", "Updated 3s ago").
- Animations 150-200ms, respect prefers-reduced-motion.

## Stack conventions
- Tailwind + daisyUI with a CUSTOM theme defined in the Tailwind config
  (never the default daisyUI look). Support light and dark themes.
- Small components in separate files. No heavy new dependencies.

## Quality bar
- Focus rings, aria-labels on map controls, 4.5:1 contrast, 44px touch targets.
- Run lint and build before finishing, and summarize what changed.