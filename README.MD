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
