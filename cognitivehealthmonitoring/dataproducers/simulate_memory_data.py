"""Simulate synthetic memory domain test data (e.g., MoCA recall / word list learning).

Example record:
{
  "device_id": "CLIN-004",
  "patient_id": "UUID-12345",
  "timestamp": "2025-09-15T11:00:00Z",
  "domain": "memory",
  "metrics": {
    "immediate_recall_correct": 5,
    "delayed_recall_correct": 3,
    "intrusion_errors": 0
  },
  "test_type": "MoCA_recall"
}

Modeling Notes:
- Assume a 5-word list (MoCA recall style); immediate recall 0–5, delayed recall 0–5.
- Immediate recall is typically higher; delayed recall decays depending on retention and baseline cognition.
- Cognitive baseline (MMSE/MoCA) influences higher recall and fewer intrusions.
- Practice effect small and short-lived. Mild decline may appear after two weeks for some patients.
- Intrusion errors: low probability; increases if delayed recall is poor and baseline cognitive scores lower.
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
except ImportError:
    pd = None  # type: ignore

MAX_WORDS = 5


def seeded(seed: Optional[int]):
    if seed is not None:
        random.seed(seed)


def derive_baselines(num_patients: int, patient_profiles: Optional[List[dict]] = None):
    baselines = []
    for i in range(num_patients):
        if patient_profiles:
            prof = patient_profiles[i]
            cog = prof.get('cognitive_baseline', {})
            mmse = cog.get('mmse', 26)
            moca = cog.get('moca', 23)
            cog_factor = (mmse + moca) / 60  # ~0.4 - 1.0
        else:
            cog_factor = random.uniform(0.45, 0.95)

        immediate_base = random.normalvariate(3.2 + 1.5 * cog_factor, 0.6)  # centers near 4-5 for higher cognition
        delayed_base = immediate_base - random.normalvariate(0.8 - 0.9 * cog_factor, 0.4)  # less decay if high cog

        immediate_base = max(0.5, min(immediate_base, MAX_WORDS))
        delayed_base = max(0.0, min(delayed_base, immediate_base, MAX_WORDS))

        # Trends: small early practice effect days 0-3, then stable; optional mild decline after day 15 if low baseline
        decline_flag = cog_factor < 0.6 and random.random() < 0.5
        late_decline_rate = random.uniform(0.02, 0.08) if decline_flag else 0.0

        intrusions_base_prob = max(0.01, 0.15 - 0.12 * cog_factor)  # higher cognitive -> fewer intrusions

        baselines.append({
            'immediate_base': immediate_base,
            'delayed_base': delayed_base,
            'late_decline_rate': late_decline_rate,
            'intrusions_base_prob': intrusions_base_prob,
            'cog_factor': cog_factor,
        })
    return baselines


def simulate_memory_day(base: dict, day_index: int):
    # Practice phase improves both a bit days 0-2
    if day_index <= 2:
        immediate = base['immediate_base'] + 0.25 * day_index
        delayed = base['delayed_base'] + 0.20 * day_index
    else:
        immediate = base['immediate_base'] + 0.25 * 2
        delayed = base['delayed_base'] + 0.20 * 2

    # Late decline after day 15 if flagged
    if base['late_decline_rate'] > 0 and day_index > 15:
        decline_days = day_index - 15
        immediate -= base['late_decline_rate'] * 0.4 * decline_days
        delayed -= base['late_decline_rate'] * decline_days

    # Add noise
    immediate = random.normalvariate(immediate, 0.5)
    delayed = random.normalvariate(delayed, 0.6)

    immediate = max(0, min(round(immediate), MAX_WORDS))
    # delayed cannot exceed immediate on same day logically for simple list recall here
    delayed = max(0, min(round(delayed), immediate, MAX_WORDS))

    # Intrusions probability increases if delayed < immediate - 2
    gap = immediate - delayed
    base_prob = base['intrusions_base_prob']
    intrusion_prob = base_prob + 0.06 * max(0, gap - 1)
    intrusion_prob = min(intrusion_prob, 0.35)
    intrusions = 1 if random.random() < intrusion_prob else 0

    return {
        'immediate_recall_correct': int(immediate),
        'delayed_recall_correct': int(delayed),
        'intrusion_errors': intrusions
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
        device_ids = [(p.get('device_ids') or {}).get('clinic') for p in profiles_slice]
        for i, d in enumerate(device_ids):
            if not d:
                device_ids[i] = f'CLIN-{i+1:03d}'
    else:
        patient_ids = [str(uuid.uuid4()) for _ in range(num_patients)]
        device_ids = [f'CLIN-{i:03d}' for i in range(1, num_patients + 1)]

    baselines = derive_baselines(num_patients, patient_profiles if provided else None)

    records = []
    for idx in range(num_patients):
        pid = patient_ids[idx]
        dev_id = device_ids[idx]
        for day in range(days):
            timestamp = start_date + timedelta(days=day, hours=random.randint(10, 12), minutes=random.randint(0, 59))
            metrics = simulate_memory_day(baselines[idx], day)
            record = {
                'device_id': dev_id,
                'patient_id': pid,
                'timestamp': timestamp.isoformat(),
                'domain': 'memory',
                'metrics': metrics,
                'test_type': 'MoCA_recall'
            }
            records.append(record)
    if provided:
        print(f"Reused {num_patients} patient IDs from profiles.")
    return records


def write_outputs(records, output_dir: Path, write_csv: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'memory_dataset.json'
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)
    csv_path = None
    if write_csv:
        if pd is None:
            print('[WARN] pandas not installed; skipping CSV export.')
        else:
            df = pd.json_normalize(records, sep='_')
            csv_path = output_dir / 'memory_dataset.csv'
            df.to_csv(csv_path, index=False)
    return json_path, csv_path


def parse_args():
    p = argparse.ArgumentParser(description='Simulate synthetic memory test dataset (MoCA recall style).')
    p.add_argument('--patients', type=int, default=1000, help='Number of patients to simulate')
    p.add_argument('--days', type=int, default=30, help='Number of days per patient')
    p.add_argument('--start-date', default='2025-09-01', help='Start date (YYYY-MM-DD)')
    p.add_argument('--output-dir', default=None, help='Directory to place output files (default: ../data)')
    p.add_argument('--csv', action='store_true', help='Also export a CSV (requires pandas)')
    p.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility')
    p.add_argument('--patient-profiles', default=None, help='Path to patient_profiles.json to reuse patient IDs and device_ids.clinic')
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

    print(f'Generating memory dataset: patients={intended_patients}, days={args.days}, start={start_date.date()} -> {output_dir}')
    records = generate_dataset(intended_patients, args.days, start_date, seed=args.seed, patient_profiles=patient_profiles)
    json_path, csv_path = write_outputs(records, output_dir, args.csv)
    print(f'Wrote JSON: {json_path}')
    if csv_path:
        print(f'Wrote CSV:  {csv_path}')
    print(f'Total records: {len(records):,}')


if __name__ == '__main__':
    main()
