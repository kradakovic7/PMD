import pyvisa
import numpy
import time


    rm = pyvisa.ResourceManager()
    osa = rm.open_resource(
        com_resource,
        baud_rate=baud_rate,
        data_bits=8,
        parity=pyvisa.constants.Parity.none,
        stop_bits=pyvisa.constants.StopBits.one,
        flow_control=pyvisa.constants.VI_ASRL_FLOW_NONE
    )
    osa.timeout = timeout_ms
    osa.write_termination = '\r'
    osa.read_termination  = '\r'

    # 2) Configure Prologix as GPIB controller
    osa.write('++mode 1')
    osa.write('++auto 0')
    osa.write('++eoi 1')
    osa.write('++ifc')
    osa.write(f'++addr {gpib_addr}')
    time.sleep(0.1)

    # SCPI helpers
    def write(cmd: str):
        osa.write(cmd)
    def query(cmd: str) -> str:
        osa.write(cmd)
        osa.write('++read eoi')
        return osa.read().strip()

    # 3) Instrument configuration without reset
    write('*CLS')              # clear status only
    write(f'STAWL1580')
    write(f':STPWL1730')
    write('SGL')    # single-sweep mode
