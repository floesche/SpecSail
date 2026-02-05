#!/usr/bin/env python3
"""
Shared spectrum plotting functionality.

Used by plot_spectra.py and save_results.py.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_spectrum(filepath):
    """
    Load a spectrum CSV file and return the mean spectrum.

    Each CSV file may contain multiple individual spectra (one per column).
    Returns wavelengths, mean_values (1D array), and whether data is calibrated.
    """
    with open(filepath) as f:
        header = f.readline().strip()
    # Check for calibrated data (either old per-nm or new per-bin format)
    calibrated = "irradiance" in header

    data = np.genfromtxt(filepath, delimiter=',', skip_header=1)
    wavelengths = data[:, 0]

    # Handle both old format (single column) and new format (multiple columns)
    if data.ndim == 1 or data.shape[1] == 2:
        # Old format: single spectrum
        values = data[:, 1] if data.ndim > 1 else data
    else:
        # New format: multiple spectra (one per column after wavelength)
        # Average across all spectra in this file
        values = np.nanmean(data[:, 1:], axis=1)

    return wavelengths, values, calibrated


def load_all_spectra(data_dir):
    """
    Load all spectrum CSV files from a directory.

    Returns (wavelengths, all_values, calibrated, csv_files) or (None, None, None, []) if no files found.
    all_values has shape [n_files, n_wavelengths] - one mean spectrum per file.
    """
    csv_files = sorted(Path(data_dir).glob("spectrum_*.csv"))

    if not csv_files:
        return None, None, None, []

    all_values = []
    wavelengths = None
    calibrated = None

    for filepath in csv_files:
        wl, values, is_calibrated = load_spectrum(filepath)
        if wavelengths is None:
            wavelengths = wl
            calibrated = is_calibrated
        all_values.append(values)

    all_values = np.array(all_values)
    return wavelengths, all_values, calibrated, csv_files


def create_spectrum_plot(wavelengths, all_values, calibrated, n_files, title=None):
    """
    Create a spectrum plot figure.

    Returns (fig, ax, mean_safe, total_values, mean_total, total_label, total_unit).
    """
    # Set labels based on data type
    if calibrated:
        y_label = 'Irradiance (µW/cm² per 5nm bin)'
        default_title = 'Calibrated Spectra'
        total_label = 'Total Irradiance'
        total_unit = 'µW/cm²'
    else:
        y_label = 'Intensity (counts)'
        default_title = 'Raw Spectra'
        total_label = 'Integrated Intensity'
        total_unit = 'counts·nm'

    if title is None:
        title = default_title

    # Calculate mean spectrum (ignoring NaN)
    mean_values = np.nanmean(all_values, axis=0)

    # Calculate total irradiance (sum of all valid bins for calibrated data)
    def sum_valid(values):
        """Sum only valid values (not NaN, not zero/negative)."""
        valid = ~np.isnan(values) & (values > 0)
        return np.sum(values[valid])

    if calibrated:
        # Data is already in µW/cm² per bin, so just sum
        total_values = [sum_valid(v) for v in all_values]
        mean_total = sum_valid(mean_values)
    else:
        # Raw data: integrate over wavelength
        def integrate_valid(values, wl):
            valid = ~np.isnan(values) & (values > 0)
            if np.sum(valid) < 2:
                return 0.0
            return np.trapezoid(values[valid], wl[valid])
        total_values = [integrate_valid(v, wavelengths) for v in all_values]
        mean_total = integrate_valid(mean_values, wavelengths)

    # Set up the plot
    fig, ax = plt.subplots(figsize=(16, 10))

    # Plot individual spectra with low alpha
    clip_floor = 1e-6 if calibrated else 1e-1
    for values in all_values:
        # Replace NaN/zeros/negatives with small value for log scale
        values_safe = np.where(np.isnan(values) | (values <= 0), clip_floor, values)
        ax.plot(wavelengths, values_safe, alpha=0.3, lw=0.8, color='steelblue')

    # Plot mean spectrum
    mean_safe = np.where(np.isnan(mean_values) | (mean_values <= 0), clip_floor, mean_values)
    ax.plot(wavelengths, mean_safe, color='darkred', lw=2, label=f'Mean spectrum (n={n_files})')

    ax.set_xlabel('Wavelength (nm)', fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_yscale('log')
    ax.set_ylim(bottom=1e-1)
    ax.set_xlim(wavelengths.min(), wavelengths.max())
    ax.grid(True, alpha=0.3, which='both')
    ax.legend(loc='upper right')

    # Find and annotate local maxima
    local_max_indices = []
    for i in range(1, len(mean_safe) - 1):
        if mean_safe[i] > mean_safe[i-1] and mean_safe[i] > mean_safe[i+1]:
            if mean_safe[i] > 0.5:
                local_max_indices.append(i)

    # Filter to keep only prominent peaks
    prominent_peaks = []
    for i in local_max_indices:
        left_min = np.min(mean_safe[max(0, i-5):i])
        right_min = np.min(mean_safe[i+1:min(len(mean_safe), i+6)])
        prominence = mean_safe[i] / max(left_min, right_min)
        if prominence > 1.2:
            prominent_peaks.append(i)

    # Annotate local maxima with vertical lines and wavelength labels
    # Find the highest peak value among prominent peaks
    if prominent_peaks:
        highest_peak_val = max(mean_safe[idx] for idx in prominent_peaks)

        # Need to draw canvas to get accurate transforms
        fig.canvas.draw()

        # Convert highest peak to display coordinates and add 50 pixels
        highest_display = ax.transData.transform((wavelengths[0], highest_peak_val))
        label_y_display = highest_display[1] + 50

        for idx in prominent_peaks:
            wl = wavelengths[idx]

            # Convert label position back to data coordinates
            label_y_data = ax.transData.inverted().transform((0, label_y_display))[1]

            # Draw 10 pixel vertical line attached below the label
            line_top_display = label_y_display
            line_bottom_display = label_y_display - 10
            line_top_data = ax.transData.inverted().transform((0, line_top_display))[1]
            line_bottom_data = ax.transData.inverted().transform((0, line_bottom_display))[1]

            ax.plot([wl, wl], [line_bottom_data, line_top_data], color='green', lw=1, alpha=0.7)
            ax.text(wl, label_y_data, f'{wl:.0f}',
                    color='green', fontsize=8, ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8, edgecolor='green'))

    # Add total irradiance text in top left corner
    stats_text = (
        f"{total_label}: {mean_total:.2f} {total_unit}\n"
        f"Range: {min(total_values):.2f} – {max(total_values):.2f} {total_unit}\n"
        f"Integration: 2500ms"
    )
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            fontsize=10, fontfamily='monospace', verticalalignment='top',
            horizontalalignment='left', color='#336699',
            bbox=dict(boxstyle='round', facecolor='#EEEEEE', alpha=0.8))

    plt.tight_layout()

    return fig, ax, mean_safe, total_values, mean_total, total_label, total_unit
