import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

FILENAME = 'OSA_automatization/PMD_Spectra_10m_reference/2.csv'  

def plot_spectrum(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    df = pd.read_csv(file_path, delimiter=';', engine='python')
    
    df.columns = [c.strip() for c in df.columns]
    df_clean = df[df[df.columns[0]] > 1190] #removes the row with wrong data at the start
    
    # Plot
    plt.figure(figsize=(10, 5))
    
    x = df_clean.iloc[:, 0] # Wavelength
    y = df_clean.iloc[:, 1] # Intensity
    
    plt.plot(x, y, color='blue', linewidth=0.8)
    
    plt.title(f"Spectrum: {os.path.basename(file_path)}")
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (dBm)")
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        plot_spectrum(sys.argv[1])
    else:
        plot_spectrum(FILENAME)