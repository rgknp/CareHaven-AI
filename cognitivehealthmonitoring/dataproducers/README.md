# CareHaven-AI Synthetic Cognitive & Functional Dataset Generators

This repository contains a suite of modular Python simulation scripts that generate realistic, multi-domain synthetic longitudinal data for older adult patients. The goal is to provide varied, correlated signals suitable for experimentation with machine learning models in areas such as cognitive decline monitoring, multimodal fusion, and temporal forecasting.

## 📁 Simulation Scripts Overview
All scripts live in `cognitivehealthmonitoring/dataproducers/` and write outputs (JSON + optional CSV) into `cognitivehealthmonitoring/data/` by default.

| Script | Domain / Purpose | Key Metrics | Notes |
|--------|------------------|-------------|-------|
| `simulate_patient_profiles.py` | Baseline demographics & clinical context | demographics, comorbidities, medications, cognitive_baseline (MMSE, MoCA, depression_score), device_ids | Foundation for all other modalities (patient identity + covariates). |
| `simulate_cognitive_data.py` | Mobility / wearable activity | gait_speed_mps, stride_variability_pct, daily_steps, fall_detected, signal_quality | Per-day variability + realistic ranges; correlated with activity and risk. |
| `simulate_language_data.py` | Language / verbal fluency | verbal_fluency_words, avg_pause_ms, articulation_rate_wps, sentiment_score, signal_quality | Longitudinal mild trends + intra-day noise; pause inversely tied to fluency. |
| `simulate_executive_function_data.py` | Executive function testing | tmt_b_completion_sec, errors, symbol_digit_correct | Practice effect then plateau/decline; cognitive baseline influences speed/accuracy. |
| `simulate_memory_data.py` | Memory recall (MoCA-style) | immediate_recall_correct, delayed_recall_correct, intrusion_errors | Short practice effect; optional mild delayed decline for low baseline cognition. |
| `simulate_multidomain_cognitive_data.py` | Unified multi-domain session record | nested: attention, executive_function, memory, orientation, processing_speed, mood_behavior | One JSON record per patient per day; enforces profile reuse; strengthened cross-domain correlations. |

All scripts support:
- `--patients` number of patients (auto-reduced if fewer profiles provided)
- `--days` number of longitudinal days (default 30)
- `--start-date` (YYYY-MM-DD)
- `--output-dir` custom output location
- `--csv` optional CSV export (requires `pandas`)
- `--seed` reproducibility for stochastic elements (where implemented)
- `--patient-profiles` (where applicable) path to `patient_profiles.json` to reuse patient/device IDs

## 🧬 Data Flow & Recommended Run Order
```
patient_profiles -> (mobility | language | executive_function | memory | unified_multidomain)
```
1. Generate baseline patient profiles.
2. Generate modality-specific datasets (order not strictly required, but using the same profiles ensures aligned `patient_id`).
3. (Optional) Build downstream unified feature sets by joining on `patient_id` + date.

## 🚀 Quick Start
### Pre-Requisites
- Python 3.10+ (tested on 3.13)
- Optional: `pandas` for CSV exports

Install pandas (optional):
```bash
pip install pandas
```

### 1. Generate Patient Profiles
```bash
python cognitivehealthmonitoring/dataproducers/simulate_patient_profiles.py --patients 1000 --seed 1001
```
Output: `cognitivehealthmonitoring/data/patient_profiles.json`

### 2. Mobility Dataset
```bash
python cognitivehealthmonitoring/dataproducers/simulate_cognitive_data.py --patients 1000 --days 30 --patient-profiles cognitivehealthmonitoring/data/patient_profiles.json --csv
```

### 3. Language Dataset
```bash
python cognitivehealthmonitoring/dataproducers/simulate_language_data.py --patients 1000 --days 30 --patient-profiles cognitivehealthmonitoring/data/patient_profiles.json --seed 2002 --csv
```

### 4. Executive Function Dataset
```bash
python cognitivehealthmonitoring/dataproducers/simulate_executive_function_data.py --patients 1000 --days 30 --patient-profiles cognitivehealthmonitoring/data/patient_profiles.json --seed 3003 --csv
```

### 5. Memory Dataset
```bash
python cognitivehealthmonitoring/dataproducers/simulate_memory_data.py --patients 1000 --days 30 --patient-profiles cognitivehealthmonitoring/data/patient_profiles.json --seed 4004 --csv
```

### 6. Unified Multi-Domain Dataset (All-in-one Sessions)
Generates a single longitudinal file with one nested record per patient per day capturing multiple cognitive/behavioral domains together. Recommended when you want pre-aligned features for direct model ingestion or sequence modeling.

Key characteristics:
- Derives per-patient latent baselines from `MMSE`, `MoCA`, and `depression_score`.
- Applies practice effects (early days) and conditional mild decline for lower baseline cognition.
- Cross-domain coupling: slower processing speed and higher pauses correlate with lower fluency; mood (sentiment/narrative) impacted by depression & decline.
- Intrusion error probability incorporates recall gap, cognitive factor, and depression burden.
- Enforces patient profile reuse unless `--allow-synthetic` explicitly set.

Schema (per record):
```json
{
	"device_id": "SPK-001",
	"patient_id": "<uuid>",
	"session_date": "2025-09-16T08:17:00",
	"attention": {"digit_span_max": 6, "errors": 1, "latency_sec": 1.05},
	"executive_function": {"verbal_fluency_words": 15, "articulation_rate_wps": 1.9, "avg_pause_ms": 910},
	"memory": {"immediate_recall": 4, "delayed_recall": 3, "intrusion_errors": 0},
	"orientation": {"date_correct": true, "city_correct": true},
	"processing_speed": {"avg_reaction_time_ms": 680, "missed_trials": 0},
	"mood_behavior": {"sentiment_score": 0.62, "narrative_coherence": 0.71}
}
```

Run with explicit profile path:
```bash
python cognitivehealthmonitoring/dataproducers/simulate_multidomain_cognitive_data.py \
	--patient-profiles cognitivehealthmonitoring/data/patient_profiles.json \
	--patients 1000 --days 30 --seed 5005 --csv
```

Or let it search typical locations automatically:
```bash
python cognitivehealthmonitoring/dataproducers/simulate_multidomain_cognitive_data.py \
	--patients 1000 --days 30 --profiles-search --seed 5005 --csv
```

Allow synthetic (no profile correlation – not recommended for longitudinal fusion):
```bash
python cognitivehealthmonitoring/dataproducers/simulate_multidomain_cognitive_data.py --patients 200 --days 14 --allow-synthetic --seed 6006
```

Output (by default) now lands in `cognitivehealthmonitoring/dataproducers/data/` for this script.

Tip: Use this unified dataset directly for sequence models (Transformers, TCNs) without first joining multiple modality tables.

## 🔁 Reproducibility Tips
- Set `--seed` consistently per domain to reproduce the modality while allowing cross-domain variance.
- Store an experiment manifest (JSON/YAML) with seeds + command invocations.
- If you need deterministic device ID ordering, always start from the same `patient_profiles.json`.

## 🔗 Joining Datasets
Join logic (pseudo-Python):
```python
import json, pandas as pd, datetime as dt
from pathlib import Path
base = Path('cognitivehealthmonitoring/data')

with (base / 'patient_profiles.json').open() as f: profiles = json.load(f)
with (base / 'mobility_dataset.json').open() as f: mobility = json.load(f)
# Repeat for other modalities...

# Example convert to DataFrame & derive date
mob_df = pd.json_normalize(mobility)
mob_df['date'] = pd.to_datetime(mob_df['timestamp']).dt.date

lang_df = pd.json_normalize(json.load((base / 'language_dataset.json').open()))
lang_df['date'] = pd.to_datetime(lang_df['timestamp']).dt.date

merged = mob_df.merge(lang_df, on=['patient_id','date'], how='inner', suffixes=('_mob','_lang'))
print(merged.head())
```

## 📊 Modeling Ideas
- Temporal forecasting (RNN/Transformer) on multi-day sequences.
- Early decline detection using subtle trends (executive + memory + language synergy).
- Multimodal feature fusion (concatenate daily aggregated metrics per domain).
- Synthetic anomaly insertion for robustness testing.
 - Direct multi-domain session modeling using the unified dataset (reduces join noise & missing alignment issues).

## 🧪 Extensibility Ideas
| Enhancement | Description |
|-------------|-------------|
| Missingness simulation | Randomly drop sessions to mimic adherence issues. |
| Acute event injection | Temporary deterioration across multiple domains. |
| Unified orchestrator | One command to generate all datasets in order. |
| Feature engineering script | Produce per-patient summary features (slopes, variability, composite scores). |
| Progression labels | Add synthetic labels for supervised learning tasks. |
| EDA Notebook | Automated profiling & visualization starter. |

## ⚠️ Disclaimer
All generated data are entirely synthetic and not derived from real patients. They are for prototyping, experimentation, and educational purposes only—NOT for clinical decision-making.

## 🤝 Contributions / Next Steps
If you’d like an orchestrator script, merging utility, or an exploratory notebook added, open an issue or request it directly.

---
Feel free to request additional modalities or complexity (sleep, mood tracking, passive sensor streams). Happy experimenting!
