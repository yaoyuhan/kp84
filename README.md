# kp84
Kitt Peak 84 inch scripts</br>
Instrument paper: [Coughlin et al. 2019](https://arxiv.org/abs/1901.04625)

## Usage
The following list steps to reduce photometric data, using 2019-11-16 as an example.

### `kp84_setup_reduction.py`
`python kp84_setup_reduction.py --day 20191116 --doCalibration --doAstrometry`
- The `--doCalibration` option will create master bias, dark, and flat frames.<br>
For calibration files done in mode 0, they need to be downsampled by 2x2.<br>
Although master bias file is not used, as it is essentially the same as the master dark in mode 0.
- The `--doAstrometry` option will solve astrometry and save the wcs, using [astrometry.net](http://astrometry.net/).
