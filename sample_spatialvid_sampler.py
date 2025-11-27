#!/usr/bin/env python3
"""
Weighted sampler for SpatialVID-HQ with camera-trajectory diversity.

Key ideas:
- Dynamics: balance camera trajectory via moveDist / rotAngle / trajTurns bins.
- Quality: keep motion score as stability signal (low drop, high slight penalty),
  distLevel as light penalty for 0; aesthetic within brightness buckets keeps bottom
  few percent only in-bucket.
- Diversity: inverse-frequency weights for brightness/time/weather/sceneType/motionTags.

Outputs a sampled CSV (with weights) or just reports in --dry-run mode.
"""

import argparse
import math
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd


# ----------------------- binning helpers ----------------------- #
def bin_move_dist(x: float) -> str:
    if x < 0.5:
        return "S"
    if x < 3:
        return "M"
    if x < 8:
        return "L"
    return "XL"


def bin_rot_angle(x: float) -> str:
    if x < 0.5:
        return "S"
    if x < 1.5:
        return "M"
    if x < 3:
        return "L"
    return "XL"


def bin_traj_turns(x: float) -> str:
    if x <= 0:
        return "0"
    if x <= 1:
        return "1"
    if x <= 2:
        return "2"
    return "3+"


# ----------------------- weight helpers ----------------------- #
def inverse_freq_weights(series: pd.Series, alpha: float = 0.7, clamp: Tuple[float, float] = (0.2, 5.0)) -> pd.Series:
    counts = series.value_counts()
    weights_map = {k: 1.0 / math.pow(v, alpha) for k, v in counts.items() if v > 0}
    w = series.map(weights_map).fillna(0.0)
    return w.clip(clamp[0], clamp[1])


def aesthetic_mask(df: pd.DataFrame, q_bright: float, q_dark: float) -> pd.Series:
    # Split by brightness buckets: Bright vs others (dim/dark)
    bright_mask = df["brightness"].fillna("").str.contains("Bright", case=False)
    thresh_bright = df.loc[bright_mask, "aesthetic score"].quantile(q_bright) if bright_mask.any() else -np.inf
    thresh_dark = df.loc[~bright_mask, "aesthetic score"].quantile(q_dark) if (~bright_mask).any() else -np.inf
    return (bright_mask & (df["aesthetic score"] >= thresh_bright)) | (
        ~bright_mask & (df["aesthetic score"] >= thresh_dark)
    )


def aesthetic_weights(df: pd.DataFrame, clamp: Tuple[float, float] = (0.5, 1.5)) -> pd.Series:
    mu = df["aesthetic score"].mean()
    sigma = df["aesthetic score"].std()
    if sigma <= 1e-6:
        return pd.Series(np.ones(len(df)), index=df.index)
    z = (df["aesthetic score"] - mu) / sigma
    w = 1.0 + 0.5 * z
    return w.clip(clamp[0], clamp[1])


def motion_score_weights(series: pd.Series) -> pd.Series:
    # drop handled elsewhere for very low; high motion slightly penalized
    w = pd.Series(np.ones(len(series)), index=series.index)
    w = w.mask(series > 8.8, 0.7)
    return w


def dist_level_weights(series: pd.Series) -> pd.Series:
    mapping = {0: 0.8, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}
    return series.map(mapping).fillna(1.0)


# ----------------------- main logic ----------------------- #
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SpatialVID-HQ weighted sampler with trajectory balancing.")
    p.add_argument("--metadata", type=Path, default=Path("SpatialVID/spatialvid_data/SpatialVID_HQ_metadata.csv"), help="Metadata CSV path.")
    p.add_argument("--output", type=Path, default=Path("SpatialVID/spatialvid_data/sampled_manifest.csv"), help="Output CSV (sampled rows with weights).")
    p.add_argument("-n", "--num", type=int, default=1000, help="Number of samples to draw.")
    p.add_argument("--seed", type=int, default=42, help="Random seed.")
    p.add_argument("--aesthetic-q-bright", type=float, default=0.05, help="Bottom quantile to drop in Bright bucket.")
    p.add_argument("--aesthetic-q-dark", type=float, default=0.02, help="Bottom quantile to drop in non-Bright buckets.")
    p.add_argument("--dry-run", action="store_true", help="Only report stats, do not sample or write output.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.metadata.is_file():
        raise FileNotFoundError(f"Metadata not found: {args.metadata}")

    df = pd.read_csv(args.metadata)
    needed_cols = [
        "id",
        "video path",
        "annotation path",
        "num frames",
        "fps",
        "moveDist",
        "rotAngle",
        "trajTurns",
        "motion score",
        "distLevel",
        "aesthetic score",
        "brightness",
        "timeOfDay",
        "weather",
        "sceneType",
        "motionTags",
    ]
    missing = [c for c in needed_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in metadata: {missing}")

    # Derived fields
    df["duration_sec"] = df["num frames"] / df["fps"]

    # Hard filters
    df = df[df["duration_sec"] >= 3.0]  # drop clips shorter than 3s

    # Aesthetic filter by brightness buckets
    mask_aes = aesthetic_mask(df, args.aesthetic_q_bright, args.aesthetic_q_dark)
    df = df[mask_aes]

    if len(df) == 0:
        raise ValueError("No rows left after filtering.")

    # Binning for trajectory
    df = df.copy()
    df["move_bin"] = df["moveDist"].apply(bin_move_dist)
    df["rot_bin"] = df["rotAngle"].apply(bin_rot_angle)
    df["turn_bin"] = df["trajTurns"].apply(bin_traj_turns)

    # Frequency-based weights
    # use alpha<1 to avoid完全拉平，保留一些原始分布信息
    w_move = inverse_freq_weights(df["move_bin"], alpha=0.8, clamp=(0.5, 3.0))
    w_rot = inverse_freq_weights(df["rot_bin"], alpha=0.8, clamp=(0.5, 3.0))
    w_turn = inverse_freq_weights(df["turn_bin"], alpha=0.8, clamp=(0.5, 3.0))
    w_brightness = inverse_freq_weights(df["brightness"].fillna("Unknown"), alpha=0.6, clamp=(0.5, 2.5))
    w_time = inverse_freq_weights(df["timeOfDay"].fillna("Unknown"), alpha=0.6, clamp=(0.5, 2.5))
    w_weather = inverse_freq_weights(df["weather"].fillna("Unknown"), alpha=0.6, clamp=(0.5, 3.0))
    w_scene = inverse_freq_weights(df["sceneType"].fillna("Unknown"), alpha=0.7, clamp=(0.3, 3.5))
    w_mtags = inverse_freq_weights(df["motionTags"].fillna("Unknown"), alpha=0.5, clamp=(0.5, 3.0))

    # Quality weights
    w_motion = motion_score_weights(df["motion score"])
    w_dist = dist_level_weights(df["distLevel"])
    w_aesthetic = aesthetic_weights(df, clamp=(0.5, 1.5))

    # Grouped weights with mean-normalization to avoid连乘爆炸
    def norm_mean(w):
        m = w.mean()
        return w if m <= 1e-9 else w / m

    w_dyn = norm_mean(w_move * w_rot * w_turn)
    w_sem = norm_mean(w_brightness * w_time * w_weather * w_scene * w_mtags)
    w_qual = norm_mean(w_motion * w_dist * w_aesthetic)

    total_w = (w_dyn * w_sem * w_qual).clip(0.05, 20.0)

    df["weight"] = total_w

    # Reports
    def report_bin(name: str, series: pd.Series) -> None:
        vc = series.value_counts(normalize=True).sort_index()
        print(f"\n{name} distribution (proportion):")
        for k, v in vc.items():
            print(f"  {k}: {v:.4f}")

    report_bin("move_bin", df["move_bin"])
    report_bin("rot_bin", df["rot_bin"])
    report_bin("turn_bin", df["turn_bin"])

    print(f"\nTotal candidates after filtering: {len(df)}")
    print(f"Sampling size: {args.num}")

    if args.dry_run:
        print("Dry-run mode: no sampling performed.")
        return

    np.random.seed(args.seed)
    n = min(args.num, len(df))
    probs = df["weight"] / df["weight"].sum()
    sampled_idx = np.random.choice(df.index, size=n, replace=False, p=probs)
    sampled = df.loc[sampled_idx].copy()

    out_cols = [c for c in df.columns if c not in ("move_bin", "rot_bin", "turn_bin")]
    sampled[out_cols].to_csv(args.output, index=False)
    print(f"Saved sampled manifest to {args.output} (rows: {len(sampled)})")


if __name__ == "__main__":
    main()
