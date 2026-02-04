#!/usr/bin/env python3
"""Live spectrum viewer for Ocean Optics USB4000 spectrometer."""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import seabreeze
seabreeze.use("cseabreeze")
from seabreeze.spectrometers import Spectrometer, list_devices


def main():
    # List available devices
    devices = list_devices()
    if not devices:
        print("No spectrometer found. Make sure the USB4000 is connected.")
        print("You may need to set up udev rules. See:")
        print("  https://python-seabreeze.readthedocs.io/en/latest/install.html#udev-rules")
        return

    print(f"Found devices: {devices}")

    # Connect to the first available spectrometer
    spec = Spectrometer.from_first_available()
    print(f"Connected to: {spec.model}")

    # Set integration time (microseconds) - adjust as needed
    integration_time_ms = 100
    spec.integration_time_micros(integration_time_ms * 1000)
    print(f"Integration time: {integration_time_ms} ms")

    # Get wavelengths (x-axis)
    wavelengths = spec.wavelengths()

    # Set up the plot
    fig, ax = plt.subplots(figsize=(10, 6))
    line, = ax.plot(wavelengths, np.zeros_like(wavelengths), 'b-', lw=1)

    ax.set_xlabel('Wavelength (nm)')
    ax.set_ylabel('Intensity (counts)')
    ax.set_title(f'Live Spectrum - {spec.model}')
    ax.set_xlim(wavelengths.min(), wavelengths.max())
    ax.set_ylim(0, 65535)  # 16-bit ADC
    ax.grid(True, alpha=0.3)

    # Text for showing current max intensity
    info_text = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                        verticalalignment='top', fontfamily='monospace')

    def update(frame):
        """Update function for animation."""
        try:
            intensities = spec.intensities()
            line.set_ydata(intensities)

            # Auto-scale y-axis based on data
            max_intensity = intensities.max()
            ax.set_ylim(0, max(max_intensity * 1.1, 100))

            # Update info text
            max_idx = np.argmax(intensities)
            info_text.set_text(
                f'Max: {max_intensity:.0f} counts at {wavelengths[max_idx]:.1f} nm'
            )

            return line, info_text
        except Exception as e:
            print(f"Error reading spectrum: {e}")
            return line, info_text

    # Create animation (update every 100ms)
    ani = animation.FuncAnimation(fig, update, interval=100, blit=True, cache_frame_data=False)

    plt.tight_layout()
    print("Starting live view. Close the window to exit.")
    plt.show()

    # Cleanup
    spec.close()
    print("Spectrometer closed.")


if __name__ == "__main__":
    main()
