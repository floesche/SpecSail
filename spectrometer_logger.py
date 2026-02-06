#!/usr/bin/env python3
"""
Spectrometer logger for Ocean Optics USB4000.

Collects spectra over 2.5-second integration windows, applying calibration
and binning into 5nm wavelength steps. Each CSV file contains all individual
100ms measurements from one window.

Output is calibrated to absolute spectral irradiance (µW/cm² per bin) using
calibration from file (sunlight calibration) or spectrometer EEPROM. Falls
back to raw counts if no calibration is available.

Usage
-----
    pixi run log        # Run until Ctrl+C
    pixi run log 10     # Collect exactly 10 files
"""

import json
import subprocess
import sys
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
CALIBRATION_FILE = Path("calibration.json")

# Common system sound paths for the click notification
CLICK_SOUND_PATHS = [
    "/usr/share/sounds/freedesktop/stereo/button-pressed.oga",
    "/usr/share/sounds/freedesktop/stereo/button-toggle-on.oga",
    "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga",
    "/usr/share/sounds/sound-icons/click.wav",
]


def play_click():
    """
    Play a click sound notification (non-blocking).

    Attempts to play a system sound using available audio players
    (paplay, aplay, ffplay). Falls back to terminal bell if no
    audio player or sound file is found.
    """
    for sound_path in CLICK_SOUND_PATHS:
        if Path(sound_path).exists():
            try:
                # Try paplay (PulseAudio) first, then aplay (ALSA)
                for player in ["paplay", "aplay", "ffplay -nodisp -autoexit"]:
                    try:
                        subprocess.Popen(
                            player.split() + [sound_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        return
                    except FileNotFoundError:
                        continue
            except Exception:
                pass
    # Fallback: just use the terminal bell
    print('\a', end='', flush=True)


def load_calibration_from_file(wavelengths):
    """
    Load calibration from JSON file (e.g., sunlight calibration).

    Parameters
    ----------
    wavelengths : numpy.ndarray
        Array of wavelengths from the spectrometer.

    Returns
    -------
    numpy.ndarray or None
        Calibration coefficients interpolated to the given wavelengths,
        or None if the calibration file doesn't exist or is invalid.
    """
    if not CALIBRATION_FILE.exists():
        return None

    try:
        with open(CALIBRATION_FILE) as f:
            cal_data = json.load(f)

        cal_wavelengths = np.array(cal_data["wavelengths"])
        cal_coefficients = np.array(cal_data["coefficients"])

        # Interpolate to current wavelengths
        coefficients = np.interp(wavelengths, cal_wavelengths, cal_coefficients)

        print(f"Calibration loaded from: {CALIBRATION_FILE}")
        print(f"  Source: {cal_data.get('description', 'unknown')}")
        return coefficients
    except Exception as e:
        print(f"Warning: Could not load calibration file ({e})")
        return None


def load_calibration_from_eeprom(spec):
    """
    Load irradiance calibration from spectrometer EEPROM.

    Parameters
    ----------
    spec : seabreeze.spectrometers.Spectrometer
        Connected spectrometer instance.

    Returns
    -------
    tuple
        (calibration_coefficients, collection_area) as (numpy.ndarray, float),
        or (None, None) if calibration is not available in EEPROM.
    """
    try:
        irrad_cal = spec.f.irradiance_calibration.read_calibration()
        area = spec.f.irradiance_calibration.read_collection_area()  # cm²
        print(f"Calibration loaded from EEPROM: collection area = {area:.4f} cm²")
        return np.array(irrad_cal), area
    except (AttributeError, Exception):
        return None, None


def apply_calibration_file(intensities, cal_coefficients, integration_time_us):
    """
    Convert raw counts to absolute spectral irradiance (µW/cm²/nm).

    Uses calibration coefficients from sunlight calibration file.

    Parameters
    ----------
    intensities : numpy.ndarray
        Raw intensity counts from spectrometer.
    cal_coefficients : numpy.ndarray
        Calibration coefficients from calibration file.
    integration_time_us : int
        Integration time in microseconds.

    Returns
    -------
    numpy.ndarray
        Spectral irradiance in µW/cm²/nm.
    """
    integration_time_s = integration_time_us / 1e6
    return intensities * cal_coefficients / integration_time_s


def apply_calibration_eeprom(intensities, irrad_cal, integration_time_us, area):
    """
    Convert raw counts to absolute spectral irradiance (µW/cm²/nm).

    Uses calibration from spectrometer EEPROM.

    Parameters
    ----------
    intensities : numpy.ndarray
        Raw intensity counts from spectrometer.
    irrad_cal : numpy.ndarray
        Irradiance calibration coefficients from EEPROM.
    integration_time_us : int
        Integration time in microseconds.
    area : float
        Collection area in cm².

    Returns
    -------
    numpy.ndarray
        Spectral irradiance in µW/cm²/nm.
    """
    integration_time_s = integration_time_us / 1e6
    return (intensities * irrad_cal) / (integration_time_s * area)


def bin_spectrum(wavelengths, intensities, bin_size=5):
    """
    Bin spectrum data into fixed wavelength steps.

    Averages intensity values within each wavelength bin, ignoring NaN values.

    Parameters
    ----------
    wavelengths : numpy.ndarray
        Array of wavelength values in nm.
    intensities : numpy.ndarray
        Array of intensity or irradiance values.
    bin_size : int, optional
        Width of each wavelength bin in nm (default: 5).

    Returns
    -------
    bin_centers : numpy.ndarray
        Center wavelength of each bin in nm.
    binned_intensities : numpy.ndarray
        Mean intensity/irradiance per bin.
    """
    wl_min = np.floor(wavelengths.min() / bin_size) * bin_size
    wl_max = np.ceil(wavelengths.max() / bin_size) * bin_size
    bin_edges = np.arange(wl_min, wl_max + bin_size, bin_size)
    bin_centers = bin_edges[:-1] + bin_size / 2

    # Compute mean intensity in each bin (ignoring NaN values)
    binned_intensities = np.zeros(len(bin_centers))
    for i in range(len(bin_centers)):
        mask = (wavelengths >= bin_edges[i]) & (wavelengths < bin_edges[i + 1])
        if np.any(mask):
            values_in_bin = intensities[mask]
            valid_values = values_in_bin[~np.isnan(values_in_bin)]
            if len(valid_values) > 0:
                binned_intensities[i] = valid_values.mean()

    return bin_centers, binned_intensities


def save_csv(timestamp, bin_centers, all_binned_values, output_dir, calibrated=True, bin_size=5):
    """
    Save all individual spectra to a timestamped CSV file.

    Each spectrum is stored as a separate column. Calibrated data is converted
    from µW/cm²/nm to µW/cm² per bin by multiplying by bin width.

    Parameters
    ----------
    timestamp : datetime.datetime
        Timestamp for the filename.
    bin_centers : numpy.ndarray
        Wavelength bin centers in nm.
    all_binned_values : list of numpy.ndarray
        List of binned spectrum arrays, one per measurement.
    output_dir : pathlib.Path
        Directory to save the CSV file.
    calibrated : bool, optional
        Whether data is calibrated (default: True).
    bin_size : int, optional
        Wavelength bin width in nm (default: 5).

    Returns
    -------
    filename : pathlib.Path
        Path to the saved CSV file.
    n_spectra : int
        Number of spectra saved.
    """
    filename = output_dir / f"spectrum_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"

    n_spectra = len(all_binned_values)

    # Calibrated data: convert from µW/cm²/nm to µW/cm² by multiplying by bin width
    if calibrated:
        col_prefix = "irradiance_uW_cm2"
        values_to_save = [v * bin_size for v in all_binned_values]
    else:
        col_prefix = "intensity_counts"
        values_to_save = all_binned_values

    # Create header: wavelength_nm, spectrum_0, spectrum_1, ...
    header = "wavelength_nm," + ",".join(f"{col_prefix}_{i}" for i in range(n_spectra))

    with open(filename, 'w') as f:
        f.write(header + "\n")
        for row_idx, wl in enumerate(bin_centers):
            row_values = [v[row_idx] for v in values_to_save]
            f.write(f"{wl:.1f}," + ",".join(f"{val:.6f}" for val in row_values) + "\n")

    return filename, n_spectra


def main():
    """
    Run the spectrometer data logger.

    Connects to the spectrometer, loads calibration (file or EEPROM),
    and continuously captures spectra in 2.5-second windows. Each window
    is saved as a timestamped CSV file containing all individual measurements.

    Accepts an optional command-line argument for the number of files to collect.
    Runs until Ctrl+C if no count is specified.
    """
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
    integration_time_us = 100 * 1000  # 100 ms in microseconds
    spec.integration_time_micros(integration_time_us)
    print(f"Integration time: {integration_time_us / 1000:.0f} ms")

    # Get wavelengths
    wavelengths = spec.wavelengths()
    print(f"Wavelength range: {wavelengths.min():.1f} - {wavelengths.max():.1f} nm")

    # Try to load calibration (file first, then EEPROM, then raw)
    cal_coefficients = load_calibration_from_file(wavelengths)
    cal_source = "file"

    if cal_coefficients is None:
        irrad_cal, area = load_calibration_from_eeprom(spec)
        if irrad_cal is not None:
            cal_coefficients = irrad_cal
            cal_source = "eeprom"

    calibrated = cal_coefficients is not None

    if not calibrated:
        print("No calibration available. Using raw counts.")
        print("Run 'pixi run calibrate' to create a sunlight calibration.")

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR.absolute()}")

    if calibrated:
        print(f"\nLogging calibrated spectra (µW/cm² per {WAVELENGTH_BIN_SIZE}nm bin)")
    else:
        print(f"\nLogging raw spectra (counts)")
    print(f"Integration window: {INTEGRATION_WINDOW_S}s, binned to {WAVELENGTH_BIN_SIZE}nm steps")

    # Parse optional count argument
    max_files = None
    if len(sys.argv) > 1:
        try:
            max_files = int(sys.argv[1])
            print(f"Will collect {max_files} files\n")
        except ValueError:
            print(f"Invalid count: {sys.argv[1]}, running until Ctrl+C\n")
    else:
        print("Press Ctrl+C to stop\n")

    counter = 0
    try:
        while max_files is None or counter < max_files:
            counter += 1

            # Play click sound to signal new file is starting
            play_click()

            # Collect spectra over the integration window
            window_start = time.time()
            timestamp = datetime.now()
            spectra = []

            while time.time() - window_start < INTEGRATION_WINDOW_S:
                intensities = spec.intensities(correct_dark_counts=True)
                spectra.append(intensities)

            n_spectra = len(spectra)

            # Apply calibration and bin each spectrum individually
            all_binned_values = []
            bin_centers = None

            for intensities in spectra:
                # Apply calibration if available
                if calibrated:
                    if cal_source == "file":
                        values = apply_calibration_file(
                            intensities, cal_coefficients, integration_time_us
                        )
                    else:
                        values = apply_calibration_eeprom(
                            intensities, cal_coefficients, integration_time_us, area
                        )
                else:
                    values = intensities

                # Bin the spectrum into 5nm steps
                bin_centers, binned_values = bin_spectrum(
                    wavelengths, values, WAVELENGTH_BIN_SIZE
                )
                all_binned_values.append(binned_values)

            unit = "µW/cm²" if calibrated else "counts"

            # Save all spectra to CSV (calibrated values are converted to µW/cm² per bin)
            filename, n_saved = save_csv(timestamp, bin_centers, all_binned_values, OUTPUT_DIR, calibrated, WAVELENGTH_BIN_SIZE)

            # Beep to signal file saved
            print('\a', end='', flush=True)

            # Show max value across all spectra (in saved units)
            all_max = max(np.nanmax(v) for v in all_binned_values)
            max_val = all_max * WAVELENGTH_BIN_SIZE if calibrated else all_max
            print(f"{counter:03d} [{timestamp.strftime('%H:%M:%S')}] Saved {filename.name} "
                  f"({n_saved} spectra, "
                  f"max: {max_val:.4f} {unit})")

        if max_files is not None and counter >= max_files:
            print(f"\nCollected {max_files} files.")
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        spec.close()
        print("Spectrometer closed.")


if __name__ == "__main__":
    main()
