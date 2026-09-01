# 02 — Design Tokens Inventory

**Estado:** COMPLETE | **No tokens in tailwind.config** (`extend: {}` empty)

## Colors (de facto)

| Token name (proposed) | Values used | Inconsistency |
|----------------------|-------------|---------------|
| `color-primary` | purple-500/600/700, #7c3aed | — |
| `color-secondary` | sky-400/600, indigo-500 | reports |
| `color-neutral` | slate-* AND gray-* | **DUPLICATE** |
| `color-success` | emerald-500/600 | — |
| `color-warning` | amber-500/600 | — |
| `color-error` | red-500/600 | — |
| `color-hero` | slate-900, from-slate-900 | reports |

## Typography

| Token | Value |
|-------|-------|
| `font-family` | Inter, system-ui fallback |
| `font-size-xs` → `3xl` | Tailwind scale |
| `font-weight` | 400, 500, 600, 700 |

## Spacing

| Token | Usage |
|-------|-------|
| page padding | `p-4 md:p-8` |
| mpr container | `px-3 sm:px-4 … 2xl:px-12` |
| card padding | `p-4`, `p-6` |

## Radius & shadow

| Token | Values |
|-------|--------|
| radius | `rounded-lg`, `rounded-xl`, `rounded-2xl` |
| shadow | `shadow`, `shadow-lg`, `shadow-xl` |

## Z-index (implicit)

| Layer | z-index |
|-------|--------:|
| navbar | 60 |
| modals | 90 |
| toasts | 100 |

## Breakpoints

Tailwind defaults only — no custom.

## Action

Centralize in `theme/static_src/tailwind.config.js` `theme.extend` during design system phase.
