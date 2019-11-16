# kp84
Kitt Peak 84 inch scripts

## Usage
The following list steps to reduce photometric data, using 2019-11-16 as an example.

### `kp84_setup_reduction.py`
`python kp84_setup_reduction.py --day 20191116 --doCalibration --doAstrometry`
- The `--doCalibration` option will create master bias, dark, and flat frames.<br>
Since calibration files are done in mode 0, they need to be downsampled by 2x2.
- The `--doAstrometry` option will solve astrometry and save the wcs, using [astrometry.net](http://astrometry.net/).
