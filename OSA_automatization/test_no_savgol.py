#!/usr/bin/env python3


# Works for now -- only have to alter delta_db every time.. :(




"""
PMD/DGD calculation using Billauer's peakdet (no SciPy, no Savitzky–Golay).

- Reads a two-column CSV: wavelength;intensity
- Uses "delta" hysteresis to ignore noise when counting extrema
- Computes Δt_PMD (ps) and D_PMD (ps/√km) with the ITU / AQ6317B formula

"""
import csv
import sys
import numpy as np

# ----------------------
# User Settings
# ----------------------
csv_file = r'spectra_csv/spectrum_01_20250723_1425.csv'  # path to your CSV
lambda_min = 1580.0        # nm
lambda_max = 1710.0        # nm
fiber_length_km = 0.01     # km
# Hysteresis for peakdet in dB (difference required before switching from tracking max to min)
delta_db = 2.88
""""
A new maximum is recorded only after the signal falls by at least delta_db below the current max.
A new minimum is recorded only after the signal rises by at least delta_db above the current min.
"""
# ----------------------
# Constants
# ----------------------
c0 = 299_792_458  # [m/s]
K  = 0.805        # strong-coupling factor

# ----------------------
# Billauer peakdet (numpy-only version)
# ----------------------
def peakdet(v, delta, x=None):
    """Detect peaks in a vector.
    Returns (maxtab, mintab) where each is an Nx2 array of [x_pos, value].
    Ported from Eli Billauer's MATLAB code (public domain).
    """
    if x is None:
        x = np.arange(len(v))
    v = np.asarray(v)
    x = np.asarray(x)

    if v.size != x.size:
        sys.exit('Input vectors v and x must have the same length')
    if not np.isscalar(delta):
        sys.exit('Input argument delta must be a scalar')
    if delta <= 0:
        sys.exit('Input argument delta must be positive')

    maxtab = []
    mintab = []

    mn, mx = np.inf, -np.inf
    mnpos, mxpos = np.nan, np.nan
    lookformax = True

    for i in range(len(v)):
        this = v[i]
        if this > mx:
            mx = this
            mxpos = x[i]
        if this < mn:
            mn = this
            mnpos = x[i]

        if lookformax:
            if this < mx - delta:
                maxtab.append((mxpos, mx))
                mn = this
                mnpos = x[i]
                lookformax = False
        else:
            if this > mn + delta:
                mintab.append((mnpos, mn))
                mx = this
                mxpos = x[i]
                lookformax = True

    return np.array(maxtab), np.array(mintab)

# ----------------------
# Read CSV
# ----------------------
wavelengths = []
intensities = []
with open(csv_file, 'r', newline='') as f:
    reader = csv.reader(f, delimiter=';')
    next(reader)
    for row in reader:
        wavelengths.append(float(row[0]))
        intensities.append(float(row[1]))

wavelengths = np.array(wavelengths)
intensities = np.array(intensities)

# ----------------------
# Find extrema with peakdet
# ----------------------
max_tab, min_tab = peakdet(intensities, delta_db, x=wavelengths)
N_ext = len(max_tab) + len(min_tab)
print(f"Peaks: {len(max_tab)}, Valleys: {len(min_tab)}, Total extrema: {N_ext}")

# ----------------------
# PMD / DGD calculations
# ----------------------
lam_min_m = lambda_min * 1e-9
lam_max_m = lambda_max * 1e-9

# Differential Group Delay [s]
delta_t_s = K * (N_ext / (2 * c0)) * (lam_max_m * lam_min_m) / (lam_max_m - lam_max_m + 1e-30)  # tiny guard
# Better to use correct denominator:
delta_t_s = K * (N_ext / (2 * c0)) * (lam_max_m * lam_min_m) / (lam_max_m - lam_min_m)

# Convert to [ps]
delta_t_ps = delta_t_s * 1e12

# PMD coefficient [ps/√km]
D_pmd_ps_per_sqrtkm = delta_t_ps / np.sqrt(fiber_length_km)

print("Differential Group Delay Δt_PMD:", delta_t_ps, "ps")
print("PMD coefficient D_PMD:", D_pmd_ps_per_sqrtkm, "ps/√km")

