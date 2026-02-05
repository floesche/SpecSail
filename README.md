# oceanstuff

Data acquisition and analysis toolkit for Ocean Optics USB4000 spectrometer.

## Features

- **Live viewer**: Real-time spectrum display with auto-scaling
- **Data logging**: Timed acquisition with configurable collection windows
- **Sunlight calibration**: Absolute irradiance calibration using AM1.5G solar reference
- **Visualization**: Plot spectra with statistics, peak detection, and mean calculation
- **Results archival**: Save plots and data with descriptive names

## Requirements

- Ocean Optics USB4000 spectrometer (or compatible)
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

Opens a real-time plot showing the current spectrum. Useful for alignment and checking signal levels.

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
pixi run plot
```

Displays all spectra from `data/` with individual traces and mean spectrum. Shows total irradiance statistics and peak wavelengths.

### Saving Results

```bash
pixi run save "Experiment name"
```

Saves the plot as PNG and moves data files to `results/Experiment name_data/`.

### Cleanup

```bash
pixi run clear
```

Deletes all CSV files in `data/`.

## Output Format

CSV files contain wavelength bins (5nm steps) with one column per spectrum captured during the 2.5s window:

```
wavelength_nm,irradiance_uW_cm2_0,irradiance_uW_cm2_1,...
347.5,0.123456,0.124567,...
352.5,0.234567,0.235678,...
```

Calibrated values are in µW/cm² per 5nm bin. Without calibration, raw counts are stored instead.

## Calibration

The system supports two calibration sources:

1. **File calibration** (`calibration.json`): Created by `pixi run calibrate` using AM1.5G solar reference. Takes precedence.
2. **EEPROM calibration**: Factory calibration stored in spectrometer (if available).

If neither is available, raw intensity counts are logged.

## Dependencies

Managed by pixi:
- seabreeze (spectrometer communication)
- numpy (data processing)
- matplotlib (visualization)
