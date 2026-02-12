# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SpecSail uses the seabreeze library to provide simple tools for collecting and visualizing light spectrum measurements.

## Commands

All commands use pixi (package manager):

```bash
pixi run run        # Live spectrum viewer (real-time plot)
pixi run log        # Log spectra to CSV files in data/
pixi run log 5      # Log exactly 5 files then stop
pixi run plot       # Plot all spectra from data/
pixi run save "Name" # Save plot as PNG and archive data to results/
pixi run calibrate  # Create sunlight calibration using AM1.5G reference
pixi run clear      # Delete all CSV files in data/
```

## Architecture

**Data flow:** spectrometer → spectrometer_logger.py → data/*.csv → spectrum_plot.py → plot/save

**Key files:**
- `spectrometer_logger.py`: Main data acquisition. Collects spectra over 2.5s windows (100ms integration × ~25 readings), stores all individual spectra per CSV file (one column per measurement), applies calibration.
- `spectrum_plot.py`: Shared plotting module. `load_spectrum()` averages spectra within a CSV file; `load_all_spectra()` returns one mean spectrum per file.
- `calibrate_sunlight.py`: Creates `calibration.json` using AM1.5G solar reference spectrum (300-900nm valid range).
- `spectrometer.py`: Simple live viewer for real-time monitoring.

**CSV format:** `wavelength_nm,irradiance_uW_cm2_0,irradiance_uW_cm2_1,...` (one column per 100ms spectrum in the 2.5s window). Values are µW/cm² per 5nm bin when calibrated.

**Calibration:** File-based calibration (`calibration.json`) takes precedence over EEPROM calibration. Raw counts used if neither available.
