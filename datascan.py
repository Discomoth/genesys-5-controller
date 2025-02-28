import serial
from typing import List
from csv import DictWriter
from matplotlib import pyplot as pl
import pandas as pd
from itertools import zip_longest

class InstrumentException(Exception):
    pass

class GenesysSerialHandler:

    def __init__(self, port:str, baudrate:int):
        self.session = serial.Serial(port, baudrate, )

    def read_write(self, command:str, termchar:str='OK'):
        self.session.write(f"{command}\r\n".encode())

        data = b''
        while True:
            if self.session.in_waiting < 1:
                pass
            tidbit = self.session.read()
            #if tidbit == b'\n':
            #    tidbit += b'\n'
            data += tidbit
            if b'OK' in data or b'ERR' in data:
                break

        data = data.decode('utf-8')
        if 'OK' in data:
            return data
        elif "ERR" in data:
            raise InstrumentException(data)

class Genesys5:

    def __init__(self, port:str, baudrate:int=9600, initialize:bool=False, datamode:str="TRANS"):
        
        self.serial = GenesysSerialHandler(port, baudrate)
        print(self.serial.read_write('MODEL'))
        self.baseline_set = False
        self.datamode = 'TRANS'
        self.set_datamode("TRANS")

        if initialize:
            self.baseline()
        
    def set_datamode(self, datamode:str):
        if datamode == "TRANS":
            self.serial.read_write("DATAMODE TRANS")
        elif datamode == "ABS":
            self.serial.read_write("DATAMODE ABS")
        else:
            raise ValueError(f"datamode must be 'TRANS' or 'ABS', not {datamode}")

    def baseline(self) -> None:
        "Measure the baseline of the instrument"

        # Set a 6 minute timeout (baseline takes 5 mins)
        self.serial.session.timeout=360
        try:
            self.serial.read_write("BASELINE")
        except InstrumentException as exc:
            raise InstrumentException("Baseline measurement failed") from exc
        except Exception as e:
            raise e
    
    def scan(self, start, stop, step) -> dict:
        """
        Execute a scan measurement and return the datapoints
        
        start       - float - the starting wavelength in nanometers
        stop        - float - the stop wavelength in nanometers
        step        - float - the increment size in nanometers (0.3 to 6.0)
        """
        if not isinstance(start, float|int):
            raise TypeError(f"start must be of type float|int, not {type(start)}")

        if 200 > start > 1100:
            raise ValueError(f"start wavelength must be between 200 and 1100, not {start}")

        if not isinstance(stop, float|int):
            raise TypeError(f"start must be of type float|int, not {type(stop)}")

        if 200 > stop > 1100:
            raise ValueError(f"start wavelength must be between 200 and 1100, not {stop}")

        if not isinstance(step, float|int):
            raise TypeError(f"start must be of type float|int, not {type(step)}")

        if 0.3 > step > 6:
            raise ValueError(f"start wavelength must be between 0.3 and 6.0, not {stop}")

        data = self.serial.read_write(f"SCAN {step} {start} {stop}")
        data = data.split('\r')

        data = [x for x in data if len(x) > 0 and "OK" not in x]

        measurements = {}
        for measurement in data:
            wavel, value = measurement.split(' ')
            measurements[float(wavel)] = float(value)
        return measurements

    def scan_cells(self, start:int|float, stop:int|float, step:int|float, cell_list:List[int]=[]) -> dict:
        """
        Execute a scan measurement and return the datapoints
        
        start       - float - the starting wavelength in nanometers
        stop        - float - the stop wavelength in nanometers
        step        - float - the increment size in nanometers (0.3 to 6.0)
        cell_list   - list  - list of cell numbers to scan. Empty list scans current cell
        """
        return_dict = {cell_no:{} for cell_no in cell_list}

        for cell_no in cell_list:
            self.set_cell(cell_no)
            return_dict[cell_no] = self.scan(start, stop, step)

        return return_dict

    def set_cell(self, cell_number):
        "Move to the specified cell"
        self.serial.read_write(f"CELL {cell_number}")
    
    def get_cell(self) -> int:
        "Returns the current cell number"
        data = self.serial.read_write("CELL")
        data.strip().replace("OK", '')
        return int(data)

if __name__ == '__main__':

    serial_port = '/dev/ttyUSB0'
    serial_baud = 9600

    instrument = Genesys5(serial_port, serial_baud, initialize=False)
    measurements = instrument.scan_cells(200, 800, 5, [1,2,3,4,5])
    #instrument.set_cell(1)

    fig, ax = pl.subplots(1,1)

    for key in measurements.keys():
        ax.plot(
        [entry[0] for entry in measurements[key].items()],
        [entry[1] for entry in measurements[key].items()],
        label=key
        )
    ax.legend()
    fig.show()
    input()
