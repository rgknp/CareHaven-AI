"""Simulate synthetic language/cognitive test data for patients.

Each record example:
{
  "device_id": "SPK-002",
  "patient_id": "UUID",
  "timestamp": "2025-09-15T09:00:00Z",
  "domain": "language",
  "metrics": {
    "verbal_fluency_words": 13,
    "avg_pause_ms": 1750,
    "articulation_rate_wps": 1.7,
    "sentiment_score": 0.6
  },
  "task_type": "verbal_fluency_test"
}
"""
from __future__ import annotations

import uuid
import random
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import argparse
from typing import List, Dict, Tuple, Optional

try:
    import pandas as pd  # type: ignore
except ImportError:  # graceful degradation
    pd = None  # type: ignore


@dataclass
class PatientLanguageProfile:
    baseline_fluency: float  # words per 60s task
    baseline_pause_ms: float  # average pause length
    baseline_articulation_rate: float  # words per second spoken segments
    baseline_sentiment: float  # general affect 0-1
    decline_trend_fluency: float  # change per day (could be slight)
    decline_trend_articulation: float
    improvement_sentiment: float  # sentiment drift


def seeded_random(seed: Optional[int]):
    if seed is not None:
        random.seed(seed)


def generate_patient_profiles(num_patients: int) -> List[PatientLanguageProfile]:
    profiles: List[PatientLanguageProfile] = []
    for _ in range(num_patients):
        # Baseline distributions (normal-ish with clipping for realism)
        fluency = max(5, min(random.normalvariate(18, 5), 40))  # words produced
        pause = max(400, min(random.normalvariate(1200, 300), 3000))  # ms
        articulation = max(0.8, min(random.normalvariate(2.2, 0.4), 3.5))  # wps
        sentiment = max(0.1, min(random.normalvariate(0.55, 0.15), 0.95))

        # Trends: mild decline or stability
        decline_flu = random.normalvariate(-0.03, 0.02)  # words/day
        decline_art = random.normalvariate(-0.002, 0.002)  # wps/day
        sentiment_drift = random.normalvariate(0.0005, 0.001)  # per day slight improvement

        profiles.append(PatientLanguageProfile(
            baseline_fluency=fluency,
            baseline_pause_ms=pause,
            baseline_articulation_rate=articulation,
            baseline_sentiment=sentiment,
            decline_trend_fluency=decline_flu,
            decline_trend_articulation=decline_art,
            improvement_sentiment=sentiment_drift,
        ))
    return profiles


def simulate_language_metrics(profile: PatientLanguageProfile, day_index: int) -> Tuple[Dict, float]:
    # Apply linear trends
    fluency_mean = profile.baseline_fluency + profile.decline_trend_fluency * day_index
    articulation_mean = profile.baseline_articulation_rate + profile.decline_trend_articulation * day_index
    sentiment_mean = profile.baseline_sentiment + profile.improvement_sentiment * day_index

    # Correlation heuristics: lower fluency -> longer pauses & lower sentiment
    # We'll model pause as inverse-signal + noise
    pause_mean = profile.baseline_pause_ms * (profile.baseline_fluency / max(1, fluency_mean))

    # Add stochastic daily variation (intra subject variability)
    fluency_value = max(3, min(random.normalvariate(fluency_mean, 3), 45))
    articulation_value = max(0.6, min(random.normalvariate(articulation_mean, 0.15), 3.8))
    pause_value = max(300, min(random.normalvariate(pause_mean, 250), 4000))
    sentiment_value = max(0.0, min(random.normalvariate(sentiment_mean, 0.07), 1.0))

    # Derive a crude signal quality (simulate audio capture quality)
    # Assume slight degradation if pauses very long or articulation very low
    quality_penalty = 0
    if pause_value > 2500:
        quality_penalty += 0.05
    if articulation_value < 1.0:
        quality_penalty += 0.05
    signal_quality = round(max(0.75, 1.0 - quality_penalty - random.uniform(0.0, 0.05)), 2)

    metrics = {
        "verbal_fluency_words": int(round(fluency_value)),
        "avg_pause_ms": int(round(pause_value)),
        "articulation_rate_wps": round(articulation_value, 2),
        "sentiment_score": round(sentiment_value, 2),
    }
    return metrics, signal_quality


def generate_dataset(num_patients: int, days: int, start_date: datetime, seed: Optional[int] = None, patient_profiles=None):
    if num_patients <= 0:
        raise ValueError("num_patients must be > 0")
    if days <= 0:
        raise ValueError("days must be > 0")
    seeded_random(seed)

    provided = False
    if patient_profiles:
        provided = True
        if len(patient_profiles) < num_patients:
            print(f"[WARN] Requested {num_patients} patients but only {len(patient_profiles)} profiles available. Reducing.")
            num_patients = len(patient_profiles)
        profiles_slice = patient_profiles[:num_patients]
        # build list of (patient_id, speech_device_id)
        id_pairs = []
        for p in profiles_slice:
            pid = p.get('patient_id')
            spk = (p.get('device_ids') or {}).get('speech') if isinstance(p.get('device_ids'), dict) else None
            if not pid:
                continue
            if not spk:
                spk = f'SPK-{len(id_pairs)+1:03d}'
            id_pairs.append((pid, spk))
        while len(id_pairs) < num_patients:
            idx = len(id_pairs) + 1
            id_pairs.append((str(uuid.uuid4()), f'SPK-{idx:03d}'))
        profiles = generate_patient_profiles(len(id_pairs))
        device_ids = [spk for _, spk in id_pairs]
        patient_ids = [pid for pid, _ in id_pairs]
    else:
        profiles = generate_patient_profiles(num_patients)
        device_ids = [f'SPK-{i:03d}' for i in range(1, num_patients + 1)]
        patient_ids = [str(uuid.uuid4()) for _ in range(num_patients)]
    all_records = []

    for idx, profile in enumerate(profiles):
        patient_id = patient_ids[idx]
        device_id = device_ids[idx]
        for day in range(days):
            # Assume verbal fluency test done in a morning time window with some jitter
            timestamp = start_date + timedelta(days=day, hours=random.randint(8, 11), minutes=random.randint(0, 59))
            metrics, signal_quality = simulate_language_metrics(profile, day)
            record = {
                "device_id": device_id,
                "patient_id": patient_id,
                "timestamp": timestamp.isoformat(),
                "domain": "language",
                "metrics": metrics,
                "signal_quality": signal_quality,
                "task_type": "verbal_fluency_test"
            }
            all_records.append(record)
    if provided:
        print(f"Reused {len(patient_ids)} patient IDs from profiles.")
    return all_records


def write_outputs(records, output_dir: Path, write_csv: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'language_dataset.json'
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)

    csv_path = None
    if write_csv:
        if pd is None:
            print('[WARN] pandas not installed; skipping CSV export.')
        else:
            df = pd.json_normalize(records, sep='_')
            csv_path = output_dir / 'language_dataset.csv'
            df.to_csv(csv_path, index=False)
    return json_path, csv_path


def parse_args():
    parser = argparse.ArgumentParser(description='Simulate synthetic language test dataset.')
    parser.add_argument('--patients', type=int, default=1000, help='Number of patients to simulate')
    parser.add_argument('--days', type=int, default=30, help='Number of days per patient')
    parser.add_argument('--start-date', default='2025-09-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--output-dir', default=None, help='Directory to place output files (default: ../data)')
    parser.add_argument('--csv', action='store_true', help='Also export a CSV (requires pandas)')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility')
    parser.add_argument('--patient-profiles', default=None, help='Path to patient_profiles.json to reuse patient/device IDs')
    return parser.parse_args()


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

    print(f'Generating language dataset: patients={intended_patients}, days={args.days}, start={start_date.date()} -> {output_dir}')
    records = generate_dataset(intended_patients, args.days, start_date, seed=args.seed, patient_profiles=patient_profiles)
    json_path, csv_path = write_outputs(records, output_dir, args.csv)
    print(f'Wrote JSON: {json_path}')
    if csv_path:
        print(f'Wrote CSV:  {csv_path}')
    print(f'Total records: {len(records):,}')


if __name__ == '__main__':
    main()
