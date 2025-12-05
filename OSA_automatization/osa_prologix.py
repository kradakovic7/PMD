import pyvisa
from time import sleep
import csv
import os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from scipy.signal import find_peaks, savgol_filter
from matplotlib.ticker import MultipleLocator
import pandas as pd

rm = pyvisa.ResourceManager("@py")
print(rm.list_resources())

osa = rm.open_resource('ASRL7::INSTR')
osa.timeout=5000
osa.write("++addr 5")
osa.write("++mode 1")
osa.write("++auto 1")
osa.write("++eos 0")
osa.write("++clr")
#osa.query("++ver")

osa.read_termination = '\r\n'
#print(osa.query('*IDN?'))

wstart = 1580
wstop = 1710

osa.write("stawl %d" % wstart)
osa.write("stpwl %d" % wstop)
#dolzina=input("Dolžina vlakna = ")

osa.write("sgl") #single sweep
sleep(20)

# Valovna dolžina
osa.write("wdata")
podatki = osa.read()
print(len(podatki))
valovna= osa.query_ascii_values("wdata", separator= ',')
#print(valovna)


#Jakost
osa.write("ldata")
data = osa.read()
#print(data)
jakost = osa.query_ascii_values("ldata", separator=',')
#print(jakost)

osa.write("pmd") #calculate pmd
sleep(10)
pmd_calc=osa.read()
pmd_value = osa.query("ANA?")   # Requests the analysis result
print("PMD (DGD):", pmd_value) # all data - right, left peak and PMD
pmd_fin = pmd_value.strip().split(',')
pmd_done = pmd_fin[2]
print(f"PMD is : {pmd_done}ps")


valovna_array = np.array(valovna[1:])
jakost_array = np.array(jakost[1:])
"""
plt.figure()
plt.plot(valovna_array, jakost_array)
plt.xlabel('Wavelength (nm)')
plt.ylabel('Intensity (dBm)')
plt.title(f'Spectrum {wstart}–{wstop} nm')
plt.xlim(wstart, wstop)
plt.gca().invert_yaxis()
plt.ylim(-85, -5)

#Grid
ax = plt.gca()
ax.xaxis.set_major_locator(MultipleLocator(20))
ax.xaxis.set_minor_locator(MultipleLocator(10))
ax.yaxis.set_major_locator(MultipleLocator(10))
ax.yaxis.set_minor_locator(MultipleLocator(5))
ax.grid(which='major', linestyle='-', linewidth=0.7)
ax.grid(which='minor', linestyle='--', linewidth=0.4)

plt.show()

"""
measurements = [(valovna_array, jakost_array)]

output_dir = 'spectra_csv'
os.makedirs(output_dir, exist_ok=True)

for idx, (wl, inten) in enumerate(measurements, start=1):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f'spectrum_{idx:02d}_{timestamp}.csv'
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['Wavelength (nm)', 'Intensity (dBm)'])
        #writer.writerow(["# PMD je:%sps, dolzina = %s m"%(pmd_done,dolzina)])
        writer.writerows(zip(wl, inten))

    print(f"Saved measurement {idx} to {filepath}") 

