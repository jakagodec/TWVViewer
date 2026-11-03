# TWV Viewer

A small macOS app for viewing, exporting frames from, and converting Aresis
Tweez `.twv` video files.

- **Central pane:** video display and playback controls (play/pause,
  previous/next frame, scrub slider, speed, loop).
- **Sidebar:** Open, Export Current Frame, Convert Video, plus file and frame
  info (resolution, frame count, frame rate, exposure, gain, laser power).
- **Frame export:** PNG, TIFF, JPEG, BMP.
- **Video conversion:** MP4, AVI, MOV, with adjustable fps, frame range, and
  an optional burned-in time label. Conversion runs on a background thread
  with its own file handle, so the viewer stays responsive.
- **Frame rate correction:** the header's `FrameRate` field is unreliable on
  some recordings (it can read `0.0`). The app cross-checks it against the
  first/last frame timestamps and uses the computed rate, labeled
  "(estimated from frame timestamps)", whenever the header value is missing
  or more than 15% off. This rate drives both playback speed and the default
  conversion fps.

## Requirements

- macOS
- [uv](https://docs.astral.sh/uv/) (`brew install uv` or
  `curl -LsSf https://astral.sh/uv/install.sh | sh`)

uv installs the right Python version and all dependencies automatically on
first run.

## Running from source

```sh
git clone https://github.com/jakagodec/TWVViewer.git
cd TWVViewer
./twv-viewer path/to/video.twv     # the file argument is optional
```

### Shortcut: run it from anywhere

`twv-viewer` resolves its own location, so you can symlink it onto your
`PATH`:

```sh
ln -s "$PWD/twv-viewer" ~/.local/bin/twv-viewer
twv-viewer ~/Data/experiment.twv
```

Equivalent commands: `./run_dev.sh [file]` or `uv run main.py [file]`.

## Building the app bundle

```sh
./build_app.sh
```

This installs PyInstaller (the `build` dependency group) and produces
`dist/TWV Viewer.app`. Move it wherever you keep apps:

```sh
mv "dist/TWV Viewer.app" /Applications/
```

## Making it the default app for `.twv` files

1. In Finder, right-click any `.twv` file → **Get Info**.
2. Under **Open with:**, choose **TWV Viewer** (browse to `/Applications` if
   it's not listed).
3. Click **Change All…** and confirm.

`.twv` files now open in TWV Viewer on double-click, and you can also drag a
file onto the app or its Dock icon.

If TWV Viewer doesn't show up in the "Open with" list, refresh the Launch
Services database:

```sh
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "/Applications/TWV Viewer.app"
```

## Project layout

| File | Purpose |
| --- | --- |
| `main.py` | Main window, playback, sidebar, macOS file-open handling |
| `twv.py` | Binary `.twv` reader (ctypes structures for the headers) |
| `converter.py` | Frame export and background video conversion (OpenCV) |
| `convert_dialog.py` | Conversion options dialog |
| `video_label.py` | Aspect-preserving video display widget |
| `build.spec` | PyInstaller spec, including `.twv` document-type registration |
| `twv-viewer` | Launcher script (symlink-safe) |
| `make_icon.py` | Draws the eye icon and writes `icon.icns` / `icon.png` (`uv run make_icon.py`) |

## Dependency management

Dependencies live in `pyproject.toml` and are pinned in `uv.lock`.

```sh
uv add <package>              # runtime dependency
uv add --group build <pkg>    # build-only dependency
uv lock --upgrade             # upgrade everything
```
