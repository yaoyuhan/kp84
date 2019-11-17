# kp84
Kitt Peak 84 inch scripts</br>
Instrument paper: [Coughlin et al. 2019](https://arxiv.org/abs/1901.04625)

## Usage
The following list steps to reduce photometric data, using 2019-11-16 as an example.

### `kp84_setup_reduction.py`
`python kp84_setup_reduction.py --day 20191116`
1. Basic calibration steps: create master bias, dark, and flat frames.<br>
For calibration files done in mode 0, they need to be downsampled by 2x2.<br>
Although master bias file is not used, as it is essentially the same as the master dark in mode 0.<br>
Typically, flats are taken with filter sloan _gr_ and Johnson _(U)BVRI_.
2. Processing science frames (subtract dark, divide flat).
3. Make register folder; Solve astrometry and save the wcs, using [astrometry.net](http://astrometry.net/).<br>
- Default upload image is the best frame in each cube (the one with most point sources identified).<br>
In the register folder, shift frames with the best frame as reference.
- If astrometry failed after trying 5 minutes, then stack all images, using the first extension as referencce.<br>
In the register folder, shift frames with extension 1 as reference.

### `kp84_photometric_reduction.py`
`python kp84_setup_reduction.py --day 20191116`
- Add the wcs solution into processing folders
