"""Build the reference and dimension-like tables (everything except prescriptions).

Each builder returns DataFrames whose columns match the DDL column order exactly,
plus the numpy arrays the transaction generator needs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from . import config as cfg
from .reference_data import (
    BNF_CHAPTERS,
    BNF_PARAGRAPHS,
    BNF_SECTIONS,
    CATALOGUE,
    FORM_UNITS,
    ICBS,
    PRICE_EVENTS,
    REGIONS,
)

TS = cfg.REFERENCE_LOADED_AT
# English place-name parts for practice names (Faker's en_GB city() invents non-English towns).
TOWN_ROOTS = ["Ash", "Oak", "Brook", "Mill", "Kings", "Church", "Elm", "Bridge", "Thorn", "Wood", "Lea", "Holly",
              "Black", "White", "Green", "Fair", "Hazel", "Red", "Stone", "Rose", "Castle", "Wolver", "Hather", "Bram"]
TOWN_SUFFIXES = ["field", "ley", "ton", "bury", "wood", "ford", "gate", "worth", "hill", "dale", "brook", "stead",
                 "vale", "side", "combe", "thorpe"]
COUNTABLE_UNITS = {"tablet", "capsule", "sachet", "patch", "pen"}


def _allocate(total: int, weights: np.ndarray, minimum: int = 1) -> np.ndarray:
    """Split an integer total across weights (largest-remainder), with a floor per bucket."""
    weights = np.asarray(weights, dtype=float)
    base = np.full(len(weights), minimum)
    remaining = total - base.sum()
    raw = remaining * weights / weights.sum()
    alloc = np.floor(raw).astype(int)
    leftover = remaining - alloc.sum()
    alloc[np.argsort(-(raw - alloc))[:leftover]] += 1
    return base + alloc


def _random_dates(rng: np.random.Generator, start: date, end: date, n: int) -> np.ndarray:
    span = (end - start).days
    return np.datetime64(start) + rng.integers(0, span + 1, n).astype("timedelta64[D]")


# --------------------------------------------------------------------------
# Organisations: region -> ICB -> practice -> prescriber
# --------------------------------------------------------------------------


@dataclass
class Organisations:
    region: pd.DataFrame
    icb: pd.DataFrame
    practice: pd.DataFrame
    prescriber_type: pd.DataFrame
    prescriber: pd.DataFrame
    # arrays aligned to practice rows
    practice_region_idx: np.ndarray
    practice_list_size: np.ndarray
    practice_imd: np.ndarray
    practice_rural: np.ndarray
    # arrays aligned to prescriber rows (sorted by practice)
    prescriber_practice_idx: np.ndarray
    prescriber_weight: np.ndarray


def build_organisations(rng: np.random.Generator, fake: Faker, vol: cfg.Volumes, dq: cfg.DataQuality) -> Organisations:
    region = pd.DataFrame(
        [(code, ons, name, TS, TS) for code, ons, name, *_ in REGIONS],
        columns=["region_code", "ons_code", "region_name", "created_at", "updated_at"],
    )
    region_index = {r[0]: i for i, r in enumerate(REGIONS)}

    icb = pd.DataFrame(
        [(code, name, reg, TS, TS) for code, name, reg, *_ in ICBS],
        columns=["icb_code", "icb_name", "region_code", "created_at", "updated_at"],
    )

    # Practices per ICB in proportion to population (at least 3 each).
    per_icb = _allocate(vol.practices, np.array([i[3] for i in ICBS]), minimum=3)
    icb_idx = np.repeat(np.arange(len(ICBS)), per_icb)
    n = len(icb_idx)
    reg_idx = np.array([region_index[ICBS[i][2]] for i in icb_idx])

    rural_share = np.array([r[5] for r in REGIONS])[reg_idx]
    rural = rng.random(n) < rural_share

    imd_mean = np.array([r[6] for r in REGIONS])[reg_idx] + np.where(rural, 1.0, 0.0)
    imd = np.clip(np.rint(rng.normal(imd_mean, 2.3)), 1, 10).astype(int)

    list_size = rng.lognormal(mean=np.log(8800), sigma=0.48, size=n)
    list_size *= np.where(rural, 0.62, 1.0) * np.where(reg_idx == region_index["Y56"], 1.12, 1.0)
    list_size = np.clip(np.rint(list_size / 10) * 10, 1500, 45000).astype(int)

    # ODS-style practice codes: region letter + 5 digits, unique.
    codes: set[str] = set()
    practice_codes = []
    for r in reg_idx:
        letters = REGIONS[r][7]
        while True:
            code = f"{letters[rng.integers(len(letters))]}{rng.integers(81000, 99999)}"
            if code not in codes:
                codes.add(code)
                practice_codes.append(code)
                break

    postcode = []
    for i in icb_idx:
        areas = ICBS[i][4]
        area = areas[rng.integers(len(areas))]
        postcode.append(f"{area}{rng.integers(1, 30 if len(area) == 1 else 40)}")

    patterns = ["{last} Medical Centre", "{street} Surgery", "The {last} Practice", "{town} Health Centre",
                "{last} and Partners", "{town} Family Practice", "{street} Medical Practice"]
    names = []
    for _ in range(n):
        p = patterns[rng.integers(len(patterns))]
        town = TOWN_ROOTS[rng.integers(len(TOWN_ROOTS))] + TOWN_SUFFIXES[rng.integers(len(TOWN_SUFFIXES))]
        names.append(p.format(last=fake.last_name(), street=fake.street_name(), town=town))

    rural_urban = np.where(rural, "Rural", "Urban").astype(object)
    opened = _random_dates(rng, date(1952, 1, 1), date(2019, 12, 31), n)

    practice = pd.DataFrame({
        "practice_code": practice_codes,
        "practice_name": names,
        "icb_code": [ICBS[i][0] for i in icb_idx],
        "postcode_district": postcode,
        "list_size": list_size,
        "rural_urban": rural_urban,
        "imd_decile": imd,
        "opened_date": opened,
        "created_at": TS,
        "updated_at": TS,
    })

    # --- data-quality defects in the practice feed ---
    bad = rng.random(n) < dq.practice_bad_casing_rate
    practice.loc[bad, "rural_urban"] = [
        [v.lower(), v.upper(), v + " "][rng.integers(3)] for v in practice.loc[bad, "rural_urban"]
    ]
    lower_pc = rng.random(n) < 0.02
    practice.loc[lower_pc, "postcode_district"] = practice.loc[lower_pc, "postcode_district"].str.lower()
    practice.loc[rng.choice(n, dq.practice_null_postcode, replace=False), "postcode_district"] = None

    # --- prescribers: more at larger practices; GP / nurse / pharmacist mix ---
    per_practice = _allocate(vol.prescribers, list_size, minimum=1)
    pr_practice_idx = np.repeat(np.arange(n), per_practice)
    m = len(pr_practice_idx)
    type_codes = [t[0] for t in cfg.PRESCRIBER_TYPES]
    type_idx = rng.choice(len(type_codes), m, p=[t[2] for t in cfg.PRESCRIBER_TYPES])
    # Every practice has at least one GP: make each practice's first prescriber a GP.
    first = np.r_[0, np.cumsum(per_practice)[:-1]]
    type_idx[first] = 0
    weight = np.array([t[3] for t in cfg.PRESCRIBER_TYPES])[type_idx] * rng.uniform(0.6, 1.4, m)

    prefixes = {"GP": "G", "NP": "N", "PH": "P"}
    reg_numbers = rng.choice(np.arange(1_000_000, 9_999_999), m, replace=False)
    prescriber = pd.DataFrame({
        "prescriber_id": np.arange(1, m + 1),
        "prescriber_code": [f"{prefixes[type_codes[t]]}{num}" for t, num in zip(type_idx, reg_numbers, strict=False)],
        "prescriber_type_code": [type_codes[t] for t in type_idx],
        "practice_code": practice["practice_code"].to_numpy()[pr_practice_idx],
        "first_name": [fake.first_name() for _ in range(m)],
        "last_name": [fake.last_name() for _ in range(m)],
        "start_date": _random_dates(rng, date(1995, 1, 1), date(2022, 9, 30), m),
        "created_at": TS,
        "updated_at": TS,
    })

    prescriber_type = pd.DataFrame(
        [(t[0], t[1]) for t in cfg.PRESCRIBER_TYPES], columns=["prescriber_type_code", "prescriber_type_name"]
    )

    return Organisations(
        region=region, icb=icb, practice=practice, prescriber_type=prescriber_type, prescriber=prescriber,
        practice_region_idx=reg_idx, practice_list_size=list_size, practice_imd=imd, practice_rural=rural,
        prescriber_practice_idx=pr_practice_idx, prescriber_weight=weight,
    )


# --------------------------------------------------------------------------
# BNF hierarchy, medicines and prices
# --------------------------------------------------------------------------


@dataclass
class Medicines:
    bnf_chapter: pd.DataFrame
    bnf_section: pd.DataFrame
    bnf_paragraph: pd.DataFrame
    bnf_chemical: pd.DataFrame
    medicine: pd.DataFrame
    medicine_price_history: pd.DataFrame
    # arrays aligned to medicine rows
    chem_idx: np.ndarray  # index into CATALOGUE
    kind: np.ndarray  # 0 generic, 1 brand with generic alternative, 2 brand-only
    split_weight: np.ndarray  # strength share x brand share within the chemical
    pack: np.ndarray
    price_by_month: np.ndarray  # (n_medicines, N_MONTHS) unit cost in force each month


def _code_suffix(i: int) -> str:
    """Two-character code: A0..Z0 then AA..AZ, BA.. (BNF-style chemical suffix)."""
    return f"{chr(65 + i)}0" if i < 26 else f"{chr(65 + (i - 26) // 26)}{chr(65 + (i - 26) % 26)}"


def _pair(i: int) -> str:
    return f"{chr(65 + i // 26)}{chr(65 + i % 26)}"


def _presentation_name(base: str, strength: str, form: str) -> str:
    base = re.sub(r"\s*\(.*\)$", "", base)
    unit = FORM_UNITS[form]
    label = f"{form}s" if unit in COUNTABLE_UNITS else form
    return f"{base} {strength} {label}"


def build_medicines(rng: np.random.Generator) -> Medicines:
    chapter = pd.DataFrame(sorted(BNF_CHAPTERS.items()), columns=["chapter_code", "chapter_name"])
    section = pd.DataFrame(
        [(k, v, k[:2]) for k, v in sorted(BNF_SECTIONS.items())],
        columns=["section_code", "section_name", "chapter_code"],
    )
    paragraph = pd.DataFrame(
        [(k, v, k[:4]) for k, v in sorted(BNF_PARAGRAPHS.items())],
        columns=["paragraph_code", "paragraph_name", "section_code"],
    )

    chem_rows, med_rows = [], []
    chem_idx, kind, split_w, pack, base_cost = [], [], [], [], []
    seq_in_paragraph: dict[str, int] = {}

    for ci, chem in enumerate(CATALOGUE):
        k = seq_in_paragraph.get(chem.paragraph, 0)
        seq_in_paragraph[chem.paragraph] = k + 1
        chem_code = f"{chem.paragraph}0{_code_suffix(k)}"
        chem_rows.append((chem_code, chem.name, chem.paragraph))

        # Share of the chemical's volume per (form, strength): first form dominates.
        combos = [(f, s, c) for f in chem.forms for s, c in zip(f.strengths, f.costs, strict=False)]
        form_w = np.array([0.75 if fi == 0 else 0.25 / max(len(chem.forms) - 1, 1)
                           for fi, f in enumerate(chem.forms) for _ in f.strengths])
        strength_w = rng.uniform(0.5, 1.5, len(combos))
        for f in chem.forms:  # normalise strengths within each form
            mask = np.array([cf is f for cf, _, _ in combos])
            strength_w[mask] /= strength_w[mask].sum()
        combo_w = form_w * strength_w
        combo_w /= combo_w.sum()

        brand_w = np.array([1.0, 0.5, 0.3, 0.2][: len(chem.brands)])
        brand_w = brand_w / brand_w.sum() if len(brand_w) else brand_w

        for si, ((form, strength, cost), cw) in enumerate(zip(combos, combo_w, strict=False)):
            fs = _pair(si)
            generic_code = f"{chem_code}AA{fs}{fs}"
            unit = FORM_UNITS[form.form]
            if chem.generic:
                med_rows.append((generic_code, _presentation_name(chem.name, strength, form.form), chem_code,
                                 1, None, None, form.form, strength, unit, form.pack))
                chem_idx.append(ci); kind.append(0); split_w.append(cw); pack.append(form.pack)
                base_cost.append(cost)
            for bi, brand in enumerate(chem.brands):
                prem = chem.brand_premium * rng.uniform(0.9, 1.1) if chem.generic else rng.uniform(0.93, 1.07)
                med_rows.append((f"{chem_code}B{chr(65 + bi)}{fs}{fs}", _presentation_name(brand, strength, form.form),
                                 chem_code, 0, brand, generic_code if chem.generic else None,
                                 form.form, strength, unit, form.pack))
                chem_idx.append(ci); kind.append(1 if chem.generic else 2)
                split_w.append(cw * brand_w[bi]); pack.append(form.pack)
                base_cost.append(cost * prem)

    chemical = pd.DataFrame(chem_rows, columns=["chemical_code", "chemical_name", "paragraph_code"])
    med = pd.DataFrame(med_rows, columns=[
        "presentation_code", "presentation_name", "chemical_code", "is_generic", "brand_name",
        "generic_equivalent_code", "form", "strength", "unit_of_measure", "pack_quantity",
    ])
    chem_idx_a = np.array(chem_idx)
    kind_a = np.array(kind)
    base_cost_a = np.round(np.array(base_cost), 4)

    history, price_by_month, current, last_change = _price_history(med, chem_idx_a, kind_a, base_cost_a)

    med["unit_cost"] = current
    med["created_at"] = TS
    med["updated_at"] = [f"{d}T06:00:00" if d else TS for d in last_change]

    return Medicines(
        bnf_chapter=chapter, bnf_section=section, bnf_paragraph=paragraph, bnf_chemical=chemical,
        medicine=med, medicine_price_history=history, chem_idx=chem_idx_a, kind=kind_a,
        split_weight=np.array(split_w), pack=np.array(pack), price_by_month=price_by_month,
    )


def _month_index(d: date) -> int:
    return (d.year - cfg.START_DATE.year) * 12 + d.month - 1


def _price_history(med: pd.DataFrame, chem_idx: np.ndarray, kind: np.ndarray, base: np.ndarray):
    """Apply PRICE_EVENTS: returns history rows, (n x months) price matrix, current price, last change date."""
    names = np.array([CATALOGUE[i].name for i in chem_idx])
    n = len(med)
    price = np.repeat(base[:, None], cfg.N_MONTHS, axis=1)
    # Per-presentation list of (effective_from, cost, reason)
    timeline: list[list[tuple[date, float, str]]] = [[(date(2022, 4, 1), base[i], "initial")] for i in range(n)]

    for kind_name, chem_name, start_s, end_s, mult in PRICE_EVENTS:
        start = date.fromisoformat(start_s)
        s_idx = _month_index(start)
        targets = np.where(kind > 0)[0] if kind_name == "uplift" else np.where((names == chem_name) & (kind == 0))[0]
        for i in targets:
            if kind_name == "concession":
                end = date.fromisoformat(end_s)
                e_idx = _month_index(end)
                baseline = timeline[i][-1][1]
                timeline[i].append((start, round(baseline * mult, 4), "price concession"))
                timeline[i].append((end + timedelta(days=1), baseline, "concession ended"))
                price[i, s_idx: e_idx + 1] = round(baseline * mult, 4)
            else:
                new = round(timeline[i][-1][1] * mult, 4)
                timeline[i].append((start, new, "tariff reduction" if kind_name == "reduction" else "annual uplift"))
                price[i, s_idx:] = new

    rows, current, last_change = [], [], []
    for i, events in enumerate(timeline):
        events.sort(key=lambda e: e[0])
        for j, (frm, cost, reason) in enumerate(events):
            to = events[j + 1][0] - timedelta(days=1) if j + 1 < len(events) else None
            rows.append((med.at[i, "presentation_code"], frm, to, cost, reason, f"{frm}T06:00:00"))
        current.append(events[-1][1])
        last_change.append(events[-1][0] if len(events) > 1 else None)

    history = pd.DataFrame(rows, columns=[
        "presentation_code", "effective_from", "effective_to", "unit_cost", "change_reason", "created_at",
    ])
    history["effective_to"] = history["effective_to"].astype(object)
    return history, price, np.array(current), last_change


# --------------------------------------------------------------------------
# Patients
# --------------------------------------------------------------------------


@dataclass
class Patients:
    patient: pd.DataFrame
    practice_idx: np.ndarray  # sorted ascending
    age_idx: np.ndarray
    sex: np.ndarray  # clean F/M/U, before casing defects


def build_patients(rng: np.random.Generator, org: Organisations, vol: cfg.Volumes, dq: cfg.DataQuality) -> Patients:
    per_practice = _allocate(vol.patients, org.practice_list_size, minimum=20)
    p_idx = np.repeat(np.arange(len(per_practice)), per_practice)
    n = len(p_idx)

    base = np.array(cfg.AGE_BAND_POPULATION)
    rural_tilt = np.array([0.9, 0.9, 0.85, 0.9, 1.05, 1.3, 1.35, 1.35])
    age_idx = np.empty(n, dtype=int)
    for rural in (False, True):
        mask = org.practice_rural[p_idx] == rural
        probs = base * (rural_tilt if rural else 1.0)
        age_idx[mask] = rng.choice(len(base), mask.sum(), p=probs / probs.sum())

    # Women outnumber men in older bands.
    p_female = np.array([0.49, 0.49, 0.50, 0.50, 0.505, 0.52, 0.55, 0.64])[age_idx]
    sex = np.where(rng.random(n) < p_female, "F", "M").astype(object)
    sex[rng.random(n) < dq.patient_unknown_sex_rate] = "U"

    imd = np.clip(org.practice_imd[p_idx] + rng.integers(-1, 2, n), 1, 10)

    patient = pd.DataFrame({
        "patient_id": np.arange(100001, 100001 + n),
        "practice_code": org.practice["practice_code"].to_numpy()[p_idx],
        "age_band": np.array(cfg.AGE_BANDS)[age_idx],
        "sex": sex.copy(),
        "imd_decile": pd.array(imd, dtype="Int64"),
        "registered_date": _random_dates(rng, date(1990, 1, 1), date(2022, 12, 31), n),
        "created_at": TS,
        "updated_at": TS,
    })

    bad_case = (rng.random(n) < dq.patient_bad_sex_casing_rate) & (sex != "U")
    patient.loc[bad_case, "sex"] = patient.loc[bad_case, "sex"].str.lower()
    patient.loc[rng.random(n) < dq.patient_null_imd_rate, "imd_decile"] = pd.NA

    return Patients(patient=patient, practice_idx=p_idx, age_idx=age_idx, sex=sex)
