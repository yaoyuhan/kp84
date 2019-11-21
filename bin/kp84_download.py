#!/usr/bin/env python

import optparse
import subprocess
import numpy as np

def parse_commandline():
    """
    Parse the options given on the command-line.
    """
    parser = optparse.OptionParser()

    parser.add_option("--outputDir",default="/Users/yuhanyao/Desktop")
    parser.add_option("--downloadType",default="data")
    parser.add_option("--objname",default="14min")
    parser.add_option("--day",default="20190427")
    parser.add_option("--filepath",default="20190427/14min/14min_1_g_20190427_024928.024522")
    parser.add_option("-n",default=-1,type=int)

    opts, args = parser.parse_args()

    return opts

# Parse command line
opts = parse_commandline()
downloadType = opts.downloadType
objname = opts.objname
day = opts.day
outputDir = opts.outputDir
filepath = opts.filepath

if downloadType == "data":
    ls_command = "ssh -p 22221 kped@140.252.53.120 ls /Data/%s/%s*.fits.fz" % (day, objname)
    result = subprocess.run(ls_command.split(" "), stdout=subprocess.PIPE)
    fitsfiles = list(filter(None,result.stdout.decode().split("\n")))

    nums = []
    for fitsfile in fitsfiles:
        fitsfileSplit = fitsfile.replace(".fits.fz","").replace(".fits","").split("_")
        try:
            num = int(fitsfileSplit[-1])
        except:
            num = -1
        nums.append(num)

    idx = np.where(np.array(nums) == opts.n)[0]
    for ii in idx:
        filename = fitsfiles[ii]

        scp_command = "scp -P 22221 kped@140.252.53.120:%s %s" % (filename, outputDir) 
        result = subprocess.run(scp_command.split(" "), stdout=subprocess.PIPE)

elif downloadType == "analysis":
    fullpath = "/home/roboao/Michael/kp84/output/%s/%s" % (day, filepath)

    scp_command = "scp -P 22220 roboao@140.252.53.120:%s/movie/movie.mpg %s/movie_%s.mpg" % (fullpath, outputDir, filepath.replace("/","_"))
    #result = subprocess.run(scp_command.split(" "), stdout=subprocess.PIPE)

    scp_command = "scp -P 22220 roboao@140.252.53.120:%s/forced.dat %s/forced_%s.dat" % (fullpath, outputDir, filepath.replace("/","_"))
    result = subprocess.run(scp_command.split(" "), stdout=subprocess.PIPE)

    scp_command = "scp -P 22220 roboao@140.252.53.120:%s/mag_relative_forced.pdf %s/mag_relative_forced_%s.pdf" % (fullpath, outputDir, filepath.replace("/","_"))
    result = subprocess.run(scp_command.split(" "), stdout=subprocess.PIPE)

    scp_command = "scp -P 22220 roboao@140.252.53.120:%s/flux_relative_forced.pdf %s/flux_relative_forced_%s.pdf" % (fullpath, outputDir, filepath.replace("/","_"))
    result = subprocess.run(scp_command.split(" "), stdout=subprocess.PIPE)
else:
    print("downloadType must be data or analysis")
