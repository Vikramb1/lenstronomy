import numpy as np
import lenstronomy.Util.data_util as data_util


class Instrument(object):
    """
    basic access points to instrument properties
    """
    def __init__(self, read_noise, pixel_scale, ccd_gain):
        """

        :param read_noise: std of noise generated by read-out (in units of electrons)
        :param pixel_scale: scale (in arcseonds) of pixels
        :param ccd_gain: electrons/ADU (analog-to-digital unit). A gain of 8 means that the camera digitizes the CCD signal
         so that each ADU corresponds to 8 photoelectrons.
        """
        self.ccd_gain = float(ccd_gain)
        self._read_noise = read_noise
        self.pixel_scale = pixel_scale


class Observation(object):
    """
    basic access point to observation properties
    """
    def __init__(self, exposure_time, sky_brightness, magnitude_zero_point, seeing, num_exposures=1, psf_type='GAUSSIAN'):
        """

        :param exposure_time: exposure time per image (in seconds)
        :param sky_brightness: sky brightness (in magnitude per square arcseconds)
        :param point_spread_function: 2d array characterising the point spread function (odd numbers per axis, centered)
        :param magnitude_zero_point: magnitude in which 1 count per second per arcsecond square is registered (in ADU's)
        :param num_exposures: number of exposures that are combined
        """
        self._exposure_time = exposure_time
        self._sky_brightness = sky_brightness
        self._magnitude_zero_point = magnitude_zero_point
        self._num_exposures = num_exposures
        self._seeing = seeing
        self._psf_type = psf_type

    @property
    def exposure_time(self):
        """
        total exposure time

        :return: summed exposure time
        """
        return self._exposure_time * self._num_exposures


class Data(Instrument, Observation):
    """
    class that combines Instrument and Observation
    """
    def __init__(self, read_noise, pixel_scale, ccd_gain, exposure_time, sky_brightness, magnitude_zero_point, seeing,
                 num_exposures=1, psf_type='GAUSSIAN', data_count_unit='ADU'):
        """

        :param read_noise: std of noise generated by read-out (in units of electrons)
        :param pixel_scale: scale (in arcseonds) of pixels
        :param ccd_gain: electrons/ADU (analog-to-digital unit). A gain of 8 means that the camera digitizes the CCD signal
         so that each ADU corresponds to 8 photoelectrons.
        :param exposure_time: exposure time per image (in seconds)
        :param sky_brightness: sky brightness (in magnitude per square arcseconds)
        :param point_spread_function: 2d array characterising the point spread function (odd numbers per axis, centered)
        :param magnitude_zero_point: magnitude in which 1 count per second per arcsecond square is registered
        :param num_exposures: number of exposures that are combined
        :param data_count_unit: string, unit of the data (and other properties), 'e-': (electrons assumed to be IID),
        'ADU': (analog-to-digital unit)
        """
        Instrument.__init__(self, read_noise, pixel_scale, ccd_gain)
        Observation.__init__(self, exposure_time, sky_brightness, magnitude_zero_point, seeing, num_exposures, psf_type)
        if data_count_unit not in ['e-', 'ADU']:
            raise ValueError("count_unit type %s not supported! Please chose e- or ADU." % data_count_unit)
        self._data_count_unit = data_count_unit

    @property
    def read_noise(self):
        """

        :return: sqrt(variance) of read noise in units of the data
        """
        if self._data_count_unit == 'ADU':
            return self._read_noise / self.ccd_gain
        else:
            return self._read_noise

    @property
    def sky_brightness(self):
        """

        :return: sky brightness (counts per square arcseconds in unit of data)
        """
        cps = data_util.magnitude2cps(self._sky_brightness, magnitude_zero_point=self._magnitude_zero_point)
        if self._data_count_unit == 'e-':
            cps *= self.ccd_gain
        return cps

    @property
    def background_noise(self):
        """
        Gaussian sigma of noise level per pixel (in counts per second)

        :return: sqrt(variance) of background noise level
        """
        return data_util.bkg_noise(self.read_noise, self._exposure_time, self.sky_brightness, self.pixel_scale,
                                   num_exposures=self._num_exposures)

    def flux_noise(self, flux):
        """

        :param flux: float or array, units of count_unit/seconds
        :return: Gaussian approximation of Poisson statistics in IIDs sqrt(variance)
        """
        if self._data_count_unit == 'ADU':
            flux_iid = flux * self.ccd_gain * self.exposure_time
        else:
            flux_iid = flux * self.exposure_time  # if in electrons per seconds
        variance = flux_iid  # the variance of a Poisson distribution is the IID count number
        noise = np.sqrt(variance) / self.exposure_time
        if self._data_count_unit == 'ADU':
            noise /= self.ccd_gain
        return noise

    def noise_for_model(self, model, background_noise=True, poisson_noise=True, seed=None):
        """

        :param model: 2d numpy array of modelled image (with pixels in units of data specified in class)
        :param background_noise: bool, if True, adds background noise
        :param poisson_noise: bool, if True, adds Poisson noise of modelled flux
        :return:
        """
        if seed is not None:
            np.random.seed(seed)
        nx, ny = np.shape(model)
        noise = np.zeros_like(model)
        if background_noise is True:
            noise += np.random.randn(nx, ny) * self.background_noise
        if poisson_noise is True:
            noise += np.random.randn(nx, ny) * self.flux_noise(model)
        return noise

    def estimate_noise(self, image):
        """

        :param image: noisy data, background subtracted
        :return: estimated noise map  sqrt(variance) for each pixel as estimated from the instrument and observation
        """
        return np.sqrt(self.background_noise**2 + data_util.flux_noise(image, self.exposure_time)**2)

    def magnitude2cps(self, magnitude):
        """
        converts an apparent magnitude to counts per second (in units of the data)

        The zero point of an instrument, by definition, is the magnitude of an object that produces one count
        (or data number, DN) per second. The magnitude of an arbitrary object producing DN counts in an observation of
        length EXPTIME is therefore:
        m = -2.5 x log10(DN / EXPTIME) + ZEROPOINT

        :param magnitude: magnitude of object
        :return: counts per second of object
        """
        # compute counts in units of ADS (as magnitude zero point is defined)
        cps = data_util.magnitude2cps(magnitude, magnitude_zero_point=self._magnitude_zero_point)
        if self._data_count_unit == 'e-':
            cps *= self.ccd_gain
        return cps
