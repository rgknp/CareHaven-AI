"""Generate synthetic patient profiles for downstream modality simulations.

Schema example:
{
  "patient_id": "UUID",
  "name": "John Doe",
  "dob": "1940-06-15",
  "sex": "male",
  "education_years": 12,
  "comorbidities": ["hypertension", "diabetes"],
  "medications": ["donepezil"],
  "device_ids": {"wearable": "WEAR-001", "speech": "SPK-001"},
  "cognitive_baseline": {
      "mmse": 27,
      "moca": 24,
      "depression_score": 5
  }
}

Design Notes:
- Ages biased toward older adult population (65-90) with a tail.
- Education years influences baseline cognitive scores (positive correlation).
- Comorbidities sampled with realistic prevalence weights.
- Some medications tied to comorbidities (e.g., donepezil for cognitive impairment, metformin for diabetes).
- Cognitive baseline metrics provide potential covariates for ML models.
"""
from __future__ import annotations

import uuid
import random
import json
from datetime import date, timedelta, datetime
from pathlib import Path
import argparse
from typing import List, Dict, Any, Optional

try:
    import pandas as pd  # type: ignore
except ImportError:
    pd = None  # type: ignore

SEX_OPTIONS = ["male", "female"]

# Weighted comorbidities (approximate relative prevalence in older adults)
COMORBIDITY_WEIGHTS = {
    "hypertension": 0.55,
    "diabetes": 0.25,
    "hyperlipidemia": 0.40,
    "coronary_artery_disease": 0.18,
    "atrial_fibrillation": 0.08,
    "chronic_kidney_disease": 0.12,
    "mild_cognitive_impairment": 0.22,
    "parkinsonism": 0.04,
    "depression": 0.20,
    "sleep_apnea": 0.10
}

MEDICATIONS_MAP = {
    "hypertension": ["lisinopril", "amlodipine", "losartan"],
    "diabetes": ["metformin", "glipizide"],
    "hyperlipidemia": ["atorvastatin", "rosuvastatin"],
    "coronary_artery_disease": ["aspirin", "clopidogrel"],
    "atrial_fibrillation": ["apixaban", "warfarin"],
    "chronic_kidney_disease": ["epoetin"],
    "mild_cognitive_impairment": ["donepezil"],
    "parkinsonism": ["carbidopa-levodopa"],
    "depression": ["sertraline", "citalopram"],
    "sleep_apnea": ["cpap"]
}

FIRST_NAMES = [
    "John","Mary","Robert","Patricia","Michael","Linda","William","Barbara","David","Elizabeth","Richard","Jennifer","Joseph","Maria","Thomas","Susan","Charles","Margaret","Christopher","Sarah"
]
LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin"
]


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def sample_comorbidities() -> List[str]:
    # Decide how many comorbidities (0-5 typical) skewed low
    k = max(0, min(int(random.normalvariate(2.0, 1.2)), 5))
    items = list(COMORBIDITY_WEIGHTS.items())
    choices = random.choices(
        [c for c,_ in items],
        weights=[w for _,w in items],
        k=10  # oversample then unique
    )
    unique = []
    for c in choices:
        if c not in unique:
            unique.append(c)
        if len(unique) >= k:
            break
    return unique


def derive_medications(comorbidities: List[str]) -> List[str]:
    meds = []
    for c in comorbidities:
        cand = MEDICATIONS_MAP.get(c, [])
        if cand:
            meds.append(random.choice(cand))
    # occasional polypharmacy random extra
    if random.random() < 0.15:
        meds.append(random.choice(["vitamin_d", "multivitamin", "omega_3"]))
    return sorted(set(meds))


def random_dob(min_age=65, max_age=90) -> date:
    today = date.today()
    age = int(random.triangular(min_age, max_age, 72))  # peak around 72
    # approximate birthdate offset
    days_offset = random.randint(0, 364)
    birth_year = today.year - age
    # Adjust for leap years by bounding to valid date
    try:
        dob = date(birth_year, 1, 1) + timedelta(days=days_offset)
    except ValueError:
        dob = date(birth_year, 6, 15)  # fallback mid-year
    return dob


def cognitive_baseline(education_years: int, has_mci: bool, has_depression: bool):
    # Start with base distributions
    mmse = random.normalvariate(27.5, 2.0)
    moca = random.normalvariate(24.5, 2.5)
    depression = random.normalvariate(5, 3)
    # Education correlation
    edu_factor = (education_years - 12) * 0.15
    mmse += edu_factor
    moca += edu_factor * 1.1
    # Mild cognitive impairment lowers scores
    if has_mci:
        mmse -= random.uniform(1.0, 3.0)
        moca -= random.uniform(2.0, 4.0)
    # Depression may reduce performance
    if has_depression:
        moca -= random.uniform(0.5, 1.5)
    mmse = max(10, min(30, mmse))
    moca = max(5, min(30, moca))
    depression = max(0, min(27, depression))
    return {
        "mmse": int(round(mmse)),
        "moca": int(round(moca)),
        "depression_score": int(round(depression))
    }


def generate_patient_profiles(n: int, seed: Optional[int] = None):
    if seed is not None:
        random.seed(seed)
    profiles = []
    for i in range(1, n + 1):
        pid = str(uuid.uuid4())
        name = random_name()
        sex = random.choice(SEX_OPTIONS)
        education_years = int(max(4, min(random.normalvariate(13, 3), 22)))
        comorbidities = sample_comorbidities()
        meds = derive_medications(comorbidities)
        dob = random_dob()
        baseline = cognitive_baseline(education_years, 'mild_cognitive_impairment' in comorbidities, 'depression' in comorbidities)
        profile = {
            "patient_id": pid,
            "name": name,
            "dob": dob.isoformat(),
            "sex": sex,
            "education_years": education_years,
            "comorbidities": comorbidities,
            "medications": meds,
            "device_ids": {"wearable": f"WEAR-{i:03d}", "speech": f"SPK-{i:03d}"},
            "cognitive_baseline": baseline
        }
        profiles.append(profile)
    return profiles


def write_outputs(profiles, output_dir: Path, write_csv: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'patient_profiles.json'
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(profiles, f, indent=2)
    csv_path = None
    if write_csv:
        if pd is None:
            print('[WARN] pandas not installed; skipping CSV export.')
        else:
            import pandas as _pd
            df = _pd.json_normalize(profiles, sep='_')
            csv_path = output_dir / 'patient_profiles.csv'
            df.to_csv(csv_path, index=False)
    return json_path, csv_path


def parse_args():
    p = argparse.ArgumentParser(description='Generate synthetic patient profile baseline dataset.')
    p.add_argument('--patients', type=int, default=1000, help='Number of patient profiles to generate')
    p.add_argument('--output-dir', default=None, help='Output directory (default: ../data)')
    p.add_argument('--csv', action='store_true', help='Also export CSV (requires pandas)')
    p.add_argument('--seed', type=int, default=None, help='Random seed')
    return p.parse_args()


def main():
    args = parse_args()
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    else:
        output_dir = (Path(__file__).resolve().parent.parent / 'data').resolve()
    profiles = generate_patient_profiles(args.patients, seed=args.seed)
    json_path, csv_path = write_outputs(profiles, output_dir, args.csv)
    print(f'Wrote patient profiles JSON: {json_path}')
    if csv_path:
        print(f'Wrote patient profiles CSV:  {csv_path}')
    print(f'Total profiles: {len(profiles):,}')


if __name__ == '__main__':
    main()
