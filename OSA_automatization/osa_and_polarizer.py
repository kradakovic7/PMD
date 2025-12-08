import pyvisa
import serial
import time
from time import sleep
import csv
import os
import numpy as np
import random
import sys

# --- CONFIGURATION ---
ARDUINO_PORT = '/dev/ttyACM0'  
ARDUINO_BAUD = 57600
N_MEASUREMENTS = 100
OUTPUT_DIR = 'PMD_Spectra'

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---OPEN CONNECTION TO ARDUINO---
try:
    ser = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
    time.sleep(2) # Wait for connection to stabilize
    print(f"Connected to Arduino on {ARDUINO_PORT}")
except Exception as e:
    print(f"Error connecting to Arduino: {e}")
    sys.exit(1)

# --- OPEN CONNECTION TO OSA ---
rm = pyvisa.ResourceManager("@py")
print("Resources:", rm.list_resources())

try:
    osa = rm.open_resource('ASRL/dev/ttyUSB0::INSTR')
    osa.timeout = 25000 
    
    osa.write("++addr 5")
    osa.write("++mode 1")
    #osa.write("++auto 1")
    osa.write("++auto 0")
    osa.write("++eos 0")
    osa.write("++clr")
    
    osa.read_termination = '\r\n'
    
    wstart = 1200
    wstop = 1425
    osa.write("stawl %d" % wstart)
    osa.write("stpwl %d" % wstop)
    
    print(f"Connected to OSA.")

except Exception as e:
    print(f"Error connecting to OSA: {e}")
    ser.close()
    sys.exit(1)

# --- HELPER FUNCTION ---
def scramble_polarization(serial_conn):

    try:
        # Random angles between 1 and 90
        angles = [random.randint(1, 90) for _ in range(3)]
        
        # Motors selection characters (ASCII 120, 121, 122)
        motor_chars = [b'x', b'y', b'z']
        
        for motor_char, angle in zip(motor_chars, angles):
            serial_conn.write(motor_char)     # Input the polarizator plane (x, y, or z)
            serial_conn.write(bytes([angle])) # Input the angle
            time.sleep(0.1) 
            
        print(f"  Polarizer scrambled to: {angles}")
        
    except Exception as e:
        print(f"  Error moving polarizer: {e}")

# --- MAIN LOOP ---

print(f"\nStarting {N_MEASUREMENTS} measurements...")

for i in range(1, N_MEASUREMENTS + 1):

    print(f"\nMeasurement {i}/{N_MEASUREMENTS}")
    scramble_polarization(ser)
    sleep(2) 
    osa.write("sgl") 
    sleep(25) #wait for sweep
    
    # E. Read Data
    try:
        valovna = osa.query_ascii_values("wdata", separator=',')
        
        jakost = osa.query_ascii_values("ldata", separator=',')
        
        filename = f'{i}.csv'
        filepath = os.path.join(OUTPUT_DIR, filename)
        data_rows = zip(valovna[1:], jakost[1:])
        
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(['Wavelength (nm)', 'Intensity (dBm)'])
            writer.writerows(data_rows)
            
        print(f"  Saved: {filename}")

    except Exception as e:
        print(f"  Error reading/saving data: {e}")

# --- CLEANUP ---
print("-" * 40)
print("Finished.")
ser.close()
osa.close()