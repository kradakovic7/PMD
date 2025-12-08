import pyvisa
import serial
import time
from time import sleep
import csv
import os
import random
import sys

# --- CONFIGURATION ---
ARDUINO_PORT = '/dev/ttyACM0'  
ARDUINO_BAUD = 9600
N_MEASUREMENTS = 100
OUTPUT_DIR = 'PMD_Spectra'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 1. CONNECT TO ARDUINO ---
try:
    print(f"Connecting to {ARDUINO_PORT}...")
    ser = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
    ser.dtr = True
    ser.rts = True
    
    print("  -> Arduino is resetting. Waiting 5s...")
    time.sleep(5) 
    
    # READ STARTUP MESSAGE (Raw Debug)
    if ser.in_waiting > 0:
        raw_msg = ser.read(ser.in_waiting)
        print(f"  -> Startup Raw: {raw_msg}")
    
    ser.reset_input_buffer()

except Exception as e:
    print(f"Error connecting to Arduino: {e}")
    sys.exit(1)

# --- 2. CONNECT TO OSA ---
rm = pyvisa.ResourceManager("@py")
try:
    osa = rm.open_resource('ASRL/dev/ttyUSB0::INSTR')
    osa.timeout = 25000 
    
    osa.write("++addr 5")
    osa.write("++mode 1")
    osa.write("++auto 0") 
    osa.write("++eos 0")
    osa.write("++clr")
    osa.read_termination = '\r\n'
    
    osa.write("ACTV A") 
    wstart = 1200
    wstop = 1425
    osa.write(f"STAWL {wstart}")
    osa.write(f"STPWL {wstop}")
    
    print(f"Connected to OSA.")

except Exception as e:
    print(f"Error connecting to OSA: {e}")
    ser.close()
    sys.exit(1)

# --- HELPER: SCRAMBLE POLARIZATION (RAW BYTE MODE) ---
def scramble_polarization(serial_conn):
    try:
        # Random angles 1-90
        angles = [random.randint(1, 90) for _ in range(3)]
        motors = [b'x', b'y', b'z'] 
        
        print(f"  > Setting: {angles}")
        
        for motor_char, angle in zip(motors, angles):
            # 1. Send Motor Selection (e.g. b'x' is byte 120)
            serial_conn.write(motor_char)
            
            # Wait for Arduino Echo
            time.sleep(0.5) 
            while serial_conn.in_waiting > 0:
                # Print raw response to see what's happening
                resp = serial_conn.read(serial_conn.in_waiting)
                # print(f"    Arduino: {resp}") 
            
            # [cite_start]2. SEND ANGLE AS RAW BYTE [cite: 2432]
            # This is the fix. We send the integer value directly.
            serial_conn.write(bytes([angle]))
            
            # Wait for Arduino Echo
            time.sleep(0.5)
            while serial_conn.in_waiting > 0:
                resp = serial_conn.read(serial_conn.in_waiting)
                # print(f"    Arduino: {resp}")
            
    except Exception as e:
        print(f"  Error moving polarizer: {e}")

# --- HELPER: READ DATA ---
def read_large_data(instrument, command):
    try:
        instrument.write(command)
        instrument.write("++read eoi")
        raw_data = instrument.read()
        values = raw_data.strip().split(',')
        try:
            return [float(x) for x in values]
        except ValueError:
            return [float(x) for x in values[1:]]
    except Exception as e:
        print(f"  Data Read Error: {e}")
        return []

# --- MAIN LOOP ---

print(f"\nStarting {N_MEASUREMENTS} measurements...")

for i in range(1, N_MEASUREMENTS + 1):
    print(f"\nMeasurement {i}/{N_MEASUREMENTS}")
    
    # A. Scramble
    scramble_polarization(ser)
    
    # B. Settle
    sleep(2) 
    
    # C. Sweep
    osa.write("SGL") 
    sleep(25) 
    
    # D. Read & Save
    try:
        valovna = read_large_data(osa, "WDATA")
        jakost = read_large_data(osa, "LDATA")
        
        if not valovna or not jakost:
            print("  Error: No data received.")
            continue
            
        filename = f'{i}.csv'
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        min_len = min(len(valovna), len(jakost))
        data_rows = zip(valovna[:min_len], jakost[:min_len])
        
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