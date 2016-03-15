import numpy as np
from scipy import interpolate, integrate


class Spectrum:
    def __init__(self):
        # the first column should be the wavelength in nanometers, the second is the power density/nm in
        # W/(m**2 nm) = J s^-1 m^-2 nm^-1 = C V m^-2 nm^-1
        self.spectrum = np.genfromtxt("ASTMG173.csv", delimiter=",", skip_header=2)[:, [0, 2]]
        self.interp = interpolate.interp1d(self.spectrum[:, 0], self.spectrum[:, 1])

    def power_density(self, start_w: float, stop_w: float):
        """
        Integrates the AM15G solar spectrum to get the power density in a sub-spectrum
        :param start_w: (float) shortest wavelength in m
        :param stop_w: (float) longest wavelength of spectrum in m
        :return power: (float) the inegrated power of the sub-spectrum
        """
        # If the spectrum limits is out of bounds, throw error
        assert start_w < self.spectrum[:, 0][0], "Start wavelength below ASTM1.5G lower bound. Use 280.0 nm "
        assert stop_w > self.spectrum[:, 0][-1], "Start wavelength below ASTM1.5G lower bound. Use 4 um "
        # get the total number of discreet wavelengths
        waves = self.spectrum[:, 0]
        bin_limit = (np.where(waves < stop_w)[0][-1] + 1) - (np.where(start_w < waves)[0][0])
        power = integrate.quad(self.interp, start_w, stop_w, full_output=1, limit=bin_limit)[0]
        power = float(power)
        return power  # Units Watts/meters^2