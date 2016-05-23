# @author AMOSus (Daniel)
# @author Inkibus (Rene)

# This script simulates all sensors of the production system, that are pushing their data for each timestamp to the
# processing unit. This script also serves the purpose of being the processing unit. It maps the drive data
# to different carriers.
# The script calls depending on the amount of drives and waitTime the CompressingAlgorithm all x seconds
# Input: CSV file with the following structure (ms; energy1;...;energyX; pos1;...;posX) (x = Amount of Drives)
# Output: CSV file for each carrier in each iteration with the following structure (time; posAbsolute; energy; drive)
# and the following name Session_X_Carrier_X_Iteration_X.csv

# TODO: Make compression only select timeStamps that are not 0. Maybe don't compress over multiple timestamps.
# TODO: Now that we have the real data some kind of measure for flexibility can be implemented and calculated here!

# IMPORTS
# Imports Pandas for Data handling
from __future__ import print_function
import pandas as pd
# Imports OS for Operating System independent absolute file paths
import os
# Imports Pandas for Data handling
import numpy as np
# Imports sleep for sleeping
from time import sleep
# Imports setConstants to maintain all constants on one place
import setConstants
# Import glob to enable the search in a folder
import glob
# Imports sys to terminate the function
import sys
# Imports Csv to Manipulate Initial CSV-File
import csv
# Imports Logging to Log File
import logging

# CONSTANTS
# WAIT_TIME_IN_SECONDS: Time the script should wait until it calls the function again (in seconds)
WAIT_TIME_IN_SECONDS = setConstants.WAIT_TIME_IN_SECONDS_DPPY
# Input file names of data here
DATA_FILE_NAMES = []
# AMOUNT_OF_CARRIERS: How many Carriers are in the system
AMOUNT_OF_CARRIERS = setConstants.AMOUNT_OF_CARRIERS
# DATA_SEPARATOR: Separator of the CSV-File
DATA_SEPARATOR = setConstants.CSV_SEPARATOR
# Every X th row of the data is kept when compressing the data
KEEP_EVERY_X_ROW = 100
# Current Session
SESSION = setConstants.SESSION


# Main data processing script. Gets input data of drives and maps it to the carries and saves them as CSV files once
# an iteration is complete
# Input: (time: int, drive: int, position: float, energy: float)
def processData(time, drive, position, energy):
    # Ensures that all modified global variables are called globally
    global iterationNumber
    global carrierData
    global lastPositionOfCarrier
    global currentPositionAtCarrierData

    # If the line has just started, then the first carrier enters the first drive and set iterationNumber to 1
    if iterationNumber == 0:
        print("line has just started: Carrier 1 at Drive 1")
        iterationNumber = 1
        driveXHasCarrier[0] = 1

    # Determine which carrier is currently on the drive
    carrier = int(driveXHasCarrier[drive - 1])

    # If the current drive doesnt have a carrier, it cannot be mapped
    if driveXHasCarrier[drive - 1] == 0:
        return

    # If the timestamp is the same as previously, the data is not recorded
    # This only happens when pushing carries which should not happen in the first place
    if time == carrierData[carrier - 1][0][currentPositionAtCarrierData[carrier - 1] - 1]:
        return

    # If position is zero and it wasn't 0 before, the carrier has left the drive and the drive needs to be reset
    if position == 0 and lastPositionOfCarrier[carrier - 1] != 0:
        print(" ")
        print("Drive     " + str(drive))
        print("Carrier   " + str(carrier))
        print("Time      " + str(time))
        print("Position  " + str(position))
        print("Energy    " + str(energy))

        # Reset the drive
        evaluateDriveReset(drive, carrier)

        # Process the timestamp that caused the drive reset
        # This needs to be done because of the position is 0, this means that the current carrier is not on the drive
        # anymore. Therefore this funciton is called again after the drive has been reset.
        processData([time, drive, position, energy])
        return

    # Ensures enough space in the carrierData array for storing the data
    ensureEnoughSpaceInCarrierData(carrier)

    # Transfer the time of the timeStamp to the carrierData
    carrierData[carrier - 1][0][currentPositionAtCarrierData[carrier - 1]] = time
    # Transfer position to the carrierData
    carrierData[carrier - 1][1][currentPositionAtCarrierData[carrier - 1]] = position

    # Transfer the energy of the timeStamp to the carrierData
    carrierData[carrier - 1][2][currentPositionAtCarrierData[carrier - 1]] = energy

    # Transfer energy consumption of the timeStamp to the carrierData
    carrierData[carrier - 1][3][currentPositionAtCarrierData[carrier - 1]] = drive

    # Saves current position for carrier for further processing
    lastPositionOfCarrier[carrier - 1] = position

    # Updates current position in the carrierData array, so that the next data point can be written to the next row
    currentPositionAtCarrierData[carrier - 1] += 1


# This method is called when da drive reset its position to 0 and the carrier moves on to the next drive.
def evaluateDriveReset(drive, carrier):
    # Ensures that all modified global variables are called globally
    global driveXHasCarrier
    global lastPositionOfCarrier
    global iterationNumber
    global driveXHasCarrierWaiting
    global carriersThroughTheSystem

    # Prints out a message that the drive just restarted and which carrier will be leaving the drive
    print("Drive " + str(drive) + " restarted, with carrier " + str(carrier))

    # Prints out state of carriers on each drive before the evaluation
    print("Before moving carriers ")
    print(driveXHasCarrier)

    # If this method is called because a carrier has been waiting to move to the next drive, then there may be the
    # possibility that in the meantime another carrier has entered the drive. So in this case the carrier doesn't leave
    # the drive.
    if drive == amountOfDrives or driveXHasCarrierWaiting[drive - 1 + 1] == 0:
        # The carrier leaves the drive, so the drive doesn't hold the carrier anymore
        driveXHasCarrier[drive - 1] = 0

    # Reset the last position of the carrier to 0
    lastPositionOfCarrier[carrier - 1] = 0

    # If the carrier is at the last drive, the iteration can be completed
    if drive == amountOfDrives:
        completeIteration(carrier)
        # If all carriers went through the drives, the iteration is complete and the iterationNumber is increased
        if carrier == AMOUNT_OF_CARRIERS:
            iterationNumber += 1

    # The carrier moves to the next drive; Checks if there is a "next" drive
    if drive < amountOfDrives:
        # If the next drive isn't empty, the carrier gets put on the waiting list (driveXHasCarrierWaiting)
        if driveXHasCarrier[drive - 1 + 1] != 0:
            # Print conflict message
            print("Carrier " + str(carrier) + " wants to go to drive " + str(drive + 1) + " ,but there is carrier " \
                  + str(driveXHasCarrier[drive - 1 + 1]) + " on there")
            # Put the carrier on the waiting list for the next drive
            driveXHasCarrierWaiting[drive - 1 + 1] = carrier
            # Print current waiting list
            print("Carriers waiting: " + str(driveXHasCarrierWaiting))
        else:
            # If the next drive is empty, the carrier moves to the next drive
            driveXHasCarrier[drive - 1 + 1] = carrier

    # If the current drive is drive 1, then a new carrier is pulled onto the drive 1
    if drive == 1:
        print("A new carrier gets pulled onto drive 1")

        # If all carriers already passed the system, the first one enters again
        if carriersThroughTheSystem >= AMOUNT_OF_CARRIERS:
            carriersThroughTheSystem = 1
        else:
            # Increase the number of carriers that are in the system
            carriersThroughTheSystem += 1

        # Put the new carrier onto the first drive
        driveXHasCarrier[drive - 1] = carriersThroughTheSystem

    # If the current drive isn't 1 and it has a carrier waiting to go on that drive, the drive before is being evaluated
    # so that the carrier that was waiting can go to the drive
    else:
        if driveXHasCarrierWaiting[drive - 1] != 0:
            print("Pulling carrier " + str(driveXHasCarrierWaiting[drive - 1]) + " to drive " + str(drive))
            # Calling evaluatingDriveReset for the drive before and the waiting carrier
            evaluateDriveReset(drive - 1, driveXHasCarrierWaiting[drive - 1])
            # Carrier is no longer waiting to go to the drive
            driveXHasCarrierWaiting[drive - 1] = 0

    # Prints out state of carriers on each drive after the evaluation
    print("After the carriers have moved ")
    print(driveXHasCarrier)


# If a carrier leaves the last drive, the data for the carrier is compressed, the CSV file is exported and
# the data is cleared
def completeIteration(carrier):
    # Compress the data for the
    # compressData(carrier)

    exportCSV(carrier)

    clearCarrierData(carrier)


# Compresses the data, so that only every X-th (KEEP_EVERY_X_ROW) is kept in the data
# Example: rows: 0,1,2,3,4,5,6 --> compressData with KEEP_EVERY_X_ROW == 2 --> rows: 0,2,4,6
def compressData(carrier):
    logging.info("Compressing data of carrier: " + str(carrier))

    # TODO: Not finished, see beginning of the script.
    # Select first and last relevant timestamp (with pos != 0) and only compress the sub selection from first to last
    '''
    print ("First before: 0")
    print ("Last before: " + str((carrierData.shape[2]) - 1))
    # Determine the first and last row of relevant timeStamps
    firstRow = findFirstRowInCarrierData(carrier)
    lastRow = findLastRowInCarrierData(carrier)

    print ("First after: " + str(firstRow))
    print ("Last after: " + str(lastRow))
    if firstRow != 0:
        # Copy all relevant time stamps to the top
        carrierData[carrier - 1][:, 0: (lastRow - firstRow)] = carrierData[carrier - 1][:, firstRow: lastRow]

        # Delete the rest of the timeStamps
        carrierData[carrier - 1][:, (lastRow - firstRow) + 1: lastRow] = 0

        # Update the currentPoisitionAtCarrierData which has now been moved up
        currentPositionAtCarrierData[carrier - 1] = lastRow
    '''
    # Iterates through all time stamps
    for i in range(0, int(currentPositionAtCarrierData[carrier - 1])):

        # Saves the first x numbers to row 0, then the second x numbers to row 1 and so on
        saveTo = int(i / KEEP_EVERY_X_ROW)

        # Write only data points that are being kept to the carrierData
        if int(i % KEEP_EVERY_X_ROW) == 0:
            carrierData[carrier - 1][0][saveTo] = carrierData[carrier - 1][0][i]
            carrierData[carrier - 1][1][saveTo] = carrierData[carrier - 1][1][i]
            carrierData[carrier - 1][2][saveTo] = carrierData[carrier - 1][2][i]
            carrierData[carrier - 1][3][saveTo] = carrierData[carrier - 1][2][i]
        else:
            # Test if saveTo doesn't equal the current i, so that the value at saveTo is not added to itself
            if saveTo != i:
                # Add the absolute energy to calculate average
                carrierData[carrier - 1][2][saveTo] = abs(carrierData[carrier - 1][2][saveTo]) + \
                                                      abs(carrierData[carrier - 1][2][i])

        # if the current row is bigger than what the last row will be after compression, delete it
        if i >= 1 + int((currentPositionAtCarrierData[carrier - 1] - 1) / float(KEEP_EVERY_X_ROW)):
            carrierData[carrier - 1][0][i] = 0
            carrierData[carrier - 1][1][i] = 0
            carrierData[carrier - 1][2][i] = 0
            carrierData[carrier - 1][3][i] = 0


# Exports the table of the carrier to a CSV file in the form time; posAbsolute; posOnDrive; energy
def exportCSV(carrier):
    # Creates the filename in the form Session_X_Carrier_X_Iteration_X.csv
    fileName = "Session_" + str(setConstants.SESSION) + "_Carrier_" + str(int(carrier)) + "_Iteration_" + \
               str(int(iterationNumber)) + ".csv"

    # Adds the relative file path to the name that the files are saved to /InitialData/
    fileName = os.path.abspath(os.path.join("CarrierData", fileName))

    # Finds the first relevant row (position != 0) in the carrier data
    firstRow = findFirstRowInCarrierData(carrier)

    # Finds the last relevant row (position != 0) in the carrier data
    lastRow = findLastRowInCarrierData(carrier)

    # Only selects the relevant sub selection from carrier data (without position == 0) to export to csv
    export = np.transpose(carrierData[carrier - 1][:, firstRow:lastRow])

    # Export carrier data with file name to csv file
    np.savetxt(fileName, export, fmt='%0.5f', delimiter=DATA_SEPARATOR, newline='\n',
               header='time;posAbsolute;energy;drive', footer='', comments='# ')

    # Write the filename to the console and the log file
    print("Exported: " + str(fileName))
    logging.info("Exported: " + str(fileName))


# Finds the first row of the array that will be exported as CSV, where pos and energy consumption != 0
def findFirstRowInCarrierData(carrier):
    if carrierData[carrier - 1][1][0] != 0:
        return 0

    lastRowWithZero = 0

    for i in range(0, int(carrierData.shape[2]) - 1):
        if (carrierData[carrier - 1][1][i] == 0):
            lastRowWithZero = i
        else:
            if lastRowWithZero >= (carrierData.shape[2]) - 1:
                return (carrierData.shape[2]) - 1
            else:
                return lastRowWithZero + 1

    print("Couldn't find first row.")
    return lastRowWithZero


# Finds the first row of the array that will be exported as CSV, where pos and energy consumption != 0
def findLastRowInCarrierData(carrier):
    if carrierData[carrier - 1][1][(carrierData.shape[2]) - 1] != 0:
        return (carrierData.shape[2]) - 1

    lastRowWithZero = (carrierData.shape[2]) - 1

    for i in range(0, int(carrierData.shape[2]) - 1):
        if (carrierData[carrier - 1][1][(carrierData.shape[2]) - 1 - i] == 0):
            lastRowWithZero = (carrierData.shape[2]) - 1 - i
        else:
            if lastRowWithZero <= 0:
                return 0
            else:
                return lastRowWithZero - 1

    print("Couldn't find last row.")
    return lastRowWithZero


# Clear the carrier data array for a certain carrier to all 0.0
def clearCarrierData(carrier):
    for i in range(0, int(carrierData.shape[2]) - 1):
        carrierData[carrier - 1][0][i] = 0
        carrierData[carrier - 1][1][i] = 0
        carrierData[carrier - 1][2][i] = 0
        carrierData[carrier - 1][3][i] = 0
    # Set the current position that is being filled to 0 so that the array can be filled again
    currentPositionAtCarrierData[carrier - 1] = 0


# Ensures enough space in the carrier data array for a certain carrier
def ensureEnoughSpaceInCarrierData(carrier):
    global carrierData
    # If the current position at the carrier data is equal to the size of the array, the array size is doubled
    if currentPositionAtCarrierData[carrier - 1] >= carrierData.shape[2]:
        extend = np.zeros((AMOUNT_OF_CARRIERS, 4, int(carrierData.shape[2])))
        carrierData = np.concatenate((carrierData, extend), axis=2)


# TODO: Refactoring of this def
# Renames the csv file headers to structure: (ms; energy1;...;energyX; pos1;...;posX) (X = Amount of Drives)
def modifyCSVFile(filename):
    # InputFileName und OutputFileName of CSV
    inputFileName = filename
    outputFileName = os.path.splitext(inputFileName)[0] + "_modified.csv"

    # Opens File
    with open(inputFileName, 'rb') as inFile, open(outputFileName, 'wb') as outfile:
        # defines reading file and writing file
        r = csv.reader(inFile, delimiter=setConstants.CSV_SEPARATOR)
        w = csv.writer(outfile, delimiter=setConstants.CSV_SEPARATOR)

        # Copys first row
        first_row = next(r)
        num_cols = len(first_row)

        # Initialize Array for new ColumnNames
        newColNames = []

        # Counter of Columns
        j = 0

        # Startposition of Positon Columns
        startPositonOfColumns = 0

        # Iterates the first row of the initial file and depending on the value writes columns into the file
        for i in first_row:
            # if j is zero
            if j == 0:
                newColNames.append("ms")
            # if column includes "iw4PowerCU" it's an energy sensor
            if "iw4PowerCU" in i:
                newColNames.append("energy" + str(j - 1))
            # if column includes "ExternalEncoderPosition" it's an position sensor
            if "ExternalEncoderPosition" in i:
                if startPositonOfColumns == 0:
                    startPositonOfColumns = j
                newColNames.append("position" + str(j - startPositonOfColumns))
                # counts the amount of drives.
                amountOfDrives = j - startPositonOfColumns

            j = j + 1

        # Skips the first row from the reader, the old header
        next(r, None)
        # Writes new header
        w.writerow(newColNames)

        # Copies the rest of reader
        for row in r:
            w.writerow(row)

        # Returns amountOfDrives
        return amountOfDrives


#########################################################
############# START OF SCRIPT ###########################
#########################################################
# TODO: Refactoring of this part
# Initialize Log-File
# Creates or loads Log DataProcessing.log
# Format of LogFile: mm/dd/yyyy hh:mm:ss PM LogMessage
logging.basicConfig(filename='dataProcessing.log', level=logging.INFO, format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

# Creates a TextFile "Running.txt" on Start to let writeCarrierDataToDataBase.py know that the script is still running
with open("Running.txt", "w") as text_file:
    text_file.write("Running")
    logging.info("compressInitialData.py now running. 'Running.txt' created.")

# Write all DATA_FILE_NAMES in an Array
for files in glob.glob("InitialData/*.csv"):
    DATA_FILE_NAMES.append(files)
logging.info("Found " + str(len(DATA_FILE_NAMES)) + " new files.")

# Checks if a File is added to DATA_FILE_NAMES. If not it is terminating the script
if not DATA_FILE_NAMES:
    print('No Files in Folder')
    # Removes Running.txt, so the simulator can also terminate
    os.remove("Running.txt")
    logging.info("Terminating compressInitialData.py. 'Running.txt' removed.")
    # Terminates the script
    sys.exit()

for fileName in DATA_FILE_NAMES:

    # Calls modifyCSVFile function
    amountOfDrives = modifyCSVFile(fileName)

    # Variables
    # Array that saves for every drive which carrier is on it
    driveXHasCarrier = np.zeros(amountOfDrives)
    # This is where all the data goes before exporting to CSV
    # carrierData[carrier number][time = 0, pos = 1, energy consumption = 2][position of array]
    carrierData = np.zeros((AMOUNT_OF_CARRIERS, 4, 100))
    # Here is stored in which row the last entry of carrier data was made for every carrier
    # (This could also be calculated by why not store it, since its used frequently)
    currentPositionAtCarrierData = np.zeros(AMOUNT_OF_CARRIERS)
    # Saves the last position on the drive of every carrier
    lastPositionOfCarrier = np.zeros(AMOUNT_OF_CARRIERS)
    # Number of complete runs through the system
    driveXHasCarrierWaiting = np.zeros(amountOfDrives)
    #
    iterationNumber = 0
    # The amount of carriers who entered drive 1 (Therefore starting with carrier 1) in the current run
    carriersThroughTheSystem = 1

    # DATA_PATH creates an OS independent file path to the data files that were input as string names
    # Initialize empty DATA_PATH array
    DATA_PATH = ["" for x in range(DATA_FILE_NAMES.__sizeof__())]

    # Set first data path
    # This is needed when the data is in a subfolder
    # DATA_PATH[0] = os.path.abspath(os.path.join("data", DATA_FILE_NAMES[0]))
    DATA_PATH[0] = os.path.abspath(DATA_FILE_NAMES[0])

    # First row of data frames
    initialData = pd.read_csv(os.path.splitext(fileName)[0] + "_modified.csv", DATA_SEPARATOR, low_memory=False,
                              header=0)
    #    Extracting the DriveNo of the first loaded File in DATA_PATH
    # Iterates each row and afterwards each drive
    #  Calls compressData with a pd.Series. The values are:
    # ms, No. of Drive, Energy Consmption, Position
    for index, row in initialData.iterrows():
        for drive in range(0, amountOfDrives):
            time = int(float(str(row['ms']).replace(',', '.')))
            position = float(str(row['position' + str(drive)]).replace(',', '.'))
            energy = float(str(row['energy' + str(drive)]).replace(',', '.'))
            processData(time, drive + 1, position, energy)
            # sleep(WAIT_TIME_IN_SECONDS)

    # Moves the processed data files to InitialDataArchive
    # Commented out for testing
    # os.rename(fileName, os.path.abspath(os.path.join("InitialDataArchive", os.path.basename(fileName))))
    # print ("Moving processed files to: " + os.path.abspath(os.path.join("CarrierData", os.path.basename(fileName))))
    # logging.info("Moving " + fileName + " to: " + os.path.abspath(os.path.join("InitialDataArchive", os.path.basename(fileName))))

# Removes the status.txt file after the end of the simulation and writes its status to log file
os.remove("Running.txt")
logging.info("Terminating compressInitialData.py. 'Running.txt removed.")
