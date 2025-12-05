#!/usr/bin/env python3
"""
adaptive_delta_peakdet.py

Automatically pick the Billauer peakdet "delta" (hysteresis) so you don't have to tune it manually
for every spectrum. Then compute PMD using the ITU / AQ6317B fringe-count formula.

Strategy:
1. Estimate the noise ripple level (σ_noise) from the lower-intensity region of the trace.
2. Set an initial delta = k * σ_noise (k≈3 by default).
3. (Optional) Scan a range of delta values and choose the one in the longest "plateau" of stable
   fringe counts N_ext vs delta.

You can switch between the quick (noise-based) and scan methods via a flag.
"""
import csv
import sys
import numpy as np

# ----------------------
# User Settings
# ----------------------
csv_file = r'spectra_csv/spectrum_01_20250723_1425.csv'
lambda_min = 1580.0    # nm
lambda_max = 1710.0    # nm
fiber_length_km = 0.01 # km

# Peakdet / adaptation params
k_sigma = 3.0          # multiplier for noise-based delta estimate
scan_method = True     # if True, refine delta by scanning
scan_min = 0.05        # dB
scan_max = 5.0         # dB
scan_steps = 100

# Constants
c0 = 299_792_458       # m/s
K  = 0.805             # strong coupling factor

# ----------------------
# Billauer peakdet (pure NumPy)
# ----------------------
def peakdet(v, delta, x=None):
    if x is None:
        x = np.arange(len(v))
    v = np.asarray(v); x = np.asarray(x)
    if v.size != x.size:
        sys.exit('v and x must be same length')
    if not np.isscalar(delta) or delta <= 0:
        sys.exit('delta must be a positive scalar')

    maxtab, mintab = [], []
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
                mintab.append((mnpos, mn))
                mx = this; mxpos = x[i]
                lookformax = True
    return np.array(maxtab), np.array(mintab)

# ----------------------
# Helpers
# ----------------------
def estimate_noise_db(intensities_db, frac=0.3):
    """Estimate noise ripple (std dev) from the low-power tail of the trace."""
    # take the lowest `frac` portion of samples in intensity
    n = len(intensities_db)
    idx = np.argsort(intensities_db)[:int(frac*n)]
    noise_segment = intensities_db[idx]
    return np.std(noise_segment)

def choose_delta_scan(y_db, x, dmin, dmax, steps):
    """Scan delta range and find the longest plateau of constant N_ext."""
    deltas = np.linspace(dmin, dmax, steps)
    counts = []
    for d in deltas:
        max_tab, min_tab = peakdet(y_db, d, x)
        counts.append(len(max_tab) + len(min_tab))
    counts = np.array(counts)
    # find longest consecutive run of the same count
    best_len = 0; best_delta = deltas[0]
    start = 0
    for i in range(1, len(counts)+1):
        if i == len(counts) or counts[i] != counts[start]:
            length = i - start
            if length > best_len:
                best_len = length
                best_delta = deltas[start + length//2]
            start = i
    return best_delta, deltas, counts

# ----------------------
# Read CSV
# ----------------------
wl = []
inten = []
with open(csv_file, 'r', newline='') as f:
    reader = csv.reader(f, delimiter=';')
    next(reader)
    for row in reader:
        wl.append(float(row[0]))
        inten.append(float(row[1]))
wl = np.array(wl)
inten = np.array(inten)

# ----------------------
# Auto delta selection
# ----------------------
noise_sigma = estimate_noise_db(inten)
initial_delta = max(0.05, k_sigma * noise_sigma)

if scan_method:
    delta_db, deltas, counts = choose_delta_scan(inten, wl, scan_min, scan_max, scan_steps)
else:
    delta_db = initial_delta

print(f"Chosen delta_db = {delta_db} dB (initial guess {initial_delta} dB)")

# ----------------------
# Count extrema
# ----------------------
max_tab, min_tab = peakdet(inten, delta_db, x=wl)
N_ext = len(max_tab) + len(min_tab)
print(f"Peaks: {len(max_tab)}, Valleys: {len(min_tab)}, Total extrema: {N_ext}")

# ----------------------
# PMD / DGD Calculations
# ----------------------
lam_min_m = lambda_min * 1e-9
lam_max_m = lambda_max * 1e-9

delta_t_ps = (K * (N_ext / (2 * c0)) * (lam_max_m * lam_min_m) / (lam_max_m - lam_min_m)) * 1e12
D_pmd_ps_per_sqrtkm = delta_t_ps / np.sqrt(fiber_length_km)

print("Differential Group Delay Δt_PMD:", delta_t_ps, "ps")
print("PMD coefficient D_PMD:", D_pmd_ps_per_sqrtkm, "ps/√km")

# (Optional) you can plot deltas vs counts to see the plateau:
# import matplotlib.pyplot as plt
# plt.plot(deltas, counts, '-')
# plt.xlabel('delta (dB)'); plt.ylabel('N_ext')
# plt.show()
