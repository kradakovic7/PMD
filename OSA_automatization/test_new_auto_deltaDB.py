#!/usr/bin/env python3


# auto delta_db, only peaks



"""
pmd_peaks_only_auto_delta.py

Compute PMD/DGD using **only peaks** (no valleys) from an interference spectrum CSV,
while automatically choosing the Billauer hysteresis parameter `delta_db` so you
don't have to tune it manually for every trace.

Formulas (peaks-only):
    Δt_PMD = K * (N_peaks / c0) * (λ_max * λ_min) / (λ_max - λ_min)
    D_PMD   = Δt_PMD / √L

Outputs:
    - Δt_PMD in picoseconds (ps)
    - D_PMD  in ps/√km

Auto-Δ strategy (two-stage):
  1) **Noise estimate**: take the lowest 30% of intensity values, estimate their std-dev →
     initial_delta = max(0.05 dB, 3 * σ_noise).
  2) **Plateau scan (optional)**: scan delta in [scan_min, scan_max], pick the middle of the
     longest plateau (constant peak count). Disable with `use_scan = False` if you want speed.

Edit the "User Settings" block and run:
    python pmd_peaks_only_auto_delta.py
"""
import csv
import sys
import numpy as np

# ----------------------
# User Settings
# ----------------------
csv_file       = r'spectra_csv/spectrum_01_20250723_1503.csv'  # path to your CSV
lambda_min     = 1580.0    # nm (sweep start)
lambda_max     = 1710.0    # nm (sweep stop)
fiber_length_km = 0.01     # km

use_scan   = True          # True = run plateau scan, False = just noise-based delta
scan_min   = 0.05          # dB
scan_max   = 5.0           # dB
scan_steps = 120
k_sigma    = 3.0           # multiplier for noise-based delta (≈3σ)

# ----------------------
# Constants
# ----------------------
c0 = 299_792_458  # m/s
K  = 0.805        # strong-coupling factor

# ----------------------
# Peakdet (peaks only)
# ----------------------
def peakdet_peaks(v, delta, x=None):
    """Return only maxima using Billauer's hysteresis method (no minima kept)."""
    if x is None:
        x = np.arange(len(v))
    v = np.asarray(v); x = np.asarray(x)
    if v.size != x.size:
        sys.exit('v and x must be same length')
    if not np.isscalar(delta) or delta <= 0:
        sys.exit('delta must be a positive scalar')

    maxtab = []
    mn, mx = np.inf, -np.inf
    mnpos, mxpos = np.nan, np.nan
    lookformax = True

    for i in range(len(v)):
        this = v[i]
        if this > mx:
            mx = this; mxpos = x[i]
        if this < mn:
            mn = this; mnpos = x[i]
        if lookformax:
            if this < mx - delta:
                maxtab.append((mxpos, mx))
                mn = this; mnpos = x[i]
                lookformax = False
        else:
            if this > mn + delta:
                mx = this; mxpos = x[i]
                lookformax = True
    return np.array(maxtab)

# ----------------------
# Helpers for auto-delta
# ----------------------
def estimate_noise_db(int_db, frac=0.3):
    """Estimate noise std-dev from the lowest `frac` portion of the trace."""
    n = len(int_db)
    idx = np.argsort(int_db)[: int(max(1, frac * n))]
    return np.std(int_db[idx])

def choose_delta_scan(int_db, x, dmin, dmax, steps):
    """Scan delta range, return delta at the largest plateau of constant peak count."""
    deltas = np.linspace(dmin, dmax, steps)
    counts = []
    for d in deltas:
        counts.append(len(peakdet_peaks(int_db, d, x)))
    counts = np.array(counts)

    best_len = 0; best_delta = deltas[0]
    start = 0
    for i in range(1, len(counts) + 1):
        if i == len(counts) or counts[i] != counts[start]:
            seg_len = i - start
            if seg_len > best_len and counts[start] > 0:
                best_len = seg_len
                mid = start + seg_len // 2
                best_delta = deltas[mid]
            start = i
    return best_delta, deltas, counts

# ----------------------
# Read CSV
# ----------------------
wl, inten = [], []
with open(csv_file, 'r', newline='') as f:
    reader = csv.reader(f, delimiter=';')  # change to ',' if comma-delimited
    next(reader)  # skip header
    for row in reader:
        wl.append(float(row[0]))
        inten.append(float(row[1]))
wl   = np.array(wl)
inten = np.array(inten)

# ----------------------
# Auto-pick delta_db
# ----------------------
noise_sigma = estimate_noise_db(inten)
initial_delta = max(0.05, k_sigma * noise_sigma)

if use_scan:
    delta_db, deltas, counts = choose_delta_scan(inten, wl, scan_min, scan_max, scan_steps)
else:
    delta_db = initial_delta

# Fallback: ensure we actually get peaks
if len(peakdet_peaks(inten, delta_db, wl)) == 0:
    # try lowering delta progressively
    for d in np.linspace(delta_db, max(0.01, delta_db/10), 10):
        if len(peakdet_peaks(inten, d, wl)) > 0:
            delta_db = d
            break

print(f"Chosen delta_db = {delta_db} dB (initial guess {initial_delta} dB)")

# ----------------------
# Detect peaks
# ----------------------
max_tab = peakdet_peaks(inten, delta_db, x=wl)
N_peaks = len(max_tab)
print(f"Peaks counted: {N_peaks}")

# ----------------------
# PMD / DGD calculations
# ----------------------
lam_min_m = lambda_min * 1e-9
lam_max_m = lambda_max * 1e-9

# Δt_PMD in seconds (peaks-only formula)
delta_t_s = K * (N_peaks / c0) * (lam_max_m * lam_min_m) / (lam_max_m - lam_min_m)
# Convert to ps
delta_t_ps = delta_t_s * 1e12

# D_PMD in ps/√km
D_pmd_ps_per_sqrtkm = delta_t_ps / np.sqrt(fiber_length_km)

print("Differential Group Delay Δt_PMD:", delta_t_ps, "ps")
print("PMD coefficient D_PMD:", D_pmd_ps_per_sqrtkm, "ps/√km")

# Optional: plot scan curve to inspect plateau (requires matplotlib)
# import matplotlib.pyplot as plt
# if use_scan:
#     plt.plot(deltas, counts, '-')
#     plt.axvline(delta_db, color='r', linestyle='--')
#     plt.xlabel('delta (dB)'); plt.ylabel('N_peaks')
#     plt.show()
