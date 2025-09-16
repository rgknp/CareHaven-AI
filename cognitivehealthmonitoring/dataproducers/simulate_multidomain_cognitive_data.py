"""Simulate multi-domain cognitive session data combining several domains in one record.

Sample target structure:
{
  "device_id": "SPK-001",
  "patient_id": "UUID-12345",
  "session_date": "2025-09-16T08:00:00Z",
  "attention": { "digit_span_max": 6, "errors": 1, "latency_sec": 1.1 },
  "executive_function": { "verbal_fluency_words": 14, "articulation_rate_wps": 2.0, "avg_pause_ms": 920 },
  "memory": { "immediate_recall": 3, "delayed_recall": 2, "intrusion_errors": 0 },
  "orientation": { "date_correct": true, "city_correct": false },
  "processing_speed": { "avg_reaction_time_ms": 710, "missed_trials": 0 },
  "mood_behavior": { "sentiment_score": 0.65, "narrative_coherence": 0.7 }
}

Design Notes:
- One composite record per patient per day ("session").
- Uses patient cognitive baseline (if provided) to modulate difficulty and performance.
- Includes mild longitudinal trends + random noise + cross-domain coupling.
"""
from __future__ import annotations

import uuid
import random
import json
from pathlib import Path
from datetime import datetime, timedelta
import argparse
from typing import Optional, List, Dict, Any, Tuple

try:
    import pandas as pd  # type: ignore
except ImportError:
    pd = None  # type: ignore

# ------------------------------ Helper Functions ------------------------------ #

def seeded(seed: Optional[int]):
    if seed is not None:
        random.seed(seed)


def extract_baselines(profile: Optional[Dict[str, Any]]) -> Tuple[float, int, int, int]:
    """Return (cognitive_factor, mmse, moca, depression_score)."""
    if not profile:
        mmse = random.randint(22, 29)
        moca = random.randint(20, 28)
        dep = random.randint(0, 14)
    else:
        cb = profile.get('cognitive_baseline', {}) or {}
        mmse = int(cb.get('mmse', 26))
        moca = int(cb.get('moca', 24))
        dep = int(cb.get('depression_score', 6))
    cf = max(0.3, min(1.0, (mmse + moca) / 60))
    return cf, mmse, moca, dep


def generate_patient_state(num_patients: int, patient_profiles: Optional[List[dict]]):
    states = []
    for i in range(num_patients):
        if patient_profiles:
            profile = patient_profiles[i]
            cf, mmse, moca, dep = extract_baselines(profile)
            pid = profile.get('patient_id') or str(uuid.uuid4())
            device_id = (profile.get('device_ids') or {}).get('speech') or f'SPK-{i+1:03d}'
        else:
            profile = None
            cf, mmse, moca, dep = extract_baselines(None)
            pid = str(uuid.uuid4())
            device_id = f'SPK-{i+1:03d}'

        # Baselines influenced by cognitive factor & depression (higher dep -> subtle penalties)
        dep_penalty = min(0.15, dep * 0.005)
        attention_span = random.normalvariate(4.0 + cf * 3.0 - dep_penalty * 1.5, 0.55)  # up to ~7-8
        attention_latency = random.normalvariate(1.65 - cf * 0.85 + dep_penalty * 0.4, 0.14)
        exec_fluency = random.normalvariate(12 + cf * 14 - dep_penalty * 6, 2.8)
        exec_pause = random.normalvariate(1420 - cf * 620 + dep_penalty * 220, 170)
        exec_artic = random.normalvariate(1.38 + cf * 0.92 - dep_penalty * 0.25, 0.18)
        memory_immediate = random.normalvariate(2.9 + cf * 2.0 - dep_penalty * 1.2, 0.48)
        memory_delayed = memory_immediate - random.normalvariate(0.9 - cf * 0.7 + dep_penalty * 0.3, 0.37)
        sentiment = random.normalvariate(0.47 + cf * 0.25 - dep_penalty * 1.1, 0.09)
        narrative = random.normalvariate(0.5 + cf * 0.34 - dep_penalty * 0.8, 0.09)
        reaction_time = random.normalvariate(905 - cf * 355 + dep_penalty * 140, 58)

        states.append({
            'patient_id': pid,
            'device_id': device_id,
            'cf': cf,
            'mmse': mmse,
            'moca': moca,
            'depression': dep,
            'attention_span_base': attention_span,
            'attention_latency_base': attention_latency,
            'exec_fluency_base': exec_fluency,
            'exec_pause_base': exec_pause,
            'exec_artic_base': exec_artic,
            'memory_immediate_base': memory_immediate,
            'memory_delayed_base': memory_delayed,
            'sentiment_base': sentiment,
            'narrative_base': narrative,
            'reaction_time_base': reaction_time,
        })
    return states


def simulate_session(state: Dict[str, Any], day_index: int):
    # Mild practice improvement first 4 days, plateau, slight decline after day 20 for some
    decline_flag = state['cf'] < 0.55 and day_index > 20
    decay_factor = (day_index - 20) * 0.05 if decline_flag else 0.0
    practice_mult = min(1.0, 0.75 + 0.07 * day_index) if day_index <= 4 else 1.0

    span = state['attention_span_base'] * practice_mult - decay_factor
    span = max(2, min(round(random.normalvariate(span, 0.5)), 8))
    att_errors = max(0, int(random.normalvariate((6 - span) * 0.6, 0.7)))
    att_latency = max(0.6, random.normalvariate(state['attention_latency_base'] / practice_mult + decay_factor * 0.2, 0.12))

    fluency = max(3, int(round(random.normalvariate(state['exec_fluency_base'] * practice_mult - decay_factor * 2, 3))))
    articulation = max(0.6, round(random.normalvariate(state['exec_artic_base'] * practice_mult - decay_factor * 0.05, 0.15), 2))
    pause = int(max(300, random.normalvariate(state['exec_pause_base'] / practice_mult + decay_factor * 120, 160)))

    imm = max(0, min(5, int(round(random.normalvariate(state['memory_immediate_base'] * practice_mult - decay_factor * 0.2, 0.6)))))
    delayed = max(0, min(imm, int(round(random.normalvariate(state['memory_delayed_base'] * practice_mult - decay_factor * 0.35, 0.7)))))
    # Intrusions incorporate depression and executive inefficiency
    intrusions_prob = 0.10
    intrusions_prob += max(0, (imm - delayed)) * 0.05
    intrusions_prob += max(0, 0.55 - state['cf']) * 0.16
    intrusions_prob += (state.get('depression', 6) / 30) * 0.12
    intrusions_prob = min(0.40, intrusions_prob)
    intrusions = 1 if random.random() < max(0.01, intrusions_prob) else 0

    # Orientation (binary) – influenced by cognitive factor & decline
    date_correct = random.random() < (0.85 + (state['cf'] - 0.6) * 0.25 - decay_factor * 0.05)
    city_correct = random.random() < (0.8 + (state['cf'] - 0.6) * 0.30 - decay_factor * 0.07)

    reaction_time = int(max(350, random.normalvariate(state['reaction_time_base'] / practice_mult + decay_factor * 40, 50)))
    missed_trials = max(0, int(random.normalvariate((reaction_time - 600) / 160, 0.6))) if reaction_time > 600 else 0

    dep = state.get('depression', 6)
    dep_adj = (dep / 30)
    sentiment = max(0.0, min(1.0, round(random.normalvariate(state['sentiment_base'] + (practice_mult - 1.0) * 0.05 - decay_factor * 0.02 - dep_adj * 0.15, 0.07), 2)))
    narrative = max(0.0, min(1.0, round(random.normalvariate(state['narrative_base'] + (practice_mult - 1.0) * 0.06 - decay_factor * 0.03 - dep_adj * 0.12, 0.08), 2)))

    return {
        'attention': {
            'digit_span_max': span,
            'errors': att_errors,
            'latency_sec': round(att_latency, 2)
        },
        'executive_function': {
            'verbal_fluency_words': fluency,
            'articulation_rate_wps': articulation,
            'avg_pause_ms': pause
        },
        'memory': {
            'immediate_recall': imm,
            'delayed_recall': delayed,
            'intrusion_errors': intrusions
        },
        'orientation': {
            'date_correct': bool(date_correct),
            'city_correct': bool(city_correct)
        },
        'processing_speed': {
            'avg_reaction_time_ms': reaction_time,
            'missed_trials': missed_trials
        },
        'mood_behavior': {
            'sentiment_score': sentiment,
            'narrative_coherence': narrative
        }
    }


def generate_dataset(num_patients: int, days: int, start_date: datetime, seed: Optional[int] = None, patient_profiles=None):
    if num_patients <= 0:
        raise ValueError('num_patients must be > 0')
    if days <= 0:
        raise ValueError('days must be > 0')
    seeded(seed)

    provided = bool(patient_profiles)
    # Assume patient_profiles already trimmed to num_patients when provided.
    states = generate_patient_state(num_patients, patient_profiles if provided else None)

    records = []
    for idx, state in enumerate(states):
        pid = state['patient_id']
        device_id = state['device_id']
        for day in range(days):
            session_time = start_date + timedelta(days=day, hours=8, minutes=random.randint(0, 50))
            metrics = simulate_session(state, day)
            record = {
                'device_id': device_id,
                'patient_id': pid,
                'session_date': session_time.isoformat(),
                **metrics
            }
            records.append(record)
    if provided:
        print(f"Reused {num_patients} patient IDs from profiles.")
    return records


def write_outputs(records, output_dir: Path, write_csv: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'multidomain_cognitive_dataset.json'
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)
    csv_path = None
    if write_csv:
        if pd is None:
            print('[WARN] pandas not installed; skipping CSV export.')
        else:
            # Flatten nested dicts for CSV
            df = pd.json_normalize(records, sep='_')
            csv_path = output_dir / 'multidomain_cognitive_dataset.csv'
            df.to_csv(csv_path, index=False)
    return json_path, csv_path


def parse_args():
    p = argparse.ArgumentParser(description='Simulate multi-domain cognitive session dataset (requires patient profiles by default).')
    p.add_argument('--patients', type=int, default=1000, help='Number of patients to simulate (ignored if --use-all-profiles).')
    p.add_argument('--use-all-profiles', action='store_true', help='Use ALL patients from provided profiles file (overrides --patients).')
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--start-date', default='2025-09-01')
    p.add_argument('--output-dir', default=None)
    p.add_argument('--csv', action='store_true')
    p.add_argument('--seed', type=int, default=None)
    p.add_argument('--patient-profiles', default=None, help='Path to patient_profiles.json for ID/baseline reuse (uses device_ids.speech if available).')
    p.add_argument('--allow-synthetic', action='store_true', help='Allow generating synthetic patient IDs if profiles file not found.')
    p.add_argument('--profiles-search', action='store_true', help='Search typical relative locations for patient_profiles.json if not explicitly provided.')
    p.add_argument('--strict-count', action='store_true', help='Exit with error if produced record count != patients*days.')
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
        # Default: place dataset within the same folder tree as this script under 'dataproducers/data'
        # (Previously this was one level up: cognitivehealthmonitoring/data)
        output_dir = (Path(__file__).resolve().parent / 'data').resolve()

    # Load patient profiles: explicit path > search > error (unless --allow-synthetic)
    patient_profiles = None
    attempted_paths = []
    if args.patient_profiles:
        pp_path = Path(args.patient_profiles).expanduser().resolve()
        attempted_paths.append(str(pp_path))
        if not pp_path.exists():
            raise SystemExit(f"Provided --patient-profiles does not exist: {pp_path}")
        try:
            with pp_path.open('r', encoding='utf-8') as f:
                patient_profiles = json.load(f)
            if not isinstance(patient_profiles, list):
                raise SystemExit('Patient profiles JSON must be a list (array) of objects.')
        except json.JSONDecodeError as e:
            raise SystemExit(f'Failed to parse patient profiles JSON: {e}')
    elif args.profiles_search or not args.allow_synthetic:
        # Candidate relative search locations
        candidates = [
            output_dir / 'patient_profiles.json',
            Path(__file__).resolve().parent / 'patient_profiles.json',
            Path(__file__).resolve().parent.parent / 'data' / 'patient_profiles.json',
        ]
        for cand in candidates:
            attempted_paths.append(str(cand))
            if cand.exists():
                try:
                    with cand.open('r', encoding='utf-8') as f:
                        patient_profiles = json.load(f)
                    if isinstance(patient_profiles, list):
                        print(f'[INFO] Loaded patient profiles from {cand}')
                        break
                except json.JSONDecodeError:
                    continue
        if patient_profiles is None and not args.allow_synthetic:
            joined = '\n  - '.join(attempted_paths)
            raise SystemExit('Could not locate patient_profiles.json in any of:\n  - ' + joined + '\nProvide --patient-profiles or use --allow-synthetic to bypass.')
    if patient_profiles is None and args.allow_synthetic:
        print('[WARN] Proceeding with synthetic patient IDs (no profile correlation).')

    intended_patients = args.patients
    profiles_slice = None
    if patient_profiles:
        total_profiles = len(patient_profiles)
        if args.use_all_profiles:
            intended_patients = total_profiles
            profiles_slice = patient_profiles
            print(f'[INFO] Using all {total_profiles} patient profiles.')
        else:
            if intended_patients > total_profiles:
                print(f'[INFO] Requested {intended_patients} patients but only {total_profiles} profiles available; using all.')
                intended_patients = total_profiles
            profiles_slice = patient_profiles[:intended_patients]
    else:
        profiles_slice = None  # synthetic

    expected_records = intended_patients * args.days
    print(f'Generating multi-domain dataset: patients={intended_patients}, days={args.days}, expected_records={expected_records:,}, start={start_date.date()} -> {output_dir}')
    records = generate_dataset(intended_patients, args.days, start_date, seed=args.seed, patient_profiles=profiles_slice)
    actual_records = len(records)
    if actual_records != expected_records:
        msg = f'[WARN] Record count mismatch: expected {expected_records:,} vs actual {actual_records:,}.'
        if args.strict_count:
            raise SystemExit(msg)
        else:
            print(msg)
    else:
        print(f'[OK] Generated expected record count: {actual_records:,}.')
    json_path, csv_path = write_outputs(records, output_dir, args.csv)
    print(f'Wrote JSON: {json_path}')
    if csv_path:
        print(f'Wrote CSV:  {csv_path}')
    print(f'Total records: {len(records):,}')
    print(f'Patients used: {intended_patients} | Days: {args.days} | Expected: {expected_records:,} | Actual: {actual_records:,}')


if __name__ == '__main__':
    main()
