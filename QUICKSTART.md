# Quick Start

## Setup

1. Install pixi: https://pixi.sh
2. Clone and install:
   ```bash
   git clone <repository>
   cd oceanstuff
   pixi install
   ```
3. Connect USB4000 spectrometer

## First Run

Test the connection:
```bash
pixi run run
```

You should see a live spectrum plot. If you get a permissions error, set up udev rules:
https://python-seabreeze.readthedocs.io/en/latest/install.html#udev-rules

## Calibrate (Recommended)

For absolute irradiance measurements in µW/cm²:
```bash
pixi run calibrate
```

Go outside, point sensor at open sky (not directly at sun), press Enter. Creates `calibration.json`.

Without calibration, data is saved as raw counts.

## Collect Data

```bash
pixi run log 5      # Collect 5 measurements
pixi run log        # Run until Ctrl+C
```

Each file captures ~25 spectra over a 2.5-second window. Files saved to `data/`.

## View Results

```bash
pixi run plot
```

Shows individual spectra and mean with total irradiance statistics.

## Save Results

```bash
pixi run save "My experiment"
```

Saves plot to `results/My experiment.png` and moves data to `results/My experiment_data/`.

## Start Fresh

```bash
pixi run clear      # Delete data/*.csv
```

## Typical Workflow

1. `pixi run calibrate` (once, outdoors)
2. `pixi run log 10` (collect data)
3. `pixi run plot` (review)
4. `pixi run save "Description"` (archive)
5. `pixi run clear` (reset for next experiment)
