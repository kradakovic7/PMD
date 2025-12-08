# --- OPEN CONNECTION TO OSA ---
rm = pyvisa.ResourceManager("@py")
print("Resources:", rm.list_resources())

try:
    osa = rm.open_resource('ASRL7::INSTR')
    osa.timeout = 20000 
    
    osa.write("++addr 5")
    osa.write("++mode 1")
    osa.write("++auto 1")
    osa.write("++eos 0")
    osa.write("++clr")
    
    osa.read_termination = '\r\n'
    
    wstart = 1200
    wstop = 1450
    osa.write("stawl %d" % wstart)
    osa.write("stpwl %d" % wstop)
    
    print(f"Connected to OSA.")

except Exception as e:
    print(f"Error connecting to OSA: {e}")
    ser.close()
    sys.exit(1)
