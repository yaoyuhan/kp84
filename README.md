# kp84
Kitt Peak 84 inch scripts</br>
Instrument paper: [Coughlin et al. 2019](https://arxiv.org/abs/1901.04625)

## Usage
The following list steps to reduce photometric data, using 2019-11-17 as an example.

### `kp84_setup_reduction.py`
`python kp84_setup_reduction.py --day 20191117`
1. Basic calibration steps: create master bias, dark, and flat frames.<br>
For calibration files done in mode 0, they need to be downsampled by 2x2.<br>
Although master bias file is not used, as it is essentially the same as the master dark in mode 0.<br>
Typically, flats are taken with filter sloan _gr_ and Johnson _(U)BVRI_.
2. Processing science frames (subtract dark, divide flat).
3. Make register folder; Solve astrometry and save the wcs, using [astrometry.net](http://astrometry.net/).<br>
Call `kp84_get_wcs.py`.<br>
Shifts between each frames in the multi-extension cubes are calculated in this step and saved to the registter folder.
- Default upload image is the best frame in each cube (the one with most point sources identified).<br>
- If astrometry failed after trying 3 minutes, then stack all images, using the first extension as referencce.<br>
I took the median of un-shifted region, try 5 minutes this time.
- If astrometry still fails using the stacked image, then the object's position (x, y) must be given to the following script.

### `kp84_photometric_reduction.py`
`python kp84_photometric_reduction.py --day 20191117 --objName ZTFJ19015309 --doStack --nimages 5 `
1. Find the coordinate of object (from the file `input/observed.dat`). So make sure to add this beforehead.
2. Use the wcs, find the (x, y) of object in each frame, save to the processing fits file's headers<br>
Mask frames where the object shifted outside of the field.
3. run source extractor


Some notes:
- If transients, turn on `--doSubtraction --subtractionSource ps1`
- If there are enough objects to solve for zero point, turn on `doZP`<br>
This can be hard sometimes due to the limited field of view (4x4 arcmin)

