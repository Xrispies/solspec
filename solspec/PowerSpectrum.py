import numpy as np
from scipy import interpolate, integrate, constants
from os import path


class PowerSpectrum:
    def __init__(self, start_w: float = 280.0, stop_w: float = 4000.0, spectra: str = "AM1.5G"):
        """
        Initilizer for PowerSpectrum class. Builds custom spectrum if variables are passed when creating instance.
        :param start_w: shortest wavelength in nanometers
        :param stop_w: longest wavelength in nanometers
        :param spectra: the name of the spectrum you want to use. AM1.5G is most popular and is the ASTMG173-03
        global tilt standard,
        the AM1.5D is the direct+circumsolar standard,
        the AM0Etr spectrum is a non-standard zero air-mass spectrum -- Please compare to the ASTM E490 standard
        :return:
        """
        # the first column should be the wavelength in nanometers, the second is the tilt power density/nm in
        # W/(m**2 nm) = J s^-1 m^-2 nm^-1 = C V m^-2 nm^-1
        spectras = {"AM0Etr": 1, "AM1.5G": 2, "AM1.5D": 3}
        self.spectrum = np.genfromtxt(path.join(path.dirname(__file__), './ASTMG173.csv'), delimiter=",",
                                      skip_header=2)[:, [0, spectras[spectra]]]
        self.start_w = start_w
        self.stop_w = stop_w
        # build custom spectrum if necessary
        if start_w != 280.0 or stop_w != 4000.0:
            self.spectrum = self.sub_spectrum(start_w, stop_w)

        # create the PowerSpectrum interpolator
        self.interp = interpolate.interp1d(self.spectrum[:, 0], self.spectrum[:, 1])

    def sub_spectrum(self, start_w: float, stop_w: float):
        """
        Returns a subset of the PowerSpectrum specified by some bounding wavelengths
        :param start_w: shortest wavelength
        :param stop_w: longest wavelength
        :return: subspec (ndarray) the spectrum between start_w and stop_w
        """
        self.__bounds_check(*[start_w, stop_w])
        start_ind = np.where(start_w <= self.spectrum[:, 0])[0][0]
        stop_ind = np.where(self.spectrum[:, 0] <= stop_w)[0][-1] + 1
        subspec = self.spectrum[start_ind:stop_ind, :].copy()
        return subspec

    def __bounds_check(self, *wavelengths: float):
        """
        Checks that the given wavelength is between the shortest and longest wavelengths of the PowerSpectrum
        :param wavelengths: (float) wavelength in nanometers
        :returns: none
        """
        lowerb = self.spectrum[:, 0][0]
        upperb = self.spectrum[:, 0][-1]
        # See if the wavelength(s) is out of bounds, throw error
        for w in wavelengths:
            if not lowerb <= w <= upperb:
                print("Wavelength %0.2f nm out of spectra bounds" % w)
                if w < lowerb:
                    raise IndexError("Please use the lower bound of %0.2f nm." % lowerb)
                elif w > upperb:
                    raise IndexError("Please use the upper bound of %0.2f nm." % upperb)
            else:
                pass
        return

    def value_at_wavelength(self, *wavelengths: float):
        """
        Interpolates the spectrum to give the value of the spectrum at the given wavelength(s).
        :param: wavelengths (float, list) wavelength(s) of interest in nanometers
        :returns: values
        """
        self.__bounds_check(*wavelengths)
        for w in wavelengths:
            irradiance = float(self.interp(w))
            yield irradiance

    def integrate(self, *w):
        """
        Integrates the solar spectrum. By defualt the full width of the spectrum is integrated, but inputting 2 floats
        within the PowerSpectrum bounds will give the integration of sub-spectrum.
        :param w: (floats, ints) shortest and longest wavelengths for a sub-spectrum
        :return power_f: (float) the integrated power of the sub-spectrum
        """
        # deal with subspectrums if necessary
        if not w:
            spectrum = self.spectrum
            interp = self.interp
        else:
            assert len(w) >= 2 and w[0] < w[
                1], 'Error: Too few wavelengths or start wavelength is not shorter than the longest wavelength.'
            spectrum = self.sub_spectrum(w[0], w[1])
            # TODO: Decide if to use quad and interp1d obj for integration or not. trapz is faster & close in result
            # interp = interpolate.interp1d(spectrum[:, 0], spectrum[:, 1])
        # get the total number of discrete wavelengths as a bin limit
        # bin_limit = len(spectrum[:, 0])
        # integrate the power
        # power_f = integrate.quad(interp, spectrum[0, 0], spectrum[-1, 0], full_output=1, limit=bin_limit)
        power_f = integrate.trapz(spectrum[:, 1], spectrum[:, 0])
        return power_f  # Units Watts/meters^2

    def get_spectrum(self):
        """
        Returns a copy of the spectrum.
        :return: (ndarray) The discrete spectrum with the wavelengths in [:,0] and the values in [:,1]
        """
        return self.spectrum.copy()

    def weight_spectrum(self, spec_in: np.ndarray, kind="cubic"):
        """
        Weights a spectrum by a normalized spectrum, e.g. absorption, reflection, transmission at wavelengths in nm
        :param kind: (str or int, optional)interpolation method specification in scipy.interpolat.interp1d:
        Specifies the kind of interpolation as a string (‘linear’, ‘nearest’, ‘zero’, ‘slinear’, ‘quadratic, ‘cubic’
        where ‘slinear’, ‘quadratic’ and ‘cubic’ refer to a spline interpolation of first, second or third order) or as
        an integer specifying the order of the spline interpolator to use. Default is ‘linear’.
        :param spec_in: (np.ndarray) a 2-D array with wavelengths in nm in spec_in[:,0] and normalized vaules in
        spec_in[:,1]
        :return: (np.ndarray) a weighted spectrum in the same format as spec_in
        """
        if spec_in.shape[1] != 2:
            try:
                spec_in = spec_in.transpose()
            except:
                pass
        spec_in = np.squeeze(spec_in)
        assert spec_in.shape[1] == 2, "Weight spectrum is not a 2D numpy array."
        spec_fun = interpolate.interp1d(spec_in[:, 0], spec_in[:, 1], kind=kind)
        if spec_in[0, 0] != self.start_w or spec_in[-1, 0] != self.stop_w:
            self.spectrum = self.sub_spectrum(spec_in[0, 0], spec_in[-1, 0])
        spec_wt = self.spectrum
        spec_wt[:, 1] = spec_fun(spec_wt[:, 0]) * spec_wt[:, 1]
        return


class PhotonSpectrum(PowerSpectrum):
    def __init__(self, start_w: float = 280.0, stop_w: float = 4000.0, spectra: str = "AM1.5G"):
        """
        Gives the spectrum in photon flux-- changes units from Watts/(meter**2 nm) to #/(s meter**2 nm)
        :param start_w: shortest wavelength
        :param stop_w: longest wavelength
        :param spectra: the ASTM standard spectrum to use
        :return: None
        """
        super().__init__(start_w, stop_w, spectra)
        self.spectrum[:, 1] = self.spectrum[:, 1] * (self.spectrum[:, 0] * 1e-9 / (constants.c * constants.h))
        self.interp = interpolate.interp1d(self.spectrum[:, 0], self.spectrum[:, 1])


class PhotocurrentSpectrum(PhotonSpectrum):
    def __init__(self, start_w: float = 280.0, stop_w: float = 4000.0, spectra: str = "AM1.5G"):
        """
        Gives the spectrum in photocurrent -- changes units from A/(meter**2 nm) to Amps/(meter**2 nm)
        :param start_w: shortest wavelength
        :param stop_w: longest wavelength
        :param spectra: the ASTM standard spectrum to use
        :return: None
        """
        super().__init__(start_w, stop_w, spectra)
        self.spectrum[:, 1] *= constants.e
        self.interp = interpolate.interp1d(self.spectrum[:, 0], self.spectrum[:, 1])
