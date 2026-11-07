# 🎨 Food Colorant QC — Colorimetry, SPC & Early-Warning Models (Python)

A QC-engineer's analysis workflow for a **food-colorant plant**: from a raw LIMS-style export to colour-difference (CIEDE2000) analysis, statistical process control, process capability, a release-decision audit, and early-warning models that flag likely off-shade batches **before** the lab result arrives.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat&logo=scikitlearn&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?style=flat&logo=pandas&logoColor=white)

👉 **Open [`colorant_qc_analysis.ipynb`](colorant_qc_analysis.ipynb)** — outputs and charts are saved in the notebook, so GitHub renders the full analysis.

## 💡 In plain words

When a food-colorant batch is produced, its colour must match a reference standard. If it does not, the batch has to be reworked or rejected, which costs time and money. This project shows how a QC team can:

1. **clean** messy lab / LIMS exports,
2. **measure** how far each batch's colour is from the standard (ΔE),
3. **detect** when the process starts to drift (control charts, process capability),
4. **predict** which batches are likely to be off-shade *before* the lab result arrives.

## 📊 Key results (on the simulated data)

| Finding | Result |
|---|---|
| Batches out of colour tolerance (ΔE00 > 1.5) | 15.8% |
| Median ΔE00, original suppliers vs. new supplier C | 0.65 vs. 1.22 |
| Strength capability (Cpk) before → after supplier C | 1.03 → 0.82 (marginal → not capable) |
| Control chart signals before → after the change | strength 1.7% → 6.3%, ΔE 4.7% → 9.5% |
| Early-warning model (time-ordered test set) | PR-AUC 0.81 vs. 0.22 for a useless model; checking 19% of batches catches 69% of the off-shade ones |
| Recorded release decisions that disagree with the spec rules | 35 batches flagged for review |

*These are results about a simulated process, not about a real plant.*

## 📖 Glossary

- **LIMS** – laboratory information system; where lab results and release decisions are stored.
- **L\*a\*b\*** – three numbers describing a colour: lightness (L\*), green–red (a\*), blue–yellow (b\*).
- **ΔE (CIEDE2000)** – one number for "how different are two colours"; 0 = identical, larger = more different.
- **Off-shade / out of tolerance** – colour difference above the allowed limit.
- **SPC / control chart** – a time chart with limits that shows whether a process is stable.
- **Cpk** – how comfortably a process fits inside its specification (≥ 1.33 capable, < 1 not capable).
- **Pareto chart** – bars sorted by size showing which problem causes most of the trouble.
- **LOQ** – limit of quantification; results below it are reported as `<0.1` or `ND`.
- **Time-ordered split** – training on older batches and testing on newer ones, because processes change over time.

## ⚠️ About the data

There is no public dataset of food-colorant batch QC (and real plant data is confidential), so the notebook runs on a **simulated LIMS-style export** (`generate_colorant_data.py`). Standard colours, process targets, spec limits and effect sizes are **illustrative assumptions, not measurements from a real plant**. The simulated file deliberately contains typical raw-data problems (footer row, duplicated batches, mixed date formats, decimal commas, lead results below the limit of quantification such as `<0.1` / `ND`, impossible values, inconsistent spelling, manual release overrides).

**To use real data:** export your own anonymised batches to `data/colorant_batches.csv` with the same column names, adjust the `SPEC`, `STANDARD_LAB` and `PROCESS_TARGETS` blocks in the setup cell, and *Restart & Run All*. Never publish confidential plant data.

## What the notebook covers

| Step | Content |
|---|---|
| Audit & cleaning | type repair, LOQ-censored lead results, range checks, duplicates, structural vs real missing values, row log |
| Colorimetry | **CIEDE2000** (validated against published reference values), ΔL\*/Δa\*/Δb\*, shade direction, chroma change |
| Decision audit | recorded release decisions vs. decisions re-derived from the spec |
| EDA & tests | ΔE by product / supplier / shift / line, Kruskal-Wallis, Mann-Whitney, chi-square |
| SPC | I-charts with baseline limits, run-rule signals, Cp/Cpk before vs after a supplier change, Pareto of non-conformances |
| Early warning | process-only features, **chronological split**, `TimeSeriesSplit`, regression of ΔE00, classification of "out of tolerance", threshold chosen on a validation window, gain chart |
| Interpretation | rank correlations, off-shade rate vs. temperature deviation, permutation importance |

## Repository layout

```
├── colorant_qc_analysis.ipynb      # the analysis (outputs included)
├── colorimetry.py                  # CIEDE2000 implementation
├── generate_colorant_data.py       # builds the simulated export
├── requirements.txt
├── .gitignore
├── data/colorant_batches.csv       # raw input (simulated; replace with your own)
└── models/                         # created by the notebook
```

## Run it (VS Code)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```
Open the notebook, pick the `.venv` kernel (top-right) and click **Run All**.

## Author
**Zoha Shirazi** — Food Tech | QC (dairy production and food coloring manufacturing)
