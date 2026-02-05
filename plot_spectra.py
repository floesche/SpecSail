#!/usr/bin/env python3
"""
Plot all spectrum files from a data directory.

Shows individual spectra as line plots and the mean spectrum.
X-axis: wavelength (nm), Y-axis: irradiance (µW/cm² per 5nm bin, log scale)

Usage:
    pixi run plot                      # Plot spectra from data/
    pixi run plot <directory>          # Plot spectra from specified directory
    pixi run plot --min 0.01           # Set y-axis minimum to 0.01
    pixi run plot <directory> --min 1  # Combine both options
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from spectrum_plot import load_all_spectra, create_spectrum_plot

DEFAULT_DATA_DIR = Path("data")


def main():
    parser = argparse.ArgumentParser(description="Plot spectrum files")
    parser.add_argument("directory", nargs="?", default=None,
                        help="Data directory (default: data/)")
    parser.add_argument("--min", type=float, default=0.1, dest="y_min",
                        help="Y-axis minimum value (default: 0.1)")
    args = parser.parse_args()

    # Determine data directory
    if args.directory:
        data_dir = Path(args.directory)
        # Derive title from directory name (remove _data suffix if present)
        dir_name = data_dir.name.rstrip("/")
        if dir_name.endswith("_data"):
            title = dir_name[:-5]  # Remove "_data" suffix
        else:
            title = dir_name
    else:
        data_dir = DEFAULT_DATA_DIR
        title = None  # Use default title from create_spectrum_plot

    # Load all spectra
    wavelengths, all_values, calibrated, csv_files = load_all_spectra(data_dir)

    if not csv_files:
        print(f"No spectrum files found in {data_dir}/")
        if data_dir == DEFAULT_DATA_DIR:
            print("Run 'pixi run log' first to collect data.")
        return

    print(f"Found {len(csv_files)} spectrum files")

    # Create plot
    fig, ax, mean_safe, total_values, mean_total, total_label, total_unit = create_spectrum_plot(
        wavelengths, all_values, calibrated, len(csv_files), title=title, y_min=args.y_min
    )

    print(f"{total_label} (mean): {mean_total:.2f} {total_unit}")
    print(f"{total_label} range: {min(total_values):.2f} - {max(total_values):.2f} {total_unit}")

    plt.show()


if __name__ == "__main__":
    main()
