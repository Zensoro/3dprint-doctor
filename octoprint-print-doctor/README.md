# OctoPrint-PrintDoctor

OctoPrint plugin for real-time print defect monitoring using
[Print Doctor](https://github.com/Zensoro/print-doctor). Detects stringing,
warping, layer shift, under/over-extrusion and first-layer failure while the
print runs, alerts in the UI, and can pause the print.

## Install

```bash
cd octoprint-print-doctor
pip install .
```

Then restart OctoPrint, open **Settings -> Plugin Manager**, find
**Print Doctor**, and configure:
- **Webcam snapshot URL** — your webcam's JPEG snapshot endpoint
  (e.g. `http://localhost:8080/webcam/?action=snapshot`)
- **Check interval (s)** — how often to sample the camera
- **Pause on defect** — automatically pause the print on detection

## How it works

- On **PrintStarted** the plugin begins sampling the webcam snapshot.
- Each frame is classified by the Print Doctor ML model.
- On a defect: a notification appears in the **Print Doctor** tab, an
  evidence screenshot is saved, and (optionally) the print pauses.
- On **PrintDone / PrintFailed / PrintCancelled** monitoring stops.

## Notes

- Requires the `print-doctor` Python package (installed automatically as a
  dependency) with a trained model at `models/defect_classifier.pkl`
  (see the main repo README for training instructions).
- Best results need a model trained on data similar to your camera setup.
- This directory is a standalone plugin; the main Print Doctor CLI also
  supports monitoring webcam snapshot URLs directly (see `print-doctor watch
  --help`), including Moonraker/Klipper printers.

## Tests

```bash
python -m unittest tests.test_plugin
```
