import logging
import threading
import time

logger = logging.getLogger("aditus.trigger")


class ClapDetector:
    def __init__(self, threshold: float = 0.15, callback=None):
        self._threshold = threshold
        self._callback = callback
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._stream = None
        self._np = None
        self._sd = None

        self._baseline = None
        self._prev_rms = 0.0
        self._peak_rms = None
        self._peak_time = 0.0
        self._sustain_count = 0
        self._in_decay_check = False
        self._clap_state = "WAITING"
        self._clap1_time = 0.0

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._stream:
            try:
                self._stream.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=3)
        self._stream = None
        self._thread = None

    def _audio_callback(self, indata, frames, time_info, status):
        if self._stop_event.is_set():
            raise self._sd.CallbackStop

        chunk = indata[:, 0]
        rms = self._np.sqrt(self._np.mean(chunk ** 2))
        now = time.time()

        if self._baseline is None:
            self._baseline = rms
        else:
            alpha = 0.999 if rms > self._baseline else 0.99
            self._baseline = alpha * self._baseline + (1 - alpha) * rms

        baseline = self._baseline or 1e-10
        db_above = 20 * self._np.log10(max(rms / max(baseline, 1e-10), 1e-10))
        attack_ratio = rms / max(self._prev_rms, 1e-10)
        self._prev_rms = rms

        if rms > 0.03 and db_above >= 10.0 and attack_ratio >= 2.5:
            self._peak_rms = rms
            self._peak_time = now
            self._sustain_count = 0
            self._in_decay_check = True
        elif self._in_decay_check:
            elapsed = now - self._peak_time
            if elapsed < 0.2:
                if rms > (self._peak_rms or 0) * 0.35:
                    self._sustain_count += 1
                    if self._sustain_count >= 3:
                        self._in_decay_check = False
                        self._peak_rms = None
                else:
                    self._in_decay_check = False
                    self._confirm_clap(self._peak_time)
                    self._peak_rms = None
            else:
                self._in_decay_check = False
                self._peak_rms = None

        if self._clap_state == "FIRST_SEEN" and (now - self._clap1_time) > 0.8:
            self._clap_state = "WAITING"

    def _confirm_clap(self, peak_time: float) -> None:
        if self._clap_state == "WAITING":
            self._clap_state = "FIRST_SEEN"
            self._clap1_time = peak_time
        elif self._clap_state == "FIRST_SEEN":
            elapsed = peak_time - self._clap1_time
            if 0.2 <= elapsed <= 0.8:
                self._clap_state = "WAITING"
                if self._callback:
                    self._callback()
            else:
                self._clap_state = "WAITING"

    def _run(self) -> None:
        try:
            import sounddevice as sd
            import numpy as np
            self._sd = sd
            self._np = np
        except ImportError:
            logger.warning("sounddevice or numpy not available, clap detection disabled")
            return
        try:
            self._stream = self._sd.InputStream(
                callback=self._audio_callback,
                samplerate=44100,
                channels=1,
                blocksize=1024,
            )
            self._stream.start()
            self._stop_event.wait()
        except Exception as e:
            logger.warning("Microphone not available: %s", e)
        finally:
            if self._stream:
                try:
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
