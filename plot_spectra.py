#!/usr/bin/env python3
"""
Plot all spectrum files from the data directory.

Shows individual spectra as line plots and the mean spectrum.
X-axis: wavelength (nm), Y-axis: irradiance (µW/cm² per 5nm bin, log scale)
"""

from pathlib import Path

import matplotlib.pyplot as plt

from spectrum_plot import load_all_spectra, create_spectrum_plot

DATA_DIR = Path("data")


def main():
    # Load all spectra
    wavelengths, all_values, calibrated, csv_files = load_all_spectra(DATA_DIR)

    if not csv_files:
        print(f"No spectrum files found in {DATA_DIR}/")
        print("Run 'pixi run log' first to collect data.")
        return

    print(f"Found {len(csv_files)} spectrum files")

    # Create plot
    fig, ax, mean_safe, total_values, mean_total, total_label, total_unit = create_spectrum_plot(
        wavelengths, all_values, calibrated, len(csv_files)
    )

    print(f"{total_label} (mean): {mean_total:.2f} {total_unit}")
    print(f"{total_label} range: {min(total_values):.2f} - {max(total_values):.2f} {total_unit}")

    plt.show()


if __name__ == "__main__":
    main()
