#!/usr/bin/env python

import os, sys, optparse, shutil, glob, copy
import numpy as np
import astropy.io.ascii as asci
from astropy.io import fits
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table, vstack
from astropy.time import Time
  
# sys.path.append("/Users/yuhanyao/Documents/GitHub/ztfsub/")
# sys.path.append("/Users/yuhanyao/Documents/GitHub/kp84/")
# sys.path.append("/Users/yuhanyao/Documents/GitHub/PythonPhot/")
import ztfsub.utils, ztfsub.surveys
import ztfsub.plotting
sys.path.append("/home/roboao/Michael/kp84/")
from citizen.photometry_utils import ps1_query
from citizen.reduction_utils import stack_images, register_images
from citizen.reduction_utils import get_wcs_xy, forcedphotometry_kp
from citizen.reduction_utils import get_reference_pos, filter2filtstr

from skimage.transform import rescale, resize, downscale_local_mean

from astroquery.vizier import Vizier
from astroML.crossmatch import crossmatch_angular

import matplotlib
fs = 14
matplotlib.rcParams.update({'font.size': fs})
from matplotlib import pyplot as plt


def parse_commandline():
    """
    Parse the options given on the command-line.
    """
    parser = optparse.OptionParser()

    parser.add_option("--day",default="20191116", help="date of observation")
    parser.add_option("--objName",default="ZTFJ19015309", help="object name")
    
    parser.add_option("-x","--xstar",default=-1,type=float, help="object's x pixel of frame 1, only give if astrometry.net solution failed")
    parser.add_option("-y","--ystar",default=-1,type=float, help="object's y pixel of frame 1, only give if astrometry.net solution failed")
    parser.add_option("--xyext",default=1,type=float, help="frame number of the Multi-extension Cube that xstar and ystar are specified")
    
    parser.add_option("--doSubtractBackground",  action="store_true", default=False)
    parser.add_option("--doOverwrite",  action="store_true", default=False, help='If true, remove the previous object-output folder') 
    
    # stack options
    parser.add_option("-n","--nimages",default=1,type=int, help="see --doStack")
    parser.add_option("--doStack",  action="store_true", default=False, help="stack each --nimages together")
    
    parser.add_option("--aper_size",default=10.0,type=float, help="aperture size in pixel numbers")
    parser.add_option("--doMakeMovie",  action="store_true", default=False)
    
    # Transient options
    parser.add_option("--doSubtraction",  action="store_true", default=False, help="subtract sdss or ps1 reference image, only used for transient observations")
    parser.add_option("--subtractionSource", default="ps1", 
                      choices=('sdss', 'ps1'), help="source of the reference image")
    
    parser.add_option("--doSaveImages",  action="store_true", default=False)
    parser.add_option("--doDifferential",  action="store_true", default=False)
    parser.add_option("--doZP",  action="store_true", default=False, help="solve for zero point in each image using ps1")

    opts, args = parser.parse_args()
    return opts
        
    
def makemovie(movieDir,fitsfiles,x=None,y=None):
    nums = []
    for fitsfile in fitsfiles:
        fitsfileSplit = fitsfile.replace(".fits.fz","").replace(".fits","").split("_")
        try:
            num = int(fitsfileSplit[-1])
        except:
            num = -1
        nums.append(num)

    fitsfiles = [fitsfiles for _,fitsfiles in sorted(zip(nums,fitsfiles))]

    cnt = 0
    for ii in range(len(fitsfiles)):
        hdulist = fits.open(fitsfiles[ii])
        for jj in range(len(hdulist)):
            if jj == 0: continue
            header = hdulist[jj].header
            data = hdulist[jj].data

            vmin = np.percentile(data,5)
            vmax = np.percentile(data,95)

            plotName = os.path.join(movieDir,'image_%04d.png'%cnt)
            plt.figure()
            plt.imshow(data,vmin=vmin,vmax=vmax,cmap='gray')
            if not x == None:
                plt.xlim(x)
                plt.ylim(y)
            plt.show()
            plt.savefig(plotName,dpi=200)             
            plt.close()
            cnt = cnt + 1
  
    moviefiles = os.path.join(movieDir,"image_%04d.png")
    filename = os.path.join(movieDir,"movie.mpg")
    ffmpeg_command = 'ffmpeg -an -y -r 20 -i %s -b:v %s %s'%(moviefiles,'5000k',filename)
    os.system(ffmpeg_command)
    filename = os.path.join(movieDir,"movie.gif")
    ffmpeg_command = 'ffmpeg -an -y -r 20 -i %s -b:v %s %s'%(moviefiles,'5000k',filename)
    os.system(ffmpeg_command)

"""
day = "20191117"
objName = "ZTFJ01395245"
setupDir = "/Users/yuhanyao/Desktop/kped_tmp/"
"""
# Parse command line
opts = parse_commandline()
setupDir = "/Data3/archive_kped/data/reductions/"
day = opts.day
objName = opts.objName

inputDir = "../input"
dataDir = os.path.join(setupDir, day, objName) # the setup directory of this object
outputDir = os.path.join("../output", day, objName) # the output directory of this object
defaultsDir = "../defaults" # where photometric defaults are stored

doSubtraction = opts.doSubtraction
subtractionSource = opts.subtractionSource
doZP = opts.doZP
doOverwrite = opts.doOverwrite
doDifferential = opts.doDifferential
doSubtractBackground = opts.doSubtractBackground
doSaveImages = opts.doSaveImages
doStack = opts.doStack
nimages = opts.nimages

xstar = opts.xstar
ystar = opts.ystar
xyext = opts.xyext
aper_size = opts.aper_size

print ("")
print ("=================================")
print ("Getting the Coordinate of Object!")
print ("=================================")
print ("")
observedFile = "%s/observed.dat"%inputDir
lines = [line.rstrip('\n') for line in open(observedFile)]
lines = np.array(lines)
objs = []
ras = []
decs = []
for ii,line in enumerate(lines):
    lineSplit = list(filter(None,line.split(" ")))
    objs.append(lineSplit[0])
    ras.append(float(lineSplit[1]))
    decs.append(float(lineSplit[2]))
    
objs = np.array(objs)
ras = np.array(ras)
decs = np.array(decs)
if objName not in objs:
    print("%s missing from observed list, please add."%objName)
    exit(0)
else:
    ind = np.where(objs==objName)[0][0]
    ra = ras[ind]
    dec = decs[ind]
print ("%s, ra=%.5f, dec=%.5f"%(objName, ra, dec))

if not os.path.isdir(outputDir):
    os.makedirs(outputDir)

fitsfiles = sorted(glob.glob(os.path.join(dataDir,'processing','*.fits'))) 
tmpheader = fits.open(fitsfiles[0])[0].header
tmpfilter = tmpheader["FILTER"]
passband = filter2filtstr(tmpfilter)


print ("")
print ("=================================================")
print ("Finding the object on each frame -- Registration!")
print ("=================================================")
print ("")
nfiles = len(fitsfiles)

for i in range(nfiles):
    fitsfile = fitsfiles[i]
    fitsfileSplit = fitsfile.split("/")[-1].replace(".fits","").replace("_proc","")
    path_out_dir='%s/%s'%(outputDir,fitsfileSplit)
    if doOverwrite:
        rm_command = "rm -rf %s"%path_out_dir
        os.system(rm_command)
    if not os.path.isdir(path_out_dir):
        os.makedirs(path_out_dir)
    print("%d/%d: %s"%(i+1, nfiles, fitsfileSplit))
    print ("  Finding it on the wcs file extension...")
    wcsfiles = glob.glob(os.path.join(dataDir,'wcs', '%s*wcs.fits'%fitsfileSplit))
    wcsfile = wcsfiles[0]
    shiftfiles = glob.glob(os.path.join(dataDir,'registration', '%s*shift.dat'%fitsfileSplit))
    shiftfile = shiftfiles[0]
    x, y, xyframe = get_wcs_xy(ra, dec, wcsfile, fitsfile, get_distance = True)
    register_images(fitsfile, shiftfile, xyframe, x, y, path_out_dir, 
                    aper_size = aper_size)
    print ("")

fitsfiles = sorted(glob.glob(os.path.join(dataDir,'registration','*_regis.fits'))) 

# yyao: This call is to be checked!
if doSubtraction:
    print ("")
    print ("======================================")
    print ("This is a transient -- do Subtraction!")
    print ("======================================")
    print ("")
    refimage = os.path.join(path_out_dir,'ref.fits')
    refband = passband[-1]
    if not os.path.isfile(refimage):
        if subtractionSource == "sdss":
            refgood = ztfsub.surveys.get_sdss(opts,refimage,ra,dec,refband)
        else:
            refgood = ztfsub.surveys.get_ps1(opts,refimage,ra,dec,refband)
    else:
        refgood = True

# yyao: This call is to be checked!
if doZP:
    radius_deg = 0.2
    result = ps1_query(ra, dec, radius_deg, maxmag=22,
                       maxsources=10000)
    ps1_ra, ps1_dec = result["RAJ2000"], result["DEJ2000"]
    if passband == "ju":
        ps1_mag = result["gmag"]
    elif passband == "B":
        ps1_mag = result["gmag"]
    elif passband == "V":
        ps1_mag = result["rmag"]
    elif passband == "R":
        ps1_mag = result["imag"]
    elif passband == "I":
        ps1_mag = result["zmag"]
    elif passband == "g":
        ps1_mag = result["gmag"]
    elif passband == "r":
        ps1_mag = result["rmag"]

# yyao: This call is to be checked
if doStack:
    stackDir = os.path.join(path_out_dir,'stack')
    if not os.path.isdir(stackDir):
        os.makedirs(stackDir)
    if nimages > 1:
        stack_images(stackDir,fitsfiles,opts.nimages,doRegistration=doRegistration,
                     registration_size=registration_size,x=x0,y=y0) 
        fitsfiles = sorted(glob.glob(os.path.join(stackDir,'*.fits*')))
    else:
        print("You asked to stack but with --nimages 1... passing.")

# yyao: This call is to be checked
if opts.doMakeMovie:
    movieDir = os.path.join(path_out_dir,'movie')
    if not os.path.isdir(movieDir):
        os.makedirs(movieDir)

    makemovie(movieDir,fitsfiles,x=[x0-50,x0+50],y=[y0-50,y0+50])


print ("")
print ("=====================")
print ("Run Source Extractor!")
print ("=====================")
print ("")

nfiles = len(fitsfiles)

for ii in range(nfiles):
    fitsfile = fitsfiles[ii]
    fitsfileSplit = fitsfile.split("/")[-1].replace("_proc_regis","").replace(".fits","")
    print("%d/%d: %s"%(ii+1, nfiles, fitsfileSplit))

    path_out_dir='%s/%s'%(outputDir, fitsfileSplit)
    if not os.path.isdir(path_out_dir):
        os.makedirs(path_out_dir)

    scienceimage = '%s/science.fits'%(path_out_dir)
    catfile = scienceimage.replace(".fits",".cat")
    catfile_zp = scienceimage.replace(".fits",".catzp")
    backfile = scienceimage.replace(".fits",".background.fits")
    subfile = scienceimage.replace(".fits",".sub.fits")
    
    # copy science image
    system_command = "cp %s %s"%(fitsfile,scienceimage)
    os.system(system_command)
                
    # yyao:This call is to be checked
    if doSubtraction:
        tmpdir='%s/subtract'%(path_out_dir)
        if not os.path.isdir(tmpdir):
            os.makedirs(tmpdir)
            
        hdulist = fits.open(fitsfile)
        hdulistsub = copy.copy(hdulist)
        if len(hdulist) > 1:
            for kk in range(len(hdulist)):
                if kk == 0:
                    hdu_primary = copy.copy(hdulist[kk])
                    continue
                else:
                    hdu = copy.copy(hdulist[kk])
                    hdu.header = wcs_header

                tmpimage='%s/%04d.fits'%(tmpdir,kk)
                hdulist2 = fits.HDUList(hdus=[hdu_primary,hdu])
                hdulist2.writeto(tmpimage,output_verify='fix',overwrite=True)
                
                ztfsub.utils.p60sdsssub(opts, tmpimage, refimage, [ra,dec],
                        distortdeg=1, scthresh1=3.0,
                        scthresh2=10.0, tu=60000, iu=60000, ig=2.3, tg=1.0,
                        stamps=None, nsx=1, nsy=1, ko=0, bgo=0, radius=10,
                        tlow=-5000.0, ilow=-5000.0, sthresh=5.0, ng=None, 
                        aperture=10.0,
                        defaultsDir=defaultsDir)

                tmplist = fits.open(tmpimage)
                hdulistsub[kk].data = tmplist[1].data

            hdulistsub.writeto(subfile,output_verify='fix',overwrite=True)

        else:
           
            ztfsub.utils.p60sdsssub(opts, scienceimage, refimage, [ra, dec],
                    distortdeg=1, scthresh1=3.0,
                    scthresh2=10.0, tu=60000, iu=60000, ig=2.3, tg=1.0,
                    stamps=None, nsx=4, nsy=4, ko=0, bgo=0, radius=10,
                    tlow=-5000.0, ilow=-5000.0, sthresh=5.0, ng=None,
                    aperture=10.0,
                    defaultsDir=defaultsDir)

    if doSubtraction:
        ztfsub.utils.sextractor(subfile, defaultsDir, 
                                doSubtractBackground = doSubtractBackground,
                                catfile = catfile, backfile = backfile)
        if doZP:
            ztfsub.utils.sextractor(scienceimage, defaultsDir,
                                        doSubtractBackground = doSubtractBackground,
                                        catfile = catfile_zp, backfile = backfile)
    else:
        ztfsub.utils.sextractor(scienceimage, defaultsDir, 
                                doSubtractBackground = doSubtractBackground, 
                                catfile = catfile, backfile = backfile)
    if not doSaveImages:
        if os.path.isfile(backfile):
            rm_command = "rm %s"%backfile
            os.system(rm_command)
  
print ("")
print ("========================")
print ("Find the Reference Star!")
print ("========================")
print ("")
for ii in range(nfiles):
    fitsfile = fitsfiles[ii]
    fitsfileSplit = fitsfile.split("/")[-1].replace("_proc_regis","").replace(".fits","")
    print("%d/%d: %s"%(ii+1, nfiles, fitsfileSplit))
    path_out_dir_tmp='%s/%s'%(outputDir, fitsfileSplit)
    scienceimage = '%s/science.fits'%(path_out_dir_tmp)
    catfile = scienceimage.replace(".fits",".cat")
    catfile_mod = scienceimage.replace(".fits",".cat.mod")
    
    cat = np.loadtxt(catfile)
    if not cat.size: 
        continue
    
    xs, ys, fluxes, fluxerrs, mags, magerrs, ras, decs, cxx, cyy, cxy, \
        cxx_world, cyy_world, cxy_world, A, B, A_world, B_world, theta, theta_world, fwhms, \
        fwhms_world, extnumber = cat[:,0], cat[:,1], cat[:,2], cat[:,3], cat[:,4], cat[:,5], cat[:,6], cat[:,7], cat[:,8], cat[:,9], cat[:,10], cat[:,11], cat[:,12], cat[:,13], cat[:,14], cat[:,15], cat[:,16], cat[:,17], cat[:,18], cat[:,19], cat[:,20], cat[:,21], cat[:,22]
    
    if doZP and doSubtraction:
        catzp = np.loadtxt(catfile_zp)
        xs_zp, ys_zp, fluxes_zp, fluxerrs_zp, mags_zp, magerrs_zp, ras_zp, decs_zp, cxx_zp, cyy_zp, cxy_zp, cxx_world_zp, cyy_world_zp, cxy_world_zp, A_zp, B_zp, A_world_zp, B_world_zp, theta_zp, theta_world_zp, fwhms_zp, fwhms_world_zp, extnumber_zp = catzp[:,0], catzp[:,1], catzp[:,2], catzp[:,3], catzp[:,4], catzp[:,5], catzp[:,6], catzp[:,7], catzp[:,8], catzp[:,9], catzp[:,10], catzp[:,11], catzp[:,12], catzp[:,13], catzp[:,14], catzp[:,15], catzp[:,16], catzp[:,17], catzp[:,18], catzp[:,19], catzp[:,20], catzp[:,21], catzp[:,22]

    if doZP:
        if doZP and doSubtraction:
            imX = np.vstack((ras_zp,decs_zp)).T
        else:
            imX = np.vstack((ras,decs)).T
        stX = np.vstack((np.array(ps1_ra),np.array(ps1_dec))).T
        max_radius = 1.5 / 3600  # 1 arcsec
        dist, ind_im = crossmatch_angular(imX, stX, max_radius)
        
        # getting ZP
        ZP_mag = []
        if doZP and doSubtraction:
            for ii in range(len(ind_im)):
                if ind_im[ii] < len(ps1_mag) and np.abs(magerrs_zp[ii])<0.025 :
                    ZP_mag.append(-mags_zp[ii]+ps1_mag[ind_im[ii]])
        else:
            for ii in range(len(ind_im)):
                if ind_im[ii] < len(ps1_mag) and np.abs(magerrs[ii])<0.025 :
                    ZP_mag.append(-mags[ii]+ps1_mag[ind_im[ii]])

        print('number of standards used:', len(ZP_mag))
        print('ZP = ',np.round(np.mean(ZP_mag),3),'+-',np.round(np.std(ZP_mag),3))#,np.mean(ZP_mag)-np.median(ZP_mag))
        mags = mags + np.mean(ZP_mag)
    
    hdulist = fits.open(scienceimage)
    mjds = np.zeros(xs.shape)
    for jj in range(len(hdulist)-1):
        header =  hdulist[jj+1].header
        if "GPS_TIME" in header:
            timeobs = Time(header["GPS_TIME"])
        elif "DATE" in header:
            timeobs = Time(header["DATE"])
        idx = np.where(extnumber==jj+1)[0]
        mjds[idx] = timeobs.mjd

    catmod = np.vstack((cat.T,mjds.T)).T
    np.savetxt(catfile_mod, catmod, fmt='%.5f')        

    catmod = np.loadtxt(catfile_mod)
    get_reference_pos(scienceimage, catmod, zp=0)
    
    #                                   'X','Y','flux','fluxerr','mag','magerr',
    #                                   'RA','Declination','CXX','CYY','CXY',
    #                                   'CXX_World','CYY_World','CXY_World',
    #                                   'A','B','A_World','B_World','Theta','Theta_World',
    #                                   'FWHM_World','FWHM','EXT','MJD'

    
print ("")
print ("==========================")
print ("Perform Forced Photometry!")
print ("==========================")
print ("")
for ii in range(nfiles):
    fitsfile = fitsfiles[ii]
    fitsfileSplit = fitsfile.split("/")[-1].replace("_proc_regis","").replace(".fits","")
    print("%d/%d: %s"%(ii+1, nfiles, fitsfileSplit))
    path_out_dir='%s/%s'%(outputDir, fitsfileSplit)
    scienceimage = '%s/science.fits'%(path_out_dir)
    
    forcedfile = '%s/science.forced'%(path_out_dir)
    if not os.path.isfile(forcedfile) or doOverwrite:
        mjd_forced, mag_forced, magerr_forced, flux_forced, fluxerr_forced = \
            forcedphotometry_kp(scienceimage, aper_size=aper_size, xkey = "X_OBJ", ykey = "Y_OBJ")

        if doDifferential:            
            mjd_forced, mag_forced_field, magerr_forced_field, flux_forced_field, fluxerr_forced_field = \
                forcedphotometry_kp(scienceimage, aper_size=aper_size, xkey = "X_FIELD", ykey = "Y_FIELD")
            
            mag = mag_forced - mag_forced_field
            magerr = np.sqrt(magerr_forced**2 + magerr_forced_field**2)
            flux = flux_forced/flux_forced_field
            fluxerr = flux*np.sqrt((fluxerr_forced/flux_forced)**2 + (fluxerr_forced_field/flux_forced_field)**2)
            
        else:
            mag, magerr, flux, fluxerr = mag_forced, magerr_forced, flux_forced, fluxerr_forced

        if doZP:
            mag = mag + np.mean(ZP_mag)

        try:
            fid = open(forcedfile,'w')
            for ii in range(len(mjd_forced)):
                fid.write('%.10f %.10f %.10f %.10f %.10f\n'%(mjd_forced[ii],mag[ii],magerr[ii],flux[ii],fluxerr[ii]))
            fid.close()
        except:
            fid = open(forcedfile,'w')
            fid.write('%.10f %.10f %.10f %.10f %.10f\n'%(mjd_forced,mag,magerr,flux,fluxerr))
            fid.close()

    if not doSaveImages:
        if os.path.isfile(scienceimage):
            rm_command = "rm %s"%scienceimage
            os.system(rm_command)
    
    plt.figure(figsize=(12,6))
    mjd0 = mjd_forced[0]
    plt.errorbar(mjd_forced-mjd0, mag_forced, magerr_forced, fmt='.k', label = "science")
    plt.errorbar(mjd_forced-mjd0, mag_forced_field, magerr_forced_field, fmt='.b', label="ref")
    plt.errorbar(mjd_forced-mjd0, mag, magerr, fmt=".r", label="differential")
    plt.legend()
    plt.title(fitsfileSplit, fontsize=fs)
    plt.gca().invert_yaxis()
    plt.xlabel("mjd - %.5f"%mjd0)
    plt.tight_layout()
    figname = os.path.join(path_out_dir, "diff_phot.pdf")
    plt.savefig(figname)
    plt.close()
    

print ("")
print ("=======================")
print ("Make Final Light Curve!")
print ("=======================")
print ("")
for ii in range(nfiles):
    fitsfile = fitsfiles[ii]    
    fitsfileSplit = fitsfile.split("/")[-1].replace("_proc_regis","").replace(".fits","")
    print("%d/%d: %s"%(ii+1, nfiles, fitsfileSplit))

    path_out_dir='%s/%s'%(outputDir, fitsfileSplit)
    scienceimage = '%s/science.fits'%(path_out_dir)
    forcedfile = scienceimage.replace(".fits",".forced")

    if ii == 0:
        tblforced = asci.read(forcedfile,names=['MJD','mag','magerr','flux','fluxerr'])
    else:
        tbltemp = asci.read(forcedfile,names=['MJD','mag','magerr','flux','fluxerr']) 
        tblforced = vstack([tblforced,tbltemp])
 
    # force photometry
    print (" Saving forced photometry light curve...")
    forcedfile = '%s/forced.dat'%(path_out_dir)
    asci.write(tblforced,forcedfile,overwrite=True)
    tblforced = asci.read(forcedfile,names=['MJD','mag','magerr','flux','fluxerr'])

    mjd_forced = tblforced['MJD'].data
    mag_forced, magerr_forced = tblforced['mag'].data, tblforced['magerr'].data
    flux_forced, fluxerr_forced = tblforced['flux'].data, tblforced['fluxerr'].data
    
finalforcefile = os.path.join(outputDir,"lightcurve.forced")
print ("Writing to %s"%finalforcefile)
tblforced.write(finalforcefile, format = "ascii")

print ("Plotting relative mag photometry...")
plotName = os.path.join(outputDir,'mag_relative_forced.pdf')
fig = plt.figure(figsize=(20,8))
plt.errorbar(mjd_forced-mjd_forced[0],mag_forced,magerr_forced,fmt='ko')
plt.xlabel('Time from %.5f [days]'%mjd_forced[0])
plt.ylabel('Magnitude [arb]')
idx = np.where(np.isfinite(mag_forced))[0]
ymed = np.nanmedian(mag_forced)
y10, y90 = np.nanpercentile(mag_forced[idx],10), np.nanpercentile(mag_forced[idx],90)
ystd = np.nanmedian(magerr_forced[idx])
ymin = y10 - 3*ystd
ymax = y90 + 3*ystd
plt.ylim([ymin,ymax])
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig(plotName)
plt.close()

print ("Plotting relative flux photometry...")
plotName = os.path.join(path_out_dir,'flux_relative_forced.pdf')
fig = plt.figure(figsize=(20,8))
plt.errorbar(mjd_forced-mjd_forced[0],flux_forced,fluxerr_forced,fmt='ko')
plt.xlabel('Time from %.5f [days]'%mjd_forced[0])
plt.ylabel('Flux')
plt.tight_layout()
plt.savefig(plotName)
plt.close()

