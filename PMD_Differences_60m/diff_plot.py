import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import sys

# --- CONFIGURATION ---
INPUT_FOLDER = 'PMD_Differences_60m'
PLOT_OUTPUT_FOLDER = 'PMD_Plots_60m'

# Pick a file to view (e.g., '1_diff.csv') or set to None for the first one
TARGET_FILE = '2_diff.csv' 

# Set to True to save images automatically
SAVE_ALL_IMAGES = False 

# ---------------------------------------------------------

def plot_single_file(filepath, save_path=None, show_plot=True):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    try:
        # Read Data
        df = pd.read_csv(filepath, delimiter=';', engine='python')
        df.columns = [c.strip() for c in df.columns]

        # DEBUG: Print columns to be sure
        # print(f"Columns in file: {df.columns.tolist()}")

        # --- CORRECT COLUMN NAMES ---
        # Matching the output of process_difference.py
        try:
            wl = df['Wavelength']
            trace_a = df['Intensity_Meas']
            trace_b = df['Intensity_Ref']
            diff_c = df['Difference_dB']
        except KeyError as e:
            # Fallback for "Reference Subtraction" script (Manual header) style
            # If the user ran the manual subtraction script instead of process_data
            wl = df.iloc[:, 0]
            trace_a = df.iloc[:, 1]
            trace_b = df.iloc[:, 2]
            diff_c = df.iloc[:, 3]

        # Create Plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        filename = os.path.basename(filepath)
        fig.suptitle(f'PMD Analysis: {filename}', fontsize=14)

        # --- TOP PLOT: Raw Spectra ---
        ax1.plot(wl, trace_a, label='Trace A (Measurement)', color='blue', linewidth=1)
        ax1.plot(wl, trace_b, label='Trace B (Reference)', color='green', linestyle='--', linewidth=1, alpha=0.7)
        ax1.set_ylabel('Power (dBm)')
        ax1.set_title('Reference and Measurement Spectra')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend(loc='lower right')

        # --- BOTTOM PLOT: Difference ---
        # Dynamic Y-Limits for better view
        ax1.set_ylim(bottom=min(trace_a.min(), trace_b.min()) - 5, top=max(trace_a.max(), trace_b.max()) + 5)
        
        ax2.plot(wl, diff_c, label='Difference (A - B)', color='red', linewidth=1.5)
        ax2.set_ylabel('Difference (dB)')
        ax2.set_xlabel('Wavelength (nm)')
        ax2.set_title('A-B (Trace C)')
        ax2.axhline(0, color='black', linewidth=0.8, linestyle='-') 
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend()

        plt.tight_layout()

        # Save or Show
        if save_path:
            plt.savefig(save_path, dpi=150)
            plt.close(fig) 
            print(f"  Saved plot: {save_path}")
        
        if show_plot:
            plt.show()

    except Exception as e:
        print(f"Error plotting {filepath}: {e}")

def run_plotting():
    # 1. Find Files
    files = sorted(glob.glob(os.path.join(INPUT_FOLDER, "*_diff.csv")), 
                   key=lambda x: int(os.path.basename(x).split('_')[0]))
    
    if not files:
        print(f"No files found in '{INPUT_FOLDER}'. Run the processing script first!")
        return

    # 2. BATCH MODE
    if SAVE_ALL_IMAGES:
        print(f"--- BATCH MODE: Saving {len(files)} plots ---")
        os.makedirs(PLOT_OUTPUT_FOLDER, exist_ok=True)
        
        for f in files:
            name = os.path.basename(f).replace('.csv', '.png')
            save_loc = os.path.join(PLOT_OUTPUT_FOLDER, name)
            plot_single_file(f, save_path=save_loc, show_plot=False)
            
        print(f"\nAll plots saved to folder: {PLOT_OUTPUT_FOLDER}")

    # 3. SINGLE MODE
    else:
        target = files[0] # Default to first
        
        if TARGET_FILE:
             specific = os.path.join(INPUT_FOLDER, TARGET_FILE)
             if os.path.exists(specific):
                 target = specific
        
        print(f"--- SINGLE MODE: Plotting {target} ---")
        plot_single_file(target, show_plot=True)

if __name__ == "__main__":
    run_plotting()