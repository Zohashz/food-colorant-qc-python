"""
Simulated LIMS-style export for a FOOD COLORANT plant.

WHY SIMULATED
-------------
No public dataset of food-colorant batch QC exists on Kaggle (and real plant
data is confidential). This script builds a dataset that mimics what a plant
LIMS/ERP export typically looks like: one row per batch with process
parameters, lab results and the release decision.

The numbers (standard colours, process targets, spec limits, effect sizes) are
ILLUSTRATIVE ASSUMPTIONS, not measurements from a real plant. Replace the file
data/colorant_batches.csv with your own (anonymised, rescaled) export and the
notebook runs unchanged as long as the column names are kept.

BUILT-IN PROCESS STORY (so the analysis has something real to find)
-------------------------------------------------------------------
  * reaction temperature above target degrades colour (lower L*, lower chroma) and strength
  * pH deviation shifts hue; short mixing time adds batch-to-batch scatter
  * over-drying (powders) darkens the product
  * night shift runs hotter and noisier
  * a NEW RAW-MATERIAL SUPPLIER ("C") starts mid-way: darker/duller shade, lower
    strength, more lead -> a process shift that SPC charts should reveal

DELIBERATE RAW-DATA PROBLEMS (so the cleaning code is exercised)
----------------------------------------------------------------
  * footer line, duplicated batch rows (LIMS re-export), mixed date formats
  * decimal commas, "<0.1" and "ND" in the lead column (below limit of quantification)
  * impossible values (L* = 0 from a failed reading, pH typed as 70, ...)
  * inconsistent product / decision spelling, ~1% missing values
  * ~2.5% of release decisions that contradict the spec rules (manual overrides)
"""
import numpy as np
import pandas as pd
from colorimetry import ciede2000

rng = np.random.default_rng(11)
N = 1500
start, end = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-06-30")
n_days = (end - start).days + 1
SUPPLIER_C_START = 230          # day index when supplier C is introduced (about 42% into the period)

day_idx = np.sort(rng.integers(0, n_days, N))
date = start + pd.to_timedelta(day_idx, unit="D")

shift = rng.choice(["Morning", "Afternoon", "Night"], N, p=[0.4, 0.4, 0.2])
line = rng.choice(["Line-1", "Line-2", "Line-3"], N, p=[0.4, 0.35, 0.25])
products = ["Yellow_Synthetic", "Red_Synthetic", "Blue_Synthetic", "Orange_Natural"]
product = rng.choice(products, N, p=[0.32, 0.28, 0.20, 0.20])
form = np.where(product == "Orange_Natural", "Liquid", rng.choice(["Powder", "Liquid"], N, p=[0.6, 0.4]))
after = day_idx >= SUPPLIER_C_START
supplier = np.where(after, rng.choice(["A", "B", "C"], N, p=[0.25, 0.30, 0.45]),
                    rng.choice(["A", "B"], N, p=[0.55, 0.45]))

# illustrative standards (L*, a*, b* of a reference-concentration solution) and process targets
STD = {"Yellow_Synthetic": (87.0, -4.0, 82.0), "Red_Synthetic": (42.0, 66.0, 38.0),
       "Blue_Synthetic": (28.0, -8.0, -52.0), "Orange_Natural": (68.0, 38.0, 72.0)}
RXN_T = {"Yellow_Synthetic": 65.0, "Red_Synthetic": 70.0, "Blue_Synthetic": 60.0, "Orange_Natural": 55.0}
PH_T = {"Yellow_Synthetic": 7.0, "Red_Synthetic": 6.5, "Blue_Synthetic": 7.2, "Orange_Natural": 5.5}

std = np.array([STD[p] for p in product])
rxn_target = np.array([RXN_T[p] for p in product])
ph_target = np.array([PH_T[p] for p in product])
night = (shift == "Night")

# ---- process parameters ------------------------------------------------------
reaction_temp = rxn_target + rng.normal(0, np.where(night, 2.9, 2.2)) + np.where(night, 0.8, 0.0) \
                + np.where(line == "Line-3", 0.7, 0.0)
ph_final = ph_target + rng.normal(0, np.where(night, 0.23, 0.18))
mixing_time = np.clip(rng.normal(np.where(night, 43, 45), 6), 20, 70)
drying_temp = np.where(form == "Powder", rng.normal(85, 3, N), np.nan)
batch_size = rng.choice([500, 1000, 2000], N, p=[0.3, 0.5, 0.2])

# ---- colour: standard + process-driven shift + noise ---------------------------
over_t = np.maximum(reaction_temp - rxn_target, 0)
under_t = np.maximum(rxn_target - reaction_temp, 0)
dry_over = np.nan_to_num(np.maximum(drying_temp - 88, 0))
ph_dev = ph_final - ph_target
short_mix = np.maximum(38 - mixing_time, 0)
supC = (supplier == "C")
supB = (supplier == "B")

chroma_f = (1 - 0.017 * over_t - 0.009 * under_t) * (1 - 0.009 * dry_over)
L = std[:, 0] - 0.34 * over_t - 0.12 * under_t - 0.27 * dry_over - 0.95 * supC + 0.15 * supB
a = std[:, 1] * chroma_f + 1.3 * ph_dev + 0.40 * supC
b = std[:, 2] * chroma_f - 2.0 * ph_dev - 1.3 * supC
noise_sd = 0.42 + 0.06 * short_mix
L = L + rng.normal(0, noise_sd)
a = a + rng.normal(0, noise_sd)
b = b + rng.normal(0, noise_sd)

# ---- other lab results ---------------------------------------------------------
strength = (100 - 0.45 * over_t - 0.25 * under_t - 0.10 * dry_over - 1.4 * supC
            + rng.normal(0, 1.2 + 0.04 * short_mix))
moisture = np.where(form == "Powder",
                    np.clip(rng.normal(3.8, 0.7, N) - 0.05 * np.nan_to_num(drying_temp - 85) + 0.3 * night, 0.5, 9),
                    np.nan)
lead = rng.lognormal(np.log(0.35), 0.6, N) * np.where(supC, 1.8, 1.0)

# ---- release decision from (illustrative) spec rules ---------------------------
dE = ciede2000(np.column_stack([L, a, b]), std)
SPEC = dict(dE_max=1.5, strength_lo=95.0, strength_hi=105.0, strength_reject=92.0,
            moisture_max=6.0, lead_max=2.0)
reject = (lead > SPEC["lead_max"]) | (strength < SPEC["strength_reject"])
rework = ((dE > SPEC["dE_max"]) | (strength < SPEC["strength_lo"]) | (strength > SPEC["strength_hi"])
          | (np.nan_to_num(moisture) > SPEC["moisture_max"]))
decision = np.where(reject, "Reject", np.where(rework, "Rework", "Release"))
flip = rng.random(N) < 0.025                       # manual overrides
decision = np.where(flip, rng.choice(["Release", "Rework", "Reject"], N), decision)

df = pd.DataFrame({
    "Batch_ID": [f"CL{24000 + i}" for i in range(N)],
    "Date": date, "Product": product, "Form": form, "Line": line, "Shift": shift, "Supplier": supplier,
    "Batch_Size_kg": batch_size, "Reaction_Temp_C": reaction_temp.round(1), "pH_Final": ph_final.round(2),
    "Mixing_Time_min": mixing_time.round(0), "Drying_Temp_C": np.round(drying_temp, 1),
    "L": L.round(2), "a": a.round(2), "b": b.round(2),
    "Strength_pct": strength.round(1), "Moisture_pct": np.round(moisture, 2), "Lead_ppm": lead.round(3),
    "Release_Decision": decision,
})

# ================== inject raw-data problems =====================================
df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
idx = rng.choice(N, 20, replace=False)                              # different date format
df.loc[idx, "Date"] = pd.to_datetime(df.loc[idx, "Date"]).dt.strftime("%d.%m.%Y")

for col in ["L", "a", "b", "Strength_pct", "Mixing_Time_min"]:     # numeric columns as text
    df[col] = df[col].astype(object)
for col in ["L", "a", "b", "Strength_pct"]:
    idx = rng.choice(N, 12, replace=False)
    df.loc[idx, col] = [f"{v}".replace(".", ",") for v in df.loc[idx, col]]

df["Lead_ppm"] = df["Lead_ppm"].astype(object)                      # below the limit of quantification
below = df.index[df["Lead_ppm"].astype(float) < 0.12]
for i in below:
    df.loc[i, "Lead_ppm"] = "<0.1" if rng.random() < 0.7 else "ND"

bad = rng.choice(N, 6, replace=False); df.loc[bad, "L"] = "0"              # failed reading
bad = rng.choice(N, 4, replace=False); df.loc[bad, "pH_Final"] = (df.loc[bad, "pH_Final"] * 10).round(1)
bad = rng.choice(N, 3, replace=False); df.loc[bad, "Strength_pct"] = "1000"

variants = {"Yellow_Synthetic": ["yellow synthetic", "YELLOW_SYNTHETIC ", "Yellow-Synthetic"],
            "Red_Synthetic": ["red synthetic", "RED_SYNTHETIC ", "Red-Synthetic"],
            "Blue_Synthetic": ["blue synthetic", "BLUE_SYNTHETIC ", "Blue-Synthetic"],
            "Orange_Natural": ["orange natural", "ORANGE_NATURAL ", "Orange-Natural"]}
for i in rng.choice(N, 90, replace=False):
    df.loc[i, "Product"] = rng.choice(variants[df.loc[i, "Product"]])
for i in rng.choice(N, 60, replace=False):
    df.loc[i, "Release_Decision"] = rng.choice([df.loc[i, "Release_Decision"].lower(),
                                                 df.loc[i, "Release_Decision"].upper() + " "])

for col in ["Reaction_Temp_C", "pH_Final", "Mixing_Time_min", "L", "a", "b", "Strength_pct"]:
    m = rng.random(N) < 0.008
    df.loc[m, col] = np.nan

dups = df.sample(18, random_state=3)                                # LIMS re-export duplicates
df = pd.concat([df, dups], ignore_index=True).sample(frac=1, random_state=5).reset_index(drop=True)
footer = {c: np.nan for c in df.columns}
footer["Batch_ID"] = "Exported from LIMS (simulated) - replace with your own export"
df = pd.concat([df, pd.DataFrame([footer])], ignore_index=True)

df.to_csv("data/colorant_batches.csv", index=False)
print("rows written:", len(df))
print("true release decisions (before overrides/noise):",
      pd.Series(np.where(reject, "Reject", np.where(rework, "Rework", "Release"))).value_counts().to_dict())
print("share with dE > tolerance:", round(float((dE > SPEC['dE_max']).mean()), 3),
      "| median dE:", round(float(np.median(dE)), 2))
print("dE by supplier:", pd.Series(dE).groupby(supplier).median().round(2).to_dict())
