"""Draw the app icon (an eye) with QPainter and write icon.icns.

Usage: uv run make_icon.py   (requires macOS `iconutil`)
"""

import os
import shutil
import subprocess
import tempfile

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QImage, QLinearGradient, QPainter,
    QPainterPath, QPen, QRadialGradient,
)

SIZE = 1024


def draw_icon() -> QImage:
    img = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    # Rounded-square background, inset per Apple's icon grid (824 of 1024).
    inset = 100
    bg = QRectF(inset, inset, SIZE - 2 * inset, SIZE - 2 * inset)
    grad = QLinearGradient(bg.topLeft(), bg.bottomLeft())
    grad.setColorAt(0, QColor("#2b3a67"))
    grad.setColorAt(1, QColor("#0f1530"))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawRoundedRect(bg, 185, 185)

    cx, cy = SIZE / 2, SIZE / 2
    w, h = 300, 190  # half-width and half-height of the eye

    # Almond-shaped eye white.
    eye = QPainterPath()
    eye.moveTo(cx - w, cy)
    eye.cubicTo(cx - w * 0.45, cy - h * 1.33, cx + w * 0.45, cy - h * 1.33, cx + w, cy)
    eye.cubicTo(cx + w * 0.45, cy + h * 1.33, cx - w * 0.45, cy + h * 1.33, cx - w, cy)
    white = QRadialGradient(QPointF(cx, cy), w)
    white.setColorAt(0, QColor("#ffffff"))
    white.setColorAt(1, QColor("#d9e2f2"))
    p.setBrush(white)
    p.drawPath(eye)

    # Iris and pupil, clipped to the eye outline.
    p.save()
    p.setClipPath(eye)
    r_iris = 150
    iris = QRadialGradient(QPointF(cx, cy), r_iris)
    iris.setColorAt(0.0, QColor("#7ff0e0"))
    iris.setColorAt(0.55, QColor("#1fa3b8"))
    iris.setColorAt(1.0, QColor("#0b4f6c"))
    p.setBrush(iris)
    p.drawEllipse(QPointF(cx, cy), r_iris, r_iris)
    p.setBrush(QColor("#0a0d1a"))
    p.drawEllipse(QPointF(cx, cy), 68, 68)
    p.setBrush(QColor(255, 255, 255, 230))
    p.drawEllipse(QPointF(cx - 45, cy - 50), 30, 30)
    p.setBrush(QColor(255, 255, 255, 140))
    p.drawEllipse(QPointF(cx + 55, cy + 40), 13, 13)
    p.restore()

    # Outline.
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#0a0d1a"), 22, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(eye)

    p.end()
    return img


def main() -> None:
    img = draw_icon()
    here = os.path.dirname(os.path.abspath(__file__))
    tmp = tempfile.mkdtemp()
    iconset = os.path.join(tmp, "icon.iconset")
    os.mkdir(iconset)
    for s in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            px = s * scale
            name = f"icon_{s}x{s}{'@2x' if scale == 2 else ''}.png"
            img.scaled(px, px, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(
                os.path.join(iconset, name)
            )
    img.save(os.path.join(here, "icon.png"))
    subprocess.run(
        ["iconutil", "-c", "icns", iconset, "-o", os.path.join(here, "icon.icns")],
        check=True,
    )
    shutil.rmtree(tmp)
    print("Wrote icon.icns and icon.png")


if __name__ == "__main__":
    main()
