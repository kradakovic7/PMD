import pandas as pd
import numpy as np

# --- 1. Load Data and Define Parameters ---

# Load the CSV file. Skip 28 rows of metadata as determined previously.
try:
    df = pd.read_csv('191125_v2_period_1min_0deg.csv', skiprows=28)
except FileNotFoundError:
    print("Error: File not found. Check the file name.")
    exit()

# Define columns (PV = Channel 1, CO = Channel 2)
TIME_COL = 'Time (s)'
PV_COL = 'Channel 1 (V)'
CO_COL = 'Channel 2 (V)'

# The Waveforms metadata showed a 1V peak-to-peak step (Amplitude 500 mV, Offset 0 V).
# This is the most reliable source for the input step.
DELTA_U_INPUT = 1.0 # V

# --- 2. Identify Step Time (t_step) and Region of Interest (ROI) ---

# Find the midpoint of the input signal (Channel 2) to identify the rising edge.
c2_midpoint = df[CO_COL].mean()
first_step_idx = df[df[CO_COL] > c2_midpoint].index[0]
t_step = df.loc[first_step_idx, TIME_COL]

# Define the ROI: Start 10s before the step, end 120s (2 minutes) after the step.
start_time = t_step - 10
end_time = t_step + 120
df_filtered = df[(df[TIME_COL] >= start_time) & (df[TIME_COL] <= end_time)].copy()


# --- 3. Calculate Steady-State Values ---

# Initial window: -10s to -5s relative to t_step
initial_window = df_filtered[(df_filtered[TIME_COL] < t_step - 5)]
# Final window: Last 10 seconds of the filtered data
final_window = df_filtered[df_filtered[TIME_COL] > end_time - 10]

# Use mean to average out noise in steady state regions
Y_initial = initial_window[PV_COL].mean()
Y_final = final_window[PV_COL].mean()
Delta_Y = Y_final - Y_initial


# --- 4. Find the Maximum Slope (m) in the Thermal Response Region ---

# Calculate the numerical derivative (slope) for the entire ROI
df_filtered['Slope_V_per_s'] = df_filtered[PV_COL].diff() / df_filtered[TIME_COL].diff()

# CRITICAL FIX: Ignore the first 5 seconds after t_step to avoid electrical transients/noise.
df_response = df_filtered[df_filtered[TIME_COL] >= t_step + 5]

# Find the maximum absolute slope in the thermal response region
max_slope_V_per_s = df_response['Slope_V_per_s'].abs().max()

# Find the row corresponding to this absolute maximum slope
row_inflection = df_response[df_response['Slope_V_per_s'].abs() == max_slope_V_per_s].iloc[0]

# Extract the tangent parameters
t_inflection = row_inflection[TIME_COL]
Y_inflection = row_inflection[PV_COL]
actual_max_slope = row_inflection['Slope_V_per_s']


# --- 5. Calculate FOPDT Model Parameters ---

# Process Gain (K)
K = Delta_Y / DELTA_U_INPUT
K_abs = np.abs(K)

# Dead Time (theta) calculation: Time when tangent intersects Y_initial
t_zero = t_inflection - (Y_inflection - Y_initial) / actual_max_slope
theta = t_zero - t_step # Dead time is relative to the start of the step

# Time Constant (tau) calculation: Time from t_zero until the tangent intersects Y_final
t_final_tangent = t_inflection - (Y_final - Y_inflection) / actual_max_slope
tau = t_final_tangent - t_zero

# Ensure time constants are positive (absolute value)
theta_abs = np.abs(theta)
tau_abs = np.abs(tau)


# --- 6. Ziegler-Nichols PI Tuning (Using PI-only Formulas) ---
if K_abs > 0 and theta_abs > 0 and not np.isnan(tau_abs):
    # ZN PI formulas: Kp = 0.9*tau / (|K|*theta); Ti = 3.33*theta
    Kp_pi = (0.9 * tau_abs) / (K_abs * theta_abs)
    Ti_pi = 3.33 * theta_abs
else:
    Kp_pi, Ti_pi = np.nan, np.nan

# --- 7. Component Calculations (Using ZN PI results) ---
# We assume an inverting PI op-amp circuit: Kp = Rf/Rin and Ti = Ri * Ci.
# We choose standard starting values for Rin and Ci for calculation.
R_in_standard = 10000.0 # 10 kOhm
C_i_standard = 10.0e-6 # 10 uF (Film/Polyester capacitor recommended)

if not np.isnan(Kp_pi) and not np.isnan(Ti_pi):
    # Proportional Resistor (Rf)
    R_f_pi = Kp_pi * R_in_standard
    
    # Integral Resistor (Ri)
    R_i_pi = Ti_pi / C_i_standard
else:
    R_f_pi, R_i_pi = np.nan, np.nan


# --- 8. Output Results ---
print("--- Process Reaction Curve (FOPDT) Parameters ---")
print(f"Dead Time (theta): {theta_abs:.4f} s")
print(f"Time Constant (tau): {tau_abs:.4f} s")
print(f"Absolute Process Gain (|K|): {K_abs:.4f}")

print("\n--- Ziegler-Nichols PI Tuning (Open-Loop) ---")
print(f"Proportional Gain (Kp): {Kp_pi:.2f}")
print(f"Integral Time (Ti): {Ti_pi:.2f} s")

print("\n--- Analog PI Controller Component Values (Based on 10 kOhm & 10 uF) ---")
print(f"Input Resistor (Rin): {R_in_standard/1000.0:.0f} kOhms (Chosen)")
print(f"Integral Capacitor (Ci): {C_i_standard*1e6:.0f} uF (Chosen)")
print(f"Feedback Resistor (Rf) for Kp: {R_f_pi/1000.0:.2f} kOhms")
print(f"Integral Resistor (Ri) for Ti: {R_i_pi/1e6:.2f} MOhms")