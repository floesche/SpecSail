#!/usr/bin/env python3
"""
Sunlight calibration for seabreeze-compatible spectrometers.

Uses the AM1.5G solar reference spectrum (NREL/ASTM G173-03) to compute
calibration coefficients for converting raw counts to absolute spectral
irradiance. Best results with clear sky; point at open sky, not directly at sun.

Usage
-----
    pixi run calibrate
"""

import json
import time
from pathlib import Path

import numpy as np
import seabreeze
seabreeze.use("pyseabreeze")
from seabreeze.spectrometers import Spectrometer, list_devices


CALIBRATION_FILE = Path("calibration.json")

# AM1.5G Solar Reference Spectrum (NREL/ASTM G173-03)
# Wavelength (nm) : Spectral Irradiance (W/m²/nm) = (µW/cm²/nm) / 100
# Selected points from 300-900nm, converted to µW/cm²/nm
AM15G_REFERENCE = {
    # nm: µW/cm²/nm
    300: 0.05,   305: 0.49,   310: 2.32,   315: 6.03,   320: 10.89,
    325: 16.14,  330: 20.51,  335: 25.89,  340: 30.59,  345: 35.10,
    350: 41.37,  355: 44.86,  360: 46.54,  365: 51.43,  370: 55.96,
    375: 59.15,  380: 62.08,  385: 67.15,  390: 70.78,  395: 76.59,
    400: 84.21,  405: 90.48,  410: 94.97,  415: 100.69, 420: 104.21,
    425: 108.35, 430: 107.65, 435: 109.47, 440: 117.59, 445: 116.02,
    450: 128.00, 455: 132.01, 460: 132.65, 465: 132.54, 470: 136.92,
    475: 136.36, 480: 135.63, 485: 131.14, 490: 130.49, 495: 130.72,
    500: 131.56, 505: 129.70, 510: 131.41, 515: 131.91, 520: 130.37,
    525: 127.42, 530: 128.21, 535: 127.31, 540: 127.08, 545: 126.59,
    550: 125.57, 555: 125.36, 560: 123.55, 565: 123.23, 570: 122.29,
    575: 120.22, 580: 119.08, 585: 117.16, 590: 115.81, 595: 114.90,
    600: 113.82, 605: 112.23, 610: 110.52, 615: 108.77, 620: 107.49,
    625: 106.00, 630: 104.86, 635: 102.95, 640: 101.59, 645: 100.11,
    650: 98.70,  655: 97.28,  660: 95.59,  665: 93.91,  670: 92.63,
    675: 91.28,  680: 89.40,  685: 88.51,  690: 86.54,  695: 84.84,
    700: 83.49,  705: 81.87,  710: 80.09,  715: 78.75,  720: 77.15,
    725: 75.46,  730: 74.19,  735: 72.58,  740: 71.30,  745: 69.74,
    750: 68.59,  755: 66.95,  760: 62.47,  765: 60.92,  770: 64.47,
    775: 63.08,  780: 61.50,  785: 60.00,  790: 58.68,  795: 57.26,
    800: 56.01,  805: 54.80,  810: 53.52,  815: 52.42,  820: 51.23,
    825: 50.06,  830: 49.01,  835: 47.84,  840: 46.77,  845: 45.76,
    850: 44.72,  855: 43.73,  860: 42.74,  865: 41.74,  870: 40.86,
    875: 39.92,  880: 39.07,  885: 38.14,  890: 37.33,  895: 36.49,
    900: 35.67,
}


def interpolate_reference(wavelengths):
    """
    Interpolate AM1.5G reference spectrum to spectrometer wavelengths.

    Parameters
    ----------
    wavelengths : numpy.ndarray
        Array of wavelengths from the spectrometer.

    Returns
    -------
    numpy.ndarray
        Reference irradiance values in µW/cm²/nm interpolated to the given
        wavelengths. Values outside 300-900nm are set to 0.
    """
    ref_wl = np.array(list(AM15G_REFERENCE.keys()))
    ref_irr = np.array(list(AM15G_REFERENCE.values()))
    return np.interp(wavelengths, ref_wl, ref_irr, left=0, right=0)


def main():
    """
    Run the sunlight calibration procedure.

    Guides the user through capturing a reference spectrum of sunlight,
    then computes calibration coefficients by comparing measured counts
    to the AM1.5G solar reference spectrum. Saves results to calibration.json.

    The calibration is valid for wavelengths 300-900nm where the AM1.5G
    reference provides reliable data.
    """
    # Connect to spectrometer
    devices = list_devices()
    if not devices:
        print("No spectrometer found.")
        return

    spec = Spectrometer.from_first_available()
    print(f"Connected to: {spec.model}")

    # Set integration time
    integration_time_us = 100 * 1000  # 100 ms
    spec.integration_time_micros(integration_time_us)
    print(f"Integration time: {integration_time_us / 1000:.0f} ms")

    wavelengths = spec.wavelengths()
    print(f"Wavelength range: {wavelengths.min():.1f} - {wavelengths.max():.1f} nm")

    # Get reference spectrum for these wavelengths
    reference_irradiance = interpolate_reference(wavelengths)

    # Calibration range (where we have good reference data)
    valid_mask = (wavelengths >= 300) & (wavelengths <= 900)
    print(f"Calibration valid for: 300 - 900 nm")

    print("\n" + "=" * 60)
    print("SUNLIGHT CALIBRATION")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Go outside with the spectrometer")
    print("2. Point the fiber/sensor at open sky (NOT directly at the sun)")
    print("3. Clear sky works best; light clouds are OK")
    print("4. Avoid shadows and reflections from buildings/trees")
    print("5. Keep the sensor orientation consistent")
    print("\nPress Enter when ready to capture calibration spectrum...")
    input()

    # Capture multiple spectra and average
    print("Capturing calibration spectrum (averaging 10 measurements)...")
    spectra = []
    for i in range(10):
        intensities = spec.intensities(correct_dark_counts=True)
        spectra.append(intensities)
        time.sleep(0.1)

    measured_counts = np.mean(spectra, axis=0)

    # Check for saturation
    max_counts = measured_counts.max()
    if max_counts > 60000:
        print(f"\nWARNING: Signal may be saturated (max: {max_counts:.0f})")
        print("Try reducing integration time or pointing away from direct sunlight.")

    # Check for low signal
    if max_counts < 1000:
        print(f"\nWARNING: Signal is very low (max: {max_counts:.0f})")
        print("Make sure the sensor is pointed at the sky.")

    # Compute calibration coefficients
    # cal_coeff = reference_irradiance / (counts / integration_time_s)
    # So: irradiance = counts * cal_coeff / integration_time_s
    integration_time_s = integration_time_us / 1e6

    # Avoid division by zero
    measured_safe = np.where(measured_counts > 10, measured_counts, np.nan)
    cal_coefficients = (reference_irradiance * integration_time_s) / measured_safe

    # Set coefficients to NaN outside valid range
    cal_coefficients[~valid_mask] = np.nan

    # Save calibration
    calibration_data = {
        "description": "Sunlight calibration using AM1.5G reference",
        "integration_time_us": integration_time_us,
        "wavelengths": wavelengths.tolist(),
        "coefficients": cal_coefficients.tolist(),
        "measured_counts": measured_counts.tolist(),
        "reference_irradiance": reference_irradiance.tolist(),
    }

    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(calibration_data, f, indent=2)

    print(f"\nCalibration saved to: {CALIBRATION_FILE}")

    # Show summary
    valid_coeffs = cal_coefficients[valid_mask & ~np.isnan(cal_coefficients)]
    print(f"\nCalibration summary:")
    print(f"  Valid coefficients: {len(valid_coeffs)} wavelengths")
    print(f"  Coefficient range: {np.nanmin(valid_coeffs):.2e} - {np.nanmax(valid_coeffs):.2e}")
    print(f"  Peak measured signal: {max_counts:.0f} counts at {wavelengths[np.argmax(measured_counts)]:.1f} nm")

    spec.close()
    print("\nDone! Run 'pixi run log' to capture calibrated spectra.")


if __name__ == "__main__":
    main()
