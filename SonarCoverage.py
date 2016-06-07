#name:          SonarCoverage.py
#created:       May 2016
#by:            p.kennedy@fugro.com
#description:   This script will compute a nadir gap outline around a trackplot from the Deeptow sonar in an efficient manner
# It will use an algorithm as agreed between Fugro and ATSB on the definition of the altitude/gap region
#notes:         See main at end of script for example how to use this
#based on XTF version 26 18/12/2008
#version 1.00

#DONE
#initial implementation
# This script will compute a nadir gap outline around a trackplot from the Deeptow sonar in an efficient manner
# designed to handle both geographic and grid positions seamlessly
# creates a shapefile of points representing nadir sensor position
# creates a coverage polygon representing the slant range setting of the sonar
# creates a nadir gap polygon representing the null area under the sidescan which is poor quality data.
# uses the sensor position, altitude and heading rather than computing CMG heading which is a bit wobbly when navigation data has duplicate points
    

import math
import argparse
import sys
import shapefile
import csv
import pyXTF
import geodetic


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
    
    parser = argparse.ArgumentParser(description='Read XTF file and create either a coverage or Nadir gap polygon.')
    parser.add_argument('-c', action='store_true', default=False, dest='createCoveragePolygon', help='-c compute a polygon across the entire sonar region, ie COVERAGE')
    parser.add_argument('-n', action='store_true', default=False, dest='createNadirPolygon', help='-n compute a polygon across the NADIR region')
    parser.add_argument('-i', dest='inputFile', action='store', help='-i <filename> input filename in ASCI Easting,Northing,Altidude comma separated format')
    
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
   
    shp_pt = shapefile.Writer(shapefile.POINT)
    # for every record there must be a corresponding geometry.
    shp_pt.autoBalance = 1
    shp_pt.field('Altitude')
    
    shp_pg = shapefile.Writer(shapefile.POLYGON)
    shp_pg.autBalance = 1 #ensures gemoetry and attributes match
    shp_pg.field('Altitude')
    # shp_pg.field('ALTITUDE_FLD')

    leftSide = [] #storage for the left side of the nadir polygon
    rightSide = [] #storage for the left side of the nadir polygon.  This will be added to teh right side to close the polygon
    prevEast = 0 

    #   open the trackplot file for reading 
    print ("Opening file:", args.inputFile)
    r = pyXTF.XTFReader(args.inputFile)
    while r.moreData():
        pingHdr = r.readPing()
        if prevEast == 0:
            prevEast = pingHdr.SensorXcoordinate
            prevNorth = pingHdr.SensorYcoordinate
            prevAltitude = pingHdr.SensorPrimaryAltitude
            continue
            
        currEast = pingHdr.SensorXcoordinate
        currNorth = pingHdr.SensorYcoordinate
        currAltitude = pingHdr.SensorPrimaryAltitude

        #add ping position to a shape file for QC purposes
        shp_pt.point(currEast,currNorth)
        shp_pt.record(currAltitude)
 
        # compute the range based on the user requesting either coverage polygons or nadir gap polygins
        if args.createNadirPolygon:       
            currRange = calcGap(currAltitude)
        else:
            currRange = pingHdr.pingChannel[0].SlantRange

        
        if (pingHdr.SensorXcoordinate < 180) & (pingHdr.SensorYcoordinate < 90):
            #compute with geographical data
            # rng, currBearing, backBearing = geodetic.vinc_dist(prevNorth, prevEast, currNorth, currEast )
            currBearing = pingHdr.SensorHeading
            # compute the left side and add to a list
            leftSideNorthing, leftSideEasting, alpha21 = geodetic.vincentyDirect(currNorth, currEast, currBearing - 90, currRange)
            leftSide.append([leftSideEasting,leftSideNorthing])
            # shp_pt.point(leftSideEasting,leftSideNorthing)
            # shp_pt.record(currAltitude)

            # compute the right side and add to a list 
            rightSideNorthing, rightSideEasting, alpha21 = geodetic.vincentyDirect(currNorth, currEast, currBearing + 90, currRange)
            rightSide.append([rightSideEasting,rightSideNorthing])
            # shp_pt.point(rightSideEasting,rightSideNorthing)
            # shp_pt.record(currAltitude)  
        else:
            # compute with grid data
            # calculate the heading instead of using the gyro field. it is not always present! 
            rng, currBearing = calculateRangeBearingFromPosition(prevEast, prevNorth, currEast, currNorth)
            currBearing = pingHdr.SensorHeading
            # compute the left side and add to a list
            leftSideEasting, leftSideNorthing = calculatePositionFromRangeBearing(currEast, currNorth, currRange, currBearing - 90.0)
            leftSide.append([leftSideEasting,leftSideNorthing])
            # shp_pt.point(leftSideEasting,leftSideNorthing)
            # shp_pt.record(currAltitude)
            
            # compute the right side and add to a list
            rightSideEasting, rightSideNorthing = calculatePositionFromRangeBearing(currEast, currNorth, currRange, currBearing + 90.0)
            rightSide.append([rightSideEasting,rightSideNorthing])
            # shp_pt.point(rightSideEasting,rightSideNorthing)
            # shp_pt.record(currAltitude)  
        
        prevEast = currEast
        prevNorth = currNorth
        prevAltitude = currAltitude

        if pingHdr.PingNumber % 100 == 0:
            print ("Ping: %f, X: %f, Y: %f, A: %f Range: %f Bearing %f" % (pingHdr.PingNumber, currEast, currNorth, currAltitude, currRange, currBearing))               
    
    print("Complete reading XTF file :-)")
    #now build the outline polygon and store to shapefile
    outline = []
    print("merging polygon vertices...")
    for pt in leftSide:
        outline.append(pt)
    rightSide.reverse()
    for pt in rightSide:
        outline.append(pt)
        
    print("creating geometry...")
        
    shp_pg.poly(parts=[outline]) #write the geometry
    shp_pg.record(currAltitude)              
    leftSide.clear()
    rightSide.clear()
            
    print("saving shapefile...")
    #Save shapefiles
    shp_pt.save('shapefiles/test/point')
    shp_pg.save('shapefiles/test/polygon')
    print("save complete.")

    # w.poly(parts=[[[1,3],[5,3]]], shapeType=shapefile.POLYLINE)
    # w.field('FIRST_FLD','C','40')
    # w.field('SECOND_FLD','C','40')
    # w.record('First','Line')
    # w.record('Second','Line')
    # w.save('shapefiles/test/line')

def isHeader(row):
    for word in row:
        if "#" in word: #skip headers
            return True
    return False

if __name__ == "__main__":
    main()

    # east, north = calculatePositionFromRangeBearing(1000.00, 1000, 10, 0)
    # calculatePositionFromRangeBearing(1000.00, 1000, 10, 90)
    # calculatePositionFromRangeBearing(1000.00, 1000, 10, 180)
    # calculatePositionFromRangeBearing(1000.00, 1000, 10, 270)
