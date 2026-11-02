# TWV Viewer

PySide6 desktop app (macOS) for viewing and converting Aresis Tweez `.twv` videos.

## Commands

- Run: `uv run main.py [file.twv]` (or `./twv-viewer`)
- Build .app: `./build_app.sh` → `dist/TWV Viewer.app`
- Add deps: `uv add <pkg>`; build-only deps go in the `build` group. Never use pip or requirements.txt.

## Architecture

Flat layout, no package (`tool.uv.package = false`):
- `main.py`: `MainWindow` (playback via `QTimer`, sidebar, frame-rate estimation) and `Application` (turns macOS `FileOpen` events into a signal).
- `twv.py`: ctypes reader. Frame offset = `VideoHeaderSize + n * (FrameHeaderSize + W*H)`; 8-bit grayscale only. Keep parsing logic unchanged unless fixing a confirmed format bug.
- `converter.py`: `ConvertWorker` (QThread) opens its **own** `TwvVideo` handle, so don't share the viewer's file object across threads.
- `build.spec`: registers the `.twv` UTI/document type in Info.plist. Keep it in sync if bundle id or extension handling changes.

## Conventions

- Dependency is `PySide6-Essentials` (QtCore/QtGui/QtWidgets only), which keeps the bundle small. Don't import Qt add-on modules without switching packages deliberately.
- OpenCV is `opencv-python-headless`; Qt does all GUI work.
- Never commit `.twv` sample files, `build/` or `dist/`.
