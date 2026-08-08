"""Expand the StackExchange defect dataset with broader defect keywords.

Extracts more image URLs from the 3D Printing StackExchange dump using a
wider set of defect keywords, downloads them (imgur via wsrv.nl proxy),
and writes an updated manifest.

Usage:
    python scripts/expand_dataset.py --stack-json /tmp/stack3d.json \
        --out /tmp/dataset/stackexchange --manifest data/stackexchange_manifest.json
"""
import argparse
import json
import os
import pickle
import re
import subprocess
import concurrent.futures
from pathlib import Path

DEFECT_KEYWORDS = {
    "stringing": ["stringing", "string", "oozing", "ooze"],
    "warping": ["warping", "warp", "curling", "curl", "lifting",
                "elephant's foot", "elephants foot"],
    "layer_shift": ["layer shift", "layer shifting", "z-band", "z band",
                    "shifted layers"],
    "under_extrusion": ["under-extrusion", "underextrusion", "under extrusion",
                        "under-extrud", "gaps", "inconsistent extrusion",
                        "underfilled"],
    "over_extrusion": ["over-extrusion", "overextrusion", "over extrusion",
                       "over-extrud", "blobbing", "blobs", "zits",
                       "pillowing", "elephant foot"],
    "first_layer": ["first layer", "first-layer", "bed adhesion", "adhesion",
                    "spaghetti", "not sticking", "not sticking to bed", "raft"],
}


def collect_urls(stack_json: Path) -> dict:
    import json
    d = json.load(open(stack_json))
    out = {}
    for name, kws in DEFECT_KEYWORDS.items():
        imgs = {}
        for p in d:
            text = ((p.get("Title") or "") + " " + (p.get("Body") or "")).lower()
            if any(k in text for k in kws):
                for m in re.findall(
                    r"https?://i\.stack\.imgur\.com/(\w+)\.(jpg|png)",
                    p.get("Body") or "",
                ):
                    key = f"{m[0]}.{m[1]}"
                    if key not in imgs:
                        imgs[key] = True
        out[name] = list(imgs)
    return out


def download_one(url: str, dest: str) -> bool:
    if os.path.exists(dest) and os.path.getsize(dest) > 5000:
        return True
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
    parser.add_argument("--stack-json", required=True, help="StackExchange dump JSON")
    parser.add_argument("--out", default="/tmp/dataset/stackexchange")
    parser.add_argument("--manifest", default="data/stackexchange_manifest.json")
    args = parser.parse_args()

    urls = collect_urls(Path(args.stack_json))
    print("collected URLs:")
    for k, v in urls.items():
        print(f"  {k}: {len(v)}")

    # Load existing manifest to preserve the 'normal' class (GitHub-hosted)
    manifest = {}
    if Path(args.manifest).exists():
        manifest = json.load(open(args.manifest))
    normal_urls = manifest.get("normal", [])
    manifest = {k: v for k, v in urls.items()}
    manifest["normal"] = normal_urls

    jobs = []
    for cat, lst in manifest.items():
        cat_dir = Path(args.out) / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        for url in lst:
            if url.startswith("github:"):
                name = url.rsplit("/", 1)[-1]
            else:
                name = url.rstrip().rsplit("/", 1)[-1]
            jobs.append((url, str(cat_dir / name)))

    print(f"downloading {len(jobs)} images...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda j: download_one(*j), jobs))
    ok = sum(results)
    print(f"done: {ok}/{len(jobs)}")

    # refresh manifest to only successful + existing files
    final = {}
    for cat in manifest:
        cat_dir = Path(args.out) / cat
        files = sorted(cat_dir.glob("*.jpg"))
        final[cat] = []
        for f in files:
            if cat == "normal":
                final[cat].append(
                    f"github:elasly/3D_Printing_Defect_Detection/Good/{f.name}"
                )
            else:
                final[cat].append(f"https://i.stack.imgur.com/{f.stem}.jpg")
    json.dump(final, open(args.manifest, "w"), indent=2)
    print("manifest updated:")
    for k, v in final.items():
        print(f"  {k}: {len(v)}")


if __name__ == "__main__":
    main()
