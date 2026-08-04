"""
random_graphs.py
================
Simulation suite for three random graph models:
  1. Erdős–Rényi   ER(n, p)
  2. Watts–Strogatz  WS(n, k, beta)
  3. Barabási–Albert  BA(n, m)

Generates graphs, computes metrics, persists runs to SQLite,
and produces comparison plots.
"""

import sqlite3
import json
import time
import itertools
import os
from collections import Counter
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.stats import poisson

DB_PATH = Path("random_graphs.db")
OUT_DIR = Path("outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

_COLOURS = {"ER": "#2196F3", "WS": "#4CAF50", "BA": "#E91E63"}


# ── SECTION 1: GRAPH GENERATORS ─────────────────────────────────────────────

def make_erdos_renyi(n: int, p: float, seed: int = None) -> nx.Graph:
    """ER(n, p): each of the C(n,2) edges included independently with probability p."""
    return nx.erdos_renyi_graph(n=n, p=p, seed=seed)


def make_watts_strogatz(n: int, k: int, beta: float, seed: int = None) -> nx.Graph:
    """
    WS(n, k, beta): k-regular ring lattice with each edge rewired with probability beta.
    beta=0 → lattice (high C, high L);  beta=1 → random (low C, low L).
    k must be even and less than n.
    """
    if k % 2 != 0:
        raise ValueError(f"Watts-Strogatz requires even k, got k={k}")
    if k >= n:
        raise ValueError(f"Watts-Strogatz requires k < n, got k={k}, n={n}")
    return nx.watts_strogatz_graph(n=n, k=k, p=beta, seed=seed)


def make_barabasi_albert(n: int, m: int, seed: int = None) -> nx.Graph:
    """
    BA(n, m): preferential attachment — each new node connects to m existing nodes.
    Produces a power-law degree distribution with exponent τ ≈ 3.
    m must be ≥ 1 and less than n.
    """
    if m < 1:
        raise ValueError(f"Barabasi-Albert requires m >= 1, got m={m}")
    if m >= n:
        raise ValueError(f"Barabasi-Albert requires m < n, got m={m}, n={n}")
    return nx.barabasi_albert_graph(n=n, m=m, seed=seed)


_MAKERS = {
    "ER": make_erdos_renyi,
    "WS": make_watts_strogatz,
    "BA": make_barabasi_albert,
}


# ── SECTION 2: METRIC COMPUTATION ───────────────────────────────────────────

def compute_metrics(G: nx.Graph) -> dict:
    """
    Compute network metrics for G.

    Returns a dict with keys:
      n, m_edges, mean_degree, degree_distribution, clustering,
      giant_component (fraction), avg_path_length, diameter, density.
    avg_path_length and diameter are NaN when the giant component has only 1 node.
    """
    n = G.number_of_nodes()
    m = G.number_of_edges()

    if n == 0:
        return dict(
            n=0, m_edges=0, mean_degree=0.0,
            degree_distribution=[], clustering=0.0,
            giant_component=0.0, avg_path_length=float("nan"),
            diameter=float("nan"), density=0.0,
        )

    deg_seq    = [d for _, d in G.degree()]
    deg_hist   = sorted(Counter(deg_seq).items())
    clustering = nx.average_clustering(G)

    giant_nodes = max(nx.connected_components(G), key=len)
    giant_frac  = len(giant_nodes) / n
    G_giant     = G.subgraph(giant_nodes)

    if len(giant_nodes) > 1:
        avg_path = nx.average_shortest_path_length(G_giant)
        diameter = nx.diameter(G_giant)
    else:
        avg_path = float("nan")
        diameter = float("nan")

    return dict(
        n                   = n,
        m_edges             = m,
        mean_degree         = float(np.mean(deg_seq)),
        degree_distribution = deg_hist,
        clustering          = float(clustering),
        giant_component     = float(giant_frac),
        avg_path_length     = float(avg_path),
        diameter            = float(diameter),
        density             = float(nx.density(G)),
    )


# ── SECTION 3: SQLITE DATABASE ──────────────────────────────────────────────

def init_db(path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Open (or create) the SQLite database and ensure the runs table exists.

    Schema: id, model, params (JSON), seed, run_timestamp, n, m_edges,
            mean_degree, clustering, giant_component, avg_path_length,
            diameter, density, degree_dist (JSON list of [k, count] pairs).
    """
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            model            TEXT    NOT NULL,
            params           TEXT    NOT NULL,
            seed             INTEGER,
            run_timestamp    REAL    NOT NULL,
            n                INTEGER,
            m_edges          INTEGER,
            mean_degree      REAL,
            clustering       REAL,
            giant_component  REAL,
            avg_path_length  REAL,
            diameter         REAL,
            density          REAL,
            degree_dist      TEXT
        )
    """)
    conn.commit()
    return conn


def save_run(conn: sqlite3.Connection,
             model: str,
             params: dict,
             seed: int,
             metrics: dict) -> int:
    """Insert one simulation run into the database; return the auto-assigned row id."""
    cur = conn.execute("""
        INSERT INTO runs
          (model, params, seed, run_timestamp,
           n, m_edges, mean_degree, clustering,
           giant_component, avg_path_length, diameter, density,
           degree_dist)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        model,
        json.dumps(params),
        seed,
        time.time(),
        metrics["n"],
        metrics["m_edges"],
        metrics["mean_degree"],
        metrics["clustering"],
        metrics["giant_component"],
        metrics["avg_path_length"],
        metrics["diameter"],
        metrics["density"],
        json.dumps(metrics["degree_distribution"]),
    ))
    conn.commit()
    return cur.lastrowid


def query_runs(conn: sqlite3.Connection,
               model: str = None,
               order_by: str = "id",
               ascending: bool = True,
               limit: int = None) -> list[dict]:
    """
    Retrieve runs from the database.

    Parameters
    ----------
    model    : filter to 'ER', 'WS', or 'BA' (None = all models)
    order_by : column to sort by
    ascending: sort direction
    limit    : max rows to return

    Returns a list of dicts; params and degree_dist are decoded from JSON.
    """
    _VALID_COLUMNS = {
        "id", "model", "params", "seed", "run_timestamp", "n", "m_edges",
        "mean_degree", "clustering", "giant_component", "avg_path_length",
        "diameter", "density", "degree_dist",
    }
    if order_by not in _VALID_COLUMNS:
        raise ValueError(f"Invalid order_by column: {order_by!r}. "
                         f"Must be one of {sorted(_VALID_COLUMNS)}")

    direction = "ASC" if ascending else "DESC"
    params_q: list = []
    where = ""
    if model is not None:
        where = "WHERE model = ?"
        params_q.append(model)
    lim = f"LIMIT {int(limit)}" if limit else ""
    sql = f"SELECT * FROM runs {where} ORDER BY {order_by} {direction} {lim}"

    cur  = conn.execute(sql, params_q)
    cols = [c[0] for c in cur.description]
    rows = []
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        d["params"]      = json.loads(d["params"])
        d["degree_dist"] = json.loads(d["degree_dist"])
        rows.append(d)
    return rows


def print_table(rows: list[dict], cols: list[str] = None) -> None:
    """Pretty-print a list of database rows to stdout."""
    if not rows:
        print("  (no rows)")
        return
    if cols is None:
        cols = ["id", "model", "params", "n", "mean_degree",
                "clustering", "avg_path_length", "giant_component"]
    widths = {c: max(len(c), max(len(str(r.get(c, ""))) for r in rows))
              for c in cols}
    header = "  ".join(str(c).ljust(widths[c]) for c in cols)
    print(header)
    print("-" * len(header))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))


# ── SECTION 4: SINGLE-GRAPH VISUALISATION ───────────────────────────────────

def visualise_graph(G: nx.Graph,
                    model: str,
                    params: dict,
                    metrics: dict,
                    filename: str,
                    layout: str = "spring") -> None:
    """
    Two-panel figure: graph drawing (left) + degree distribution bar chart (right).
    layout: 'spring' | 'circular' | 'spectral'
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    colour = _COLOURS.get(model, "#607D8B")

    ax = axes[0]
    if layout == "circular":
        pos = nx.circular_layout(G)
    elif layout == "spectral" and G.number_of_edges() > 0:
        pos = nx.spectral_layout(G)
    else:
        pos = nx.spring_layout(G, seed=0, k=1.5 / np.sqrt(max(G.number_of_nodes(), 1)))

    degrees   = dict(G.degree())
    node_size = [max(20, min(300, 20 * degrees[v])) for v in G.nodes()]

    nx.draw_networkx(
        G, pos=pos, ax=ax,
        node_color=colour, node_size=node_size,
        edge_color="#BDBDBD", alpha=0.85, width=0.6,
        with_labels=G.number_of_nodes() <= 50, font_size=6,
    )
    ax.set_title(f"{model} graph\n{params}", fontsize=11, fontweight="bold")
    ax.axis("off")

    stats = (
        f"n={metrics['n']}  edges={metrics['m_edges']}\n"
        f"⟨k⟩={metrics['mean_degree']:.2f}  density={metrics['density']:.4f}\n"
        f"clustering={metrics['clustering']:.3f}\n"
        f"giant={metrics['giant_component']:.2%}\n"
        f"avg path={metrics['avg_path_length']:.2f}  diam={metrics['diameter']:.0f}"
    )
    ax.text(0.01, 0.01, stats, transform=ax.transAxes, fontsize=8,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", alpha=0.8))

    ax2 = axes[1]
    deg_hist = metrics["degree_distribution"]
    ks     = [pair[0] for pair in deg_hist]
    counts = [pair[1] for pair in deg_hist]
    total  = sum(counts)
    props  = [c / total for c in counts]

    ax2.bar(ks, props, color=colour, alpha=0.75, width=0.8, label="Empirical")

    mean_k = metrics["mean_degree"]
    if model == "ER" and mean_k > 0:
        k_range = np.arange(0, max(ks) + 2)
        ax2.plot(k_range, poisson.pmf(k_range, mean_k), "o--",
                 color="black", markersize=4, linewidth=1.5,
                 label=f"Poisson(λ={mean_k:.2f})")
        ax2.legend(fontsize=9)

    ax2.set_xlabel("Degree k", fontsize=11)
    ax2.set_ylabel("Proportion of nodes", fontsize=11)
    ax2.set_title("Degree Distribution", fontsize=11, fontweight="bold")

    fig.suptitle(
        f"{model} Model – Single Instance Visualisation",
        fontsize=13, fontweight="bold", y=1.01
    )
    plt.tight_layout()
    plt.savefig(str(filename), dpi=150, bbox_inches="tight")
    plt.close()


# ── SECTION 5: BULK SIMULATION ───────────────────────────────────────────────

def _simulate_one(job):
    """
    Worker function for ProcessPoolExecutor — runs in a subprocess.
    job: (model, params, seed)
    Returns dict with keys: model, params, seed, metrics.
    """
    model, params, seed = job
    G       = _MAKERS[model](**params, seed=seed)
    metrics = compute_metrics(G)
    return {"model": model, "params": params, "seed": seed, "metrics": metrics}


def bulk_simulate_parallel(conn: sqlite3.Connection,
                           model: str,
                           param_grid: dict,
                           reps: int = 5,
                           base_seed: int = 0,
                           max_workers: int = None) -> list[int]:
    """
    Run every parameter combination in param_grid, reps times each, in parallel.
    Graph generation and metric computation use ProcessPoolExecutor;
    database writes are serial to avoid SQLite file-locking errors.

    Parameters
    ----------
    conn        : open sqlite3.Connection
    model       : 'ER', 'WS', or 'BA'
    param_grid  : {param_name: [values]}, e.g. {'n': [500], 'p': [0.01, 0.05]}
    reps        : independent realisations per parameter combination
    base_seed   : starting seed (incremented per run)
    max_workers : CPU cores to use; None = os.cpu_count()

    Returns a list of database row ids in submission order.

    Note: on Windows and in Jupyter, guard the call with
    ``if __name__ == '__main__':`` to avoid spawning recursion.
    """
    keys   = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))

    jobs = []
    seed = base_seed
    for combo in combos:
        params = dict(zip(keys, combo))
        for _ in range(reps):
            jobs.append((model, params, seed))
            seed += 1

    workers = max_workers or os.cpu_count() or 1
    total   = len(jobs)
    print(f"  Running {len(combos)} param combos × {reps} reps "
          f"= {total} graphs across {workers} workers …")

    results = [None] * total
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {pool.submit(_simulate_one, job): i
                         for i, job in enumerate(jobs)}
        done = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                print(f"\n  WARNING: job {idx} failed and will be skipped: {exc}")
                results[idx] = None
            done += 1
            print(f"  {done}/{total} complete", end="\r", flush=True)

    print()

    row_ids = []
    for r in results:
        if r is None:
            continue
        rid = save_run(conn, r["model"], r["params"], r["seed"], r["metrics"])
        row_ids.append(rid)

    print(f"  Saved {len(row_ids)} runs to database.")
    return row_ids


# ── SECTION 6: COMPARATIVE ANALYSIS PLOTS ───────────────────────────────────

def plot_metrics_vs_parameter(conn: sqlite3.Connection,
                               model: str,
                               sweep_param: str,
                               filename: str) -> None:
    """
    Four-panel plot of mean_degree, clustering, avg_path_length, and
    giant_component as a function of sweep_param for the given model,
    averaged over repeated runs at each parameter value.
    """
    rows = query_runs(conn, model=model)
    if not rows:
        print(f"  No data for model={model}")
        return

    grouped = {}
    for r in rows:
        key = r["params"].get(sweep_param)
        if key is None:
            continue
        grouped.setdefault(key, []).append(r)

    if not grouped:
        print(f"  Parameter '{sweep_param}' not found in {model} runs.")
        return

    x_vals = sorted(grouped.keys())
    metrics_of_interest = [
        ("mean_degree",     "Mean degree ⟨k⟩",        _COLOURS.get(model, "C0")),
        ("clustering",      "Avg clustering C",         "#FF9800"),
        ("avg_path_length", "Avg path length ℓ",        "#9C27B0"),
        ("giant_component", "Giant component fraction", "#F44336"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    axes = axes.flatten()

    for ax, (col, label, colour) in zip(axes, metrics_of_interest):
        means, stds = [], []
        for x in x_vals:
            vals = [r[col] for r in grouped[x]
                    if r[col] is not None and not np.isnan(r[col])]
            means.append(np.nanmean(vals) if vals else np.nan)
            stds.append(np.nanstd(vals)  if vals else np.nan)

        ax.errorbar(x_vals, means, yerr=stds,
                    fmt="o-", color=colour, capsize=4,
                    linewidth=2, markersize=6,
                    label=f"{model} (mean ± std)")
        ax.set_xlabel(sweep_param, fontsize=11)
        ax.set_ylabel(label, fontsize=11)
        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    fig.suptitle(f"{model} Model — Metrics vs {sweep_param}",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(str(filename), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {Path(filename).name}")


def plot_small_world_sweep(conn: sqlite3.Connection, filename: str) -> None:
    """
    Watts–Strogatz small-world plot: C(β)/C(0) and L(β)/L(0) vs β on a log axis.
    Shows the regime where L drops while C remains high.
    """
    rows = query_runs(conn, model="WS")
    if not rows:
        print("  No WS data in DB for small-world sweep.")
        return

    grouped = {}
    for r in rows:
        beta = r["params"].get("beta", r["params"].get("p"))
        if beta is None:
            continue
        grouped.setdefault(beta, []).append(r)

    if not grouped:
        return

    betas   = sorted(grouped.keys())
    mean_cl = np.array([np.nanmean([r["clustering"] for r in grouped[b]])
                        for b in betas])
    mean_pl = np.array([
        np.nanmean([r["avg_path_length"] for r in grouped[b]
                    if r["avg_path_length"] is not None
                    and not np.isnan(r["avg_path_length"])])
        for b in betas
    ])

    cl_norm = mean_cl / (mean_cl[0] + 1e-12)
    pl_norm = mean_pl / (mean_pl[0] + 1e-12)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.semilogx(betas, cl_norm, "o-", color="#4CAF50",
                linewidth=2.5, markersize=7, label="C(β) / C(0)  clustering")
    ax.semilogx(betas, pl_norm, "s-", color="#9C27B0",
                linewidth=2.5, markersize=7, label="L(β) / L(0)  path length")
    ax.axvspan(0.001, 0.1, alpha=0.08, color="#FF9800", label="Small-world window")
    ax.set_xlabel("Rewiring probability β  (log scale)", fontsize=12)
    ax.set_ylabel("Normalised metric", fontsize=12)
    ax.set_title(
        "Watts–Strogatz Small-World Effect\n"
        "L drops before C — the 'sweet spot' between lattice and random graph",
        fontsize=12, fontweight="bold"
    )
    ax.legend(fontsize=10)
    ax.set_ylim(0, 1.2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(filename), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {Path(filename).name}")


def plot_model_comparison(conn: sqlite3.Connection, filename: str) -> None:
    """
    Six-panel dashboard: degree distributions (top row) and clustering vs
    path length scatter (bottom row) for ER, WS, and BA side-by-side.
    ER runs are filtered to n≈2000; WS and BA to n≈500.
    """
    fig = plt.figure(figsize=(18, 11))
    gs  = gridspec.GridSpec(2, 3, figure=fig,
                            hspace=0.45, wspace=0.38,
                            left=0.07, right=0.97,
                            top=0.82, bottom=0.07)

    _target_n = {"ER": 2000, "WS": 500, "BA": 500}

    for col_idx, (model, colour) in enumerate([("ER", "#2196F3"),
                                                ("WS", "#4CAF50"),
                                                ("BA", "#E91E63")]):
        target = _target_n[model]
        rows = [r for r in query_runs(conn, model=model)
                if r["n"] and abs(r["n"] - target) < 100]
        if not rows:
            continue

        # top row: aggregated degree distribution
        ax_top = fig.add_subplot(gs[0, col_idx])

        # For ER, restrict bars to the λ=8 Poisson-regime runs only so that
        # the empirical histogram and the Poisson overlay are drawn from the
        # same population.
        if model == "ER":
            P_POIS = 8 / 2000
            bar_rows = [r for r in rows
                        if abs(r["params"].get("p", 0.0) - P_POIS) < 1e-9]
            if not bar_rows:
                bar_rows = rows   # fallback if the λ=8 run is missing
        else:
            bar_rows = rows

        all_deg = {}
        for r in bar_rows:
            for k, cnt in r["degree_dist"]:
                all_deg[k] = all_deg.get(k, 0) + cnt
        total  = sum(all_deg.values())
        ks     = sorted(all_deg.keys())
        props  = [all_deg[k] / total for k in ks]
        ax_top.bar(ks, props, color=colour, alpha=0.7, width=0.9)
        mean_k = np.mean([r["mean_degree"] for r in rows])

        if model == "ER":
            # Restrict Poisson overlay to λ=8 runs only, excluding high-p sweep runs
            P_POIS    = 8 / 2000
            pois_rows = [r for r in rows
                         if abs(r["params"].get("p", 0.0) - P_POIS) < 1e-12]
            lam = float(np.mean([r["mean_degree"] for r in pois_rows])) \
                  if pois_rows else mean_k
            k_r = np.arange(0, max(ks) + 2)
            ax_top.plot(k_r, poisson.pmf(k_r, lam), "k--",
                        linewidth=1.5, label=f"Pois(λ={lam:.1f})")
            ax_top.legend(fontsize=8)

        ax_top.set_xlabel("Degree k", fontsize=9)
        ax_top.set_ylabel("Proportion", fontsize=9)
        ax_top.set_xlim(-0.5, min(max(ks) + 1, 30))
        ax_top.set_title(f"{model} degree distribution\n(⟨k⟩={mean_k:.2f})",
                         fontsize=10, fontweight="bold")

        # bottom row: clustering coefficient vs average path length
        ax_bot = fig.add_subplot(gs[1, col_idx])
        paired = [
            (r["clustering"], r["avg_path_length"])
            for r in rows
            if r["avg_path_length"] is not None and not np.isnan(r["avg_path_length"])
        ]
        if paired:
            cls_plot, pl_vals = zip(*paired)
            ax_bot.scatter(cls_plot, pl_vals, color=colour, alpha=0.55,
                           s=40, edgecolors="none")
            ax_bot.axvline(float(np.mean(cls_plot)), color=colour,
                           linestyle="--", linewidth=2.5, alpha=1.0,
                           zorder=5, label=f"mean C={np.mean(cls_plot):.3f}")
            ax_bot.axhline(float(np.mean(pl_vals)), color="dimgrey",
                           linestyle=":", linewidth=2.0, alpha=1.0,
                           zorder=5, label=f"mean L={np.mean(pl_vals):.2f}")
        ax_bot.set_xlabel("Clustering coefficient C", fontsize=9)
        ax_bot.set_ylabel("Avg path length L", fontsize=9)
        ax_bot.set_title(f"{model}: C vs L across runs", fontsize=10, fontweight="bold")
        ax_bot.legend(fontsize=7)

    fig.text(0.5, 0.97, "Model Comparison: ER  |  WS  |  BA",
             ha="center", va="top", fontsize=14, fontweight="bold")
    fig.text(0.5, 0.91,
             "Top: degree distributions          Bottom: clustering vs path length",
             ha="center", va="top", fontsize=11, color="#444444")

    plt.savefig(str(filename), dpi=160, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {Path(filename).name}")


# ── SECTION 7: RESIDUAL ANALYSIS ─────────────────────────────────────────────

def plot_er_poisson_residuals(conn: sqlite3.Connection, filename: str) -> None:
    """
    Two-panel figure for the ER model (n≈2000):
      Top    – empirical degree distribution (bars) with Poisson(λ) overlay.
      Bottom – residuals: empirical proportion minus Poisson(λ) at each k.
    Residuals randomly scattered around zero confirm the Poisson approximation.
    """
    P_POIS = 8 / 2000
    rows = [r for r in query_runs(conn, model="ER")
            if r["n"] and abs(r["n"] - 2000) < 100
            and abs(r["params"].get("p", 0.0) - P_POIS) < 1e-9]
    if not rows:
        print("  No ER data for residual plot.")
        return

    all_deg: dict = {}
    for r in rows:
        for k, cnt in r["degree_dist"]:
            all_deg[k] = all_deg.get(k, 0) + cnt

    total     = sum(all_deg.values())
    ks        = sorted(all_deg.keys())
    empirical = np.array([all_deg[k] / total for k in ks])
    mean_k    = float(np.mean([r["mean_degree"] for r in rows]))
    theory    = poisson.pmf(np.array(ks), mean_k)
    residuals = empirical - theory

    colour = "#2196F3"
    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(10, 8),
        gridspec_kw={"height_ratios": [2, 1], "hspace": 0.45}
    )

    ax_top.bar(ks, empirical, color=colour, alpha=0.70, width=0.85,
               label="Empirical (aggregated)")
    k_smooth = np.arange(0, max(ks) + 2)
    ax_top.plot(k_smooth, poisson.pmf(k_smooth, mean_k), "k--",
                linewidth=2, label=f"Poisson(λ={mean_k:.2f})")
    ax_top.set_xlabel("Degree k", fontsize=11)
    ax_top.set_ylabel("Proportion", fontsize=11)
    ax_top.set_xlim(-0.5, min(max(ks) + 1, 30))
    ax_top.set_title(
        f"ER Degree Distribution vs Poisson(λ={mean_k:.2f})\n"
        f"({len(rows)} runs, n≈2000)",
        fontsize=12, fontweight="bold"
    )
    ax_top.legend(fontsize=10)
    ax_top.grid(True, alpha=0.3)

    colours_res = [colour if r >= 0 else "#E53935" for r in residuals]
    ax_bot.bar(ks, residuals, color=colours_res, alpha=0.75, width=0.85)
    ax_bot.axhline(0, color="black", linewidth=1.2, linestyle="-")
    ax_bot.set_xlabel("Degree k", fontsize=11)
    ax_bot.set_ylabel("Residual\n(empirical − Poisson)", fontsize=10)
    ax_bot.set_xlim(-0.5, min(max(ks) + 1, 30))
    ax_bot.set_title(
        "Residuals: Empirical − Poisson(λ)  "
        "[random scatter around 0 → good fit]",
        fontsize=11, fontweight="bold"
    )
    ax_bot.grid(True, alpha=0.3)

    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    ax_bot.text(0.98, 0.05, f"RMSE = {rmse:.5f}",
                transform=ax_bot.transAxes, fontsize=10,
                ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8))

    plt.savefig(str(filename), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {Path(filename).name}")


# ── SECTION 8: MAIN ──────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  Random Graph Simulation Suite")
    print("  Models: Erdős–Rényi | Watts–Strogatz | Barabási–Albert")
    print("=" * 65)

    print("\n[1] Initialising database …")
    conn = init_db()
    print(f"    Database ready: {DB_PATH}")

    print("\n[2] Generating and visualising single graphs …")
    er = make_erdos_renyi(n=80, p=0.07, seed=1)
    ws = make_watts_strogatz(n=80, k=6, beta=0.1, seed=1)
    ba = make_barabasi_albert(n=80, m=2, seed=1)

    for G, model, params in [
        (er, "ER", {"n": 80, "p": 0.07}),
        (ws, "WS", {"n": 80, "k": 6, "beta": 0.1}),
        (ba, "BA", {"n": 80, "m": 2}),
    ]:
        metrics = compute_metrics(G)
        fname   = OUT_DIR / f"graph_{model.lower()}_single.png"
        visualise_graph(G, model, params, metrics, fname)
        print(f"    {model}: ⟨k⟩={metrics['mean_degree']:.2f}  "
              f"C={metrics['clustering']:.3f}  "
              f"L={metrics['avg_path_length']:.2f}")

    print("\n[3] WS beta sweep visualisation …")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, beta in zip(axes, [0.0, 0.1, 1.0]):
        G   = make_watts_strogatz(n=50, k=4, beta=beta, seed=42)
        pos = nx.circular_layout(G)
        nx.draw_networkx(G, pos=pos, ax=ax,
                         node_color="#4CAF50", node_size=120,
                         edge_color="#BDBDBD", with_labels=False,
                         width=0.8, alpha=0.9)
        met = compute_metrics(G)
        ax.set_title(f"β={beta}\nC={met['clustering']:.3f}  "
                     f"L={met['avg_path_length']:.2f}", fontsize=11)
        ax.axis("off")
    fig.suptitle("Watts–Strogatz: lattice → small-world → random",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(str(OUT_DIR / "ws_beta_sweep_visual.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("    Saved: ws_beta_sweep_visual.png")

    print("\n[4] Bulk simulation (parallel) …")

    print("  ER: varying p …")
    bulk_simulate_parallel(conn, "ER",
                           param_grid={"n": [1000], "p": [0.0005, 0.0008, 0.0009,
                                                          0.0010, 0.0011, 0.0012,
                                                          0.0015, 0.0020, 0.0030]},
                           reps=1, base_seed=100)

    print("  ER: Poisson-regime run (λ=8) …")
    bulk_simulate_parallel(conn, "ER",
                           param_grid={"n": [2000], "p": [8 / 2000]},
                           reps=1, base_seed=200)

    print("  WS: varying beta …")
    bulk_simulate_parallel(conn, "WS",
                           param_grid={"n": [500], "k": [8],
                                       "beta": [0.0001, 0.001, 0.005, 0.01,
                                                0.05, 0.1, 0.3, 0.5, 1.0]},
                           reps=1, base_seed=300)

    print("  BA: varying m …")
    bulk_simulate_parallel(conn, "BA",
                           param_grid={"n": [500], "m": [1, 2, 3, 5, 8, 12]},
                           reps=1, base_seed=500)

    print("\n[5] Database queries …")
    print("\n  Top 5 ER runs by clustering (highest first):")
    print_table(query_runs(conn, model="ER", order_by="clustering",
                           ascending=False, limit=5),
                ["id", "params", "clustering", "avg_path_length",
                 "mean_degree", "giant_component"])

    print("\n  Top 5 WS runs by avg_path_length (lowest first):")
    print_table(query_runs(conn, model="WS", order_by="avg_path_length",
                           ascending=True, limit=5),
                ["id", "params", "clustering", "avg_path_length"])

    print("\n  Top 5 BA runs by mean_degree (highest first):")
    print_table(query_runs(conn, model="BA", order_by="mean_degree",
                           ascending=False, limit=5),
                ["id", "params", "mean_degree", "clustering", "avg_path_length"])

    print("\n[6] Metric sweep plots …")
    plot_metrics_vs_parameter(conn, "ER", "p",    OUT_DIR / "er_metrics_vs_p.png")
    plot_metrics_vs_parameter(conn, "WS", "beta", OUT_DIR / "ws_metrics_vs_beta.png")
    plot_metrics_vs_parameter(conn, "BA", "m",    OUT_DIR / "ba_metrics_vs_m.png")

    print("\n[7] Watts–Strogatz small-world plot …")
    plot_small_world_sweep(conn, OUT_DIR / "ws_small_world.png")

    print("\n[8] Three-model comparison dashboard …")
    plot_model_comparison(conn, OUT_DIR / "model_comparison.png")

    print("\n[9] ER Poisson residual analysis …")
    plot_er_poisson_residuals(conn, OUT_DIR / "er_poisson_residuals.png")

    conn.close()
    print("\n" + "=" * 65)
    print(f"  All outputs written to {OUT_DIR}/")
    print(f"  Database saved to {DB_PATH}")
    print("=" * 65)


if __name__ == "__main__":
    np.random.seed(42)
    main()
