#!/usr/bin/env python3
"""
pmd_peaks_only_threshold.py

Goal: Match the OSA (AQ6317B) PMD readout when it uses a 20 dB threshold and counts
ONLY peaks (no valleys). No Savitzky–Golay, no SciPy — just NumPy and a simple
neighbor-based peak finder after thresholding.

Formula (peaks-only):
    Δt_PMD = K * (N_peaks / c0) * (λ_max * λ_min) / (λ_max - λ_min)
    D_PMD   = Δt_PMD / √L

Outputs:
    - Δt_PMD in picoseconds (ps)
    - D_PMD  in ps/√km

Edit the "User Settings" block and run:
    python pmd_peaks_only_threshold.py
"""
import csv
import numpy as np

# ----------------------
# User Settings
# ----------------------
csv_file        = r'spectra_csv/spectrum_01_20250723_1539.csv'  # path to your CSV
lambda_min      = 1580.0   # nm (sweep start)
lambda_max      = 1650.0   # nm (sweep stop)
fiber_length_km = 0.02     # km
threshold_db    = 18.0     # OSA-style threshold: keep points within max-20 dB

# Optional small hysteresis to merge noise ripples (0 disables)
delta_db        = 0.0      # dB

# ----------------------
# Constants
# ----------------------
c0 = 299_792_458  # m/s
K  = 0.805        # strong-coupling factor

# ----------------------
# Simple peak finder (no valleys)
# ----------------------
def find_peaks_only(x, y):
    """Return indices of local maxima (strictly greater than both neighbors).
       Includes optional edge checks so we don't miss peaks at the ends.
    """
    if len(y) < 3:
        return np.array([], dtype=int)
    core = (y[1:-1] > y[:-2]) & (y[1:-1] > y[2:])
    idx = np.where(core)[0] + 1
    # Edge handling
    if y[0] > y[1]:
        idx = np.r_[0, idx]
    if y[-1] > y[-2]:
        idx = np.r_[idx, len(y) - 1]
    return np.unique(idx)

# Optional Billauer-style hysteresis just for peaks
def peakdet_peaks(v, delta, x=None):
    if delta <= 0:
        # fall back to neighbor method if delta is off
        return np.column_stack((x, v)) if x is not None else np.column_stack((np.arange(len(v)), v))
    if x is None:
        x = np.arange(len(v))
    v = np.asarray(v); x = np.asarray(x)
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
# Apply OSA-like threshold mask
# ----------------------
mask = inten >= (inten.max() - threshold_db)
x = wl[mask]
y = inten[mask]

# ----------------------
# Peak detection
# ----------------------
if delta_db > 0:
    # Billauer hysteresis (peaks only)
    max_tab = peakdet_peaks(y, delta_db, x)
    N_peaks = len(max_tab)
else:
    # Simple neighbor compare
    peaks_idx = find_peaks_only(x, y)
    N_peaks = len(peaks_idx)

print(f"Peaks counted (≥ max-{threshold_db} dB): {N_peaks}")

# ----------------------
# PMD / DGD calculations (peaks only)
# ----------------------
lam_min_m = lambda_min * 1e-9
lam_max_m = lambda_max * 1e-9

# Δt_PMD in seconds
delta_t_s = K * (N_peaks / c0) * (lam_max_m * lam_min_m) / (lam_max_m - lam_min_m)
# Convert to ps
delta_t_ps = delta_t_s * 1e12

# D_PMD in ps/√km
D_pmd_ps_per_sqrtkm = delta_t_ps / np.sqrt(fiber_length_km)

print("Differential Group Delay Δt_PMD:", delta_t_ps, "ps")
print("PMD coefficient D_PMD:", D_pmd_ps_per_sqrtkm, "ps/√km")

# If you want SI units too:
# D_pmd_s_per_sqrtm = delta_t_s / np.sqrt(fiber_length_km * 1e3)
# print("Δt_PMD (s):", delta_t_s)
# print("D_PMD (s/√m):", D_pmd_s_per_sqrtm)
