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
    
    # READ STARTUP MESSAGE
    if ser.in_waiting > 0:
        raw_msg = ser.read(ser.in_waiting)
        print(f"  -> Arduino Startup: {raw_msg}")
    
    ser.reset_input_buffer()

except Exception as e:
    print(f"Error connecting to Arduino: {e}")
    sys.exit(1)

# --- 2. CONNECT TO OSA ---
rm = pyvisa.ResourceManager("@py")
try:
    print("Connecting to OSA...")
    osa = rm.open_resource('ASRL/dev/ttyUSB0::INSTR')
    
    # [FIX 1] Increased timeout to 60s to cover long data transfers
    osa.timeout = 30000 
    
    # [FIX 2] Disable termination character check to prevent timeouts on missing \n
    osa.read_termination = None
    
    # PROLOGIX CONFIGURATION
    osa.write("++addr 5")    # Set GPIB Address 5
    osa.write("++mode 1")    # Controller Mode
    osa.write("++auto 0")    # Manual Read Mode (We must ask for data)
    osa.write("++eos 0")     # Append CR+LF to commands sent
    osa.write("++clr")       # Clear OSA buffer
    
    # VERIFY CONNECTION (Bi-directional check)
    print("  -> Verifying bi-directional link...")
    osa.write("*IDN?")
    osa.write("++read eoi")
    try:
        idn = osa.read_raw().decode('utf-8').strip()
        print(f"  -> SUCCESS: Connected to {idn}")
    except Exception as e:
        print(f"  -> WARNING: IDN Check failed ({e}). Check GPIB address/cable.")

    # MEASUREMENT SETUP
    osa.write("ACTV A") 
    wstart = 1550
    wstop = 1725
    osa.write(f"STAWL {wstart}")
    osa.write(f"STPWL {wstop}")
    
except Exception as e:
    print(f"Error connecting to OSA: {e}")
    ser.close()
    sys.exit(1)

# --- HELPER: SCRAMBLE POLARIZATION ---
def scramble_polarization(serial_conn):
    try:
        # Random angles 1-90
        angles = [random.randint(1, 90) for _ in range(3)]
        motors = [b'x', b'y', b'z'] 
        
        print(f"  > Setting Pol: {angles}")
        
        for motor_char, angle in zip(motors, angles):
            # 1. Send Motor Selection
            serial_conn.write(motor_char)
            time.sleep(0.5) 
            while serial_conn.in_waiting > 0: 
                serial_conn.read(serial_conn.in_waiting)
            
            # 2. Send Angle Byte
            serial_conn.write(bytes([angle]))
            time.sleep(0.5)
            while serial_conn.in_waiting > 0: 
                serial_conn.read(serial_conn.in_waiting)
            
    except Exception as e:
        print(f"  Error moving polarizer: {e}")

# --- HELPER: READ DATA (ROBUST RAW VERSION) ---
# --- HELPER: READ DATA (CORRECTED) ---
def read_large_data(instrument, command):
    try:
        # [FIX] Do NOT use instrument.clear() -> It causes VI_ERROR_NSUP_OPER
        # Instead, send the Prologix-specific clear command:
        instrument.write("++clr") 
        
        # Send command to OSA
        instrument.write(command)
        
        # Tell Prologix to get the answer
        instrument.write("++read eoi")
        
        # Read RAW bytes to avoid "newline missing" timeouts
        # We request a large chunk (e.g., 100KB) to ensure we get the whole trace
        # If the trace is short, it will return what is available.
        raw_bytes = instrument.read_raw(size=102400)
        
        # Decode and Parse
        raw_string = raw_bytes.decode('utf-8', errors='ignore')
        values = raw_string.strip().split(',')
        
        clean_values = []
        for x in values:
            try:
                clean_values.append(float(x))
            except ValueError:
                continue
                
        return clean_values

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
    #osa.write("SGL")
    #sleep(40) # Ensure this is longer than the actual sweep time!
    
    # OPTION: Wait for sweep status (More robust than sleep)
    osa.write("SGL")
    sleep(40) # Keeping your sleep based on request, but ensure Sensitivity isn't HIGH
    
    # D. Read & Save
    try:
        valovna = read_large_data(osa, "WDATA")
        
        # Short pause to let Prologix reset
        sleep(0.5)
        
        jakost = read_large_data(osa, "LDATA")
        
        if not valovna or not jakost:
            print("  Error: No data received (Empty lists).")
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