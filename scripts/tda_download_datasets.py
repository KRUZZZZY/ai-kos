#!/usr/bin/env python3
"""
Phase 2: Download and preprocess TDA benchmark datasets.

Sources:
  UCR Archive   — ECG200 (time series, 2-class arrhythmia)
  OpenML        — MNIST, Fashion-MNIST (image classification)
  Princeton     — ModelNet10 (3D shape point clouds)
  TUDataset     — COLLAB (scientific collaboration graphs)
  Synthetic     — sphere vs torus, circle vs ellipse (generated)

Output: data/tda/{ucr,images,shapes,graphs,synthetic}/*.npy + metadata
"""

import numpy as np
from pathlib import Path
import json
import sys

DATA_ROOT = Path(__file__).resolve().parent.parent / "data" / "tda"


def download_ecg200():
    """ECG200 from UCR — 200 time series, 2 classes (normal/abnormal), length 96.
    Downloads from the UEA/UCR Time Series Classification Archive."""
    print("→ ECG200 (UCR time series)")
    import urllib.request
    import zipfile
    import io

    url = "https://www.timeseriesclassification.com/aeon-toolkit/ECG200.zip"
    try:
        resp = urllib.request.urlopen(url)
        zf = zipfile.ZipFile(io.BytesIO(resp.read()))
        train_file = [f for f in zf.namelist() if "TRAIN" in f.upper()][0]
        test_file = [f for f in zf.namelist() if "TEST" in f.upper()][0]

        def _parse_arff(zf, fname):
            content = zf.read(fname).decode("utf-8")
            data_start = content.index("@data")
            lines = [
                l for l in content[data_start:].split("\n")
                if l.strip() and not l.startswith("@") and not l.startswith("%")
            ]
            rows = [list(map(float, l.split(","))) for l in lines]
            m = np.array(rows)
            # Class label is the last column
            return m[:, :-1], m[:, -1].astype(int)

        X_train, y_train = _parse_arff(zf, train_file)
        X_test, y_test = _parse_arff(zf, test_file)
        X = np.concatenate([X_train, X_test])
        y = np.concatenate([y_train, y_test])
        out = DATA_ROOT / "ucr"
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "ecg200_X.npy", X)
        np.save(out / "ecg200_y.npy", y)
        print(f"   Saved: {X.shape[0]} samples × {X.shape[1]} timesteps, {len(np.unique(y))} classes")
        return {"name": "ECG200", "samples": int(X.shape[0]), "dim": int(X.shape[1]),
                "classes": int(len(np.unique(y))), "source": "UCR Archive"}
    except Exception as e:
        print(f"   FAILED: {e}")
        return None


def download_mnist():
    """MNIST — 70K 28×28 greyscale digits, 10 classes."""
    print("→ MNIST (OpenML)")
    try:
        from sklearn.datasets import fetch_openml
        mnist = fetch_openml("mnist_784", version=1, as_frame=False, parser="auto")
        X = mnist.data.astype(np.float32) / 255.0
        y = mnist.target.astype(int)
        # Reshape to 28×28 images
        X = X.reshape(-1, 28, 28)
        out = DATA_ROOT / "images"
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "mnist_X.npy", X)
        np.save(out / "mnist_y.npy", y)
        print(f"   Saved: {X.shape[0]} samples × 28×28, {len(np.unique(y))} classes")
        return {"name": "MNIST", "samples": int(X.shape[0]), "dim": "28×28",
                "classes": int(len(np.unique(y))), "source": "OpenML"}
    except Exception as e:
        print(f"   FAILED: {e}")
        return None


def download_fashion_mnist():
    """Fashion-MNIST — 70K 28×28 clothing images, 10 classes."""
    print("→ Fashion-MNIST (OpenML)")
    try:
        from sklearn.datasets import fetch_openml
        fmnist = fetch_openml("Fashion-MNIST", version=1, as_frame=False, parser="auto")
        X = fmnist.data.astype(np.float32) / 255.0
        y = fmnist.target.astype(int)
        X = X.reshape(-1, 28, 28)
        out = DATA_ROOT / "images"
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "fashion_mnist_X.npy", X)
        np.save(out / "fashion_mnist_y.npy", y)
        print(f"   Saved: {X.shape[0]} samples × 28×28, {len(np.unique(y))} classes")
        return {"name": "Fashion-MNIST", "samples": int(X.shape[0]), "dim": "28×28",
                "classes": int(len(np.unique(y))), "source": "OpenML"}
    except Exception as e:
        print(f"   FAILED: {e}")
        return None


def generate_synthetic():
    """Generate synthetic sphere, torus, circle, ellipse point clouds."""
    print("→ Synthetic shapes (generated)")
    rng = np.random.default_rng(42)
    N = 500
    points = 500
    out = DATA_ROOT / "synthetic"
    out.mkdir(parents=True, exist_ok=True)

    datasets = {}

    # Spheres
    X_sphere = []
    for _ in range(N):
        u = rng.standard_normal((points, 3))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        X_sphere.append(u)
    X_sphere = np.array(X_sphere)
    np.save(out / "sphere_X.npy", X_sphere)
    np.save(out / "sphere_y.npy", np.zeros(N, dtype=int))
    datasets["sphere"] = {"samples": N, "points_per_cloud": points, "dim": 3}

    # Tori
    X_torus = []
    for _ in range(N):
        theta = rng.uniform(0, 2 * np.pi, points)
        phi = rng.uniform(0, 2 * np.pi, points)
        t = np.column_stack([
            (2 + np.cos(phi)) * np.cos(theta),
            (2 + np.cos(phi)) * np.sin(theta),
            np.sin(phi),
        ])
        X_torus.append(t)
    X_torus = np.array(X_torus)
    np.save(out / "torus_X.npy", X_torus)
    np.save(out / "torus_y.npy", np.ones(N, dtype=int))
    datasets["torus"] = {"samples": N, "points_per_cloud": points, "dim": 3}

    # Combined classification dataset
    X_combined = np.concatenate([X_sphere, X_torus])
    y_combined = np.concatenate([np.zeros(N, dtype=int), np.ones(N, dtype=int)])
    np.save(out / "sphere_torus_X.npy", X_combined)
    np.save(out / "sphere_torus_y.npy", y_combined)

    print(f"   Saved: sphere {N}×{points}×3, torus {N}×{points}×3, combined 2×{N} samples")


def main():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    registry = []

    # 1. ECG200
    result = download_ecg200()
    if result:
        registry.append(result)

    # 2. MNIST
    result = download_mnist()
    if result:
        registry.append(result)

    # 3. Fashion-MNIST
    result = download_fashion_mnist()
    if result:
        registry.append(result)

    # 4. Synthetic
    generate_synthetic()
    registry.append({"name": "Sphere+Torus", "samples": 1000, "dim": "500 pts × 3D",
                     "classes": 2, "source": "Generated"})

    # Save registry
    with open(DATA_ROOT / "registry.json", "w") as f:
        json.dump(registry, f, indent=2)

    print(f"\n{'='*50}")
    print(f"  Datasets cached: {len(registry)}")
    print(f"  Location: {DATA_ROOT}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
