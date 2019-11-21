#!/usr/bin/env python
import os, optparse, glob, sys
import numpy as np
from copy import deepcopy
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import sigma_clipped_stats
from scipy.ndimage import median_filter
#from astropy.visualization import SqrtStretch, LogStretch
#from astropy.visualization.mpl_normalize import ImageNormalize
from skimage.transform import downscale_local_mean

import warnings
from photutils import DAOStarFinder

sys.path.append("/home/roboao/Michael/kp84/")
from citizen.reduction_utils import filter2filtstr, stack_shifted_frames

#import matplotlib
#import matplotlib.pyplot as plt
#from matplotlib.ticker import NullLocator
#fs = 14
#matplotlib.rcParams.update({'font.size': fs})


def parse_commandline():
    """
    Parse the options given on the command-line.
    """
    parser = optparse.OptionParser()
    parser.add_option("--day",default="20180923")
    opts, args = parser.parse_args()
    return opts

# Parse command line
opts = parse_commandline()
KPED_data = "/Data3/data"
setupDir = "/Data3/archive_kped/data/reductions/"
day = opts.day

outputDir = os.path.join(setupDir,day)

print ("")
print ("===============================")
print ("Setup Pre-processing Directory!")
print ("===============================")
print ("")

dataDir = os.path.join(KPED_data,day)
filenames = glob.glob('%s/*.fits'%dataDir) + glob.glob('%s/*.fits.fz'%dataDir)

if len(filenames)==0:
    print ("Oops! No raw data exist at %s"%dataDir)
    exit(0)
    
print ("Making output directory...")
if not os.path.isdir(outputDir):
    os.makedirs(outputDir)
    
print ("Copy all files into output directory...")
for filename in filenames:
    filenameSplit = filename.split('/')    
    outfile = "%s/%s"%(outputDir,filenameSplit[-1])
    if not os.path.isfile(outfile):
        cp_command = "cp %s %s"%(filename,outputDir)
        os.system(cp_command)

print ("Getting objects...")
filenames = glob.glob('%s/*.fits'%outputDir) + glob.glob('%s/*.fits.fz'%dataDir)
objs = []
for filename in filenames:
    filenameSplit = filename.split('/')
    filenameSplit = filenameSplit[-1].split('_')
    if filenameSplit[0] == "kped":
        #obj = "%s_%s_%s"%(filenameSplit[0],filenameSplit[1],filenameSplit[2])
        obj = "%s"%(filenameSplit[3]) 
    elif filenameSplit[0] == "bias":
        # bias is only taken under mode 0, bias_0_*.fits
        obj = "%s_%s"%(filenameSplit[0], filenameSplit[1])
    elif filenameSplit[0] == "flat":
        # flat is named as flat_filter_*.fits
        obj = "%s_%s"%(filenameSplit[0], filenameSplit[1])
    elif filenameSplit[0] == "dark":
        # dark_amplifiermode*.fits
        obj = "%s_%s"%(filenameSplit[0], filenameSplit[1])
    if obj not in objs:
        objs.append(obj)

# fid = open('run_analysis.sh','w')
print ("Setting pre-processing directory...")
for obj in objs:
    #notTransient = "fits.fz" in fitsfiles[0]
    objsplit = obj.split("_")
    if objsplit[0] in ["flat", "bias", "dark"]:
        folderName = "%s/%s/%s"%(outputDir,objsplit[0],obj)
        folderName_raw = "%s/raw"%(folderName)
        fitsfiles = sorted(glob.glob('%s/%s_*.fit*'%(outputDir,obj)))
    else:   
        folderName = "%s/%s"%(outputDir,objsplit[0])
        folderName_raw = "%s/raw"%(folderName)
        fitsfiles = sorted(glob.glob('%s/*%s*.fit*'%(outputDir,obj)))
    print (folderName)
    if not os.path.isdir(folderName_raw):
        os.makedirs(folderName_raw)
    if objsplit[0] in ["flat", "bias", "dark"]:
        mv_command = "mv %s/%s_*.fit* %s"%(outputDir,obj,folderName_raw)
    else:
        mv_command = "mv %s/*%s*.fit* %s"%(outputDir,obj,folderName_raw)
        #fid.write("python kp84_photometric_reduction --dataDir %s --outputDir ../output/%s/%s"%(folderName,day,obj)+\
        #          " --doPlots --doForcedPhotometry --doDifferential\n")
    os.system(mv_command) 
#fid.close()

print ("Unpacking object files...")
for obj in objs:
    #notTransient = "fits.fz" in fitsfiles[0]
    objsplit = obj.split("_")
    if objsplit[0] not in ["flat", "bias", "dark"]:
        folderName = "%s/%s"%(outputDir,objsplit[0])
        folderName_raw = "%s/raw"%(folderName)
        fzfiles = glob.glob('%s/*.fits.fz'%folderName_raw)
        for fzfile in fzfiles:
            system_command = 'funpack %s'%fzfile
            os.system(system_command)
        for fzfile in fzfiles:
            system_command = 'rm %s'%fzfile
            os.system(system_command)

# give permission
chmod_command = "chmod -R 777 %s"%outputDir
os.system(chmod_command)


def get_median_frame_from_files(biasFolder):
    biasList = sorted(glob.glob(os.path.join(biasFolder,'*.fit*')))
    nx = fits.open(biasList[0])[1].data.shape[0]
    ny = nx
    numBiasFiles = len(biasList)
    biasImages = np.zeros((ny, nx, numBiasFiles))
    for i in range(numBiasFiles):
        HDUList = fits.open(biasList[i])     # Open the file
        biasImages[:,:,i] = HDUList[1].data  # Load the data into the appropriate layer
        HDUList.close()                      # Close the file
    masterBias = np.median(biasImages, axis=2)
    # if nx==1024:
    #    masterBias = downscale_local_mean(masterBias, (2,2))
    hdu = fits.PrimaryHDU(1)
    hdul = fits.HDUList([hdu])
    hdul[0].data = masterBias
    return hdul


def get_median_frame_from_cubes(darkFolder):
    darkfile = sorted(glob.glob(os.path.join(darkFolder,'*.fit*')))[0]
    nx = fits.open(darkfile)[1].data.shape[0]
    ny = nx
    HDUList = fits.open(darkfile) 
    numDarkFiles = len(HDUList)-1
    darkImages = np.zeros((ny, nx, numDarkFiles))
    for i in range(numDarkFiles):
        ii = i+1
        darkImages[:,:,i] = HDUList[ii].data 
    HDUList.close()          
    masterDark = np.median(darkImages, axis=2)
    #if nx==1024:
    #    masterDark = downscale_local_mean(masterDark, (2,2))
    hdu = fits.PrimaryHDU(1)
    hdul = fits.HDUList([hdu])
    hdul[0].data = masterDark
    return hdul


def get_master_flat(flatFolder, dark0frame):
    flatList = sorted(glob.glob(os.path.join(flatFolder,'*.fit*')))
    nx = fits.open(flatList[0])[1].data.shape[0]
    ny = nx
    numFlatFiles = len(flatList)
    flatImages = np.zeros((ny, nx, numFlatFiles))
    for i in range(numFlatFiles):
        HDUList = fits.open(flatList[i])     # Open the file
        data = np.array(HDUList[1].data, dtype = float)  # Load the data into the appropriate layer
        HDUList.close()                      # Close the file
        # Bias-subtract, normalize, and add to the array layer
        data -= dark0frame
        normfactor = np.median(data)
        # print(normfactor)
        flatImages[:,:,i] = data / normfactor
        
    masterFlat = np.median(flatImages, axis = 2)
    #plt.imshow(masterFlat)
    #plt.colorbar()
    hdu = fits.PrimaryHDU(1)
    hdul = fits.HDUList([hdu])
    hdul[0].data = masterFlat
    return hdul


print ("")
print ("=====================================")
print ("Creating Master Bias, Dark, and Flat!")
print ("=====================================")
print ("")
print ("Creating Master Bias file...")
obj = "bias_0"
biasFolder = "%s/bias/%s/raw"%(outputDir, obj) # bias frames subdirectory
hdul = get_median_frame_from_files(biasFolder)
hdul.writeto("%s/bias/%s/bias.fits"%(outputDir, obj), overwrite=True)
print ("  bias.fits")
# bias0frame = fits.open("%s/bias/%s/bias.fits"%(outputDir, "bias_0"))[0].data
print ("Creating Master Dark file...")
for obj in objs:
    if obj[:4]=="dark":
        darkFolder = "%s/dark/%s/raw"%(outputDir, obj) # dark frames subdirectory
        if obj=="dark_0":
            hdul = get_median_frame_from_files(darkFolder)
        else:
            hdul = get_median_frame_from_cubes(darkFolder)
        hdul.writeto("%s/dark/%s/%s.fits"%(outputDir, obj, obj), overwrite=True)
        print ("  %s.fits"%obj)
dark0frame = fits.open("%s/dark/%s/%s.fits"%(outputDir, "dark_0", "dark_0"))[0].data
print ("Creating Master Flat file...")
for obj in objs:
    if obj[:4]=="flat":
        flatFolder = "%s/flat/%s/raw"%(outputDir, obj) # flat frames subdirectory
        hdul = get_master_flat(flatFolder, dark0frame)
        hdul.writeto("%s/flat/%s/%s.fits"%(outputDir, obj, obj), overwrite=True)
        print ("  %s.fits"%obj)

print ("")
print ("===========================")
print ("Correct for Science Images!")
print ("===========================")
print ("")
for obj in objs:
    objsplit = obj.split("_")
    if objsplit[0] in ["flat", "bias", "dark"]:
        continue
    print ("%s"%obj)
    folderName = "%s/%s"%(outputDir,obj)
    folderName_raw = "%s/raw"%(folderName)
    folderName_processing = "%s/processing"%(folderName)
    if not os.path.isdir(folderName_processing):
        os.makedirs(folderName_processing)
    fitsfiles = sorted(glob.glob('%s/*.fit*'%(folderName_raw)))
    for i in range(len(fitsfiles)):
        flatflag = 1
        fitsfile = fitsfiles[i]
        filename = fitsfile.split("/")[-1].split(".fit")[0]
        procfile = "%s/%s_proc.fits"%(folderName_processing,filename)
        print ("    %s"%filename)
        # Read in the FITS data.
        HDUList = fits.open(fitsfile)
        primaryHeader = HDUList[0].header
        myfilter = primaryHeader["FILTER"]
        filtstr = filter2filtstr(myfilter)
        nxdata = HDUList[1].data.shape[0]
        modenum = primaryHeader["MODE_NUM"]
        if nxdata == 512:
            if modenum <=5 :
                print ("    Old files MODE_NUM = %d is wrong -- manually change modenum to 9"%modenum)
                print ("    Do not apply flat field")
                modenum = 9
                flatflag = 0
        darkfile = "%s/dark/dark_%d/dark_%d.fits"%(outputDir, modenum, modenum)
        masterDark = fits.open(darkfile)[0].data
        flatfile = "%s/flat/flat_%s/flat_%s.fits"%(outputDir, filtstr, filtstr)
        masterFlat = fits.open(flatfile)[0].data
        nframes = len(HDUList)-1
        procHDU = deepcopy(HDUList)
        if nxdata < masterFlat.shape[0]:
            masterFlat = downscale_local_mean(masterFlat, (2,2))
        for j in range(nframes):
            jj = j+1
            # Correct for the bias and flats here
            data = HDUList[jj].data
            if flatflag == 1:
                procHDU[jj].data = (data - masterDark) / masterFlat
            else:
                procHDU[jj].data = (data - masterDark)
        if flatflag == 1:
            procHDU[0].header.add_history('Dark corrected and flat-fielded') # Add a note to the header
        else:
            procHDU[0].header.add_history('Dark corrected')
        # Write the reduced frame to disk
        procHDU.writeto(procfile, overwrite=True)


print ("")
print ("=====================================================")
print ("Preparing for astrometry runs: select the best frame!")
print ("=====================================================")
print ("")


def get_n_source(data, subtract_median = False, return_data = False):
    nx = data.shape[0]
    if subtract_median ==True:
        median_size = 40
        data_median = np.asfarray(median_filter(data, size=(median_size, median_size)))
        data -= data_median
    mean, median, std = sigma_clipped_stats(data, sigma=3.0)  
    daofind = DAOStarFinder(fwhm=3.0, threshold=5.*std)  
    try:
        warnings.filterwarnings('ignore', category=UserWarning, append=True)
        sources = daofind(data - median)  
        ix = (sources["xcentroid"]>10)&(sources["xcentroid"]<nx-10)&(sources["ycentroid"]>10)&(sources["ycentroid"]<nx-10)
        sources = sources[ix]
        n = len(sources)
    except Exception:
        n = 0
    if return_data == False:
        return n
    else:
        return n, data


fid = open('run_astrometry.sh','w')

# get the best frame in each fits cubes -- to be used to solve the astrometry
npool = 30
subtract_median = False

for obj in objs:
    objsplit = obj.split("_")
    if objsplit[0] in ["flat", "bias", "dark"]:
        continue
    print ("Getting finding chart for %s..."%obj)
    folderName = "%s/%s"%(outputDir,obj)
    folderName_processing = "%s/processing"%(folderName)
    folderName_wcs = "%s/wcs"%(folderName)
    folderName_upload = "%s/upload"%(folderName)
    fitsfiles = sorted(glob.glob('%s/*.fit*'%(folderName_processing)))
    if not os.path.isdir(folderName_wcs):
        os.makedirs(folderName_wcs)
    if not os.path.isdir(folderName_upload):
        os.makedirs(folderName_upload)
    for i in range(len(fitsfiles)):
        fitsfile = fitsfiles[i]
        filename = fitsfile.split("/")[-1].split(".fit")[0]
        print ("    %s"%filename)
        upfiles = glob.glob("%s/%s_*.fits"%(folderName_upload, filename))
        ndata = fits.open(fitsfile)[1].data.shape[0]
        if len(upfiles)!=0:
            upfile = upfiles[0]
            framenum = upfile.split("/")[-1].split("_")[-1].split(".")[0]
            print ("    best frame already exist!")
            wcsfile = "%s/%s_%s_wcs.fits"%(folderName_wcs, filename, framenum)
            # w = WCS(fitsfile[int(framenum)].header)
            w = WCS(fitsfile[0].header)
            ra, dec = w.wcs_pix2world(ndata//2, ndata//2, 0)
            if os.path.isfile(wcsfile):
                print ("    wcs file exist for %s"%filename)
            else:
                fid.write("timeout 180s python kp84_get_wcs.py --upload %s "%upfile+\
                          "--ra %.5f --dec %.5f --radius %.1f "%(ra, dec, 5)+\
                          "--wcs %s/%s_%s_wcs.fits --private\n"%(folderName_wcs, filename, framenum))
            continue
        hdus = fits.open(fitsfile)
        if len(hdus)<=(npool+1):
            ipools = np.arange(1, len(hdus))
        else:
            ipools = np.arange(len(hdus)-1)+1
            np.random.shuffle(ipools)
            ipools = ipools[:npool]
            ipools = ipools[np.argsort(ipools)]
        print ("      finding best frame...")
        ns = np.zeros(len(ipools))
        for j in range(len(ipools)):
            ii = ipools[j]
            ns[j] = get_n_source(hdus[ii].data, subtract_median = subtract_median)
        
        if max(ns)<5:
            subtract_median = True
            print ("        max n = %d, redo by subtracting median"%(max(ns)))
            
            if len(ipools)<10:
                ipools = ipools
            elif len(ipools)<20:
                ipools = ipools[::2]
            else:
                ipools = ipools[::3]
            ns = np.zeros(len(ipools))
            for j in range(len(ipools)):
                if j%5==0:
                    print ("          processing... %d in %d"%(j, len(ipools)))
                ii = ipools[j]
                ns[j] = get_n_source(hdus[ii].data, subtract_median = subtract_median)
        
        iselect = ipools[np.where(ns == max(ns))[0][0]]
        nmax, data = get_n_source(hdus[iselect].data, subtract_median = subtract_median, return_data = True)
        
        print ("      saving frame %d: %d point source identified"%(iselect, nmax))
        hdu = fits.PrimaryHDU()
        hdul = fits.HDUList([hdu])
        hdul[0].data = data
        upfile = "%s/%s_%d.fits"%(folderName_upload, filename, iselect)
        hdul.writeto(upfile, overwrite=True)
        fid.write("timeout 180s python kp84_get_wcs.py --upload %s "%upfile+\
                      "--wcs %s/%s_%d_wcs.fits --private\n"%(folderName_wcs, filename, iselect))
fid.close()
    
print ("")
print ("=========================================")
print ("Running astrometry.net -- DEFAULT option!")
print ("=========================================")
print ("")
chmod_command = "chmod +x run_astrometry.sh"
os.system(chmod_command)
os.system("./run_astrometry.sh")

#objs = ["ZTFJ01395245", "ZTFJ18494132", "ZTFJ19244707", "ZTFJ19454455"]
print ("")
print ("================================")
print ("Calculate Shifts Between Frames!")
print ("================================")
print ("")

fid = open('run_astrometry.sh','w')

for obj in objs:
    objsplit = obj.split("_")
    if objsplit[0] in ["flat", "bias", "dark"]:
        continue
    folderName = "%s/%s"%(outputDir,obj)
    folderName_processing = "%s/processing"%(folderName)
    folderName_registration = "%s/registration"%(folderName)
    folderName_wcs = "%s/wcs"%(folderName)
    folderName_upload = "%s/upload"%(folderName)
    fitsfiles = sorted(glob.glob('%s/*.fit*'%(folderName_processing)))
    if not os.path.isdir(folderName_registration):
        os.makedirs(folderName_registration)
    for i in range(len(fitsfiles)):
        fitsfile = fitsfiles[i]
        filename = fitsfile.split("/")[-1].split(".fit")[0]
        print ("%s"%filename)
        print ("  Calculating shift w.r.t extension 1...")
        tb_shift, data_stacked = stack_shifted_frames(fitsfile)
        shiftedtbfile= "%s/%s_shift.dat"%(folderName_registration, filename)
        tb_shift.write(shiftedtbfile, format="ascii", overwrite=True)
        wcsfiles = glob.glob("%s/%s_*.fits"%(folderName_wcs, filename))
        if len(wcsfiles)!=0:
            wcsfile = wcsfiles[0]
            framenum = int(wcsfile.split("/")[-1].split("_")[-2].split(".")[0])
            print ("  Found wcs in frame %d"%(framenum))
        else:
            print ("  Didn't find wcs -- save stacked img to be uploaded")
            w = WCS(fitsfile[0].header)
            ra, dec = w.wcs_pix2world(data_stacked.shape[0]//2, data_stacked.shape[0]//2, 0)
            hdu = fits.PrimaryHDU()
            hdul = fits.HDUList([hdu])
            hdul[0].data = data_stacked
            stackedfile = "%s/%s_stack.fits"%(folderName_upload, filename)
            hdul.writeto(stackedfile, overwrite=True)
            fid.write("timeout 180s python kp84_get_wcs.py --upload %s "%stackedfile +\
                      "--ra %.5f --dec %.5f --radius %.1f "%(ra, dec, 10/60)+\
                      "--wcs %s/%s_stack_wcs.fits --private\n"%(folderName_wcs, filename))
fid.close()
    
print ("")
print ("=======================================")
print ("Running astrometry.net -- STACK option!")
print ("=======================================")
print ("")
    
chmod_command = "chmod +x run_astrometry.sh"
os.system(chmod_command)
os.system("./run_astrometry.sh")
