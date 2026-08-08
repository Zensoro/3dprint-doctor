# FAQ

## What file formats are supported?

STL and 3MF (binary and ASCII STL, via trimesh).

## Do I need a GPU or heavy ML stack?

No. The classifier is a RandomForest over hand-crafted features — CPU-only,
trains in seconds. No PyTorch/TensorFlow.

## Is my data sent anywhere?

No. Everything runs locally and offline. Diagnosis and monitoring process
images on your machine. The optional webhook is the only network call (only if
you configure one).

## How accurate is defect diagnosis?

On real photos: healthy-vs-defect ~100% (0% false positives), 90-100% per-class
accuracy on the 6 defect classes. Labels are weak (derived from forum text), so
results vary with how similar your photos are to the training data.

## What happens if the ML model is missing?

Diagnosis falls back to traditional CV detectors (`--cv` to force). These are
less reliable on arbitrary photos but run without a model file.

## How do I calibrate cost for my printer?

Run `scripts/calibrate.py` (needs OrcaSlicer) to compare estimates against real
slicing, then tune `shell_factor`. See [Cost Model](cost.md).

## Can I use this with my print farm?

Yes. `watch` monitors a Moonraker (Klipper) webcam snapshot URL or a photo
directory, and there's a full [OctoPrint plugin](octoprint.md).

## Is there an API for my shop system?

`print-doctor check --json` emits a stable machine-readable schema. `check-batch
--json` does the same for many models. See [Cost Model](cost.md#json-schema).

## How do I contribute data to improve the classifier?

Add labeled image URLs to `data/stackexchange_manifest.json` (or a custom
manifest) and retrain. See [Dataset](dataset.md) and [Training](training.md).

## How does Print Doctor compare to slicers?

Slicers prepare G-code. Print Doctor analyzes the mesh *before* slicing
(printability + cost) and the print *after* (defects). It complements slicers.

## License?

MIT. The OctoPrint plugin is also MIT.
