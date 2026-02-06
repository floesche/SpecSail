#!/usr/bin/env python3
"""
Migrate legacy OceanView txt spectrometer files to CSV format.

Converts tab-separated txt files (wavelength, irradiance in W/m²/nm) to the
CSV format used by spectrum_plot.py and other tools in this project.

The conversion process:

1. Reads OceanView tab-separated data (wavelength, irradiance)
2. Converts from W/m²/nm to µW/cm²/nm (factor of 100)
3. Bins to 5nm steps (averaging within each bin)
4. Converts from µW/cm²/nm to µW/cm² per bin (multiply by bin width)

Usage
-----
    pixi run migrate
"""

import sys
from pathlib import Path

import numpy as np

DATA_DIR = Path("data")
WAVELENGTH_BIN_SIZE = 5  # nm, same as spectrometer_logger.py


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

    binned_intensities = np.zeros(len(bin_centers))
    for i in range(len(bin_centers)):
        mask = (wavelengths >= bin_edges[i]) & (wavelengths < bin_edges[i + 1])
        if np.any(mask):
            values_in_bin = intensities[mask]
            valid_values = values_in_bin[~np.isnan(values_in_bin)]
            if len(valid_values) > 0:
                binned_intensities[i] = valid_values.mean()

    return bin_centers, binned_intensities


def convert_txt_to_csv(txt_path: Path) -> Path:
    """
    Convert a tab-separated OceanView txt file to CSV format.

    OceanView outputs W/m²/nm which is converted to µW/cm² per 5nm bin
    to match the output format of spectrometer_logger.py.

    Parameters
    ----------
    txt_path : pathlib.Path
        Path to the input txt file.

    Returns
    -------
    pathlib.Path
        Path to the created CSV file.
    """
    # Read the tab-separated data
    wavelengths = []
    values = []

    with open(txt_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                wavelengths.append(float(parts[0]))
                values.append(float(parts[1]))

    wavelengths = np.array(wavelengths)
    values = np.array(values)

    # OceanView "Absolute Irradiance" outputs in µW/cm²/nm
    # Convert to µW/cm² per bin to match spectrometer_logger.py output:
    # 1. Multiply by bin width (5nm) to get µW/cm² per bin
    # 2. Multiply by 100 to convert from W/m²/nm to µW/cm²/nm if OceanView uses SI units
    #    (1 W/m² = 100 µW/cm², since 1W = 10^6 µW and 1m² = 10^4 cm²)
    UNIT_CONVERSION = 100  # W/m²/nm -> µW/cm²/nm

    # Bin to 5nm steps (average within each bin)
    bin_centers, binned_values = bin_spectrum(wavelengths, values, WAVELENGTH_BIN_SIZE)

    # Convert units and from per-nm to per-bin
    binned_values = binned_values * UNIT_CONVERSION * WAVELENGTH_BIN_SIZE

    # Determine output filename
    csv_filename = "spectrum_" + txt_path.stem + ".csv"
    csv_path = DATA_DIR / csv_filename

    # Use irradiance column name for calibrated data
    col_name = "irradiance_uW_cm2_0"

    # Write CSV with header
    with open(csv_path, 'w') as f:
        f.write(f"wavelength_nm,{col_name}\n")
        for wl, val in zip(bin_centers, binned_values):
            f.write(f"{wl:.1f},{val:.6f}\n")

    return csv_path


def main():
    """
    Migrate all OceanView txt files in the data directory to CSV format.

    Scans data/ for .txt files and converts each to a spectrum_*.csv file.
    Original txt files are preserved; user must delete them manually.

    Returns
    -------
    int
        Exit code: 0 if all conversions succeeded, 1 if any errors occurred.
    """
    if not DATA_DIR.exists():
        print(f"Data directory '{DATA_DIR}' does not exist.")
        return 1

    # Find all txt files in data/
    txt_files = list(DATA_DIR.glob("*.txt"))

    if not txt_files:
        print("No .txt files found in data/")
        return 0

    print(f"Found {len(txt_files)} txt file(s) to migrate:")
    print(f"Converting OceanView µW/cm²/nm -> µW/cm² per {WAVELENGTH_BIN_SIZE}nm bin\n")

    converted = 0
    errors = 0

    for txt_path in sorted(txt_files):
        try:
            csv_path = convert_txt_to_csv(txt_path)
            print(f"  {txt_path.name} -> {csv_path.name}")
            converted += 1
        except Exception as e:
            print(f"  ERROR: {txt_path.name}: {e}")
            errors += 1

    print(f"\nMigration complete: {converted} converted, {errors} errors")

    if converted > 0:
        print(f"\nCSV files created in: {DATA_DIR.absolute()}")
        print("Original txt files have NOT been deleted.")
        print("To remove originals after verifying, run:")
        print(f"  rm {DATA_DIR}/*.txt")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
