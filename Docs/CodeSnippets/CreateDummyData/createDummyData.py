import numpy as np
from scipy import interpolate
import os
# import setConstants to maintain all constants on one place
import setConstants
import logging

# a script to create dummy data -- preliminary version
# TODO: documentation, restructuring, bugfixes   

lineLength = setConstants.LINE_LENGTH
driveLength = setConstants.DRIVE_LENGTH
T1 = 100
T2 = T1 + 100
T3 = T2 + 100
endTime = T3
x = np.array([-20, 0, T1, T2, T3, T3 + 50])
y = np.array([0, 0, driveLength, 3 * driveLength, 4 * driveLength + 5, 4 * driveLength + 5])
spline = interpolate.UnivariateSpline(x, y, k=3, s=0)


# the function describe position/velocity/acceleration of
# carriers RELATIVE to their entry point

def positionFunction(time):
    return spline(time)


def velocityFunction(time):
    velocity = spline.derivative()
    return velocity(time)


def accelerationFunction(time):
    acceleration = spline.derivative(n=2)
    return acceleration(time)


def energyFunction(time, driveId):
    mass = 1
    return mass * velocityFunction(time) * accelerationFunction(time) + contaminationFunction(driveId)


def contaminationFunction(driveId):
    # add contamination here that depends on the drive
    return 0


class Carrier:
    entryTime = -1  # time when carriers enters line

    def __init__(self, entryTime, carrierId):
        self.entryTime = entryTime
        self.carrierId = carrierId

    def getPosition(self, time):
        # get position of this carrier with respect to the global time frame
        if time < self.entryTime:
            # carrier is not yet on the line
            return -1
        else:
            return positionFunction(time - self.entryTime)

    def getEnergy(self, time):
        # get energy of this carrier with respect to the global time frame
        if time < self.entryTime:
            return 0
        else:
            return energyFunction(time - self.entryTime, self.carrierId)


class Drive:
    # variables data store position and energy data
    drivePosition = 0  # position where the drive 'begins'

    def __init__(self, drivePosition, driveNumber):
        self.drivePosition = drivePosition
        self.data = np.zeros((endTime + 1, 3))
        self.driveNumber = driveNumber
        for time in range(endTime + 1):
            self.data[time, 0] = time

    def addPositionPoint(self, time, position, energy):
        self.data[time, 1] = position - self.drivePosition
        self.data[time, 2] = energy

    def export2Csv(self):

        # Creates the name of the file
        fileName = "Session_" + str(setConstants.SESSION) + "_Drive_" + str(self.driveNumber) + ".csv"

        # Adds the relative file path to the name that the files are saved to /InitialData/
        fileName = os.path.abspath(os.path.join("InitialData", fileName))

        print "Exporting ..."
        print fileName

        np.savetxt(fileName, self.data, fmt='%0.5f', delimiter=';', newline='\n',
                   header='time;position;energy', footer='', comments='# ')
        logging.info("Exported to file " + fileName)
        return


class Data:
    numberOfCarriers = 0
    numberOfDrives = 0
    driveLength = 0
    carriers = []
    drives = []

    def __init__(self, entryTimes, numberOfDrives, driveLength):
        self.driveLength = driveLength
        self.numberOfDrives = numberOfDrives
        self.numberOfCarriers = len(entryTimes)

        carrierId = 0
        for entryTime in entryTimes:
            self.carriers.append(Carrier(entryTime, carrierId))
            carrierId = carrierId + 1

        for driveNumber in range(numberOfDrives):
            self.drives.append(Drive(driveNumber * driveLength, driveNumber))

    def getDrive(self, position):
        # returns the drive to which the position belongs
        driveNumber = int(position / self.driveLength)
        if driveNumber >= self.numberOfDrives or position < 0:
            return None
        else:
            return self.drives[driveNumber]

    def createDummy(self):
        for time in range(endTime + 1):
            for carrier in self.carriers:
                # for each carrier get the drive that it is on
                position = carrier.getPosition(time)
                drive = self.getDrive(position)
                if drive is not None:
                    drive.addPositionPoint(time, position, carrier.getEnergy(time))

    def export2Csv(self):
        for drive in self.drives:
            drive.export2Csv()

# Start of script


# Initialize Log-File
# Creates or loads Log DataProcessing.log
# Format of LogFile: mm/dd/yyyy hh:mm:ss PM LogMessage
logging.basicConfig(filename='dataProcessing.log',level=logging.INFO,format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

logging.info("createDummyData.py starting to create dummy data.")

d = Data([5, 150, 300, 500, 700], 5, 200)

d.createDummy()
d.export2Csv()

logging.info("createDummyData.py terminating.")

