"""Diccionario de equivalencia talle/color/pack BEST ↔ AdministraNET."""

from __future__ import annotations

DICT_VERSION = "2026-07-10-v3"

TALLE_ADMIN_TO_BEST = {
    "T1": "1",
    "T2": "2",
    "T3": "3",
    "T4": "4",
    "T5": "5",
    "T6": "6",
    "TL": "4",
    "TM": "5",
    "T110": "4",
    "T120": "5",
    "T130": "6",
}

COLOR_CODE_TO_WORDS = {
    "BL": {"BLANCO", "BLANCA", "BL", "WHITE"},
    "NE": {"NEGRO", "NEGRA", "NE", "BLACK"},
    "GM": {"GRIS", "GM", "GMEL", "GREY", "GRAY"},
    "GR": {"GRIS", "GR", "GREY", "GRAY"},
    "MN": {"MARINO", "MN", "MNO"},
    "M4": {"M4"},
    "FU": {"FUCSIA", "FU", "FUCHSIA"},
    "RO": {"ROJO", "ROJA", "RO", "RED"},
    "AZ": {"AZUL", "AZ", "BLUE"},
    "VE": {"VERDE", "VE", "GREEN"},
    "RS": {"ROSA", "RS", "PINK"},
    "CR": {"CRUDO", "CR", "CREMA"},
    "BE": {"BEIGE", "BE"},
    "MA": {"MARRON", "MA", "BROWN"},
    "SU": {"SU"},
    "AO": {"AO"},
    "AE": {"AE"},
    "GT": {"GT"},
}

COLOR_WORD_TO_CODE: dict[str, str] = {}
for _code, _words in COLOR_CODE_TO_WORDS.items():
    for _w in _words:
        COLOR_WORD_TO_CODE.setdefault(_w, _code)

KNOWN_COLOR_CODES = list(COLOR_CODE_TO_WORDS.keys())
