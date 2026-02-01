import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import sys

# --- Length ---
INPUT_FOLDER = 'PMD_summaries_1550nm_compare'  
PLOT_FILENAME = "PMD_vs_Length_Specific.png"

# 1. THE EXACT LABELS YOU WANT ON THE PLOT (IN THIS ORDER)
ORDERED_LABELS = [
    "10m", 
    "10m_1550nm", 
    "20m", 
    "20m_1550nm", 
    "30m", 
    "30m_1550nm",
    "10+20m"
]

# 2. DETECTION LIST (Prioritize specific/longer names to avoid errors)
# We check "10+20m" (6 chars) BEFORE "20m" (3 chars) so it doesn't match incorrectly.
DETECTION_ORDER = sorted(ORDERED_LABELS, key=len, reverse=True)

print("--- Plotting PMD vs Lengths ---")

files = glob.glob(os.path.join(INPUT_FOLDER, "SUMMARY*.csv"))
if not files:
    print(f"No summary files found in {INPUT_FOLDER}")
    sys.exit(1)

data_points = []

for filepath in files:
    filename = os.path.basename(filepath)
    label_found = None
    
    # Check against our sorted list (longest strings first)
    for candidate in DETECTION_ORDER:
        if candidate in filename:
            label_found = candidate
            break
    
    if not label_found:
        print(f"Skipping {filename} (Does not match any known Length)")
        continue

    # Load Data
    try:
        df = pd.read_csv(filepath)
        
        # Find PMD Column
        pmd_col = next((c for c in df.columns if "PMD" in c), None)
        
        if pmd_col:
            avg_pmd = df[pmd_col].mean()
            std_pmd = df[pmd_col].std()
            
            data_points.append({
                "Length": label_found,
                "PMD_Value": avg_pmd,
                "Error": std_pmd
            })
            print(f"Loaded: {filename} -> {label_found}")
        else:
            print(f"Skipping {filename} (No PMD column)")
            
    except Exception as e:
        print(f"Error reading {filename}: {e}")

# Plotting
if data_points:
    df_res = pd.DataFrame(data_points)
    
    # Sort by your custom list order
    df_res['Length'] = pd.Categorical(df_res['Length'], categories=ORDERED_LABELS, ordered=True)
    df_res = df_res.sort_values('Length')
    
    plt.figure(figsize=(12, 6))
    
    plt.errorbar(df_res['Length'], df_res['PMD_Value'], yerr=df_res['Error'], 
                 fmt='-o', color='blue', ecolor='red', capsize=5, 
                 linewidth=2, markersize=8, label='Measured PMD')
    
    plt.xlabel("Length")
    plt.ylabel(r'PMD Coefficient ($ps/\sqrt{km}$)')
    plt.title("PMD Value vs. Length")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    plt.tight_layout()
    
    save_path = os.path.join(INPUT_FOLDER, PLOT_FILENAME)
    plt.savefig(save_path, dpi=150)
    print(f"\nGraph saved to: {save_path}")
    plt.show()
    
    # Save Data Table
    df_res.to_csv(os.path.join(INPUT_FOLDER, "Final_Length_Data.csv"), index=False)

else:
    print("No valid data points found.")