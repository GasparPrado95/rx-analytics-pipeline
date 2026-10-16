"""Generator settings: volumes, date range, behavioural parameters and data-quality rates.

Everything that shapes the synthetic data lives here, so a reviewer can see the
"story" baked into the dataset without reading the generation code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

SEED = 20230101

# Dispensing window covered by the data (inclusive).
START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)
N_MONTHS = 36

# Snapshot time of the source system. Late-arriving rows never land after this.
AS_OF = date(2026, 4, 30)

# Fixed load timestamp for reference tables, so reruns are byte-identical.
REFERENCE_LOADED_AT = "2022-12-01T06:00:00"


@dataclass(frozen=True)
class Volumes:
    practices: int = 400
    prescribers: int = 1500
    patients: int = 50_000
    target_lines: int = 2_500_000
    lines_per_prescription_extra: float = 0.45  # lines = 1 + Poisson(this)


@dataclass(frozen=True)
class DataQuality:
    """Deliberate defects the dbt staging layer has to handle."""

    duplicate_line_rate: float = 0.002  # double-submitted lines (new id, same content)
    late_arrival_rate: float = 0.015  # lines that reach the source 35-150 days after dispensing
    correction_rate: float = 0.003  # lines restated later (quantity/cost changed, updated_at bumped)
    null_actual_cost_rate: float = 0.003
    null_quantity_rate: float = 0.0005
    null_nic_rate: float = 0.0005
    credit_line_rate: float = 0.0002  # negative quantity/cost credit notes
    patient_null_imd_rate: float = 0.01
    patient_bad_sex_casing_rate: float = 0.005
    patient_unknown_sex_rate: float = 0.003
    practice_null_postcode: int = 3
    practice_bad_casing_rate: float = 0.08


@dataclass(frozen=True)
class Settings:
    seed: int = SEED
    volumes: Volumes = field(default_factory=Volumes)
    dq: DataQuality = field(default_factory=DataQuality)


# Monthly seasonality multipliers, January..December.
SEASONALITY: dict[str, list[float]] = {
    "flat": [1.0] * 12,
    # Antibiotics: winter respiratory infections.
    "winter": [1.45, 1.35, 1.15, 0.95, 0.85, 0.75, 0.72, 0.75, 0.90, 1.05, 1.25, 1.50],
    # Mild winter uplift: inhaled steroids, mucolytics, oral steroids, vitamin D.
    "mild_winter": [1.15, 1.10, 1.05, 1.00, 0.95, 0.90, 0.88, 0.90, 0.95, 1.00, 1.05, 1.12],
    # Influenza antivirals: sharp peak in the flu season only.
    "flu": [2.80, 1.80, 0.80, 0.30, 0.15, 0.10, 0.10, 0.10, 0.20, 0.60, 1.60, 3.00],
    # Hay fever: antihistamines and nasal steroids.
    "summer": [0.55, 0.60, 0.85, 1.25, 1.70, 1.90, 1.60, 1.15, 0.80, 0.60, 0.50, 0.50],
    # Smoking cessation: New Year resolutions.
    "new_year": [1.60, 1.20, 1.00, 0.95, 0.90, 0.85, 0.85, 0.85, 0.90, 1.00, 0.95, 0.75],
}

# Overall growth in prescribing volume per year (on top of per-medicine trends).
GLOBAL_ANNUAL_GROWTH = 0.015

# Branded share falls by this fraction of its starting value over the 36 months,
# unless a medicine sets its own end share.
DEFAULT_BRAND_SHARE_DECLINE = 0.45

# Practice deprivation effect on prescribing rate: decile 1 (most deprived) -> 10.
IMD_RATE_FACTOR = [1.25, 1.20, 1.15, 1.10, 1.05, 1.00, 0.96, 0.92, 0.89, 0.86]

# Patient age bands and how strongly each drives prescribing.
AGE_BANDS = ["0-4", "5-14", "15-24", "25-44", "45-64", "65-74", "75-84", "85+"]
AGE_BAND_POPULATION = [0.055, 0.120, 0.115, 0.270, 0.255, 0.100, 0.060, 0.025]

# Who receives a medicine: age weights per band, plus an optional sex restriction.
AGE_PROFILES: dict[str, tuple[list[float], str | None]] = {
    "all": ([0.4, 0.3, 0.5, 0.8, 1.7, 3.2, 4.5, 5.5], None),
    "older": ([0.02, 0.02, 0.05, 0.3, 1.5, 4.0, 6.0, 7.0], None),
    "child": ([3.0, 2.0, 0.6, 0.5, 0.4, 0.4, 0.4, 0.4], None),
    "young": ([0.0, 2.0, 2.0, 1.0, 0.3, 0.05, 0.0, 0.0], None),
    "acute": ([1.2, 1.0, 0.8, 0.8, 1.0, 1.4, 1.8, 2.2], None),
    "female_repro": ([0.0, 0.05, 2.0, 1.5, 0.1, 0.0, 0.0, 0.0], "F"),
    "female_midlife": ([0.0, 0.0, 0.0, 0.3, 3.0, 1.2, 0.5, 0.2], "F"),
    "female_older": ([0.0, 0.0, 0.0, 0.2, 2.0, 3.0, 3.0, 2.0], "F"),
    "male_older": ([0.0, 0.0, 0.0, 0.2, 1.5, 3.0, 3.0, 2.0], "M"),
}

# Practices: prescribers by type and their relative share of prescriptions issued.
PRESCRIBER_TYPES = [
    ("GP", "General practitioner", 0.65, 3.0),
    ("NP", "Nurse independent prescriber", 0.20, 1.2),
    ("PH", "Pharmacist independent prescriber", 0.15, 1.0),
]
