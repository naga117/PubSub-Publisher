# PubSub-Publisher

A macOS desktop app to publish messages to Google Cloud Pub/Sub with optional attributes, logs, and CSV export.

## Highlights
- Native desktop UI built with PyQt6
- Single message publish and bulk CSV/TSV publish
- Visible app version in `Settings` and `Help -> About PubSub Publisher`
- Native macOS menu bar with `File`, `Edit`, `View`, `Window`, and `Help`

## Requirements
- Python 3.9+
- macOS 10.13+
- Google Cloud Project with Pub/Sub enabled

## Setup
```bash
git clone https://github.com/naga117/PubSub-Publisher.git
cd PubSub-Publisher
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Authentication
Option 1: Application Default Credentials (ADC)
```bash
gcloud auth application-default login
```

Option 2: Service account JSON file
- Use the UI checkbox and select a JSON file.

## Run (Dev)
```bash
python -m pubsub_publisher.main
```

## Build macOS App (PyInstaller)
```bash
pip install pyinstaller
python build_pyinstaller.py
```

The app bundle will be in `dist-launcher/PubSub Publisher.app`.

## Release Process (GitHub + Changelog)
This repository includes automated GitHub releases for each semantic version tag (`vX.Y.Z`).

1. Prepare a new release version and changelog entry:
```bash
python scripts/prepare_release.py 1.0.2
```

2. Review generated changes in:
- `pubsub_publisher/__init__.py`
- `PubSub Publisher.spec`
- `CHANGELOG.md`

3. Commit, tag, and push:
```bash
git add pubsub_publisher/__init__.py "PubSub Publisher.spec" CHANGELOG.md
git commit -m "Release 1.0.2"
git tag v1.0.2
git push origin <your-branch> --follow-tags
```

4. GitHub Actions workflow `.github/workflows/release.yml` automatically:
- validates tag version matches `__version__`
- extracts notes for that version from `CHANGELOG.md`
- creates a GitHub Release with those changelog notes

## Recent Improvements
- Reused Pub/Sub clients to reduce publish overhead
- Bulk publish now queues async publish futures in batches for better throughput
- Debounced project change handling to reduce repeated sync calls and config writes
- Fixed bundled app startup import issue

## macOS Menu Bar
- `File -> Preferences` opens the Settings tab
- `Help -> About PubSub Publisher` shows installed version
- `View` includes quick tab switching shortcuts:
  - `Cmd+1`: Publish
  - `Cmd+2`: Bulk Publish
  - `Cmd+3`: Settings

## Config File
The app stores project IDs in:
`~/Library/Application Support/PubSubPublisher/config.json`
