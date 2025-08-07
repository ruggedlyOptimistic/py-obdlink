import obd
from obd import OBDStatus
import time

print("Establishing a connection to the vehicle...")
connection = obd.OBD("/dev/ttyUSB0")  # auto-connect to available port
isConnected = False

if connection.status() != OBDStatus.NOT_CONNECTED:
    isConnected = True
    print("Connected successfully!\n")
    
# else:
#     print("Connection attempt unsuccessful...quitting")
#     # exit(1)

if isConnected:     # Run the program if the programs connects to the vehicle
    try:
        
        print("****************************** VEHICLE STATUS *******************************")

        # Query and print a subset of common live data commands
        for cmd in connection.supported_commands:
            if cmd.mode == 1:  # Mode 1 is for current data
                response = connection.query(cmd)
                print(f"{cmd.name}:\t\t{response.value}")

        print("\n***************************** FAULT CODES ******************************")

        # Retrieve and print Diagnostic Trouble Codes (DTCs)
        dtc_response = connection.query(obd.commands.GET_DTC)
        dtcs = dtc_response.value
        if dtcs:
            # display fault codes 
            for code, desc in dtcs:
                print(f"{code}:\t\t{desc}")

            # offer the user the option to clear them
            choice = input("Clear codes? (Y/n):  ")

            try:
                if choice.lower() == 'y':
                    print("Clearing DTCs...",end='')
                    connection.query(obd.commands.CLEAR_DTC)
                    print("done.")
                else:
                    print("Codes not cleared")
            except TypeError:
                print("Codes not cleared. Invalid input")

        else:
            print("No fault codes found.")

        print("**********************************************************************\n")

    except KeyboardInterrupt:
        print("Exiting program")
        connection.close()

    print("Exiting program")
else:
    print("We couldn't connect :(")
