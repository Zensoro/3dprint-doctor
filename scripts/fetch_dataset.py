"""Download the StackExchange 3D-printing defect dataset.

The image URLs come from `data/stackexchange_manifest.json`, scraped
from 3D Printing StackExchange posts whose text mentions a defect type
(weak labels). Images are fetched via the images.weserv.nl proxy since
stack.imgur.com is often unreachable directly.

Usage:
    python scripts/fetch_dataset.py --out /tmp/dataset/stackexchange
"""
import argparse
import json
import os
import subprocess
import concurrent.futures
from pathlib import Path


def download(url: str, dest: str) -> bool:
    if os.path.exists(dest) and os.path.getsize(dest) > 5000:
        return True

    # GitHub-hosted images (e.g. the "normal" class) use the github: prefix.
    # Format: github:<owner>/<repo>/<path>
    if url.startswith("github:"):
        parts = url[len("github:"):].split("/", 2)
        repo = f"{parts[0]}/{parts[1]}"
        path = parts[2]
        try:
            r = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/{path}",
                 "-H", "Accept: application/vnd.github.raw"],
                capture_output=True, timeout=60,
            )
            if r.returncode == 0 and len(r.stdout) > 5000:
                with open(dest, "wb") as fh:
                    fh.write(r.stdout)
                return True
        except Exception:
            pass
        return False

    img_key = url.rstrip().rsplit("/", 1)[-1]
    proxied = f"https://wsrv.nl/?url=i.stack.imgur.com/{img_key}&output=jpg"
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", "40", "-A", "Mozilla/5.0",
             "-L", proxied, "-o", dest],
            capture_output=True, timeout=50,
        )
        if os.path.exists(dest) and os.path.getsize(dest) > 5000:
            return True
        if os.path.exists(dest):
            os.remove(dest)
    except Exception:
        pass
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/stackexchange_manifest.json")
    parser.add_argument("--out", default="/tmp/dataset/stackexchange")
    args = parser.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    jobs = []
    for cat, urls in manifest.items():
        cat_dir = Path(args.out) / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        for url in urls:
            name = url.rstrip().rsplit("/", 1)[-1]
            jobs.append((url, str(cat_dir / name)))

    print(f"downloading {len(jobs)} images to {args.out}...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda j: download(*j), jobs))
    ok = sum(results)
    print(f"done: {ok}/{len(jobs)} downloaded")

    # per-class counts
    for cat in manifest:
        n = len(list((Path(args.out) / cat).glob("*.jpg")))
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
