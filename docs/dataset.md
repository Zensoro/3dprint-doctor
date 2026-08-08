# Dataset

The defect classifier is trained on **600 real photos** with **weak labels**.

## Source

Images were scraped from [3D Printing StackExchange](https://3dprinting.stackexchange.com)
posts. A photo is labeled by the defect keywords in the surrounding post text —
hence *weak* labels: the image may not perfectly show the defect mentioned.

The 600-image manifest is in `data/stackexchange_manifest.json` — URLs plus the
class label derived from post text. The "normal" class (94 healthy prints)
comes from the `elasly/3D_Printing_Defect_Detection` GitHub repository.

## Class distribution

| Class | Images |
|---|---|
| first_layer | 219 |
| normal | 94 |
| under_extrusion | 89 |
| warping | 71 |
| stringing | 68 |
| over_extrusion | 31 |
| layer_shift | 28 |

## Download

Images are hosted on imgur (blocked in some regions). The fetch script proxies
them through `images.weserv.nl`:

```bash
# Needs `gh` auth for the "normal" class (GitHub-hosted)
python scripts/fetch_dataset.py --out /tmp/dataset/stackexchange
```

## Reproducibility

The manifest is committed so the dataset is fully reproducible. Images are not
committed to the repo (size); download via the script.

## Adding data

The simplest contribution path: add more photos with labels to
`data/stackexchange_manifest.json` (or run fetch with a custom manifest), then
retrain. See [Training](training.md).

!!! warning
    Weak labels mean results vary. More data, and *cleaner* labels (photos
    verified to match), improve accuracy directly.
