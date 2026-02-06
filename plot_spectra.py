#!/usr/bin/env python3
"""
Plot all spectrum files from a data directory.

Creates a publication-quality plot showing individual spectra as semi-transparent
lines with a bold mean spectrum. Uses logarithmic y-axis and annotates peak
wavelengths.

Usage
-----
    pixi run plot                          # Plot spectra from data/
    pixi run plot <directory>              # Plot spectra from specified directory
    pixi run plot --min 0.01               # Set y-axis minimum to 0.01
    pixi run plot --max 1000               # Set y-axis maximum to 1000
    pixi run plot --output result.png      # Save to file instead of displaying
    pixi run plot --allpeaks               # Show all local maxima
    pixi run plot <directory> --min 1      # Combine options
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from spectrum_plot import load_all_spectra, create_spectrum_plot

DEFAULT_DATA_DIR = Path("data")


def main():
    """
    Plot spectrum files from a directory.

    Parses command-line arguments for data directory, y-axis limits,
    output file, and peak display options. Loads all spectrum CSV files,
    creates the plot, and either displays it interactively or saves to file.
    """
    parser = argparse.ArgumentParser(description="Plot spectrum files")
    parser.add_argument("directory", nargs="?", default=None,
                        help="Data directory (default: data/)")
    parser.add_argument("--min", type=float, default=0.1, dest="y_min",
                        help="Y-axis minimum value (default: 0.1)")
    parser.add_argument("--max", type=float, default=None, dest="y_max",
                        help="Y-axis maximum value (default: auto)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Save plot to file instead of displaying")
    parser.add_argument("--allpeaks", action="store_true",
                        help="Show all local maxima, not just prominent ones")
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
        wavelengths, all_values, calibrated, len(csv_files), title=title, y_min=args.y_min, y_max=args.y_max,
        all_peaks=args.allpeaks
    )

    print(f"{total_label} (mean): {mean_total:.2f} {total_unit}")
    print(f"{total_label} range: {min(total_values):.2f} - {max(total_values):.2f} {total_unit}")

    if args.output:
        # Save to file with same parameters as save_results.py
        fig.set_size_inches(1600 / 100, 1000 / 100)
        fig.savefig(args.output, dpi=100, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved plot: {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
