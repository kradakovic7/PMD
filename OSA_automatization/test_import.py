#!/usr/bin/env python3
"""
pmd_calculation.py - Fixed PMD & DGD Calculation with Threshold

Reads a two-column CSV spectrum, applies smoothing, counts fringes above
a default 3 dB threshold, and computes:
  - Differential Group Delay (Δt_PMD) in picoseconds (ps)
  - PMD coefficient (D_PMD) in ps/√km

Instructions:
1. Update the CSV path and measurement parameters below.
2. Run: python pmd_calculation.py

Formulas (ITU):
    Δt_PMD = K * (N_ext / (2*c0)) * (λ_max * λ_min / (λ_max - λ_min))
    D_PMD  = Δt_PMD / sqrt(L)

Constants:
    c0 = 299792458 m/s
    K  = 0.805    # coupling factor (strong coupling)
"""
import csv
import numpy as np
from scipy.signal import savgol_filter

# ------------------
# User Settings
# ------------------
csv_file = 'spectra_csv\spectrum_01_20250620_1407.csv'  # Path to your CSV
lambda_min = 1580.0       # nm
lambda_max = 1710.0       # nm
fiber_length_km = 0.01    # fiber length [km]
threshold_db = 26.0         # dB above noise

# Constants
c0 = 299792458  # m/s
K = 0.805       # coupling factor

# ------------------
# Read Spectrum Data
# ------------------
wavelengths, intensities = [], []
with open(csv_file, 'r', newline='') as f:
    reader = csv.reader(f, delimiter=';')
    next(reader)
    for row in reader:
        wavelengths.append(float(row[0]))
        intensities.append(float(row[1]))
wavelengths = np.array(wavelengths)
intensities = np.array(intensities)

# ------------------
# Smooth Data
# ------------------
int_smooth = savgol_filter(intensities, window_length=11, polyorder=3)

# ------------------
# Apply threshold mask
# ------------------
thresh_line = np.max(int_smooth) - threshold_db
mask = int_smooth >= thresh_line
x = wavelengths[mask]
y = int_smooth[mask]

# ------------------
# Find extrema across masked data
# ------------------
def find_extrema(x, y):
    dy = np.gradient(y, x)
    sc = np.sign(dy[:-1]) * np.sign(dy[1:])
    peaks = np.where((sc < 0) & (dy[:-1] > 0))[0] + 1
    valleys = np.where((sc < 0) & (dy[:-1] < 0))[0] + 1
    return peaks, valleys

peaks, valleys = find_extrema(x, y)
N_ext = len(peaks) + len(valleys)
print(f"Total extrema (peaks+valleys) above {threshold_db} dB: {N_ext}")

# ------------------
# Compute Δt_PMD [s] then to ps
# ------------------
lam_min_m = lambda_min * 1e-9
lam_max_m = lambda_max * 1e-9
delta_t_s = K * (N_ext / (2 * c0)) * (lam_max_m * lam_min_m) / (lam_max_m - lam_min_m)
delta_t_ps = delta_t_s * 1e12
print(f"Differential Group Delay Δt_PMD: {delta_t_ps} ps")

# ------------------
# Compute D_PMD [ps/√km]
# ------------------
D_pmd_ps_per_sqrtkm = delta_t_ps / np.sqrt(fiber_length_km)
print(f"PMD coefficient D_PMD: {D_pmd_ps_per_sqrtkm} ps/√km")
