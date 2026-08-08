# OctoPrint Integration

Print Doctor ships a full [OctoPrint plugin](../octoprint-print-doctor/) for
real-time defect monitoring during prints.

## What it does

- On **PrintStarted** it starts sampling your webcam snapshot.
- Each frame is classified by the Print Doctor ML model.
- On a defect: a notification appears in a **Print Doctor** tab, an evidence
  screenshot is saved, and (optionally) the print pauses.
- On **PrintDone / PrintFailed / PrintCancelled** monitoring stops.

## Install

```bash
cd octoprint-print-doctor
pip install .
```

Restart OctoPrint, open **Settings → Plugin Manager**, find **Print Doctor**,
and configure:

- **Webcam snapshot URL** — your webcam's JPEG snapshot endpoint
  (e.g. `http://localhost:8080/webcam/?action=snapshot`)
- **Check interval (s)** — how often to sample
- **Pause on defect** — automatically pause the print

## Requirements

- `print-doctor` Python package (installed as a dependency)
- A trained model at `models/defect_classifier.pkl` (see [Training](training.md))

## Also

The main CLI can monitor a webcam snapshot URL directly without the plugin:

```bash
print-doctor watch "http://localhost:8080/webcam/?action=snapshot" -i 5
```
