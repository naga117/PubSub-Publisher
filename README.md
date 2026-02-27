# PubSub-Publisher

A macOS desktop app to publish messages to Google Cloud Pub/Sub with optional attributes, logs, and CSV export.

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

## Config File
The app stores project IDs in:
`~/Library/Application Support/PubSubPublisher/config.json`
