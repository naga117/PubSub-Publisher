import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SPEC_FILE = BASE_DIR / "PubSub Publisher.spec"
ASSETS_DIR = BASE_DIR / "pubsub_publisher" / "assets"
ICON_PNG = ASSETS_DIR / "icon.png"
ICON_ICNS = ASSETS_DIR / "AppIcon.icns"


def _generate_icns_from_png(source_png: Path, output_icns: Path) -> None:
    sips = shutil.which("sips")
    iconutil = shutil.which("iconutil")
    if not sips or not iconutil:
        raise RuntimeError("Required macOS tools ('sips' and 'iconutil') are not available.")

    with tempfile.TemporaryDirectory() as temp_dir:
        iconset_dir = Path(temp_dir) / "AppIcon.iconset"
        iconset_dir.mkdir(parents=True, exist_ok=True)

        sizes = [
            ("icon_16x16.png", 16),
            ("icon_16x16@2x.png", 32),
            ("icon_32x32.png", 32),
            ("icon_32x32@2x.png", 64),
            ("icon_128x128.png", 128),
            ("icon_128x128@2x.png", 256),
            ("icon_256x256.png", 256),
            ("icon_256x256@2x.png", 512),
            ("icon_512x512.png", 512),
        ]

        for filename, size in sizes:
            subprocess.run(
                [sips, "-z", str(size), str(size), str(source_png), "--out", str(iconset_dir / filename)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        subprocess.run(
            ["/bin/cp", str(source_png), str(iconset_dir / "icon_512x512@2x.png")],
            check=True,
        )

        subprocess.run(
            [iconutil, "--convert", "icns", "--output", str(output_icns), str(iconset_dir)],
            check=True,
        )


def _ensure_macos_icon() -> Path | None:
    if sys.platform != "darwin":
        return None
    if not ICON_PNG.exists():
        return None

    should_regenerate = not ICON_ICNS.exists()
    if not should_regenerate:
        should_regenerate = ICON_PNG.stat().st_mtime > ICON_ICNS.stat().st_mtime

    if should_regenerate:
        try:
            _generate_icns_from_png(ICON_PNG, ICON_ICNS)
        except Exception as exc:
            print(f"Warning: could not generate AppIcon.icns: {exc}", file=sys.stderr)

    return ICON_ICNS if ICON_ICNS.exists() else None


def _pyinstaller_executable() -> str:
    candidates = [
        BASE_DIR / "venv311" / "bin" / "pyinstaller",
        BASE_DIR / "venv" / "bin" / "pyinstaller",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    found = shutil.which("pyinstaller")
    if found:
        return found
    raise FileNotFoundError(
        "PyInstaller not found. Install it in your venv (e.g. `venv311/bin/pip install pyinstaller`)."
    )


def main() -> int:
    pyinstaller = _pyinstaller_executable()
    _ensure_macos_icon()
    cmd = [
        pyinstaller,
        "--noconfirm",
        "--distpath",
        str(BASE_DIR / "dist-launcher"),
        str(SPEC_FILE),
    ]

    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(BASE_DIR))


if __name__ == "__main__":
    raise SystemExit(main())
