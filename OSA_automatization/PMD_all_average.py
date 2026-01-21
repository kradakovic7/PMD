#!/usr/bin/env python3
"""
PMD Trend Plotter
Reads 'SUMMARY*.csv' files, extracts the fiber length from the filename,
and plots Average PMD vs. Length as a line graph with error bars.
"""
import sys
import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt

# ----------------------
# User Settings
# ----------------------
INPUT_FOLDER = r'PMD_summaries'  # Folder containing SUMMARY CSV files
PLOT_FILENAME = "PMD_Trend_Graph.png"

# ----------------------
# Processing Logic
# ----------------------
print("--- PMD Trend Analysis ---")

# 1. Find Files
search_path = os.path.join(INPUT_FOLDER, "SUMMARY*.csv")
file_list = glob.glob(search_path)

if not file_list:
    print(f"No summary files found in: {INPUT_FOLDER}")
    sys.exit(1)

stats_report = []

# 2. Loop & Extract Data
for csv_path in file_list:
    filename = os.path.basename(csv_path)
    
    # Try to extract the length number from filename (e.g. "SUMMARY_10m.csv" -> 10)
    # Looks for any number in the filename
    match = re.search(r'(\d+)', filename)
    if match:
        length_val = int(match.group(1))
    else:
        print(f"Warning: Could not extract length number from {filename}. Skipping sort.")
        length_val = 0 # Fallback

    try:
        df = pd.read_csv(csv_path)
        
        # Identify PMD Column
        target_col = None
        for col in df.columns:
            if "PMD_Coeff" in col:
                target_col = col
                break
        
        if target_col and not df.empty:
            pmd_values = df[target_col].dropna()
            stats_report.append({
                "Length": length_val,       # Numeric value for X-axis sorting
                "Label": f"{length_val}m",  # Text label
                "Average_PMD": pmd_values.mean(),
                "Std_Dev": pmd_values.std()
            })
            print(f"Loaded: {filename} (Length={length_val}m)")
            
    except Exception as e:
        print(f"Error reading {filename}: {e}")

# 3. Sort & Plot
if stats_report:
    # Convert to DataFrame and SORT by Length (Critical for line graphs)
    df_results = pd.DataFrame(stats_report)
    df_results = df_results.sort_values(by="Length")

    print("\nPlotting Trend...")

    plt.figure(figsize=(10, 6))

    # Plot Line Graph with Error Bars
    # x = Length, y = Average PMD, yerr = Standard Deviation
    plt.errorbar(df_results['Length'], df_results['Average_PMD'], 
                 yerr=df_results['Std_Dev'], 
                 fmt='-o',          # 'o' for dots, '-' for line
                 linewidth=2,       # Thicker line
                 markersize=8,      # Bigger dots
                 capsize=5,         # Width of error bar caps
                 color='blue', 
                 ecolor='red',      # Error bar color
                 label='Mean PMD ± Std Dev')

    plt.xlabel('Fiber Length (m)')
    plt.ylabel('PMD Coefficient (ps/√km)')
    plt.title('PMD Coefficient vs. Fiber Length')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    
    # Optional: Force X-axis ticks to match your specific lengths
    plt.xticks(df_results['Length']) 

    plt.tight_layout()
    
    # Save
    plot_path = os.path.join(INPUT_FOLDER, PLOT_FILENAME)
    plt.savefig(plot_path, dpi=150)
    print(f"Graph saved to: {plot_path}")
    plt.show()

    # Save numeric data too
    csv_out = os.path.join(INPUT_FOLDER, "FINAL_TREND_DATA.csv")
    df_results.to_csv(csv_out, index=False)
    print(f"Data saved to: {csv_out}")

else:
    print("No valid data found.")