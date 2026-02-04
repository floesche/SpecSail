#!/usr/bin/env python3
"""
Plot all spectrum files from the data directory.

Shows individual spectra as line plots and the mean spectrum.
X-axis: wavelength (nm), Y-axis: intensity (log scale)
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

DATA_DIR = Path("data")


def load_spectrum(filepath):
    """Load a spectrum CSV file."""
    data = np.genfromtxt(filepath, delimiter=',', skip_header=1)
    wavelengths = data[:, 0]
    intensities = data[:, 1]
    return wavelengths, intensities


def main():
    # Find all spectrum CSV files
    csv_files = sorted(DATA_DIR.glob("spectrum_*.csv"))

    if not csv_files:
        print(f"No spectrum files found in {DATA_DIR}/")
        print("Run 'pixi run log' first to collect data.")
        return

    print(f"Found {len(csv_files)} spectrum files")

    # Load all spectra
    all_intensities = []
    wavelengths = None

    for filepath in csv_files:
        wl, intensities = load_spectrum(filepath)
        if wavelengths is None:
            wavelengths = wl
        all_intensities.append(intensities)

    all_intensities = np.array(all_intensities)

    # Calculate mean spectrum
    mean_intensities = np.mean(all_intensities, axis=0)

    # Set up the plot
    fig, ax = plt.subplots(figsize=(12, 7))

    # Plot individual spectra with low alpha
    for i, intensities in enumerate(all_intensities):
        # Replace zeros/negatives with small value for log scale
        intensities_safe = np.clip(intensities, 1e-1, None)
        ax.plot(wavelengths, intensities_safe, alpha=0.3, lw=0.8, color='steelblue')

    # Plot mean spectrum
    mean_safe = np.clip(mean_intensities, 1e-1, None)
    ax.plot(wavelengths, mean_safe, color='darkred', lw=2, label=f'Mean (n={len(csv_files)})')

    ax.set_xlabel('Wavelength (nm)', fontsize=12)
    ax.set_ylabel('Intensity (counts)', fontsize=12)
    ax.set_title('Recorded Spectra', fontsize=14)
    ax.set_yscale('log')
    ax.set_xlim(wavelengths.min(), wavelengths.max())
    ax.grid(True, alpha=0.3, which='both')
    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
