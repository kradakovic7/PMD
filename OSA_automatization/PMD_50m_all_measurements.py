#!/usr/bin/env python3
"""
Batch PMD Calculator (Fixed Peak Alignment)
Corrects the issue where peak markers appeared shifted down the slope.
"""
import csv
import sys
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

# ----------------------
# User Settings
# ----------------------
MEASUREMENT_FOLDER = r'PMD_Spectra_50m' 

# Path to the ONE Reference file (Green Trace)
REFERENCE_FILE     = r'PMD_Spectra_50m_reference/1.csv'

# Output folder for images and table
OUTPUT_FOLDER      = r'test_50m'

fiber_length_km = 0.05

# Range
START_WAVELENGTH = 1260.0
STOP_WAVELENGTH  = 1375.0

# Smoothing
ENABLE_SMOOTHING = True
SMOOTH_WINDOW = 11
SMOOTH_POLY = 3

# Sensitivity
scan_min = 0.1
scan_max = 3.0
scan_steps = 200
MIN_STABILITY_WIDTH_DB = 0.3 

# Physics
c0 = 299_792_458
K  = 0.82

# ----------------------
# Helper Functions
# ----------------------
def load_csv_trace(filepath):
    data = []
    try:
        with open(filepath, 'r', newline='') as f:
            sample = f.read(1024)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                dialect = csv.excel
            reader = csv.reader(f, dialect)
            for row in reader:
                try:
                    data.append([float(row[0]), float(row[1])])
                except (ValueError, IndexError):
                    continue
    except Exception:
        return None
    arr = np.array(data)
    if len(arr) == 0: return None
    return arr[arr[:, 0].argsort()]

def peakdet(v, delta, x=None):
    """
    Fixed Billauer algorithm. 
    Now correctly stores the POSITION of the max/min, not the detection point.
    """
    if x is None: x = np.arange(len(v))
    v = np.asarray(v); x = np.asarray(x)
    
    maxtab, mintab = [], []
    mn, mx = np.inf, -np.inf
    mnpos, mxpos = np.nan, np.nan  # <--- Added position trackers
    
    lookformax = True

    for i in range(len(v)):
        this = v[i]
        
        # Track Max/Min and their positions
        if this > mx: 
            mx = this
            mxpos = x[i]   # Remember WHERE the max is
        if this < mn: 
            mn = this
            mnpos = x[i]   # Remember WHERE the min is
            
        if lookformax:
            if this < mx - delta:
                # We found a peak! Use the remembered position (mxpos)
                maxtab.append((mxpos, mx)) 
                mn = this
                mnpos = x[i]
                lookformax = False
        else:
            if this > mn + delta:
                # We found a valley! Use the remembered position (mnpos)
                mintab.append((mnpos, mn))
                mx = this
                mxpos = x[i]
                lookformax = True
                
    return np.array(maxtab), np.array(mintab)

def find_optimal_delta(y_val, x_val):
    deltas = np.linspace(scan_min, scan_max, scan_steps)
    step_size = deltas[1] - deltas[0]
    min_steps = int(MIN_STABILITY_WIDTH_DB / step_size)
    
    counts = []
    for d in deltas:
        p, v = peakdet(y_val, d, x_val)
        counts.append(len(p) + len(v))
    counts = np.array(counts)
    
    valid_plateaus = []
    curr_start = 0
    for i in range(1, len(counts) + 1):
        if i == len(counts) or counts[i] != counts[curr_start]:
            run_len = i - curr_start
            if run_len >= min_steps:
                mid_idx = curr_start + run_len // 2
                valid_plateaus.append({
                    'count': counts[curr_start],
                    'delta': deltas[mid_idx]
                })
            curr_start = i
            
    if not valid_plateaus:
        return deltas[len(deltas)//2], deltas, counts
    
    return valid_plateaus[0]['delta'], deltas, counts

# ----------------------
# Batch Processing
# ----------------------
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

print(f"--- Smart Batch Analysis (Fixed Alignment) ---")

ref_data = load_csv_trace(REFERENCE_FILE)
if ref_data is None: sys.exit("Ref Error")
wl_ref = ref_data[:, 0]
int_ref = ref_data[:, 1]

file_list = glob.glob(os.path.join(MEASUREMENT_FOLDER, "*.csv"))
file_list.sort()
results_table = []
count = 0

for meas_path in file_list:
    filename = os.path.basename(meas_path)
    if os.path.abspath(meas_path) == os.path.abspath(REFERENCE_FILE): continue
    count += 1
    print(f"[{count}/{len(file_list)}] {filename}...", end="\r")

    meas_data = load_csv_trace(meas_path)
    if meas_data is None: continue

    wl_meas = meas_data[:, 0]
    int_meas = meas_data[:, 1] 
    
    int_ref_interp = np.interp(wl_meas, wl_ref, int_ref)
    diff = int_meas - int_ref_interp 
    
    mask = (wl_meas >= START_WAVELENGTH) & (wl_meas <= STOP_WAVELENGTH)
    wl = wl_meas[mask]
    diff = diff[mask]
    if len(wl) == 0: continue
    
    if ENABLE_SMOOTHING and len(diff) > SMOOTH_WINDOW:
        diff_smooth = savgol_filter(diff, SMOOTH_WINDOW, SMOOTH_POLY)
    else:
        diff_smooth = diff

    optimal_delta, deltas_checked, counts_found = find_optimal_delta(diff_smooth, wl)
    peaks, valleys = peakdet(diff_smooth, optimal_delta, x=wl)
    N_ext = len(peaks) + len(valleys)

    l1, l2 = np.min(wl)*1e-9, np.max(wl)*1e-9
    dgd_ps = (K * N_ext * l1 * l2) / (2 * c0 * (l2 - l1)) * 1e12
    pmd_coeff = dgd_ps / np.sqrt(fiber_length_km)

    results_table.append([filename, N_ext, f"{dgd_ps:.4f}", f"{pmd_coeff:.4f}", f"{optimal_delta:.2f}"])

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12))
    
    ax1.plot(wl, int_ref_interp[mask], 'g--', label='Ref')
    ax1.plot(wl, int_meas[mask], 'b-', alpha=0.7, label='Meas')
    ax1.set_title(f'Input Spectra: {filename}')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(wl, diff_smooth, 'r-', label='Diff')
    if len(peaks) > 0: ax2.plot(peaks[:,0], peaks[:,1], 'bo', label='Peaks')
    if len(valleys) > 0: ax2.plot(valleys[:,0], valleys[:,1], 'go', label='Valleys')
    ax2.set_title(f'Fringe Counting (N={N_ext})')
    ax2.grid(True)

    ax3.plot(deltas_checked, counts_found, 'k-')
    ax3.plot(optimal_delta, N_ext, 'ro', label=f'Chosen: {optimal_delta:.2f}dB')
    ax3.axvspan(optimal_delta - MIN_STABILITY_WIDTH_DB/2, optimal_delta + MIN_STABILITY_WIDTH_DB/2, color='green', alpha=0.1, label='Stability Check')
    ax3.set_title(f'Threshold Selection | DGD: {dgd_ps:.3f} ps')
    ax3.legend()
    ax3.grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FOLDER, os.path.splitext(filename)[0] + ".png"))
    plt.close(fig)

with open(os.path.join(OUTPUT_FOLDER, "SUMMARY.csv"), 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Filename", "N_ext", "DGD_ps", "PMD_Coeff", "Delta_dB"])
    writer.writerows(results_table)

print(f"\nDone! Results in {OUTPUT_FOLDER}")