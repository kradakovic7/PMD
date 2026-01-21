#!/usr/bin/env python3
import csv
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter 


csv_file = r'DIFF_results_final/PMD_Differences_10m/8_diff.csv'
fiber_length_km = 0.01

# 1. Analysis Range Limits
START_WAVELENGTH = 1200.0
STOP_WAVELENGTH  = 1395.0

# 2. Smoothing
# Smoothing removes the "jitter" so the peak detector only sees real waves.
ENABLE_SMOOTHING = True
SMOOTH_WINDOW = 5  # Must be odd number. Higher = more smooth.
SMOOTH_POLY = 2     # Polynomial order (typically 2 or 3)

# Peak detection settings
scan_min = 0.03
scan_max = 0.8
scan_steps = 200
K  = 0.805
c0 = 299_792_458

# ----------------------
# Functions
# ----------------------
def peakdet(v, delta, x=None):
    if x is None: x = np.arange(len(v))
    v = np.asarray(v); x = np.asarray(x)
    maxtab, mintab = [], []
    mn, mx = np.inf, -np.inf
    mnpos, mxpos = np.nan, np.nan
    lookformax = True
    for i in range(len(v)):
        this = v[i]
        if this > mx: mx = this; mxpos = x[i]
        if this < mn: mn = this; mnpos = x[i]
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

def choose_delta_scan(y_db, x, dmin, dmax, steps):
    deltas = np.linspace(dmin, dmax, steps)
    counts = []
    for d in deltas:
        max_tab, min_tab = peakdet(y_db, d, x)
        counts.append(len(max_tab) + len(min_tab))
    counts = np.array(counts)
    best_len = 0
    best_delta = deltas[0]
    current_start = 0
    for i in range(1, len(counts) + 1):
        if i == len(counts) or counts[i] != counts[current_start]:
            run_length = i - current_start
            if run_length > best_len:
                best_len = run_length
                mid_idx = current_start + run_length // 2
                best_delta = deltas[mid_idx]
            current_start = i
    return best_delta, deltas, counts

# ----------------------
# Main Processing
# ----------------------
raw_data = []
with open(csv_file, 'r', newline='') as f:
    reader = csv.reader(f, delimiter=';')
    next(reader, None) # Skip header
    for row in reader:
        if len(row) >= 2:
            # Assuming Col 0 is Wavelength, Col 1 is Difference
            raw_data.append([float(row[0]), float(row[1])])

data = np.array(raw_data)
# Sort by wavelength
data = data[data[:, 0].argsort()]
wl_full = data[:, 0]
sig_full = data[:, 1]

# --- STEP 1: TRIM THE DATA ---
# Only keep the "clean" region defined in User Settings
mask = (wl_full >= START_WAVELENGTH) & (wl_full <= STOP_WAVELENGTH)
wl = wl_full[mask]
signal = sig_full[mask]

# --- STEP 2: SMOOTH THE DATA (Optional) ---
if ENABLE_SMOOTHING and len(signal) > SMOOTH_WINDOW:
    signal_smooth = savgol_filter(signal, SMOOTH_WINDOW, SMOOTH_POLY)
else:
    signal_smooth = signal

# --- STEP 3: RUN ANALYSIS ON CLEAN DATA ---
# Use the Smoothed signal for peak detection
chosen_delta, deltas_checked, counts_found = choose_delta_scan(signal_smooth, wl, scan_min, scan_max, scan_steps)

# Get final peaks
max_tab, min_tab = peakdet(signal_smooth, chosen_delta, x=wl)
N_ext = len(max_tab) + len(min_tab)

# ----------------------
# Physics & Output
# ----------------------
l1 = np.min(wl) * 1e-9
l2 = np.max(wl) * 1e-9
dgd_ps = (K * N_ext * l1 * l2) / (2 * c0 * (l2 - l1)) * 1e12
pmd_coeff = dgd_ps / np.sqrt(fiber_length_km)

print(f"Analysis Range: {np.min(wl):.1f} - {np.max(wl):.1f} nm")
print(f"Delta: {chosen_delta:.3f} dB")
print(f"Extrema Found: {N_ext}")
print(f"Differential Group Delay: {dgd_ps:.4f} ps")  # Added Line
print(f"PMD Coefficient: {pmd_coeff:.4f} ps/√km")

# Plotting
plt.figure(figsize=(10, 8))

# Plot 1: The Signal with Peaks
plt.subplot(2, 1, 1)
plt.plot(wl_full, sig_full, 'gray', alpha=0.4, label='Raw Full Data') # Show discarded data in gray
plt.plot(wl, signal_smooth, 'r-', label='Analyzed (Trimmed/Smoothed)')
if len(max_tab) > 0: plt.scatter(max_tab[:,0], max_tab[:,1], c='blue', s=40, zorder=5)
if len(min_tab) > 0: plt.scatter(min_tab[:,0], min_tab[:,1], c='green', s=40, zorder=5)
plt.axvline(STOP_WAVELENGTH, color='k', linestyle='--', label='Cutoff')
plt.title(f"Range {START_WAVELENGTH}-{STOP_WAVELENGTH}nm | Delta={chosen_delta:.2f}dB")
plt.legend()
plt.grid(True, alpha=0.3)

# Plot 2: Stability
plt.subplot(2, 1, 2)
plt.plot(deltas_checked, counts_found, 'k-')
plt.scatter([chosen_delta], [N_ext], c='r')
plt.xlabel("Delta Threshold (dB)")
plt.ylabel("Extrema Count")
plt.grid(True)
plt.tight_layout()
plt.show()