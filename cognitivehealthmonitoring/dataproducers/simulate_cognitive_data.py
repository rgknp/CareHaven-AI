import uuid
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
import argparse

try:
    import pandas as pd  # type: ignore
except ImportError:  # Provide graceful degradation if pandas not installed
    pd = None  # type: ignore


def simulate_mobility_metrics():
    """Simulate a single set of mobility metrics plus signal quality."""
    gait_speed = round(random.normalvariate(0.9, 0.15), 2)  # m/s
    gait_speed = max(0.4, min(gait_speed, 1.5))

    stride_var = round(random.normalvariate(14, 5), 1)  # %
    stride_var = max(5, min(stride_var, 30))

    daily_steps = int(random.normalvariate(4000, 1500))
    daily_steps = max(500, min(daily_steps, 15000))

    fall_detected = random.choices([False, True], weights=[0.98, 0.02])[0]
    signal_quality = round(random.uniform(0.85, 1.0), 2)

    return {
        'gait_speed_mps': gait_speed,
        'stride_variability_pct': stride_var,
        'daily_steps': daily_steps,
        'fall_detected': fall_detected
    }, signal_quality


def generate_dataset(num_patients: int, days: int, start_date: datetime, patient_profiles=None):
    """Generate a list of mobility records for all patients across days.

    If patient_profiles is provided (list of dict with patient_id and device_ids.wearable),
    reuse those IDs; otherwise synthesize new IDs.
    """
    if num_patients <= 0:
        raise ValueError("num_patients must be > 0")
    if days <= 0:
        raise ValueError("days must be > 0")

    provided = False
    if patient_profiles:
        provided = True
        # Trim or slice list to requested size
        if len(patient_profiles) < num_patients:
            print(f"[WARN] Requested {num_patients} patients but only {len(patient_profiles)} profiles available. Reducing.")
            num_patients = len(patient_profiles)
        profiles_slice = patient_profiles[:num_patients]
        id_pairs = []
        for p in profiles_slice:
            pid = p.get('patient_id')
            wearable = (p.get('device_ids') or {}).get('wearable')
            if not pid or not wearable:
                continue
            id_pairs.append((pid, wearable))
        if len(id_pairs) < num_patients:
            print(f"[WARN] Some profiles missing wearable IDs; generating synthetic for missing.")
        # fill remaining with synthetic
        while len(id_pairs) < num_patients:
            idx = len(id_pairs) + 1
            id_pairs.append((str(uuid.uuid4()), f'WEAR-{idx:03d}'))
    else:
        id_pairs = [(str(uuid.uuid4()), f'WEAR-{i:03d}') for i in range(1, num_patients + 1)]

    all_records = []
    for patient_idx, (patient_id, device_id) in enumerate(id_pairs):
        for day in range(days):
            timestamp = start_date + timedelta(
                days=day,
                hours=random.randint(6, 22),
                minutes=random.randint(0, 59)
            )
            metrics, signal_quality = simulate_mobility_metrics()
            record = {
                'device_id': device_id,
                'patient_id': patient_id,
                'timestamp': timestamp.isoformat(),
                'domain': 'mobility',
                'metrics': metrics,
                'signal_quality': signal_quality
            }
            all_records.append(record)
    if provided:
        print(f"Reused {len(id_pairs)} patient IDs from profiles.")
    return all_records


def write_outputs(records, output_dir: Path, write_csv: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'mobility_dataset.json'
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)

    csv_path = None
    if write_csv:
        if pd is None:
            print("[WARN] pandas not installed; skipping CSV export.")
        else:
            df = pd.json_normalize(records, sep='_')
            csv_path = output_dir / 'mobility_dataset.csv'
            df.to_csv(csv_path, index=False)
    return json_path, csv_path


def parse_args():
    parser = argparse.ArgumentParser(description="Simulate synthetic mobility metrics dataset.")
    parser.add_argument('--patients', type=int, default=1000, help='Number of patients to simulate')
    parser.add_argument('--days', type=int, default=30, help='Number of days per patient')
    parser.add_argument('--start-date', default='2025-09-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--output-dir', default=None, help='Directory to place output files (default: ../data)')
    parser.add_argument('--csv', action='store_true', help='Also export a CSV (requires pandas)')
    parser.add_argument('--patient-profiles', default=None, help='Path to patient_profiles.json to reuse patient/device IDs')
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    except ValueError as e:
        raise SystemExit(f"Invalid --start-date format: {e}")

    # Determine output directory (avoid hardcoded Linux-only paths)
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    else:
        # Place outputs in a sibling 'data' directory to this script's parent package
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

    print(f"Generating dataset: patients={intended_patients}, days={args.days}, start={start_date.date()} -> {output_dir}")
    records = generate_dataset(intended_patients, args.days, start_date, patient_profiles=patient_profiles)
    json_path, csv_path = write_outputs(records, output_dir, args.csv)
    print(f"Wrote JSON: {json_path}")
    if csv_path:
        print(f"Wrote CSV:  {csv_path}")
    print(f"Total records: {len(records):,}")


if __name__ == '__main__':
    main()
