"""Template tags UI migración Odoo."""

from django import template

register = template.Library()

TONE_CLASSES = {
    "slate": "bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
    "sky": "bg-sky-100 text-sky-800 ring-sky-200 dark:bg-sky-900/40 dark:text-sky-200 dark:ring-sky-800",
    "emerald": "bg-emerald-100 text-emerald-800 ring-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-200 dark:ring-emerald-800",
    "amber": "bg-amber-100 text-amber-900 ring-amber-200 dark:bg-amber-900/40 dark:text-amber-200 dark:ring-amber-800",
    "red": "bg-red-100 text-red-800 ring-red-200 dark:bg-red-900/40 dark:text-red-200 dark:ring-red-800",
    "violet": "bg-violet-100 text-violet-800 ring-violet-200 dark:bg-violet-900/40 dark:text-violet-200 dark:ring-violet-800",
}

BAR_TONE = {
    "slate": "bg-slate-400",
    "sky": "bg-sky-500",
    "emerald": "bg-emerald-500",
    "amber": "bg-amber-500",
    "red": "bg-red-500",
    "violet": "bg-violet-500",
}


@register.filter
def odoo_mig_badge_class(tone: str) -> str:
    return TONE_CLASSES.get(tone or "slate", TONE_CLASSES["slate"])


@register.filter
def odoo_mig_bar_class(tone: str) -> str:
    return BAR_TONE.get(tone or "slate", BAR_TONE["slate"])
