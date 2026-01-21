#!/usr/bin/env python3
"""
PMD Calculator: Two-File Input (Measurement & Reference)
"""
import csv
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

# ----------------------
# User Settings
# ----------------------
# 1. File Paths (Update these!)
meas_file = r'PMD_Spectra_10m/9.csv' # The Blue Trace
ref_file  = r'PMD_Spectra_10m_reference/1.csv'   # The Green Trace

fiber_length_km = 0.01  # 10m

# 2. Analysis Range (Trim noisy tail)
START_WAVELENGTH = 1200.0
STOP_WAVELENGTH  = 1395.0

# 3. Smoothing (Clean up noise)
ENABLE_SMOOTHING = True
SMOOTH_WINDOW = 11
SMOOTH_POLY = 3

# 4. Sensitivity (Scan for stability)
scan_min = 0.1
scan_max = 3.0
scan_steps = 150

# Physics Constants
c0 = 299_792_458
K  = 0.82

# ----------------------
# Helper Functions
# ----------------------
def load_csv_trace(filepath):
    """Loads wavelength and intensity from a CSV."""
    data = []
    try:
        with open(filepath, 'r', newline='') as f:
            # Auto-detect delimiter
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample)
            reader = csv.reader(f, dialect)
            
            for row in reader:
                try:
                    # Assumes Col 0 is Wavelength, Col 1 is Intensity
                    w = float(row[0])
                    i = float(row[1])
                    data.append([w, i])
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        sys.exit(1)
        
    arr = np.array(data)
    # Sort by wavelength
    return arr[arr[:, 0].argsort()]

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

def find_optimal_delta(y_val, x_val):
    deltas = np.linspace(scan_min, scan_max, scan_steps)
    counts = []
    for d in deltas:
        p, v = peakdet(y_val, d, x_val)
        counts.append(len(p) + len(v))
    counts = np.array(counts)
    
    best_len = 0
    best_delta = deltas[0]
    curr_start = 0
    for i in range(1, len(counts) + 1):
        if i == len(counts) or counts[i] != counts[curr_start]:
            run_len = i - curr_start
            if run_len > best_len:
                best_len = run_len
                best_delta = deltas[curr_start + run_len // 2]
            curr_start = i
    return best_delta, deltas, counts

# ----------------------
# Main Execution
# ----------------------
print("--- PMD Analysis (2 Files) ---")

# 1. Load Files
meas_data = load_csv_trace(meas_file)
ref_data  = load_csv_trace(ref_file)

wl_meas = meas_data[:, 0]
int_meas = meas_data[:, 1]
wl_ref = ref_data[:, 0]
int_ref = ref_data[:, 1]

# 2. Interpolate Reference
# Crucial: Wavelength points might not match exactly between files.
# We map the Reference curve onto the Measurement's wavelength grid.
int_ref_interp = np.interp(wl_meas, wl_ref, int_ref)

# 3. Calculate Difference
diff_full = int_meas - int_ref_interp

# 4. Trim Range
mask = (wl_meas >= START_WAVELENGTH) & (wl_meas <= STOP_WAVELENGTH)
wl = wl_meas[mask]
diff = diff_full[mask]
# For plotting only:
meas_plot = int_meas[mask]
ref_plot = int_ref_interp[mask]

# 5. Smooth
if ENABLE_SMOOTHING and len(diff) > SMOOTH_WINDOW:
    diff_smooth = savgol_filter(diff, SMOOTH_WINDOW, SMOOTH_POLY)
else:
    diff_smooth = diff

# 6. Analyze
optimal_delta, deltas_checked, counts_found = find_optimal_delta(diff_smooth, wl)
peaks, valleys = peakdet(diff_smooth, optimal_delta, x=wl)
N_ext = len(peaks) + len(valleys)

# 7. Physics
l1 = np.min(wl) * 1e-9
l2 = np.max(wl) * 1e-9
dgd_ps = (K * N_ext * l1 * l2) / (2 * c0 * (l2 - l1)) * 1e12
pmd_coeff = dgd_ps / np.sqrt(fiber_length_km)

# ----------------------
# Output
# ----------------------
print("\n" + "="*35)
print("      PMD RESULTS      ")
print("="*35)
print(f"Range            : {np.min(wl):.1f} - {np.max(wl):.1f} nm")
print(f"Optimal Delta    : {optimal_delta:.2f} dB")
print(f"Extrema Count    : {N_ext} (Peaks:{len(peaks)}, Valleys:{len(valleys)})")
print("-" * 35)
print(f"Differential Group Delay : {dgd_ps:.4f} ps")
print(f"PMD Coefficient          : {pmd_coeff:.4f} ps/√km")
print("="*35 + "\n")

# ----------------------
# Plots
# ----------------------
plt.figure(figsize=(10, 10))

# Plot 1: Raw Inputs (Interpolated Ref)
plt.subplot(3, 1, 1)
plt.plot(wl, ref_plot, 'g--', label='Reference (Interpolated)')
plt.plot(wl, meas_plot, 'b-', alpha=0.7, label='Measurement')
plt.ylabel('Power (dBm)')
plt.title('Step 1: Input Spectra')
plt.legend()
plt.grid(True, alpha=0.3)

# Plot 2: Difference & Peaks
plt.subplot(3, 1, 2)
plt.plot(wl, diff_smooth, 'r-', label='Difference (Meas - Ref)')
if len(peaks) > 0: plt.plot(peaks[:,0], peaks[:,1], 'bo', label='Peaks')
if len(valleys) > 0: plt.plot(valleys[:,0], valleys[:,1], 'go', label='Valleys')
plt.ylabel('Diff (dB)')
plt.title(f'Step 2: Fringe Counting (N={N_ext})')
plt.legend()
plt.grid(True)

# Plot 3: Stability
plt.subplot(3, 1, 3)
plt.plot(deltas_checked, counts_found, 'k-')
plt.plot(optimal_delta, N_ext, 'ro')
plt.xlabel('Delta Threshold (dB)')
plt.ylabel('Extrema Count')
plt.title('Step 3: Threshold Selection')
plt.grid(True)

plt.tight_layout()
plt.show()