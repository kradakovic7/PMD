import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Default filename
FILENAME = 'PMD_Spectra/86.csv'  

def plot_spectrum(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        # [FIX] skiprows=2 ignores the first two rows. 
        # names=[...] ensures we have correct labels even if the header was skipped.
        df = pd.read_csv(file_path, delimiter=';', skiprows=2, names=['wavelength', 'intensity'], engine='python')
        
        # Ensure data is numeric (converts any remaining text/garbage to NaN)
        df['wavelength'] = pd.to_numeric(df['wavelength'], errors='coerce')
        df['intensity'] = pd.to_numeric(df['intensity'], errors='coerce')
        
        # Remove any empty or failed rows
        df_clean = df.dropna()

        # Plot
        plt.figure(figsize=(10, 5))
        
        plt.plot(df_clean['wavelength'], df_clean['intensity'], color='blue', linewidth=0.8)
        
        plt.title(f"Spectrum: {os.path.basename(file_path)}")
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Intensity (dBm)")
        plt.grid(True, linestyle='--', alpha=0.6)
        
        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        plot_spectrum(sys.argv[1])
    else:
        plot_spectrum(FILENAME)