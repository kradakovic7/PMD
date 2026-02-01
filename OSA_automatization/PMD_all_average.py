#!/usr/bin/env python3
"""
PMD Trend Plotter (Categorical / String Axis)
"""
import sys
import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

# ----------------------
# User Settings
# ----------------------
INPUT_FOLDER = r'PMD_summaries_1550nm'  
PLOT_FILENAME = "PMD_averages_plot.png"

# THE EXACT ORDER YOU WANT ON THE X-AXIS
# (We use these as strings, not numbers)
ORDERED_LABELS = ["10", "20", "30", "10+20", "40", "50"]

# ----------------------
# Processing Logic
# ----------------------
print("--- PMD Trend Analysis (Categorical) ---")

search_path = os.path.join(INPUT_FOLDER, "SUMMARY*.csv")
file_list = glob.glob(search_path)

if not file_list:
    print(f"No summary files found in: {INPUT_FOLDER}")
    sys.exit(1)

stats_report = []

for csv_path in file_list:
    filename = os.path.basename(csv_path)
    label_found = None
    
    # 1. IDENTIFY LABEL (String Matching)
    # Check "10+20" first so it doesn't get matched as just "10" or "20"
    if "10+20" in filename:
        label_found = "10+20"
    else:
        # Check the single numbers
        for opt in ["10", "20", "30", "40", "50"]:
            # Check if "10" is in "SUMMARY_10m.csv"
            # We look for the number followed by 'm' or end of string to be safe
            if opt in filename:
                label_found = opt
                break
    
    if not label_found:
        print(f"Skipping {filename} (No matching label found)")
        continue

    # 2. LOAD DATA
    try:
        df = pd.read_csv(csv_path)
        
        # Find PMD Column
        target_col = None
        for col in df.columns:
            if "PMD_Coeff" in col:
                target_col = col
                break
        
        if target_col and not df.empty:
            pmd_values = df[target_col].dropna()
            stats_report.append({
                "Label": label_found, 
                "Average_PMD": pmd_values.mean(),
                "Std_Dev": pmd_values.std()
            })
            print(f"Loaded: {filename} -> Label: '{label_found}'")
            
    except Exception as e:
        print(f"Error reading {filename}: {e}")

# 3. SORT & PLOT
if stats_report:
    df_results = pd.DataFrame(stats_report)
    
    # CRITICAL: Force the sorting order using Categorical data
    df_results['Label'] = pd.Categorical(df_results['Label'], categories=ORDERED_LABELS, ordered=True)
    df_results = df_results.sort_values('Label')

    print("\nPlotting...")

    plt.figure(figsize=(10, 6))

    plt.errorbar(df_results['Label'], df_results['Average_PMD'], 
                 yerr=df_results['Std_Dev'], 
                 fmt='-o',          
                 linewidth=2,       
                 markersize=8,      
                 capsize=5,         
                 color='blue', 
                 ecolor='red',      
                 label='Mean PMD ± Std Dev')

    plt.xlabel('Fiber length')
    plt.ylabel('PMD Coefficient (ps/√km)')
    plt.title('PMD Coefficient vs. Fiber length')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    
    plt.tight_layout()
    
    plot_path = os.path.join(INPUT_FOLDER, PLOT_FILENAME)
    plt.savefig(plot_path, dpi=150)
    print(f"Graph saved to: {plot_path}")
    plt.show()

    # Save numeric data
    csv_out = os.path.join(INPUT_FOLDER, "FINAL_TREND_DATA.csv")
    df_results.to_csv(csv_out, index=False)

else:
    print("No valid data found matching your list.")