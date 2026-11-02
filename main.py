#!/usr/bin/env python3
"""TWV Viewer — a small macOS app for viewing, exporting and converting
Aresis Tweez .twv video files."""
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QEvent
from PySide6.QtGui import QImage, QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QSlider,
    QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout, QComboBox,
    QCheckBox, QFileDialog, QMessageBox, QProgressDialog, QFrame,
    QSizePolicy, QStatusBar,
)

from twv import TwvVideo
from converter import ConvertWorker, save_frame
from convert_dialog import ConvertDialog
from video_label import VideoLabel

APP_NAME = 'TWV Viewer'
SPEED_OPTIONS = [0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]


def numpy_to_qimage(image):
    image = image if image.flags['C_CONTIGUOUS'] else image.copy()
    h, w = image.shape
    return QImage(image.data, w, h, w, QImage.Format_Grayscale8).copy()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 720)
        self.setAcceptDrops(True)

        self.video = None
        self.video_path = None
        self.current_index = 0
        self.current_image = None
        self.playing = False
        self.source_fps = 30.0
        self._convert_worker = None
        self._progress_dialog = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance_frame)

        self._build_ui()
        self._build_menu()
        self._set_controls_enabled(False)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QWidget()
        root_layout = QHBoxLayout(central)

        # --- Video area (central) ---
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = VideoLabel()
        video_layout.addWidget(self.video_label, stretch=1)

        controls_layout = QHBoxLayout()
        self.play_button = QPushButton('Play')
        self.play_button.clicked.connect(self.toggle_play)
        self.prev_button = QPushButton('◀◀')
        self.prev_button.clicked.connect(self.step_prev)
        self.next_button = QPushButton('▶▶')
        self.next_button.clicked.connect(self.step_next)

        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.sliderPressed.connect(self._pause_for_scrub)
        self.frame_slider.sliderMoved.connect(self.show_frame)

        self.frame_label = QLabel('0 / 0')
        self.frame_label.setMinimumWidth(160)

        self.speed_combo = QComboBox()
        for s in SPEED_OPTIONS:
            self.speed_combo.addItem(f'{s:g}x', s)
        self.speed_combo.setCurrentIndex(SPEED_OPTIONS.index(1.0))
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)

        self.loop_check = QCheckBox('Loop')
        self.loop_check.setChecked(True)

        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.next_button)
        controls_layout.addWidget(self.frame_slider, stretch=1)
        controls_layout.addWidget(self.frame_label)
        controls_layout.addWidget(self.speed_combo)
        controls_layout.addWidget(self.loop_check)

        video_layout.addLayout(controls_layout)

        # --- Sidebar ---
        sidebar = QWidget()
        sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)

        self.open_button = QPushButton('Open Video…')
        self.open_button.clicked.connect(self.open_file_dialog)
        sidebar_layout.addWidget(self.open_button)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        sidebar_layout.addWidget(line)

        frame_box = QGroupBox('Current Frame')
        frame_form = QFormLayout(frame_box)
        self.info_frame_num = QLabel('–')
        self.info_frame_time = QLabel('–')
        self.info_laser_power = QLabel('–')
        frame_form.addRow('Frame #:', self.info_frame_num)
        frame_form.addRow('Time:', self.info_frame_time)
        frame_form.addRow('Laser power:', self.info_laser_power)
        self.export_frame_button = QPushButton('Export Frame…')
        self.export_frame_button.clicked.connect(self.export_current_frame)
        frame_form.addRow(self.export_frame_button)
        sidebar_layout.addWidget(frame_box)

        convert_box = QGroupBox('Convert')
        convert_layout = QVBoxLayout(convert_box)
        self.convert_button = QPushButton('Convert Video…')
        self.convert_button.clicked.connect(self.open_convert_dialog)
        convert_layout.addWidget(self.convert_button)
        sidebar_layout.addWidget(convert_box)

        info_box = QGroupBox('Video Info')
        info_form = QFormLayout(info_box)
        self.info_file = QLabel('–')
        self.info_file.setWordWrap(True)
        self.info_resolution = QLabel('–')
        self.info_frames = QLabel('–')
        self.info_fps = QLabel('–')
        self.info_exposure = QLabel('–')
        self.info_gain = QLabel('–')
        info_form.addRow('File:', self.info_file)
        info_form.addRow('Resolution:', self.info_resolution)
        info_form.addRow('Frames:', self.info_frames)
        info_form.addRow('Frame rate:', self.info_fps)
        info_form.addRow('Exposure:', self.info_exposure)
        info_form.addRow('Gain:', self.info_gain)
        sidebar_layout.addWidget(info_box)

        sidebar_layout.addStretch(1)

        root_layout.addWidget(video_container, stretch=1)
        root_layout.addWidget(sidebar)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

    def _build_menu(self):
        file_menu = self.menuBar().addMenu('&File')

        open_action = QAction('Open…', self, shortcut=QKeySequence.Open)
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)

        export_action = QAction('Export Current Frame…', self, shortcut='Ctrl+E')
        export_action.triggered.connect(self.export_current_frame)
        file_menu.addAction(export_action)

        convert_action = QAction('Convert Video…', self, shortcut='Ctrl+Shift+E')
        convert_action.triggered.connect(self.open_convert_dialog)
        file_menu.addAction(convert_action)

        file_menu.addSeparator()
        quit_action = QAction('Quit', self, shortcut=QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        playback_menu = self.menuBar().addMenu('&Playback')
        play_action = QAction('Play/Pause', self, shortcut='Space')
        play_action.triggered.connect(self.toggle_play)
        playback_menu.addAction(play_action)

        next_action = QAction('Next Frame', self, shortcut='Right')
        next_action.triggered.connect(self.step_next)
        playback_menu.addAction(next_action)

        prev_action = QAction('Previous Frame', self, shortcut='Left')
        prev_action.triggered.connect(self.step_prev)
        playback_menu.addAction(prev_action)

    # ------------------------------------------------------------ File I/O
    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Open TWV Video', '', 'TWV Video (*.twv);;All Files (*)'
        )
        if path:
            self.open_file(path)

    # Header FrameRate is sometimes 0 or otherwise not trustworthy (seen in
    # real capture files), so cross-check it against actual frame timestamps
    # and fall back to (frames - 1) / duration when it's missing or far off.
    FPS_MISMATCH_TOLERANCE = 0.15

    def _determine_frame_rate(self, video):
        header_fps = getattr(video.frameData, 'FrameRate', 0.0) or 0.0

        computed_fps = None
        if video.recordedFrames > 1:
            try:
                t_first = video.frame(0).time
                t_last = video.frame(video.recordedFrames - 1).time
                duration = t_last - t_first
                if duration > 0:
                    computed_fps = (video.recordedFrames - 1) / duration
            except Exception:  # noqa: BLE001
                computed_fps = None

        if computed_fps and computed_fps > 0:
            mismatch = header_fps <= 0 or (
                abs(header_fps - computed_fps) / computed_fps > self.FPS_MISMATCH_TOLERANCE
            )
            if mismatch:
                return computed_fps, True
            return header_fps, False

        if header_fps > 0:
            return header_fps, False

        return 30.0, False

    def open_file(self, path):
        path = str(path)
        if not os.path.exists(path):
            QMessageBox.warning(self, APP_NAME, f'File not found:\n{path}')
            return

        self.timer.stop()
        self.playing = False
        self.play_button.setText('Play')

        if self.video is not None:
            self.video.close()
            self.video = None

        try:
            video = TwvVideo(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, APP_NAME, f'Could not open file:\n{exc}')
            return

        self.video = video
        self.video_path = path

        self.source_fps, fps_is_estimated = self._determine_frame_rate(video)

        self.frame_slider.blockSignals(True)
        self.frame_slider.setMaximum(max(0, video.recordedFrames - 1))
        self.frame_slider.setValue(0)
        self.frame_slider.blockSignals(False)

        self.setWindowTitle(f'{APP_NAME} — {Path(path).name}')
        self.info_file.setText(Path(path).name)
        self.info_resolution.setText(f'{video.imageW} × {video.imageH}')
        self.info_frames.setText(str(video.recordedFrames))
        fps_text = f'{self.source_fps:.3f} fps'
        if fps_is_estimated:
            fps_text += ' (estimated from frame timestamps)'
        self.info_fps.setText(fps_text)
        self.info_exposure.setText(f'{getattr(video.frameData, "Exposure", 0.0):.4f} ms')
        self.info_gain.setText(f'{getattr(video.frameData, "Gain", 0.0):.3f}')

        self._set_controls_enabled(True)
        self.show_frame(0)
        self.statusBar().showMessage(f'Opened {path}', 5000)

    # -------------------------------------------------------------- Frames
    def show_frame(self, index):
        if self.video is None:
            return
        index = max(0, min(index, self.video.recordedFrames - 1))
        try:
            twv_image = self.video.frame(index)
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(f'Failed to read frame {index}: {exc}', 5000)
            return

        self.current_index = index
        self.current_image = twv_image.image

        self.video_label.set_image(numpy_to_qimage(twv_image.image))

        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(index)
        self.frame_slider.blockSignals(False)

        self.frame_label.setText(f'{index + 1} / {self.video.recordedFrames}')
        self.info_frame_num.setText(str(index))
        self.info_frame_time.setText(f'{twv_image.time:.3f} s')
        laser = twv_image.laser_power
        self.info_laser_power.setText(f'{laser:.4f}' if laser is not None else '–')

    def step_next(self):
        self._pause_for_scrub()
        if self.video is not None:
            self.show_frame(self.current_index + 1)

    def step_prev(self):
        self._pause_for_scrub()
        if self.video is not None:
            self.show_frame(self.current_index - 1)

    def _pause_for_scrub(self):
        if self.playing:
            self.toggle_play()

    # ----------------------------------------------------------- Playback
    def toggle_play(self):
        if self.video is None:
            return
        self.playing = not self.playing
        if self.playing:
            if self.current_index >= self.video.recordedFrames - 1:
                self.show_frame(0)
            self.play_button.setText('Pause')
            self._restart_timer()
        else:
            self.timer.stop()
            self.play_button.setText('Play')

    def _on_speed_changed(self):
        if self.playing:
            self._restart_timer()

    def _restart_timer(self):
        speed = self.speed_combo.currentData()
        effective_fps = max(0.1, self.source_fps * speed)
        interval_ms = max(1, round(1000.0 / effective_fps))
        self.timer.start(interval_ms)

    def _advance_frame(self):
        if self.video is None:
            return
        next_index = self.current_index + 1
        if next_index >= self.video.recordedFrames:
            if self.loop_check.isChecked():
                next_index = 0
            else:
                self.toggle_play()
                return
        self.show_frame(next_index)

    # ------------------------------------------------------------- Export
    def export_current_frame(self):
        if self.video is None or self.current_image is None:
            return
        default_name = f'{Path(self.video_path).stem}_frame{self.current_index:06d}.png'
        default_path = str(Path(self.video_path).parent / default_name)
        path, _ = QFileDialog.getSaveFileName(
            self, 'Export Frame', default_path,
            'PNG Image (*.png);;TIFF Image (*.tiff);;JPEG Image (*.jpg);;Bitmap (*.bmp)'
        )
        if not path:
            return
        try:
            save_frame(self.current_image, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, APP_NAME, f'Could not save frame:\n{exc}')
            return
        self.statusBar().showMessage(f'Saved frame to {path}', 5000)

    # ------------------------------------------------------------ Convert
    def open_convert_dialog(self):
        if self.video is None:
            return
        dialog = ConvertDialog(
            self, video_path=self.video_path,
            num_frames=self.video.recordedFrames,
            source_fps=self.source_fps,
        )
        if dialog.exec() != ConvertDialog.Accepted:
            return

        settings = dialog.get_settings()
        if not settings['output_path']:
            QMessageBox.warning(self, APP_NAME, 'Please choose an output file.')
            return

        total = settings['end_frame'] - settings['start_frame'] + 1
        self._progress_dialog = QProgressDialog('Converting video…', 'Cancel', 0, total, self)
        self._progress_dialog.setWindowTitle('Converting')
        self._progress_dialog.setWindowModality(Qt.WindowModal)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setValue(0)

        worker = ConvertWorker(
            source_path=self.video_path,
            output_path=settings['output_path'],
            fmt=settings['format'],
            fps=settings['fps'],
            start_frame=settings['start_frame'],
            end_frame=settings['end_frame'],
            time_overlay=settings['time_overlay'],
        )
        worker.progress.connect(lambda i, n: self._progress_dialog.setValue(i))
        worker.finished_ok.connect(self._on_convert_finished)
        worker.failed.connect(self._on_convert_failed)
        self._progress_dialog.canceled.connect(worker.cancel)

        self._convert_worker = worker
        worker.start()

    def _on_convert_finished(self, output_path):
        if self._progress_dialog is not None:
            self._progress_dialog.close()
        QMessageBox.information(self, APP_NAME, f'Conversion complete:\n{output_path}')
        self._convert_worker = None

    def _on_convert_failed(self, message):
        if self._progress_dialog is not None:
            self._progress_dialog.close()
        if message != 'Conversion cancelled':
            QMessageBox.critical(self, APP_NAME, f'Conversion failed:\n{message}')
        self._convert_worker = None

    # ------------------------------------------------------------- Misc
    def _set_controls_enabled(self, enabled):
        for widget in (self.play_button, self.prev_button, self.next_button,
                       self.frame_slider, self.speed_combo, self.loop_check,
                       self.export_frame_button, self.convert_button):
            widget.setEnabled(enabled)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.twv'):
                self.open_file(path)
                break

    def closeEvent(self, event):
        self.timer.stop()
        if self._convert_worker is not None and self._convert_worker.isRunning():
            self._convert_worker.cancel()
            self._convert_worker.wait(3000)
        if self.video is not None:
            self.video.close()
        super().closeEvent(event)


class Application(QApplication):
    """QApplication subclass that turns macOS 'Open With' events (double-clicking
    a .twv file while the app is already running) into a Qt signal."""
    fileOpened = Signal(str)

    def event(self, event):
        if event.type() == QEvent.FileOpen:
            self.fileOpened.emit(event.file())
            return True
        return super().event(event)


def main():
    app = Application(sys.argv)
    app.setApplicationName(APP_NAME)

    window = MainWindow()
    app.fileOpened.connect(window.open_file)
    window.show()

    # Cold-start: a file path may have been passed as a CLI argument
    # (e.g. via PyInstaller's argv_emulation on macOS, or `open -a`).
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args and os.path.exists(args[0]):
        QTimer.singleShot(0, lambda: window.open_file(args[0]))

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
