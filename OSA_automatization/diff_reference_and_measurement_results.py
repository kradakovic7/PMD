import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import sys

# --- CONFIGURATION ---
# 1. Name of your Reference file (Output without polarizer/fiber)
REFERENCE_FILE = 'OSA_automatization/PMD_Spectra_60m_reference/1.csv' 

# 2. Folder containing your 100 measurement files
INPUT_FOLDER = 'OSA_automatization/PMD_Spectra_60m'

# 3. Where to save the calculated differences
OUTPUT_FOLDER = 'PMD_Differences_60m'

# 4. Wavelength Cutoff (To fix the "1131" artifact)
MIN_WAVELENGTH = 1190

# ---------------------------------------------------------

def load_clean_data(filepath):
    """Loads CSV, fixes delimiter, and removes '1131' header artifact."""
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return None
        
    try:
        # Load with Python engine to handle potential bad lines/delimiters
        df = pd.read_csv(filepath, delimiter=';', engine='python')
        
        # Clean column names
        df.columns = [c.strip() for c in df.columns]
        
        # Standardize names for easier merging
        # We assume Col 1 is Wavelength, Col 2 is Intensity
        df.rename(columns={df.columns[0]: 'Wavelength', df.columns[1]: 'Intensity'}, inplace=True)
        
        # Filter out artifact data (header numbers like 1131 appearing as wavelength)
        df = df[df['Wavelength'] > MIN_WAVELENGTH]
        
        return df
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def process_data():
    # 1. Create Output Directory
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # 2. Load Reference
    print(f"Loading Reference: {REFERENCE_FILE}...")
    ref_df = load_clean_data(REFERENCE_FILE)
    if ref_df is None:
        print("CRITICAL: Could not load reference file. Please check the name.")
        return

    # 3. Find all measurement files (1.csv, 2.csv, etc.)
    # We sort them numerically so 2.csv comes before 10.csv
    files = sorted(glob.glob(os.path.join(INPUT_FOLDER, "*.csv")), 
                   key=lambda x: int(os.path.basename(x).split('.')[0]))
    
    print(f"Found {len(files)} measurement files.")
    
    # 4. Processing Loop
    for filepath in files:
        filename = os.path.basename(filepath)
        
        # Load Measurement
        meas_df = load_clean_data(filepath)
        if meas_df is None: continue
        
        # --- SMART MERGE ---
        # This aligns the Reference and Measurement by Wavelength.
        # It handles cases where one file might have 1 extra point than the other.
        merged = pd.merge_asof(meas_df.sort_values('Wavelength'), 
                               ref_df.sort_values('Wavelength'), 
                               on='Wavelength', 
                               suffixes=('_Meas', '_Ref'),
                               direction='nearest')
        
        # --- CALCULATE DIFFERENCE ---
        # Difference = Measurement - Reference
        merged['Difference_dB'] = merged['Intensity_Meas'] - merged['Intensity_Ref']
        
        # Save to new CSV
        output_filename = filename.replace('.csv', '_diff.csv')
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Save columns: Wavelength, Meas, Ref, Diff
        merged.to_csv(output_path, sep=';', index=False, float_format='%.4f')
        print(f"  Processed {filename} -> {output_filename}")

    print("\nProcessing Complete!")
    
    # --- PLOTTING EXAMPLE (Last processed file) ---
    if 'merged' in locals():
        plt.figure(figsize=(10, 6))
        
        plt.plot(merged['Wavelength'], merged['Intensity_Ref'], 
                 label='Reference (Trace B)', color='green', linestyle='--', alpha=0.6)
        
        plt.plot(merged['Wavelength'], merged['Intensity_Meas'], 
                 label='Measurement (Trace A)', color='blue', alpha=0.6)
                 
        plt.plot(merged['Wavelength'], merged['Difference_dB'], 
                 label='Difference (A - B)', color='red', linewidth=1.5)
        
        plt.title(f"Example Result: {filename}")
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Intensity / Difference (dB)")
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    process_data()