import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

# --- CONFIGURATION ---
# Replace this with the name of the file you want to plot
FILENAME = 'OSA_automatization/PMD_Spectra_10m/100.csv'  

def plot_csv(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    try:
        # Read the CSV (assuming semicolon delimiter from your previous scripts)
        # We use engine='python' to be more robust with delimiters
        df = pd.read_csv(file_path, delimiter=';')
        
        # Clean up column names (remove whitespace)
        df.columns = [c.strip() for c in df.columns]
        
        print(f"Loaded {len(df)} rows.")
        print("Columns found:", df.columns.tolist())
        
        # Determine Plot Type based on columns
        plt.figure(figsize=(10, 6))
        
        # X-Axis is always Wavelength
        x_col = df.columns[0] # 'Wavelength (nm)'
        
        if len(df.columns) == 2:
            # --- SIMPLE PLOT (Measurement Only) ---
            y_col = df.columns[1] # 'Intensity (dBm)'
            plt.plot(df[x_col], df[y_col], label='Measurement', color='blue', linewidth=1)
            plt.ylabel('Intensity (dBm)')
            plt.title(f'Optical Spectrum: {file_path}')
            
        elif len(df.columns) >= 4:
            # --- DIFFERENCE PLOT (Reference Subtraction) ---
            # Plot A (Measurement)
            plt.plot(df[x_col], df.iloc[:, 1], label='Trace A (Meas)', color='blue', alpha=0.5, linestyle='--')
            
            # Plot B (Reference)
            plt.plot(df[x_col], df.iloc[:, 2], label='Trace B (Ref)', color='green', alpha=0.5, linestyle='--')
            
            # Plot C (Difference) - Make this one bold
            plt.plot(df[x_col], df.iloc[:, 3], label='Trace C (Diff)', color='red', linewidth=1.5)
            
            plt.ylabel('Power / Difference (dB)')
            plt.title(f'PMD Measurement (Ref Subtracted): {file_path}')
            
        # Common formatting
        plt.xlabel('Wavelength (nm)')
        plt.grid(True, which='both', linestyle='--', alpha=0.7)
        plt.legend()
        plt.tight_layout()
        
        # Show plot
        plt.show()

    except Exception as e:
        print(f"Error plotting file: {e}")

if __name__ == "__main__":
    # Allow running from command line: "python plot_spectrum.py 5.csv"
    if len(sys.argv) > 1:
        plot_csv(sys.argv[1])
    else:
        plot_csv(FILENAME)