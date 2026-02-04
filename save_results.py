#!/usr/bin/env python3
"""
Save spectrum results: plot to PNG and archive data files.

Usage: python save_results.py "Result name"
"""

import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from spectrum_plot import load_all_spectra, create_spectrum_plot

DATA_DIR = Path("data")
RESULTS_DIR = Path("results")


def main():
    # Get result name from command line
    if len(sys.argv) < 2:
        print("Usage: python save_results.py \"Result name\"")
        print("Example: pixi run save \"My experiment\"")
        sys.exit(1)

    result_name = " ".join(sys.argv[1:])
    print(f"Saving results as: {result_name}")

    # Load all spectra
    wavelengths, all_values, calibrated, csv_files = load_all_spectra(DATA_DIR)

    if not csv_files:
        print(f"No spectrum files found in {DATA_DIR}/")
        print("Run 'pixi run log' first to collect data.")
        sys.exit(1)

    print(f"Found {len(csv_files)} spectrum files")

    # Create plot
    fig, ax, mean_safe, total_values, mean_total, total_label, total_unit = create_spectrum_plot(
        wavelengths, all_values, calibrated, len(csv_files), title=result_name
    )

    # Create results directory
    RESULTS_DIR.mkdir(exist_ok=True)

    # Save PNG at 1200x700
    png_path = RESULTS_DIR / f"{result_name}.png"
    fig.set_size_inches(1600 / 100, 1000 / 100)
    fig.savefig(png_path, dpi=100, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved plot: {png_path}")

    # Move data to results folder
    data_dest = RESULTS_DIR / f"{result_name}_data"
    data_dest.mkdir(exist_ok=True)

    for csv_file in csv_files:
        shutil.move(str(csv_file), str(data_dest / csv_file.name))

    print(f"Moved {len(csv_files)} data files to: {data_dest}")
    print("Done!")


if __name__ == "__main__":
    main()
