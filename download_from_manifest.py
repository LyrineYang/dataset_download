#!/usr/bin/env python3
"""
Download selected SpatialVID-HQ clips and annotations based on a manifest CSV.

Workflow:
- Read manifest (default: SpatialVID/spatialvid_data/sampled_manifest.csv)
- Take first N rows (optionally shuffle) and gather required groups
- Download the corresponding group tarballs from Hugging Face
- Extract only the needed mp4 files and annotation subfolders

Requires: huggingface_hub, pandas
"""

import argparse
import tarfile
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download clips/annotations from SpatialVID-HQ manifest.")
    p.add_argument(
        "--manifest",
        type=Path,
        default=Path("sampled_manifest.csv"),
        help="Path to manifest CSV (must contain 'video path' and 'annotation path'). Defaults to local bundled file.",
    )
    p.add_argument(
        "-n",
        "--num",
        type=int,
        default=30000,
        help="Number of rows to download from the manifest (after optional shuffle).",
    )
    p.add_argument(
        "--shuffle",
        action="store_true",
        help="Shuffle manifest before taking the first N rows.",
    )
    p.add_argument(
        "--repo-id",
        type=str,
        default="SpatialVID/SpatialVID-HQ",
        help="Hugging Face dataset repo id.",
    )
    p.add_argument(
        "--local-dir",
        type=Path,
        default=Path("SpatialVID/spatialvid_data"),
        help="Local directory to store downloads and extractions.",
    )
    return p.parse_args()


def extract_selected(tar_path: Path, needed_files: Set[str], needed_prefixes: Set[str], dest: Path) -> None:
    if not tar_path.is_file():
        print(f"[WARN] Tarball not found: {tar_path}")
        return
    with tarfile.open(tar_path, "r:gz") as tar:
        members: List[tarfile.TarInfo] = []
        for m in tar.getmembers():
            name = m.name
            if name in needed_files:
                members.append(m)
                continue
            if any(name.startswith(prefix) for prefix in needed_prefixes):
                members.append(m)
        if not members:
            print(f"[WARN] No matching members in {tar_path}")
            return
        tar.extractall(path=dest, members=members)
        print(f"Extracted {len(members)} members from {tar_path}")


def main() -> None:
    args = parse_args()
    if not args.manifest.is_file():
        raise FileNotFoundError(f"Manifest not found: {args.manifest}")

    df = pd.read_csv(args.manifest)
    if args.shuffle:
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    df = df.head(args.num)

    required_cols = {"video path", "annotation path"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in manifest: {missing}")

    # Build group-level requirements
    groups: Dict[str, Dict[str, List[str]]] = {}
    for _, row in df.iterrows():
        video_path = str(row["video path"]).strip()
        ann_path = str(row["annotation path"]).strip().rstrip("/")
        parts = video_path.split("/")
        if len(parts) < 2 or not parts[1].startswith("group_"):
            continue
        gid = parts[1]
        g = groups.setdefault(gid, {"vids": [], "ann_prefix": []})
        if video_path:
            g["vids"].append(video_path)
        if ann_path:
            g["ann_prefix"].append(ann_path + "/")

    if not groups:
        raise ValueError("No group ids parsed from manifest; check paths.")

    patterns = []
    for gid in groups:
        patterns.append(f"videos/{gid}.tar.gz")
        patterns.append(f"annotations/{gid}.tar.gz")

    args.local_dir.mkdir(parents=True, exist_ok=True)

    print("Tarballs to fetch:")
    for p in patterns:
        print(f"  - {p}")

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise SystemExit("Install dependencies first: pip install huggingface_hub pandas") from exc

    snapshot_download(
        repo_id=args.repo_id,
        repo_type="dataset",
        allow_patterns=patterns,
        local_dir=str(args.local_dir),
        local_dir_use_symlinks=False,
    )

    # Extract only needed files
    for gid, data in groups.items():
        tar_video = args.local_dir / f"videos/{gid}.tar.gz"
        tar_ann = args.local_dir / f"annotations/{gid}.tar.gz"
        needed_files = set(data["vids"])
        needed_prefixes = set(data["ann_prefix"])
        extract_selected(tar_video, needed_files, needed_prefixes, args.local_dir)
        extract_selected(tar_ann, needed_files, needed_prefixes, args.local_dir)

    print("\nDownload and selective extraction done.")


if __name__ == "__main__":
    main()
