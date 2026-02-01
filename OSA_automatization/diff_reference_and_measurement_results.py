import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import sys

# --- CONFIGURATION ---
# 1. Name of your Reference file (Output without polarizer/fiber)
REFERENCE_FILE = 'PMD_Spectra_1550nm_reference/3.csv' 

# 2. Folder containing 100 measurement files
INPUT_FOLDER = 'PMD_Spectra_30m_1550nm'

# 3. Where to save the calculated differences
OUTPUT_FOLDER = 'PMD_Differences_30m_1550nm'

# 4. Wavelength Cutoff (To fix the "1131" artifact or empty starts)
MIN_WAVELENGTH = 1200

# ---------------------------------------------------------

def load_clean_data(filepath):
    """
    Loads CSV, ignoring first 2 rows, handling comma decimals, 
    and forcing numeric conversion to remove junk.
    """
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return None
        
    try:
        # [FIX 1] Skip first 2 rows and manually name columns
        # This prevents pandas from using the first row as a header
        df = pd.read_csv(filepath, delimiter=';', skiprows=2, 
                         names=['Wavelength', 'Intensity'], engine='python')
        
        # [FIX 2] Handle Comma Decimals (Europe vs US)
        # We convert to string, replace comma with dot, then convert back.
        df['Wavelength'] = df['Wavelength'].astype(str).str.replace(',', '.')
        df['Intensity'] = df['Intensity'].astype(str).str.replace(',', '.')

        # [FIX 3] Force Convert to Numbers (Coerce errors to NaN)
        # This turns any remaining text like "WDATA" or "AQ6317" into NaN (Not a Number)
        df['Wavelength'] = pd.to_numeric(df['Wavelength'], errors='coerce')
        df['Intensity'] = pd.to_numeric(df['Intensity'], errors='coerce')

        # [FIX 4] Remove junk rows (NaNs)
        df = df.dropna()
        
        # Filter by wavelength
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
    if ref_df is None or ref_df.empty:
        print("CRITICAL: Could not load reference file (or file is empty after cleaning).")
        return

    # 3. Find all measurement files (1.csv, 2.csv, etc.)
    # We sort them numerically so 2.csv comes before 10.csv
    files = sorted(glob.glob(os.path.join(INPUT_FOLDER, "*.csv")), 
                   key=lambda x: int(os.path.basename(x).split('.')[0]) if os.path.basename(x).split('.')[0].isdigit() else 0)
    
    print(f"Found {len(files)} measurement files.")
    
    # 4. Processing Loop
    for filepath in files:
        filename = os.path.basename(filepath)
        
        # Load Measurement
        meas_df = load_clean_data(filepath)
        if meas_df is None or meas_df.empty: 
            print(f"  Skipping {filename} (Empty or invalid data)")
            continue
        
        # --- SMART MERGE ---
        # This aligns the Reference and Measurement by Wavelength.
        try:
            merged = pd.merge_asof(meas_df.sort_values('Wavelength'), 
                                   ref_df.sort_values('Wavelength'), 
                                   on='Wavelength', 
                                   suffixes=('_Meas', '_Ref'),
                                   direction='nearest',
                                   tolerance=0.05) # Only match if wavelengths are within 0.05nm
        except Exception as e:
            print(f"  Error merging {filename}: {e}")
            continue
        
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
    if 'merged' in locals() and not merged.empty:
        plt.figure(figsize=(10, 6))
        
        plt.plot(merged['Wavelength'], merged['Intensity_Ref'], 
                 label='Reference', color='green', linestyle='--', alpha=0.6)
        
        plt.plot(merged['Wavelength'], merged['Intensity_Meas'], 
                 label='Measurement', color='blue', alpha=0.6)
                 
        plt.plot(merged['Wavelength'], merged['Difference_dB'], 
                 label='Difference', color='red', linewidth=1.5)
        
        plt.title(f"Example Result: {filename}")
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Intensity / Difference (dB)")
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    process_data()