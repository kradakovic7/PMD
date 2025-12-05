import pyvisa
from time import sleep
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from scipy.signal import find_peaks, savgol_filter
from matplotlib.ticker import MultipleLocator
import csv

# 1. Maxima 
maxima_idx, _ = find_peaks(P, prominence=4, distance=5)
# 2. Minima
inv = -P
minima_idx, _ = find_peaks(inv, prominence=4, distance=5)

print(f"Number of maxima: {len(maxima_idx)}")
print(f"Number of minima: {len(minima_idx)}")
extremes= len(maxima_idx) + len(minima_idx)
print (f"Number of extremes: {extremes}")