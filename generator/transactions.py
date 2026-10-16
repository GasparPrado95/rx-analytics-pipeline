"""Generate prescriptions (headers) and prescription items (lines), month by month.

Volume model, per practice p and month m:
    expected prescriptions = k * list_size[p] * region_rate * imd_factor * practice_noise
                             * medicine_demand(m, region) * global_growth(m)
where medicine_demand sums each presentation's weight for that month: popularity,
seasonality, per-medicine trend, branded->generic shift and regional antibiotic
habits. k is solved so the expected total hits the target line count.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from . import config as cfg
from .dimensions import Medicines, Organisations, Patients
from .reference_data import CATALOGUE, REGIONS

log = logging.getLogger(__name__)

DAY = np.timedelta64(1, "D")
SECOND = np.timedelta64(1, "s")


@dataclass
class Transactions:
    prescription: pd.DataFrame
    prescription_item: pd.DataFrame
    stats: dict


def _month_starts() -> list[date]:
    return [date(cfg.START_DATE.year + i // 12, i % 12 + 1, 1) for i in range(cfg.N_MONTHS)]


def medicine_weights(med: Medicines) -> np.ndarray:
    """Weight of each presentation for each (month, region): shape (months, regions, medicines)."""
    t = np.arange(cfg.N_MONTHS)
    chems = [CATALOGUE[i] for i in med.chem_idx]
    pop = np.array([c.popularity for c in chems])
    trend = np.array([c.trend for c in chems])
    season = np.array([cfg.SEASONALITY[c.season] for c in chems])  # (n, 12)
    s0 = np.array([c.brand_share for c in chems])
    s_end = np.array([
        c.brand_share_end if c.brand_share_end is not None else c.brand_share * (1 - cfg.DEFAULT_BRAND_SHARE_DECLINE)
        for c in chems
    ])
    antibacterial = np.array([c.paragraph.startswith("0501") for c in chems])

    frac = t / (cfg.N_MONTHS - 1)
    brand_share = s0[None, :] + (s_end - s0)[None, :] * frac[:, None]  # (months, n)
    split = np.where(
        med.kind[None, :] == 0, 1 - brand_share,
        np.where(med.kind[None, :] == 1, brand_share, 1.0),
    ) * med.split_weight[None, :]

    w = (
        pop[None, :]
        * season[:, t % 12].T
        * (1 + trend[None, :]) ** (t[:, None] / 12)
        * split
    )  # (months, n)

    abx_factor = np.array([r[4] for r in REGIONS])  # (regions,)
    region_mult = np.where(antibacterial[None, :], abx_factor[:, None], 1.0)  # (regions, n)
    return w[:, None, :] * region_mult[None, :, :]


def _cumulative_by_group(group_sorted: np.ndarray, weights: np.ndarray, n_groups: int):
    """For rows sorted by group: global cumulative weights plus each group's start offset and total."""
    cum = np.cumsum(weights)
    totals = np.bincount(group_sorted, weights=weights, minlength=n_groups)
    starts = np.r_[0.0, np.cumsum(totals)[:-1]]
    return cum, starts, totals


def _pick_within_group(rng, cum, starts, totals, groups: np.ndarray) -> np.ndarray:
    """Weighted pick of one row inside each requested group (vectorised inverse-CDF)."""
    target = starts[groups] + rng.random(len(groups)) * totals[groups]
    idx = np.searchsorted(cum, target, side="right")
    return np.minimum(idx, len(cum) - 1)


def build_transactions(rng: np.random.Generator, org: Organisations, med: Medicines, pts: Patients,
                       vol: cfg.Volumes, dq: cfg.DataQuality) -> Transactions:
    n_practices = len(org.practice)
    months = _month_starts()
    W = medicine_weights(med)  # (months, regions, medicines)
    demand = W.sum(axis=2)  # (months, regions)

    region_rate = np.array([r[3] for r in REGIONS])[org.practice_region_idx]
    imd_factor = np.array(cfg.IMD_RATE_FACTOR)[org.practice_imd - 1]
    practice_noise = rng.lognormal(0, 0.12, n_practices)
    practice_base = org.practice_list_size * region_rate * imd_factor * practice_noise

    growth = (1 + cfg.GLOBAL_ANNUAL_GROWTH) ** (np.arange(cfg.N_MONTHS) / 12)
    lam = practice_base[:, None] * demand[:, org.practice_region_idx].T * growth[None, :]  # (practices, months)
    lines_per_rx = 1 + vol.lines_per_prescription_extra
    lam *= vol.target_lines / lines_per_rx / lam.sum()

    # --- patient pickers: one per age/sex profile ---
    profile_names = list(cfg.AGE_PROFILES)
    profile_of_chem = np.array([profile_names.index(c.profile) for c in CATALOGUE])
    pickers = []
    for name in profile_names:
        age_w, sex_only = cfg.AGE_PROFILES[name]
        w = np.array(age_w)[pts.age_idx] * rng.uniform(0.3, 1.7, len(pts.age_idx))  # some patients prescribe more
        if sex_only:
            w = w * (pts.sex == sex_only)
        w = np.maximum(w, 1e-9)
        pickers.append(_cumulative_by_group(pts.practice_idx, w, n_practices))

    prescriber_picker = _cumulative_by_group(org.prescriber_practice_idx, org.prescriber_weight, n_practices)

    is_acute = np.array([
        CATALOGUE[c].paragraph.startswith("05") or CATALOGUE[c].profile == "acute" for c in med.chem_idx
    ])

    hdr_parts, line_parts = [], []
    for m, month_start in enumerate(months):
        counts = rng.poisson(lam[:, m])
        h_practice = np.repeat(np.arange(n_practices), counts)
        nh = len(h_practice)
        n_lines = 1 + rng.poisson(vol.lines_per_prescription_extra, nh)
        l_header = np.repeat(np.arange(nh), n_lines)
        l_region = org.practice_region_idx[h_practice][l_header]

        l_med = np.empty(len(l_header), dtype=np.int32)
        for r in range(len(REGIONS)):
            mask = l_region == r
            p = W[m, r] / W[m, r].sum()
            l_med[mask] = rng.choice(len(p), mask.sum(), p=p)

        # Patient chosen to fit the first line's medicine (age band / sex profile).
        first_line = np.r_[0, np.cumsum(n_lines)[:-1]]
        h_profile = profile_of_chem[med.chem_idx[l_med[first_line]]]
        # A prescription never lists the same presentation twice: drop repeat draws (never the first line).
        _, keep = np.unique(l_header.astype(np.int64) * len(med.medicine) + l_med, return_index=True)
        keep.sort()
        l_header, l_med = l_header[keep], l_med[keep]

        h_patient = np.empty(nh, dtype=np.int64)
        for pi, (cum, starts, totals) in enumerate(pickers):
            mask = h_profile == pi
            h_patient[mask] = _pick_within_group(rng, cum, starts, totals, h_practice[mask])
        h_prescriber = _pick_within_group(rng, *prescriber_picker, h_practice)

        # Issue dates: weekdays, with a little Saturday activity.
        days = pd.date_range(month_start, periods=31, freq="D")
        days = days[days.month == month_start.month]
        day_w = np.where(days.dayofweek < 5, 1.0, np.where(days.dayofweek == 5, 0.08, 0.0))
        h_issue = days.values.astype("datetime64[D]")[rng.choice(len(days), nh, p=day_w / day_w.sum())]
        h_created = h_issue + rng.integers(8 * 3600, 18 * 3600 + 1800, nh) * SECOND

        lag = rng.choice(8, len(l_header), p=[0.30, 0.25, 0.15, 0.10, 0.07, 0.05, 0.04, 0.04])
        l_disp = np.minimum(h_issue[l_header] + lag * DAY, np.datetime64(cfg.END_DATE))

        hdr_parts.append((h_practice, h_patient, h_prescriber, h_issue, h_created))
        line_parts.append((l_header, l_med, l_disp))
        log.debug("month %s: %d prescriptions, %d lines", month_start, nh, len(l_header))

    # --- stitch months together ---
    offsets = np.r_[0, np.cumsum([len(h[0]) for h in hdr_parts])[:-1]]
    h_practice, h_patient, h_prescriber, h_issue, h_created = (np.concatenate(x) for x in zip(*hdr_parts, strict=False))
    l_header = np.concatenate([lp[0] + off for lp, off in zip(line_parts, offsets, strict=False)])
    l_med = np.concatenate([lp[1] for lp in line_parts])
    l_disp = np.concatenate([lp[2] for lp in line_parts])
    n_lines = len(l_header)

    # Prescription ids follow arrival order, like an IDENTITY column would.
    h_order = np.argsort(h_created, kind="stable")
    h_rank = np.empty_like(h_order)
    h_rank[h_order] = np.arange(len(h_order))
    prescription_id = 5_000_000_001 + h_rank

    # --- line measures ---
    acute = is_acute[l_med]
    items = np.where(acute, 1, rng.choice([1, 2, 3], n_lines, p=[0.93, 0.06, 0.01]))
    months_supply = np.where(acute, 1, rng.choice([1, 2, 3], n_lines, p=[0.80, 0.15, 0.05]))
    quantity = (med.pack[l_med] * items * months_supply).astype(float)

    disp_month = (l_disp.astype("datetime64[M]") - np.datetime64(cfg.START_DATE, "M")).astype(int)
    disp_month = disp_month.clip(0, cfg.N_MONTHS - 1)
    unit_cost = med.price_by_month[l_med, disp_month]
    discount = rng.uniform(0.905, 0.935, n_lines)

    # --- arrival timestamps: normal submission lag, plus late arrivals ---
    as_of = np.datetime64(cfg.AS_OF) + np.timedelta64(86399, "s")

    def cap(ts: np.ndarray) -> np.ndarray:
        """Timestamps past the source snapshot land in its last 3 days (not all on one instant)."""
        over = ts > as_of
        ts = ts.copy()
        ts[over] = as_of - rng.integers(0, 3 * 86400, over.sum()) * SECOND
        return ts
    sub_lag = np.minimum(2 + rng.geometric(0.25, n_lines), 28)
    created = l_disp + sub_lag * DAY + rng.integers(6 * 3600, 22 * 3600, n_lines) * SECOND
    late = rng.random(n_lines) < dq.late_arrival_rate
    created[late] = l_disp[late] + rng.integers(35, 151, late.sum()) * DAY + rng.integers(0, 86400, late.sum()) * SECOND
    created = cap(created)
    updated = created.copy()

    # Corrections: restated later with a different quantity; updated_at moves on.
    corrected = rng.random(n_lines) < dq.correction_rate
    quantity[corrected] = np.maximum(1, np.rint(quantity[corrected] * rng.choice([0.5, 2.0], corrected.sum())))
    updated[corrected] = np.maximum(cap(created[corrected] + rng.integers(20, 201, corrected.sum()) * DAY),
                                created[corrected])

    nic = np.round(quantity * unit_cost, 2)
    actual = np.round(nic * discount, 2)

    # Credit notes: negative lines.
    credit = rng.random(n_lines) < dq.credit_line_rate
    quantity[credit] *= -1
    nic[credit] *= -1
    actual[credit] *= -1

    # --- duplicates: double-submitted lines, new id, same content ---
    dup_src = np.where(rng.random(n_lines) < dq.duplicate_line_rate)[0]
    dup_created = cap(created[dup_src] + rng.integers(60, 3 * 86400, len(dup_src)) * SECOND)

    def with_dups(a):
        return np.concatenate([a, a[dup_src]])

    l_header, l_med, l_disp, items, quantity, nic, actual = map(
        with_dups, (l_header, l_med, l_disp, items, quantity, nic, actual)
    )
    created = np.concatenate([created, dup_created])
    updated = np.concatenate([updated, dup_created])
    late = np.concatenate([late, np.zeros(len(dup_src), bool)])
    total_lines = len(l_header)

    # --- nulls ---
    actual[rng.random(total_lines) < dq.null_actual_cost_rate] = np.nan
    quantity[rng.random(total_lines) < dq.null_quantity_rate] = np.nan
    nic[rng.random(total_lines) < dq.null_nic_rate] = np.nan

    # Item ids follow arrival order (created_at): late arrivals get high ids.
    l_order = np.argsort(created, kind="stable")

    prescription = pd.DataFrame({
        "prescription_id": prescription_id[h_order],
        "patient_id": pts.patient["patient_id"].to_numpy()[h_patient][h_order],
        "prescriber_id": org.prescriber["prescriber_id"].to_numpy()[h_prescriber][h_order],
        "practice_code": org.practice["practice_code"].to_numpy()[h_practice][h_order],
        "issue_date": h_issue[h_order],
        "created_at": h_created[h_order],
        "updated_at": h_created[h_order],
    })
    item = pd.DataFrame({
        "item_line_id": np.arange(1, total_lines + 1, dtype=np.int64),
        "prescription_id": prescription_id[l_header][l_order],
        "presentation_code": med.medicine["presentation_code"].to_numpy()[l_med][l_order],
        "items": items[l_order],
        "quantity": quantity[l_order],
        "net_ingredient_cost": nic[l_order],
        "actual_cost": actual[l_order],
        "dispensing_date": l_disp[l_order],
        "created_at": created[l_order],
        "updated_at": updated[l_order],
    })

    stats = {
        "prescriptions": len(prescription),
        "lines": total_lines,
        "duplicates": len(dup_src),
        "late_arrivals": int(late.sum()),
        "corrections": int(corrected.sum()),
        "credits": int(credit.sum()),
    }
    return Transactions(prescription=prescription, prescription_item=item, stats=stats)
