from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QPushButton, QSpinBox,
    QVBoxLayout,
)

FORMAT_EXTENSIONS = {
    'MP4 (.mp4)': ('mp4', 'mp4'),
    'AVI (.avi)': ('avi', 'avi'),
    'QuickTime (.mov)': ('mov', 'mov'),
}


class ConvertDialog(QDialog):
    """Collects options for converting a TWV video to a standard container."""

    def __init__(self, parent, video_path, num_frames, source_fps):
        super().__init__(parent)
        self.setWindowTitle('Convert Video')
        self.setMinimumWidth(420)

        self._video_path = Path(video_path)
        default_output = self._video_path.with_suffix('.mp4')

        self.format_combo = QComboBox()
        self.format_combo.addItems(FORMAT_EXTENSIONS.keys())
        self.format_combo.currentTextChanged.connect(self._on_format_changed)

        self.output_edit = QLineEdit(str(default_output))
        browse_button = QPushButton('Browse…')
        browse_button.clicked.connect(self._browse)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit)
        output_row.addWidget(browse_button)

        self.fps_spin = QDoubleSpinBox()
        self.fps_spin.setRange(0.1, 1000.0)
        self.fps_spin.setDecimals(2)
        self.fps_spin.setValue(source_fps if source_fps and source_fps > 0 else 30.0)

        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, max(0, num_frames - 1))
        self.start_spin.setValue(0)

        self.end_spin = QSpinBox()
        self.end_spin.setRange(0, max(0, num_frames - 1))
        self.end_spin.setValue(max(0, num_frames - 1))

        self.overlay_check = QCheckBox('Burn in frame time as text overlay')
        self.overlay_check.setChecked(True)

        form = QFormLayout()
        form.addRow('Format:', self.format_combo)
        form.addRow('Output file:', output_row)
        form.addRow('Frame rate (fps):', self.fps_spin)
        form.addRow('Start frame:', self.start_spin)
        form.addRow('End frame (inclusive):', self.end_spin)
        form.addRow('', self.overlay_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_format_changed(self, label):
        _, ext = FORMAT_EXTENSIONS[label]
        self.output_edit.setText(str(Path(self.output_edit.text()).with_suffix(f'.{ext}')))

    def _browse(self):
        label = self.format_combo.currentText()
        _, ext = FORMAT_EXTENSIONS[label]
        path, _ = QFileDialog.getSaveFileName(
            self, 'Choose Output File', self.output_edit.text(),
            f'{label} (*.{ext})'
        )
        if path:
            self.output_edit.setText(path)

    def get_settings(self):
        label = self.format_combo.currentText()
        fmt, _ = FORMAT_EXTENSIONS[label]
        return {
            'output_path': self.output_edit.text(),
            'format': fmt,
            'fps': self.fps_spin.value(),
            'start_frame': self.start_spin.value(),
            'end_frame': self.end_spin.value(),
            'time_overlay': self.overlay_check.isChecked(),
        }
