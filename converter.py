"""
Conversion helpers for TWV videos: single-frame export and export to
standard video containers (MP4 / AVI), run off the UI thread.
"""
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from twv import TwvVideo

FOURCC_BY_FORMAT = {
    'mp4': 'mp4v',
    'avi': 'MJPG',
    'mov': 'mp4v',
}


def add_time_overlay(image_bgr, text, position=(10, 30), font_scale=0.7, color=(255, 255, 255), thickness=2):
    """Draw a time label with a filled background rectangle onto a BGR image (in place)."""
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    background_tl = (position[0] - 5, position[1] - text_size[1] - 10)
    background_br = (position[0] + text_size[0] + 5, position[1] + 5)
    cv2.rectangle(image_bgr, background_tl, background_br, (0, 0, 0), -1)
    cv2.putText(image_bgr, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    return image_bgr


def save_frame(image, path):
    """Save a single grayscale frame (numpy uint8 array) to an image file."""
    ok = cv2.imwrite(str(path), image)
    if not ok:
        raise IOError(f'Could not write image to {path}')


class ConvertWorker(QThread):
    """Converts a TWV file to a standard video container in the background."""

    progress = Signal(int, int)        # (current_frame, total_frames)
    finished_ok = Signal(str)          # output path
    failed = Signal(str)               # error message

    def __init__(self, source_path, output_path, fmt, fps, start_frame, end_frame,
                 time_overlay=True, parent=None):
        super().__init__(parent)
        self.source_path = source_path
        self.output_path = output_path
        self.fmt = fmt
        self.fps = fps
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.time_overlay = time_overlay
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        video = None
        writer = None
        try:
            # Open our own file handle so this doesn't disturb playback in the UI.
            video = TwvVideo(self.source_path)

            end = min(self.end_frame, video.recordedFrames - 1)
            start = max(0, min(self.start_frame, end))
            total = end - start + 1

            fourcc = cv2.VideoWriter_fourcc(*FOURCC_BY_FORMAT.get(self.fmt, 'mp4v'))
            writer = cv2.VideoWriter(str(self.output_path), fourcc, self.fps,
                                      (video.imageW, video.imageH))
            if not writer.isOpened():
                raise RuntimeError('Could not open video writer for output file')

            for i, frame_num in enumerate(range(start, end + 1)):
                if self._cancelled:
                    break

                twv_image = video.frame(frame_num)
                image_bgr = cv2.cvtColor(twv_image.image, cv2.COLOR_GRAY2BGR)

                if self.time_overlay:
                    add_time_overlay(image_bgr, f'Time: {twv_image.time:.3f}s')

                writer.write(image_bgr)

                if i % 10 == 0 or i == total - 1:
                    self.progress.emit(i + 1, total)

            if self._cancelled:
                self.failed.emit('Conversion cancelled')
            else:
                self.finished_ok.emit(str(self.output_path))

        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            if writer is not None:
                writer.release()
            if video is not None:
                video.close()
