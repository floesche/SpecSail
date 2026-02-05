# Quick Start

## Setup

1. Install pixi: https://pixi.sh
2. Clone and install:
   ```bash
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

## Calibrate (Optional)

For absolute irradiance measurements:
```bash
pixi run calibrate
```

Go outside, point sensor at open sky, press Enter. Creates `calibration.json`.

## Collect Data

```bash
pixi run log 5      # Collect 5 measurements
```

Each file captures a 2.5-second window. Files saved to `data/`.

## View Results

```bash
pixi run plot
```

## Save Results

```bash
pixi run save "My experiment"
```

Saves plot to `results/My experiment.png` and moves data to `results/My experiment_data/`.

## Start Fresh

```bash
pixi run clear      # Delete data/*.csv
```
