# oceanstuff

Data acquisition and analysis toolkit for Ocean Optics USB4000 spectrometer.

## Features

- **Live viewer**: Real-time spectrum display with auto-scaling
- **Data logging**: Timed acquisition with configurable collection windows (2.5s per file)
- **Sunlight calibration**: Absolute irradiance calibration using AM1.5G solar reference
- **Visualization**: Plot spectra with statistics, peak detection, and mean calculation
- **Results archival**: Save plots and data with descriptive names
- **Data migration**: Convert legacy OceanView txt files to project CSV format

## Requirements

- Ocean Optics USB4000 spectrometer (or compatible seabreeze-supported device)
- Linux with udev rules configured for seabreeze
- [pixi](https://pixi.sh) package manager

## Installation

```bash
git clone <repository>
cd oceanstuff
pixi install
```

For spectrometer access without root, set up udev rules:
https://python-seabreeze.readthedocs.io/en/latest/install.html#udev-rules

## Usage

### Live Viewer

```bash
pixi run run
```

Opens a real-time plot showing the current spectrum. Useful for alignment and checking signal levels. Updates every 100ms.

### Calibration

```bash
pixi run calibrate
```

Creates `calibration.json` using sunlight as a reference. Point the sensor at open sky (not directly at the sun) on a clear day. Valid calibration range: 300-900nm.

### Data Logging

```bash
pixi run log        # Run until Ctrl+C
pixi run log 10     # Collect exactly 10 files
```

Captures spectra in 2.5-second windows, saving all individual measurements (100ms integration each) to timestamped CSV files in `data/`. Audio feedback indicates capture timing.

### Plotting

```bash
pixi run plot                        # Plot spectra from data/
pixi run plot results/experiment_data  # Plot from specific directory
pixi run plot --min 0.01             # Set y-axis minimum
pixi run plot --max 1000             # Set y-axis maximum
pixi run plot --output result.png    # Save to file instead of displaying
pixi run plot --allpeaks             # Show all local maxima
```

Displays all spectra with individual traces and mean spectrum. Shows total irradiance statistics and peak wavelengths.

### Saving Results

```bash
pixi run save "Experiment name"
pixi run save "Experiment name" --min 0.01 --max 1000
pixi run save "Experiment name" --allpeaks
```

Saves the plot as PNG and moves data files to `results/Experiment name_data/`. Accepts the same `--min`, `--max`, and `--allpeaks` options as `pixi run plot`.

### Cleanup

```bash
pixi run clear
```

Deletes all CSV files in `data/`.

### Data Migration

```bash
pixi run migrate
```

Converts legacy OceanView tab-separated txt files in `data/` to the CSV format used by this project. Original files are preserved.

## Output Format

CSV files contain wavelength bins (5nm steps) with one column per spectrum captured during the 2.5s window:

```
wavelength_nm,irradiance_uW_cm2_0,irradiance_uW_cm2_1,...
347.5,0.123456,0.124567,...
352.5,0.234567,0.235678,...
```

Calibrated values are in µW/cm² per 5nm bin. Without calibration, raw counts are stored instead (column prefix: `intensity_counts`).

## Calibration

The system supports two calibration sources:

1. **File calibration** (`calibration.json`): Created by `pixi run calibrate` using AM1.5G solar reference. Takes precedence.
2. **EEPROM calibration**: Factory calibration stored in spectrometer (if available).

If neither is available, raw intensity counts are logged.

## File Structure

```
oceanstuff/
├── spectrometer.py         # Live spectrum viewer
├── spectrometer_logger.py  # Data acquisition and logging
├── spectrum_plot.py        # Shared plotting module
├── calibrate_sunlight.py   # Sunlight calibration
├── plot_spectra.py         # Plot CLI tool
├── save_results.py         # Save and archive results
├── migrate_data.py         # Legacy data migration
├── calibration.json        # Calibration coefficients (if created)
├── data/                   # Collected spectrum CSV files
└── results/                # Saved plots and archived data
```

## Dependencies

Managed by pixi:
- seabreeze (spectrometer communication)
- numpy (data processing)
- matplotlib (visualization)
