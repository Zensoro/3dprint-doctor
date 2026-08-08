"""Audit weak labels with a vision model, producing a cleaned dataset.

For each image (optionally only the suspect ones from audit_dataset.py),
ask a vision model whether the photo actually shows the labeled defect.
Images the vision model disagrees with are moved out of the training set
(kept, not deleted) into a <data_root>/_rejected/ directory.

Uses the opencode Go OpenAI-compatible endpoint with a vision-capable
model (mimo-v2.5-free) - the same credential opencode uses.

Usage:
    python scripts/audit_labels.py --data /tmp/dataset/stackexchange \
        --model mimo-v2.5-free --limit 200 --out /tmp/cleaned.csv
"""
import argparse
import base64
import csv
import glob
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Class name -> prompt keyword mapping (vision-friendly descriptions)
CLASS_HINTS = {
    "stringing": "stringing (thin strands/webs of filament)",
    "warping": "warping (corners/layers lifting up from the bed)",
    "layer_shift": "layer shift (horizontal offset/shift in the layers)",
    "under_extrusion": "under-extrusion (gaps, holes, thin/weak areas)",
    "over_extrusion": "over-extrusion (blobs, bulges, excess material)",
    "first_layer": "first-layer failure or poor bed adhesion (bottom layers missing/messy)",
    "normal": "a healthy, normal print with no visible defects",
}


def get_api_key() -> str:
    from pathlib import Path
    import json
    auth = Path.home() / ".local/share/opencode/auth.json"
    d = json.load(open(auth))
    return d["opencode-go"]["key"]


API_URL = "https://opencode.ai/zen/go/v1/chat/completions"


def ask_vision(key: str, model: str, image_path: str, label: str) -> str:
    """Ask the vision model whether the image matches the label.

    Returns "match", "mismatch", or "error". Uses the OpenCode Go
    endpoint (zen/go/v1) where MiMo-V2.5 is available to subscribers.
    """
    b64 = base64.b64encode(open(image_path, "rb").read()).decode()
    hint = CLASS_HINTS.get(label, label)
    prompt = (
        "You are auditing labels for a 3D print defect dataset. "
        f'The image is labeled "{label}". '
        f'Definition: {hint}. '
        "Decide immediately with minimal reasoning and reply with exactly "
        "one word: MATCH if the photo clearly shows this defect, or "
        "MISMATCH if it does NOT show this defect (or is not a print photo). "
        "Do not add explanations."
    )
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{b64}"}},
        ]}],
        "max_tokens": 200,
    }).encode()

    req = urllib.request.Request(
        API_URL, data=body,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "User-Agent": "Mozilla/5.0"},
    )
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=120).read())
        msg = r["choices"][0]["message"]
        text = (msg.get("content")
                or msg.get("reasoning_content")
                or msg.get("reasoning") or "").upper()
        if "MISMATCH" in text:
            return "mismatch"
        if "MATCH" in text:
            return "match"
        return "error"
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  [429] rate limited", flush=True)
            time.sleep(30)
        return "error"
    except Exception:
        return "error"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--model", default="mimo-v2.5")
    parser.add_argument("--limit", type=int, default=0, help="max images (0=all)")
    parser.add_argument("--out", default="/tmp/cleaned.csv")
    parser.add_argument("--reject-dir", default="_rejected",
                        help="subdir to move rejected images into (kept, not deleted)")
    parser.add_argument("--sleep", type=float, default=0.5,
                        help="seconds between API calls (rate limit)")
    args = parser.parse_args()

    key = get_api_key()
    data = Path(args.data)

    files = []
    for cat in sorted(p for p in data.iterdir() if p.is_dir() and not p.name.startswith("_")):
        for f in sorted(cat.glob("*.jpg")):
            files.append((str(f), cat.name))
    if args.limit:
        import random
        random.seed(42)
        files = random.sample(files, min(args.limit, len(files)))

    # Skip already-audited files if resuming from an existing audit CSV
    audited = {}
    if Path(args.out).exists():
        with open(args.out) as f:
            for row in csv.DictReader(f):
                audited[row["file"]] = row["verdict"]
        remaining = [item for item in files if item[0] not in audited]
        print(f"resuming: {len(files) - len(remaining)} already audited, "
              f"{len(remaining)} left", flush=True)
        files = remaining

    print(f"auditing {len(files)} images with {args.model} "
          f"(workers=1, backoff on 429)...", flush=True)
    n_match = n_mismatch = n_error = 0
    reject_dir = data / args.reject_dir
    reject_dir.mkdir(exist_ok=True)

    # append-mode writer so progress survives interruption
    fresh = not Path(args.out).exists()
    out_f = open(args.out, "a", newline="")
    writer = csv.DictWriter(out_f, fieldnames=["file", "label", "verdict"])
    if fresh:
        writer.writeheader()

    done = 0
    for path, label in files:
        verdict = ask_vision(key, args.model, path, label)
        for _ in range(3):  # retry transient failures
            if verdict == "error":
                verdict = ask_vision(key, args.model, path, label)
            else:
                break
        writer.writerow({"file": path, "label": label, "verdict": verdict})
        out_f.flush()
        if verdict == "match":
            n_match += 1
        elif verdict == "mismatch":
            n_mismatch += 1
            dest = reject_dir / f"{label}__{Path(path).name}"
            try:
                shutil.move(path, dest)
            except OSError:
                pass
        else:
            n_error += 1
        done += 1
        if done % 10 == 0:
            print(f"  ...{done}/{len(files)} (match={n_match} "
                  f"mismatch={n_mismatch} err={n_error})", flush=True)

    out_f.close()

    print(f"\nresult: match={n_match} mismatch={n_mismatch} error={n_error}")
    print(f"rejected {n_mismatch} images -> {reject_dir}")
    print(f"audit log -> {args.out}")
    print("\nremaining per class:")
    for cat in sorted(p for p in data.iterdir() if p.is_dir() and not p.name.startswith("_")):
        print(f"  {cat.name}: {len(list(cat.glob('*.jpg')))}")


if __name__ == "__main__":
    main()
