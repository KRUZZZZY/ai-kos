#!/usr/bin/env python3
"""
Minimal end-to-end TDA pipeline benchmark — Phase 1 milestone.
Sphere vs Torus classification via persistent homology.

Pipeline: point cloud → VR filtration → persistence diagram → persistence image → SVM.

Sphere:  β = (1, 0, 1)  — no 1D holes
Torus:   β = (1, 2, 1)  — two 1D holes (the topological signal)
"""

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from gtda.homology import VietorisRipsPersistence
from gtda.diagrams import PersistenceImage


def sample_sphere(n_points: int, radius: float = 1.0, noise: float = 0.0,
                  rng: np.random.Generator | None = None) -> np.ndarray:
    """Uniform sample on a 2-sphere in R^3 via Marsaglia's method."""
    if rng is None:
        rng = np.random.default_rng()
    u = rng.standard_normal((n_points, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    points = u * radius
    if noise > 0:
        points += rng.standard_normal((n_points, 3)) * noise
    return points


def sample_torus(n_points: int, R: float = 2.0, r: float = 1.0, noise: float = 0.0,
                 rng: np.random.Generator | None = None) -> np.ndarray:
    """Sample points on a torus with major radius R and minor radius r."""
    if rng is None:
        rng = np.random.default_rng()
    theta = rng.uniform(0, 2 * np.pi, n_points)
    phi = rng.uniform(0, 2 * np.pi, n_points)
    x = (R + r * np.cos(phi)) * np.cos(theta)
    y = (R + r * np.cos(phi)) * np.sin(theta)
    z = r * np.sin(phi)
    points = np.column_stack([x, y, z])
    if noise > 0:
        points += rng.standard_normal((n_points, 3)) * noise
    return points


def main():
    # ── Parameters ──────────────────────────────────────────────────────
    N_SAMPLES = 50           # point clouds per class
    N_POINTS = 100           # points per cloud (VR complexity: ~C(100,3) ≈ 162K triangles)
    NOISE = 0.05             # Gaussian noise std
    HOM_DIMS = (0, 1)        # H1 captures the torus's two 1-cycles
    PI_RESOLUTION = 20       # persistence image grid
    PI_SIGMA = 0.1           # Gaussian kernel width
    CV_FOLDS = 5

    print(f"Generating {N_SAMPLES * 2} point clouds ({N_POINTS} points each)...")
    rng = np.random.default_rng(42)

    X_list, y_list = [], []
    for _ in range(N_SAMPLES):
        X_list.append(sample_sphere(N_POINTS, noise=NOISE, rng=rng))
        y_list.append(0)
        X_list.append(sample_torus(N_POINTS, noise=NOISE, rng=rng))
        y_list.append(1)

    X = np.array(X_list)
    y = np.array(y_list)
    print(f"  Shape: {X.shape}")

    # ── Pipeline ────────────────────────────────────────────────────────
    pipeline = Pipeline([
        ("vr", VietorisRipsPersistence(
            metric="euclidean",
            homology_dimensions=HOM_DIMS,
            n_jobs=1,
        )),
        ("pi", PersistenceImage(
            sigma=PI_SIGMA,
            n_bins=PI_RESOLUTION,
            weight_function=None,
        )),
        # PI outputs (n, |HOM_DIMS|, bins, bins) — flatten to 2D for SVM
        ("flatten", FunctionTransformer(
            lambda X_arr: X_arr.reshape(X_arr.shape[0], -1),
            validate=False,
        )),
        ("svm", SVC(kernel="rbf", C=1.0, gamma="scale", random_state=42)),
    ])

    n_features = len(HOM_DIMS) * PI_RESOLUTION * PI_RESOLUTION
    print(f"\nPipeline: VR dims={HOM_DIMS} → PI({PI_RESOLUTION}×{PI_RESOLUTION}) → {n_features} features → RBF-SVM")

    # ── Cross-validation ────────────────────────────────────────────────
    print(f"Running {CV_FOLDS}-fold stratified CV...")
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy", n_jobs=1)

    print(f"\n{'=' * 60}")
    print(f"  Accuracy: {scores.mean():.4f} ± {scores.std():.4f}")
    print(f"  Per-fold: {np.array2string(scores, precision=4, separator=', ')}")
    print(f"{'=' * 60}")

    # Sanity check: train accuracy
    pipeline.fit(X, y)
    train_acc = (pipeline.predict(X) == y).mean()
    print(f"  Train accuracy: {train_acc:.4f}")

    if scores.mean() > 0.75:
        print("\n  ✓ Pipeline discriminates sphere vs torus — H1 captures the two 1-cycles.")
    else:
        print("\n  ⚠ Accuracy below threshold — may need larger point clouds or less noise.")

    # ── Diagnostic: verify torus H1 signal ──────────────────────────────
    vr = pipeline.named_steps["vr"]
    diagrams = vr.fit_transform(X[:2])  # [sphere, torus]
    for i, label in enumerate(["sphere", "torus"]):
        h1 = diagrams[i][diagrams[i][:, 2] == 1]
        lifetimes = h1[:, 1] - h1[:, 0]
        sig_mask = lifetimes > 0.3
        print(f"  {label}: {sig_mask.sum()} significant H1 features, "
              f"max lifetime = {lifetimes.max():.4f}")

    return scores.mean()


if __name__ == "__main__":
    main()
