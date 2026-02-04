#!/usr/bin/env python3
"""
Spectrometer logger for Ocean Optics USB4000.

Integrates measurements over 2.5s windows and saves timestamped CSV files
with spectrum data binned into 5nm steps.

Output is calibrated to absolute spectral irradiance (µW/cm²/nm) using
calibration from file (sunlight calibration) or spectrometer EEPROM.
"""

import json
import subprocess
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
    """Play a click sound notification (non-blocking)."""
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

    Returns calibration coefficients interpolated to the given wavelengths,
    or None if file doesn't exist.
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

    Returns (calibration_coefficients, collection_area) or (None, None) if unavailable.
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
    Formula: irradiance = counts * cal_coefficient / integration_time_s
    """
    integration_time_s = integration_time_us / 1e6
    return intensities * cal_coefficients / integration_time_s


def apply_calibration_eeprom(intensities, irrad_cal, integration_time_us, area):
    """
    Convert raw counts to absolute spectral irradiance (µW/cm²/nm).

    Uses calibration from spectrometer EEPROM.
    Formula: irradiance = (counts * cal_coefficient) / (integration_time_s * area)
    """
    integration_time_s = integration_time_us / 1e6
    return (intensities * irrad_cal) / (integration_time_s * area)


def bin_spectrum(wavelengths, intensities, bin_size=5):
    """
    Bin spectrum data into fixed wavelength steps.

    Returns bin centers and mean intensity per bin.
    Uses nanmean to handle NaN values from uncalibrated wavelength regions.
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


def save_csv(timestamp, bin_centers, binned_values, output_dir, calibrated=True, bin_size=5):
    """Save spectrum data to a timestamped CSV file."""
    filename = output_dir / f"spectrum_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"

    # Calibrated data: convert from µW/cm²/nm to µW/cm² by multiplying by bin width
    if calibrated:
        header = "wavelength_nm,irradiance_uW_cm2"
        values_to_save = binned_values * bin_size
    else:
        header = "wavelength_nm,intensity_counts"
        values_to_save = binned_values

    with open(filename, 'w') as f:
        f.write(header + "\n")
        for wl, value in zip(bin_centers, values_to_save):
            f.write(f"{wl:.1f},{value:.6f}\n")

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
    print("Press Ctrl+C to stop\n")

    counter = 0
    try:
        while True:
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

            # Average all spectra in the window
            averaged_intensities = np.mean(spectra, axis=0)
            n_spectra = len(spectra)

            # Apply calibration if available
            if calibrated:
                if cal_source == "file":
                    values = apply_calibration_file(
                        averaged_intensities, cal_coefficients, integration_time_us
                    )
                else:
                    values = apply_calibration_eeprom(
                        averaged_intensities, cal_coefficients, integration_time_us, area
                    )
                unit = "µW/cm²"
            else:
                values = averaged_intensities
                unit = "counts"

            # Bin the spectrum into 5nm steps
            bin_centers, binned_values = bin_spectrum(
                wavelengths, values, WAVELENGTH_BIN_SIZE
            )

            # Save to CSV (calibrated values are converted to µW/cm² per bin)
            filename = save_csv(timestamp, bin_centers, binned_values, OUTPUT_DIR, calibrated, WAVELENGTH_BIN_SIZE)

            # Beep to signal file saved
            print('\a', end='', flush=True)

            # Show max value (in saved units)
            max_val = np.nanmax(binned_values) * WAVELENGTH_BIN_SIZE if calibrated else np.nanmax(binned_values)
            print(f"{counter:03d} [{timestamp.strftime('%H:%M:%S')}] Saved {filename.name} "
                  f"({n_spectra} spectra averaged, "
                  f"max: {max_val:.4f} {unit})")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        spec.close()
        print("Spectrometer closed.")


if __name__ == "__main__":
    main()
