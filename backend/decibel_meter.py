#!/usr/bin/env python3
"""
A-weighted Decibel Meter

Usage:
    # As a library
    @see main() -- bellow

    # As CLI
    python audio_db_meter.py --list
    python audio_db_meter.py --device 0
"""
import numpy as np
from scipy import signal
from dataclasses import dataclass
from typing import Optional, Iterator
from collections import deque
from abc import ABC, abstractmethod
import threading
import pyaudio
import time

# Time Weighting Constants 
TIME_WEIGHTING_FAST = 0.125  # 125ms - responsive, general measurement
TIME_WEIGHTING_SLOW = 1.0    # 1000ms - averaged, less fluctuation


@dataclass
class SoundLevel:
    """Single audio level measurement."""
    db_a: float = 0.0     # A-weighted level in dB(A)
    db_linear: float = 0.0   # Unweighted level in dB
    peak: float = 0.0        # Peak amplitude (0.0 to 1.0)


@dataclass
class AudioDeviceInfo:
    """Audio input device information."""
    index: int
    name: str
    channels: int
    sample_rate: int
    is_default: bool



def create_a_weighting_filter(sample_rate: int) -> np.ndarray:
    """
    Create A-weighting filter coefficients for given sample rate.
    Returns second-order sections (SOS) array for use with scipy.signal.sosfilt.
    """
    # A-weighting corner frequencies (Hz)
    f1, f2, f3, f4 = 20.598997, 107.65265, 737.86223, 12194.217

    # Convert to angular frequencies (rad/s)
    w1, w2, w3, w4 = [2 * np.pi * f for f in (f1, f2, f3, f4)]

    # Analog prototype: 4 zeros at origin, 6 poles
    zeros_analog = [0, 0, 0, 0]
    poles_analog = [-w1, -w1, -w4, -w4, -w2, -w3]
    gain_analog = (w4 ** 2) * (w1 ** 2)

    # Convert to digital filter via bilinear transform
    z, p, k = signal.bilinear_zpk(zeros_analog, poles_analog, gain_analog, sample_rate)
    sos = signal.zpk2sos(z, p, k)

    # Normalize gain to 0 dB at 1 kHz
    w_1khz = 2 * np.pi * 1000 / sample_rate
    _, h = signal.sosfreqz(sos, worN=[w_1khz])
    sos[0, :3] /= np.abs(h[0])

    return sos


def calculate_decibel(samples: np.ndarray, reference_db: float = 94.0) -> float:
    """Calculate dB SPL (sound pressure level) from audio samples. Returns -inf for silence."""
    rms = np.sqrt(np.mean(samples ** 2))
    if rms <= 0:
        return float('-inf')
    return 20 * np.log10(rms) + reference_db


def process_audio(samples: np.ndarray, sos_filter: np.ndarray,
                  calibration_db: float = 0.0) -> SoundLevel:
    filtered = signal.sosfilt(sos_filter, samples)

    return SoundLevel(
        db_a=calculate_decibel(filtered) + calibration_db,
        db_linear=calculate_decibel(samples) + calibration_db,
        peak=float(np.max(np.abs(samples)))
    )


# =============================================================================
# Device Discovery
# =============================================================================

def list_input_devices() -> list[AudioDeviceInfo]:
    """Return list of available audio input devices."""
    p = pyaudio.PyAudio()
    devices = []

    try:
        default_index = p.get_default_input_device_info()['index']
    except IOError:
        default_index = -1

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            devices.append(AudioDeviceInfo(
                index=i,
                name=info['name'],
                channels=info['maxInputChannels'],
                sample_rate=int(info['defaultSampleRate']),
                is_default=(i == default_index)
            ))

    p.terminate()
    return devices


# =============================================================================
# Audio Meter (Main Interface)
# =============================================================================

class DecibelMeterABC(ABC):
     @abstractmethod    
     def readSoundLevel(self) -> SoundLevel:
         pass

class DummyDecibelMeter(DecibelMeterABC):
    def readSoundLevel(self) -> SoundLevel:
        time.sleep(0.5)
        return SoundLevel(0, 0, 0)

    def _stop(self) -> None:
        pass


class DecibelMeter(DecibelMeterABC):
    """
    Real-time A-weighted decibel meter.

    Example:
        with  AudioMeter(device_index=0) as meter:
            while True:
                reading = meter.read()
                print(f"{reading.db_a:.1f} dB(A)")


    """

    def __init__(self, device_index: int = 0,
                 time_window: float = TIME_WEIGHTING_FAST,
                 calibration_db: float = 0.0):
        self.device_index = device_index
        self.time_window = time_window
        self.calibration_db = calibration_db

        self._chunk_size: int = 0
        self._pyaudio = pyaudio.PyAudio()

        try:
            device_info = self._pyaudio.get_device_info_by_index(self.device_index)
            self.sample_rate = int(device_info['defaultSampleRate'])

            self._chunk_size = int(self.sample_rate * self.time_window)
            self._filter = create_a_weighting_filter(self.sample_rate)

            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self._chunk_size
            )
        except (OSError, ValueError) as e:
            self._pyaudio.terminate()
            raise ValueError(f"Cannot open audio device (index={device_index}): {e}") from e

    def _stop(self) -> None:
        self._stream.stop_stream()
        self._stream.close()
        self._pyaudio.terminate()

    def readSoundLevel(self) -> SoundLevel:
        raw = self._stream.read(self._chunk_size, exception_on_overflow=False)
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0

        return process_audio(samples, self._filter, self.calibration_db)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._stop()


class ThreadedDecibelMeter:
    """
    Thread-safe wrapper around DecibelMeter that continuously reads
    audio levels in a background thread and stores them in a bounded deque.
    """

    def __init__(self, meter: DecibelMeterABC, max_readings: int = 100):
        self._meter = meter
        self._readings: deque[SoundLevel] = deque(maxlen=max_readings)
        self._lock = threading.Lock()
        self._lock_meter = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()

    def start(self) -> None:
        self._running.set()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()



    def stop(self) -> None:
        self._running.clear()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def set_decibel_meter(self, meter: DecibelMeterABC):
        with self._lock_meter:
            self._meter = meter

    def _read_loop(self) -> None:
        while self._running.is_set():
            with self._lock_meter:
                reading = self._meter.readSoundLevel()
            with self._lock:
                self._readings.append(reading)

    def get_last_n_readings(self, n: int) -> list[SoundLevel]:
        with self._lock:
            items = list(self._readings)
        return items[-n:]

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        self._meter._stop()



def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="A-weighted Decibel Meter")
    parser.add_argument('--list', '-l', action='store_true', help='List audio devices')
    parser.add_argument('--device', '-d', type=int, help='Device index', default=0)
    parser.add_argument('--time-window', '-t', type=float, default=TIME_WEIGHTING_FAST,
                        help=f'Time window in seconds (Fast={TIME_WEIGHTING_FAST}, Slow={TIME_WEIGHTING_SLOW})')
    parser.add_argument('--calibration', '-c', type=float, default=0.0, help='Calibration offset (dB)')
    args = parser.parse_args()

    if args.list:
        print("\nAudio Input Devices:")
        print("-" * 50)
        for dev in list_input_devices():
            default_marker = " [DEFAULT]" if dev.is_default else ""
            print(f"  {dev.index}: {dev.name} ({dev.sample_rate} Hz){default_marker}")
        return 0

    import time

    print(f"\nStarting dB meter (Ctrl+C to stop)...")
    print(f"{'dB(A)':>10} {'dB(Lin)':>10} {'Peak':>8}  Level")
    print("-" * 60)

    decibel_meter = DecibelMeter(device_index=args.device, time_window=args.time_window, calibration_db=args.calibration)
    with ThreadedDecibelMeter(decibel_meter) as threaded_meter:
        while True:
            readings = threaded_meter.get_last_n_readings(1)
            if readings:
                reading = readings[0]
                bar_len = int(max(0, min(40, (reading.db_a - 30) / 1.5)))
                bar = "█" * bar_len + "░" * (40 - bar_len)
                print(f"\r{reading.db_a:>8.1f}  {reading.db_linear:>8.1f}  {reading.peak:>8.3f}  [{bar}]", end="")
            time.sleep(0.05)


    return 0


if __name__ == "__main__":
    main()
