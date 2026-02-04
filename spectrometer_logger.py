#!/usr/bin/env python3
"""
Spectrometer logger for Ocean Optics USB4000.

Integrates measurements over 2.5s windows and saves timestamped CSV files
with spectrum data binned into 5nm steps.
"""

import time
from datetime import datetime
from pathlib import Path

import numpy as np
import seabreeze
seabreeze.use("cseabreeze")
from seabreeze.spectrometers import Spectrometer, list_devices


INTEGRATION_WINDOW_S = 2.5  # seconds
WAVELENGTH_BIN_SIZE = 5    # nm
OUTPUT_DIR = Path("data")


def bin_spectrum(wavelengths, intensities, bin_size=5):
    """
    Bin spectrum data into fixed wavelength steps.

    Returns bin centers and mean intensity per bin.
    """
    wl_min = np.floor(wavelengths.min() / bin_size) * bin_size
    wl_max = np.ceil(wavelengths.max() / bin_size) * bin_size
    bin_edges = np.arange(wl_min, wl_max + bin_size, bin_size)
    bin_centers = bin_edges[:-1] + bin_size / 2

    # Compute mean intensity in each bin
    binned_intensities = np.zeros(len(bin_centers))
    for i in range(len(bin_centers)):
        mask = (wavelengths >= bin_edges[i]) & (wavelengths < bin_edges[i + 1])
        if np.any(mask):
            binned_intensities[i] = intensities[mask].mean()

    return bin_centers, binned_intensities


def save_csv(timestamp, bin_centers, binned_intensities, output_dir):
    """Save spectrum data to a timestamped CSV file."""
    filename = output_dir / f"spectrum_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"

    with open(filename, 'w') as f:
        f.write("wavelength_nm,intensity\n")
        for wl, intensity in zip(bin_centers, binned_intensities):
            f.write(f"{wl:.1f},{intensity:.2f}\n")

    return filename


def main():
    # List available devices
    devices = list_devices()
    if not devices:
        print("No spectrometer found. Make sure the USB4000 is connected.")
        print("You may need to set up udev rules. See:")
        print("  https://python-seabreeze.readthedocs.io/en/latest/install.html#udev-rules")
        return

    print(f"Found devices: {devices}")

    # Connect to the first available spectrometer
    spec = Spectrometer.from_first_available()
    print(f"Connected to: {spec.model}")

    # Set integration time - use shorter time to allow multiple readings per window
    integration_time_ms = 100
    spec.integration_time_micros(integration_time_ms * 1000)
    print(f"Integration time: {integration_time_ms} ms")

    # Get wavelengths
    wavelengths = spec.wavelengths()
    print(f"Wavelength range: {wavelengths.min():.1f} - {wavelengths.max():.1f} nm")

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR.absolute()}")

    print(f"\nLogging spectra with {INTEGRATION_WINDOW_S}s integration windows")
    print(f"Binning to {WAVELENGTH_BIN_SIZE}nm steps")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            # Collect spectra over the integration window
            window_start = time.time()
            timestamp = datetime.now()
            spectra = []

            while time.time() - window_start < INTEGRATION_WINDOW_S:
                intensities = spec.intensities()
                spectra.append(intensities)

            # Average all spectra in the window
            averaged_intensities = np.mean(spectra, axis=0)
            n_spectra = len(spectra)

            # Bin the spectrum into 5nm steps
            bin_centers, binned_intensities = bin_spectrum(
                wavelengths, averaged_intensities, WAVELENGTH_BIN_SIZE
            )

            # Save to CSV
            filename = save_csv(timestamp, bin_centers, binned_intensities, OUTPUT_DIR)

            print(f"[{timestamp.strftime('%H:%M:%S')}] Saved {filename.name} "
                  f"({n_spectra} spectra averaged, "
                  f"max: {binned_intensities.max():.0f} counts)")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        spec.close()
        print("Spectrometer closed.")


if __name__ == "__main__":
    main()
