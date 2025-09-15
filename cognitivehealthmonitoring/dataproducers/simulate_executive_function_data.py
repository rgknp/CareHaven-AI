"""Simulate synthetic executive function test data (e.g., Trail Making Test B, Symbol Digit Modalities).

Example record:
{
  "device_id": "APP-003",
  "patient_id": "UUID-12345",
  "timestamp": "2025-09-15T10:15:00Z",
  "domain": "executive_function",
  "metrics": {
    "tmt_b_completion_sec": 110,
    "errors": 2,
    "symbol_digit_correct": 48
  },
  "task_type": "trail_making_test_b"
}

Modeling Notes:
- TMT-B completion times (lower is better) generally 70–180s in older adults; mildly impaired can exceed 200s.
- Errors modestly correlated with longer completion time (fatigue / executive dysfunction).
- Symbol Digit Modalities (oral or written) correct counts in a 90s window: typical older adults ~40–55; mild impairment ~30–40.
- Practice effect: slight improvement (faster time, more correct) early in series then plateau / slight decline.
- Optional patient profile reuse aligns cognitive baseline (e.g., higher MoCA/MMSE -> faster TMT-B, more symbol digits).
"""
from __future__ import annotations

import uuid
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
import argparse
from typing import Optional, List

try:
    import pandas as pd  # type: ignore
except ImportError:  # graceful degradation
    pd = None  # type: ignore


# ---------------------------------- Core Simulation ---------------------------------- #

def seeded(seed: Optional[int]):
    if seed is not None:
        random.seed(seed)


def derive_baselines(num_patients: int, patient_profiles: Optional[List[dict]] = None):
    """Derive per-patient baseline parameters.

    If patient_profiles provided, use cognitive baselines to modulate exec function performance.
    Returns list of dict with baseline metrics and trends.
    """
    baselines = []
    for i in range(num_patients):
        if patient_profiles:
            prof = patient_profiles[i]
            cog = prof.get('cognitive_baseline', {})
            mmse = cog.get('mmse', 26)
            moca = cog.get('moca', 24)
            # Map cognitive scores to performance factor (higher => better exec function)
            perf_factor = ((mmse + moca) / 60)  # ~0.5 to 1.0
        else:
            perf_factor = random.uniform(0.55, 0.95)

        # Base TMT-B completion: inverse with perf_factor
        tmt_base = random.normalvariate(170 - perf_factor * 80, 15)  # typical range center
        tmt_base = max(65, min(tmt_base, 260))

        # Errors baseline; more if slower
        errors_base = max(0, int(random.normalvariate((220 - tmt_base) / 40, 1.0)))
        errors_base = min(errors_base, 10)

        # Symbol digit baseline: direct with perf_factor
        sdmt_base = random.normalvariate(30 + perf_factor * 30, 4)  # 30–60 typical
        sdmt_base = max(15, min(sdmt_base, 70))

        # Trends: initial practice improvement first ~5 days then slight fatigue/plateau
        practice_gain_tmt = random.uniform(0.5, 1.5)  # seconds improvement per day early
        practice_gain_sdmt = random.uniform(0.6, 1.4)  # items improvement early
        late_decline_tmt = random.uniform(0.05, 0.25)  # slight re-worsening per day after plateau
        late_decline_sdmt = random.uniform(0.05, 0.20)  # slight decline after plateau

        baselines.append({
            'tmt_base': tmt_base,
            'errors_base': errors_base,
            'sdmt_base': sdmt_base,
            'practice_gain_tmt': practice_gain_tmt,
            'practice_gain_sdmt': practice_gain_sdmt,
            'late_decline_tmt': late_decline_tmt,
            'late_decline_sdmt': late_decline_sdmt,
        })
    return baselines


def simulate_exec_day(base: dict, day_index: int):
    """Simulate daily executive function outcomes with practice then plateau dynamics."""
    # Practice phase days 0-4
    if day_index <= 4:
        tmt = base['tmt_base'] - base['practice_gain_tmt'] * day_index
        sdmt = base['sdmt_base'] + base['practice_gain_sdmt'] * day_index
    else:
        # plateau then mild decline after day 10
        tmt = base['tmt_base'] - base['practice_gain_tmt'] * 4 + base['late_decline_tmt'] * max(0, day_index - 10)
        sdmt = base['sdmt_base'] + base['practice_gain_sdmt'] * 4 - base['late_decline_sdmt'] * max(0, day_index - 10)

    # Add noise
    tmt = random.normalvariate(tmt, 6)
    sdmt = random.normalvariate(sdmt, 2.5)

    # Bound values
    tmt = max(55, min(tmt, 300))
    sdmt = max(10, min(sdmt, 80))

    # Errors correlate with slower times
    errors_mean = (tmt - 60) / 50  # e.g., 100s -> ~0.8
    errors = max(0, int(random.normalvariate(errors_mean, 1)))
    errors = min(errors, 12)

    return {
        'tmt_b_completion_sec': int(round(tmt)),
        'errors': errors,
        'symbol_digit_correct': int(round(sdmt))
    }


def generate_dataset(num_patients: int, days: int, start_date: datetime, seed: Optional[int] = None, patient_profiles=None):
    if num_patients <= 0:
        raise ValueError('num_patients must be > 0')
    if days <= 0:
        raise ValueError('days must be > 0')
    seeded(seed)

    provided = False
    if patient_profiles:
        provided = True
        if len(patient_profiles) < num_patients:
            print(f"[WARN] Requested {num_patients} patients but only {len(patient_profiles)} profiles available. Reducing.")
            num_patients = len(patient_profiles)
        profiles_slice = patient_profiles[:num_patients]
        patient_ids = [p.get('patient_id') or str(uuid.uuid4()) for p in profiles_slice]
        device_ids = [(p.get('device_ids') or {}).get('app') for p in profiles_slice]
        # If no app device id, synthesize
        for i,d in enumerate(device_ids):
            if not d:
                device_ids[i] = f'APP-{i+1:03d}'
    else:
        patient_ids = [str(uuid.uuid4()) for _ in range(num_patients)]
        device_ids = [f'APP-{i:03d}' for i in range(1, num_patients + 1)]

    baselines = derive_baselines(num_patients, patient_profiles if provided else None)

    records = []
    for idx in range(num_patients):
        pid = patient_ids[idx]
        app_id = device_ids[idx]
        for day in range(days):
            timestamp = start_date + timedelta(days=day, hours=random.randint(9, 14), minutes=random.randint(0, 59))
            metrics = simulate_exec_day(baselines[idx], day)
            record = {
                'device_id': app_id,
                'patient_id': pid,
                'timestamp': timestamp.isoformat(),
                'domain': 'executive_function',
                'metrics': metrics,
                'task_type': 'trail_making_test_b'
            }
            records.append(record)
    if provided:
        print(f"Reused {num_patients} patient IDs from profiles.")
    return records


def write_outputs(records, output_dir: Path, write_csv: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'executive_function_dataset.json'
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)
    csv_path = None
    if write_csv:
        if pd is None:
            print('[WARN] pandas not installed; skipping CSV export.')
        else:
            df = pd.json_normalize(records, sep='_')
            csv_path = output_dir / 'executive_function_dataset.csv'
            df.to_csv(csv_path, index=False)
    return json_path, csv_path


def parse_args():
    p = argparse.ArgumentParser(description='Simulate synthetic executive function test dataset.')
    p.add_argument('--patients', type=int, default=1000, help='Number of patients to simulate')
    p.add_argument('--days', type=int, default=30, help='Number of days per patient')
    p.add_argument('--start-date', default='2025-09-01', help='Start date (YYYY-MM-DD)')
    p.add_argument('--output-dir', default=None, help='Directory to place output files (default: ../data)')
    p.add_argument('--csv', action='store_true', help='Also export a CSV (requires pandas)')
    p.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility')
    p.add_argument('--patient-profiles', default=None, help='Path to patient_profiles.json to reuse patient IDs and device ids (device_ids.app)')
    return p.parse_args()


def main():
    args = parse_args()
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    except ValueError as e:
        raise SystemExit(f'Invalid --start-date format: {e}')

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    else:
        output_dir = (Path(__file__).resolve().parent.parent / 'data').resolve()

    patient_profiles = None
    if args.patient_profiles:
        pp_path = Path(args.patient_profiles).expanduser().resolve()
        if not pp_path.exists():
            raise SystemExit(f"Provided --patient-profiles does not exist: {pp_path}")
        try:
            with pp_path.open('r', encoding='utf-8') as f:
                patient_profiles = json.load(f)
            if not isinstance(patient_profiles, list):
                raise SystemExit('Patient profiles JSON must be a list of objects.')
        except json.JSONDecodeError as e:
            raise SystemExit(f'Failed to parse patient profiles JSON: {e}')

    intended_patients = args.patients
    if patient_profiles and intended_patients > len(patient_profiles):
        print(f"[INFO] Reducing patients from {intended_patients} to {len(patient_profiles)} (available profiles).")
        intended_patients = len(patient_profiles)

    print(f'Generating executive function dataset: patients={intended_patients}, days={args.days}, start={start_date.date()} -> {output_dir}')
    records = generate_dataset(intended_patients, args.days, start_date, seed=args.seed, patient_profiles=patient_profiles)
    json_path, csv_path = write_outputs(records, output_dir, args.csv)
    print(f'Wrote JSON: {json_path}')
    if csv_path:
        print(f'Wrote CSV:  {csv_path}')
    print(f'Total records: {len(records):,}')


if __name__ == '__main__':
    main()
