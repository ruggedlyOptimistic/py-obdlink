import obd
from obd import OBDStatus
import time

print("Establishing a connection to the vehicle...")
connection = obd.OBD()  # auto-connect to available port

if connection.status() == OBDStatus.NOT_CONNECTED:
    print("Connection attempt unsuccessful...quitting")
    exit(1)

else:
    print("Connected successfully!\n")

try:
    while True:
        print("************* VEHICLE STATUS ****************")

        # Query and print a subset of common live data commands
        for cmd in connection.supported_commands:
            if cmd.mode == 1:  # Mode 1 is for current data
                response = connection.query(cmd)
                print(f"{cmd.name}:\t\t{response.value}")

        print("\n************* FAULT CODES ******************")

        # Retrieve and print Diagnostic Trouble Codes (DTCs)
        dtc_response = connection.query(obd.commands.GET_DTC)
        dtcs = dtc_response.value
        if dtcs:
            for code, desc in dtcs:
                print(f"{code}:\t\t{desc}")
        else:
            print("No fault codes found.")

        print("********************************************\n")
        time.sleep(5)
except KeyboardInterrupt:
    print("Exiting program")
    connection.close()
