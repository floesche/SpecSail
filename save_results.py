#!/usr/bin/env python3
"""
Save spectrum results: plot to PNG and archive data files.

Creates a publication-quality PNG plot and moves the source CSV files
to a named archive folder in results/.

Usage
-----
    pixi run save "Experiment name"
    pixi run save "Experiment name" --min 0.01 --max 1000
    pixi run save "Experiment name" --allpeaks
"""

import argparse
import shutil
from pathlib import Path

import matplotlib.pyplot as plt

from spectrum_plot import load_all_spectra, create_spectrum_plot

DATA_DIR = Path("data")
RESULTS_DIR = Path("results")


def main():
    """
    Save spectrum results with a descriptive name.

    Parses command-line arguments for result name, y-axis limits, and peak
    display options. Loads all spectrum files from data/, creates a plot
    saved as results/<name>.png, and moves the CSV files to results/<name>_data/.
    """
    parser = argparse.ArgumentParser(description="Save spectrum results")
    parser.add_argument("name", nargs="+",
                        help="Result name (can contain spaces)")
    parser.add_argument("--min", type=float, default=0.1, dest="y_min",
                        help="Y-axis minimum value (default: 0.1)")
    parser.add_argument("--max", type=float, default=None, dest="y_max",
                        help="Y-axis maximum value (default: auto)")
    parser.add_argument("--allpeaks", action="store_true",
                        help="Show all local maxima, not just prominent ones")
    args = parser.parse_args()

    result_name = " ".join(args.name)
    print(f"Saving results as: {result_name}")

    # Load all spectra
    wavelengths, all_values, calibrated, csv_files = load_all_spectra(DATA_DIR)

    if not csv_files:
        print(f"No spectrum files found in {DATA_DIR}/")
        print("Run 'pixi run log' first to collect data.")
        return 1

    print(f"Found {len(csv_files)} spectrum files")

    # Create plot
    fig, ax, mean_safe, total_values, mean_total, total_label, total_unit = create_spectrum_plot(
        wavelengths, all_values, calibrated, len(csv_files), title=result_name,
        y_min=args.y_min, y_max=args.y_max, all_peaks=args.allpeaks
    )

    # Create results directory
    RESULTS_DIR.mkdir(exist_ok=True)

    # Save PNG at 1600x1000
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
    return 0


if __name__ == "__main__":
    exit(main())
