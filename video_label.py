from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel


class VideoLabel(QLabel):
    """A QLabel that keeps the last frame around and re-scales it to fit
    whenever the widget is resized, preserving aspect ratio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setStyleSheet('background-color: #202020;')
        self._image = None

    def set_image(self, image: QImage):
        self._image = image
        self._render()

    def clear_image(self):
        self._image = None
        self.clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render()

    def _render(self):
        if self._image is None:
            return
        pixmap = QPixmap.fromImage(self._image)
        scaled = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)
