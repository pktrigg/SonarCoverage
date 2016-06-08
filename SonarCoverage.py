#name:          SonarCoverage.py
#created:       May 2016
#by:            p.kennedy@fugro.com
#description:   This script will compute a nadir gap outline around a trackplot from the Deeptow sonar in an efficient manner
# It will use an algorithm as agreed between Fugro and ATSB on the definition of the altitude/gap region
#notes:         See main at end of script for example how to use this
#based on XTF version 26 18/12/2008
#version 1.00

#DONE
# tried to update teh readme file
# added -odix to control the output folder
# create a WGS84 prj file.  Good for ArcMap, but not always correct if we have an east/north XTF FileExistsError
# added support for xtf wildcards
# added support for splitting polygons based on minimum gap width
# added support for -o output file name, or default, which is the first input file to be processed.  This means for processing 1 file you do not need to specify the output.
# This script will compute a nadir gap outline around a trackplot from the Deeptow sonar in an efficient manner
# designed to handle both geographic and grid positions seamlessly
# creates a shapefile of points representing nadir sensor position
# creates a coverage polygon representing the slant range setting of the sonar
# creates a nadir gap polygon representing the null area under the sidescan which is poor quality data.
# uses the sensor position, altitude and heading rather than computing CMG heading which is a bit wobbly when navigation data has duplicate points
# initial implementation

import math
import argparse
import sys
import shapefile
import csv
import pyXTF
import geodetic
import os
from glob import glob
# from pyproj import Proj, transform
import time

def calcGap(altitude):
    return (altitude * 0.70) / 2.0
    
def isValidGap(altitude, gap):
    MINIMUMGAP = 50
    if gap < MINIMUMGAP:
        return False
    return True

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

    start_time = time.time() # time the process
    parser = argparse.ArgumentParser(description='Read XTF file and create either a coverage or Nadir gap polygon.')
    # parser.add_argument('-c', action='store_true', default=False, dest='createCoveragePolygon', help='-c compute a polygon across the entire sonar region, ie COVERAGE')
    parser.add_argument('-n', action='store_true', default=False, dest='createNadirPolygon', help='-n compute a polygon across the NADIR region')
    parser.add_argument('-i', dest='inputFile', action='store', help='-i <filename> input sonar XTF filename')
    parser.add_argument('-o', dest='outputFile', action='store', help='-o <filename> output shape filename. Do not provide file extension. It will be added for you  [default = Nadir_pg]')
    parser.add_argument('-odix', dest='outputFolder', action='store', help='-odix <folder> output folder to store shape files.  If not specified, the files will be alongside the input XTF file')
    
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
   
    if args.outputFolder == None:
        firstFile = glob(args.inputFile)[0]
        args.outputFolder = os.path.abspath(os.path.join(firstFile, os.pardir))

    shp_pt = shapefile.Writer(shapefile.POINT)
    # for every record there must be a corresponding geometry.
    shp_pt.autoBalance = 1
    shp_pt.field('XTFFile', 'C', 255)
    shp_pt.field('ALTITUDE', 'C',255)
    
    shp_pg = shapefile.Writer(shapefile.POLYGON)
    shp_pg.autBalance = 1 #ensures gemoetry and attributes match
    shp_pg.field('XTFFile', 'C', 255)

    for filename in glob(args.inputFile):
        if args.createNadirPolygon:       
            computeNadir(filename, shp_pt, shp_pg)
        else:
            print ("option not yet implemented!.  Try '-n' to compute nadir gaps")
            exit (0)

    if args.outputFile is None:
        baseName = os.path.basename(os.path.splitext(glob(args.inputFile)[0])[0])
        pointFile = os.path.join(args.outputFolder, baseName + "_pt")
        # pointFile = args.outputFolder + baseName + "_pt"
        polyFile = os.path.join(args.outputFolder, baseName + "_pg")
        # polyFile = baseName + "_pg"
    else:
        pointFile = args.outputFile + "_pt"
        polyFile = args.outputFile + "_pg"

    print("saving shapefile...")
    #Save shapefiles
    if len(shp_pt.shapes()) > 0:
        shp_pt.save(pointFile)
    else:
        print ("Nothing to save in points shape file")
    if len(shp_pg.shapes()) > 0:
        shp_pg.save(polyFile)
        print("save complete.")
    else:
        print ("Nothing to save in polygon shape file")

    # now write out the prj file of spatial reference, so we can open in ArcMap
    prj = open(polyFile + ".prj", "w")
    prj.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')
    # epsg = getWKT_PRJ("4326")
    # prj.write(epsg)
    prj.close() 
    prj = open(pointFile + ".prj", "w")
    prj.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')
    # epsg = getWKT_PRJ("4326")
    # prj.write(epsg)
    prj.close() 
    
    print("--- %s seconds ---" % (time.time() - start_time)) # print the processing time.

    return (0)

def savePolygon(leftSide, rightSide, shp_pg, shp_pt, fileName):
    
    #now build the outline polygon and store to shapefile
    outline = []
    print("merging polygon vertices...")
    for pt in leftSide:
        outline.append(pt)
    rightSide.reverse()
    for pt in rightSide:
        outline.append(pt)
        
    # print("creating geometry...")
    if len(outline) > 2:    
        shp_pg.poly(parts=[outline]) #write the geometry
        shp_pg.record(fileName)              
        leftSide.clear()
        rightSide.clear()
    # else:
        # print("oops, no geometry!!")
def computeNadir(filename, shp_pt, shp_pg):

    leftSide = [] #storage for the left side of the nadir polygon
    rightSide = [] #storage for the left side of the nadir polygon.  This will be added to teh right side to close the polygon
    prevEast = 0 

    #   open the trackplot file for reading 
    print ("Opening file:", filename)
    r = pyXTF.XTFReader(filename)
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
        shp_pt.record(filename, str(currAltitude))
 
        # compute the range based on the user requesting either coverage polygons or nadir gap polygins
        currRange = calcGap(currAltitude)

        if isValidGap(currAltitude, currRange) == False:
            if len(leftSide) > 2:
                savePolygon(leftSide, rightSide, shp_pg, shp_pt, filename)
            continue

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

        if pingHdr.PingNumber % 500 == 0:
            print ("Ping: %f, X: %f, Y: %f, A: %f Range: %f Bearing %f" % (pingHdr.PingNumber, currEast, currNorth, currAltitude, currRange, currBearing))               
    
    print("Complete reading XTF file :-)")

    savePolygon(leftSide, rightSide, shp_pg, shp_pt, filename)

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
