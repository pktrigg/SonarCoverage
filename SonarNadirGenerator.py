import math
import argparse
import sys
import shapefile
import csv

# This script will compute a nadir gap outline around a trackplot from the Deeptow sonar in an efficient manner
# It will use an algorithm as agreed between Fugro and ATSB on the definition of the altitude/gap region

def calcGap(altitude):
    return (altitude * 0.33) + 12
    

# from: http://mathforum.org/library/drmath/view/62034.html
def calculateRangeBearingFromPosition(easting1, northing1, easting2, northing2):
    """given 2 east, north, pairs, compute the range and bearing"""

    dx = easting2-easting1
    dy = northing2-northing1

    bearing = 90 - (180/math.pi)*math.atan2(northing2-northing1, easting2-easting1)
    return (math.sqrt((dx*dx)+(dy*dy)), bearing)


# taken frm http://gis.stackexchange.com/questions/76077/how-to-create-points-based-on-the-distance-and-bearing-from-a-survey-point
def calculatePositionFromRangeBearing(easting, northing, distance, bearing):
    """given an east, north, range and bearing, compute a new coordinate on the grid"""
    point =   (easting, northing)
    angle =   90 - bearing
    bearing = math.radians(bearing)
    angle =   math.radians(angle)

    # polar coordinates
    dist_x = distance * math.cos(angle)
    dist_y = distance * math.sin(angle)

    xfinal = point[0] + dist_x
    yfinal = point[1] + dist_y

    # direction cosines
    cosa = math.cos(angle)
    cosb = math.cos(bearing)
    xfinal = point[0] + (distance * cosa)
    yfinal = point[1] + (distance * cosb)
    
    return [xfinal, yfinal]

def main():

    MINIMUM_NADIR = 100 #used to control when to make a polygon.  A nadir gap less than this will NOT be created
    
    parser = argparse.ArgumentParser(description='Compute sonar Nadir region from Position, Altiude ASCII file.')
    parser.add_argument('-i', dest='inputFile', action='store', help='-i <filename> input filename in ASCI Easting,Northing,Altidude comma separated format')
    args = parser.parse_args()
   

    #   open the trackplot file for reading 
    f = open(args.inputFile)
    reader = csv.reader(f, delimiter=',')
    
    row = next(reader)
    prevEast = float(row[0])
    prevNorth = float(row[1])
    prevAltitude = float(row[2])


    shp_pt = shapefile.Writer(shapefile.POINT)
    # for every record there must be a corresponding geometry.
    shp_pt.autoBalance = 1
    shp_pt.field('Altitude')
    
    shp_pg = shapefile.Writer(shapefile.POLYLINE)
    shp_pg.autBalance = 1 #ensures gemoetry and attributes match
    shp_pg.field('Altitude')
    # shp_pg.field('ALTITUDE_FLD')

    leftSide = [] #storage for the left side of the nadir polygon
    rightSide = [] #storage for the left side of the nadir polygon.  This will be added to teh right side to close the polygon
    
    for row in reader:
        currEast = float(row[0])
        currNorth = float(row[1])
        currAltitude = float(row[2])        
        currRange, currBearing = calculateRangeBearingFromPosition(prevEast, prevNorth, currEast, currNorth)
               
        shp_pt.point(currEast,currNorth)
        # add attribute data
        id = 0
        target = ""
        date = ""
        shp_pt.record(currAltitude)               
        
        # compute the left side and add to a list
        leftEast, leftNorth = calculatePositionFromRangeBearing(currEast, currNorth, currRange, currBearing - 90.0)
        leftSide.append([leftEast,leftNorth])
        
        # compute the right side and add to a list
        rightEast, rightNorth = calculatePositionFromRangeBearing(currEast, currNorth, currRange, currBearing + 90.0)
        rightSide.append([rightEast,rightNorth])
                
        shp_pg.poly(parts=[leftSide]) #write the geometry
        shp_pg.record(currAltitude)              
        
        # shp_pg.record()
        
    #Save shapefiles
    shp_pt.save('shapefiles/test/point')
    shp_pg.save('shapefiles/test/polygon')

    # w.poly(parts=[[[1,3],[5,3]]], shapeType=shapefile.POLYLINE)
    # w.field('FIRST_FLD','C','40')
    # w.field('SECOND_FLD','C','40')
    # w.record('First','Line')
    # w.record('Second','Line')
    # w.save('shapefiles/test/line')

if __name__ == "__main__":
    main()

    # east, north = calculatePositionFromRangeBearing(1000.00, 1000, 10, 0)
    # calculatePositionFromRangeBearing(1000.00, 1000, 10, 90)
    # calculatePositionFromRangeBearing(1000.00, 1000, 10, 180)
    # calculatePositionFromRangeBearing(1000.00, 1000, 10, 270)
