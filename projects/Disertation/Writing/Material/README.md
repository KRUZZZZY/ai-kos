# Random Graph Simulation Suite

Simulation, visualisation, and analysis of three foundational random graph models, with full metric computation and an SQLite database backend for storing and sorting results.

**Models covered**

| Model | Key parameter | Characteristic behaviour |
|---|---|---|
| Erdős–Rényi (ER) | `p` — edge probability | Poisson degree distribution; sharp phase transition at λ = 1 |
| Watts–Strogatz (WS) | `β` — rewiring probability | Small-world: high clustering, short path length |
| Barabási–Albert (BA) | `m` — edges per new node | Power-law (scale-free) degree distribution, τ ≈ 3 |

Based on van der Hofstad, *Random Graphs and Complex Networks*, Vol. I — ER (Ch. 4–5), WS (§1.4.3), BA (Ch. 8).

---

## Contents

- [Installation](#installation)
- [Running the Script](#running-the-script)
- [Generating Graphs](#generating-graphs)
- [Computing Metrics](#computing-metrics)
- [Visualising Graphs](#visualising-graphs)
- [Changing Parameters](#changing-parameters)
- [Bulk Simulation](#bulk-simulation)
- [Database Guide](#database-guide)
- [Output Files](#output-files)
- [Quick Reference](#quick-reference)

---

## Installation

Python 3.10 or higher is required.

```bash
pip install networkx matplotlib numpy scipy
```

If your system uses PEP 668 managed packages:

```bash
pip install networkx matplotlib numpy scipy --break-system-packages
```

| Package | Purpose |
|---|---|
| `networkx` | Graph generation, layout algorithms, metric computation |
| `matplotlib` | All visualisation and figure export |
| `numpy` | Numerical arrays, random seeds, statistical calculations |
| `scipy` | Poisson PMF overlay for Erdős–Rényi degree plots |

No further setup is needed. Place `random_graphs.py` anywhere and run it directly.

### Output locations

The script creates two output locations automatically on first run:

| Path | What is stored there |
|---|---|
| `~/random_graphs.db` | SQLite database — created on first run, appended on all subsequent runs |
| `./outputs/` | All PNG figures |

To change either path, edit the two constants near the top of the script before running:

```python
DB_PATH = Path("/your/path/random_graphs.db")   # database file
OUT_DIR = Path("/your/path/outputs")             # figures folder
```

---

## Running the Script

### Full demo run

Running the script with no arguments executes the complete demonstration in sequence. This is the recommended first run.

```bash
python random_graphs.py
```

Expected output:

```
==================================================================
  Random Graph Simulation Suite
  Models: Erdős–Rényi | Watts–Strogatz | Barabási–Albert
==================================================================

[1] Initialising database …
    Database ready: /home/yourname/random_graphs.db

[2] Generating and visualising single graphs …
    ER: ⟨k⟩=5.95  C=0.056  L=2.64
    WS: ⟨k⟩=6.00  C=0.473  L=3.45
    BA: ⟨k⟩=3.90  C=0.126  L=2.94

[3] Parameter sweep demo (3 values of beta for WS) …
[4] Bulk simulation …
[5] Database queries and sorting …
[6] Generating metric sweep plots from database …
[7] Watts–Strogatz small-world plot …
[8] Three-model comparison dashboard …
[9] ER Poisson residual analysis …
```

Expected runtime on a modern laptop is 5–10 minutes.

**What the demo does — step by step**

| Step | What happens |
|---|---|
| `[1]` Initialise database | Creates `random_graphs.db` if it does not exist; opens a connection |
| `[2]` Single-graph visualisation | Generates one ER, WS, and BA graph of 80 nodes, computes metrics, saves three PNGs |
| `[3]` Parameter sweep visual | WS graphs at β = 0.0, 0.1, 1.0 side-by-side showing lattice → small-world → random |
| `[4]` Bulk simulation | Runs ~3 010 graphs total (999 ER sweep + 1 000 ER Poisson-regime + 1 008 WS + 1 002 BA) and stores all results in the database |
| `[5]` Database queries | Prints three sorted tables to the terminal |
| `[6]` Metric sweep plots | Reads the database and plots metrics vs parameter for each model |
| `[7]` Small-world plot | Normalised C(β)/C(0) and L(β)/L(0) on a log axis |
| `[8]` Comparison dashboard | Six-panel figure comparing all three models |
| `[9]` Poisson residual analysis | Two-panel figure: ER(2000, 8/2000) degree distribution with Poisson(λ) overlay and residual bar chart |

### Importing individual functions

Every function is importable for use in your own scripts or notebooks:

```python
from random_graphs import (
    make_erdos_renyi, make_watts_strogatz, make_barabasi_albert,
    compute_metrics, init_db, save_run, query_runs, print_table,
    visualise_graph, bulk_simulate
)
```

---

## Generating Graphs

Each generator returns a plain `networkx.Graph`. The `seed` argument makes results reproducible.

```python
# Erdős–Rényi: 200 nodes, edge probability 0.03
G = make_erdos_renyi(n=200, p=0.03, seed=42)

# Watts–Strogatz: 200 nodes, 6 nearest-neighbour connections, rewiring prob 0.1
G = make_watts_strogatz(n=200, k=6, beta=0.1, seed=42)

# Barabási–Albert: 200 nodes, 3 edges added per new vertex
G = make_barabasi_albert(n=200, m=3, seed=42)
```

---

## Computing Metrics

`compute_metrics(G)` accepts any `networkx.Graph` regardless of which model produced it.

```python
metrics = compute_metrics(G)

print(metrics['mean_degree'])      # e.g. 5.97
print(metrics['clustering'])       # e.g. 0.058
print(metrics['avg_path_length'])  # e.g. 2.64
print(metrics['giant_component'])  # fraction of nodes in largest component
print(metrics['diameter'])         # diameter of the giant component
```

**All available keys**

| Key | Description |
|---|---|
| `n` | Number of nodes |
| `m_edges` | Number of edges |
| `mean_degree` | Average degree ⟨k⟩ |
| `degree_distribution` | List of `(degree, count)` pairs — full histogram |
| `clustering` | Average clustering coefficient (0 = tree-like, 1 = fully clustered) |
| `giant_component` | Fraction of nodes in the largest connected component |
| `avg_path_length` | Mean shortest path inside the giant component (`NaN` if trivial) |
| `diameter` | Longest shortest path inside the giant component |
| `density` | Edge density 2m / n(n−1) |

> **Note on performance** — `avg_path_length` runs a full BFS from every node (O(n²)) and is the slowest metric. For n = 1000 expect roughly 1–3 seconds per graph. For very large graphs you can replace it with `float('nan')` inside `compute_metrics()`.

---

## Visualising Graphs

`visualise_graph()` produces a two-panel PNG: the graph drawing on the left (node size scales with degree) and the degree distribution bar chart on the right. Labels are shown only when n ≤ 50. For ER graphs a Poisson overlay is added automatically.

```python
visualise_graph(
    G,
    model    = 'ER',
    params   = {'n': 200, 'p': 0.03},
    metrics  = metrics,
    filename = 'my_graph.png',
    layout   = 'spring'       # also: 'circular', 'spectral'
)
```

---

## Changing Parameters

Every generator accepts arbitrary keyword arguments so parameter changes are made inline. No global configuration is needed.

### Erdős–Rényi — choosing `p`

| Goal | Formula | Example (n = 500) |
|---|---|---|
| Sparse, subcritical (no giant component) | `p < 1/n` | `p = 0.001` |
| Phase transition point | `p = 1/n` | `p = 0.002` |
| Supercritical (giant component present) | `p > 1/n` | `p = 0.005` |
| Near connectivity threshold | `p ≈ log(n)/n` | `p = 0.012` |
| Dense graph | `p = 0.1` | `p = 0.1` |

### Watts–Strogatz — choosing `k` and `β`

- `k` must be **even**. `k = 4`, `6`, or `8` is typical.
- `β = 0` → perfect ring lattice, maximum clustering, long paths
- `β ≈ 0.05` → small-world sweet spot (short paths, clustering still high)
- `β = 1` → fully randomised, behaves like Erdős–Rényi

### Barabási–Albert — choosing `m`

- `m = 1` → trees only (no cycles), steepest power-law tail
- `m = 2` → standard model from the original Barabási–Albert paper
- `m = 5–10` → denser scale-free graphs with lower diameter

---

## Bulk Simulation

`bulk_simulate()` runs every combination of a parameter grid, `reps` times each, and writes every result to the database automatically. Seeds are assigned sequentially so all runs are reproducible.

```python
conn = init_db()

bulk_simulate(
    conn,
    model      = 'ER',
    param_grid = {
        'n': [200, 500, 1000],
        'p': [0.005, 0.010, 0.020, 0.050]
    },
    reps       = 10,
    base_seed  = 0
)
# runs 3 × 4 × 10 = 120 graphs and saves all 120 rows to the database
```

### Sweeping Watts–Strogatz rewiring

```python
bulk_simulate(
    conn,
    model      = 'WS',
    param_grid = {
        'n'   : [500],
        'k'   : [6, 8],
        'beta': [0.001, 0.01, 0.05, 0.1, 0.5, 1.0]
    },
    reps      = 8,
    base_seed = 500
)
```

### Sweeping Barabási–Albert attachment

```python
bulk_simulate(
    conn,
    model      = 'BA',
    param_grid = {
        'n': [1000],
        'm': [1, 2, 3, 5, 8, 12, 20]
    },
    reps      = 10,
    base_seed = 1000
)
```

---

## Database Guide

All simulation data is stored in a single SQLite file (`random_graphs.db`). SQLite is serverless and built into Python's standard library — no installation, no daemon, no credentials required.

### Schema

Every simulation run occupies exactly one row in the `runs` table:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Auto-incrementing primary key |
| `model` | TEXT | `'ER'`, `'WS'`, or `'BA'` |
| `params` | TEXT | JSON object of all parameters used, e.g. `{"n":500,"p":0.01}` |
| `seed` | INTEGER | Random seed used for this run |
| `run_timestamp` | REAL | Unix timestamp |
| `n` | INTEGER | Number of nodes |
| `m_edges` | INTEGER | Number of edges |
| `mean_degree` | REAL | Average degree ⟨k⟩ |
| `clustering` | REAL | Average clustering coefficient |
| `giant_component` | REAL | Fraction of nodes in the largest component |
| `avg_path_length` | REAL | Average shortest path inside the giant component |
| `diameter` | REAL | Diameter of the giant component |
| `density` | REAL | Edge density |
| `degree_dist` | TEXT | JSON list of `[degree, count]` pairs |

### Initialising the database

```python
from random_graphs import init_db

conn = init_db()                              # uses default ~/random_graphs.db
conn = init_db('/data/my_project.db')         # custom path
```

`init_db()` is safe to call repeatedly — it opens the existing file if one already exists and creates it if not.

### Querying and sorting

`query_runs()` returns a list of Python dicts. Every column is a key. The `degree_dist` column is automatically decoded from JSON.

```python
from random_graphs import init_db, query_runs, print_table

conn = init_db()

# All runs, default order (by id)
all_runs = query_runs(conn)

# Only ER runs, sorted by clustering coefficient (highest first)
top_clustering = query_runs(
    conn,
    model      = 'ER',
    order_by   = 'clustering',
    ascending  = False,
    limit      = 10
)

# WS runs with the shortest average path length
short_paths = query_runs(
    conn,
    model     = 'WS',
    order_by  = 'avg_path_length',
    ascending = True,
    limit     = 20
)

# BA runs ordered by giant component size (largest first)
giant_ba = query_runs(
    conn,
    model     = 'BA',
    order_by  = 'giant_component',
    ascending = False
)

# Pretty-print any result
print_table(top_clustering, ['id', 'params', 'clustering', 'avg_path_length'])
```

### What to sort by

| Column | Good for finding … |
|---|---|
| `clustering` | Most clustered graphs; best small-world candidates |
| `avg_path_length` | Graphs with the shortest or longest paths |
| `mean_degree` | Denser or sparser graphs within the same model |
| `giant_component` | Runs near the connectivity phase transition |
| `diameter` | Graphs with the widest or narrowest diameter |
| `density` | Edge density across parameter settings |
| `n` | Scaling studies across different graph sizes |

### Building a well-structured database

The recommended approach is three bulk sweeps — one per model — with consistent `n` and enough repetitions for stable averages. Use non-overlapping `base_seed` ranges so no two runs share a seed.

```python
from random_graphs import init_db, bulk_simulate

conn = init_db()

# ── Erdős–Rényi ──────────────────────────────────────────────────────────
# Sweep p from sub-critical through the connected regime
bulk_simulate(conn, 'ER',
    param_grid = {
        'n': [500],
        'p': [0.001, 0.002, 0.004, 0.006, 0.008,
              0.010, 0.012, 0.015, 0.020, 0.030,
              0.050, 0.100]
    },
    reps=10, base_seed=0
)

# ── Watts–Strogatz ───────────────────────────────────────────────────────
# Sweep beta across 5 orders of magnitude (log scale recommended)
bulk_simulate(conn, 'WS',
    param_grid = {
        'n'   : [500],
        'k'   : [8],
        'beta': [0.0001, 0.0005, 0.001, 0.005, 0.01,
                 0.05,   0.1,    0.3,   0.5,   1.0]
    },
    reps=10, base_seed=1000
)

# ── Barabási–Albert ──────────────────────────────────────────────────────
# Sweep m to vary the power-law degree distribution
bulk_simulate(conn, 'BA',
    param_grid = {
        'n': [500],
        'm': [1, 2, 3, 5, 8, 10, 15, 20]
    },
    reps=10, base_seed=2000
)

conn.close()
print('Database populated.')
```

This produces 570 rows covering the interesting parameter range for all three models.

### Saving a single run manually

```python
from random_graphs import make_watts_strogatz, compute_metrics, init_db, save_run

conn    = init_db()
G       = make_watts_strogatz(n=300, k=6, beta=0.05, seed=99)
metrics = compute_metrics(G)
row_id  = save_run(conn, 'WS', {'n': 300, 'k': 6, 'beta': 0.05}, 99, metrics)
print(f'Saved as row {row_id}')
conn.close()
```

### Accessing the database from outside Python

The `.db` file is a standard SQLite3 database and can be opened with any SQLite client:

- [DB Browser for SQLite](https://sqlitebrowser.org) — free GUI for Windows, macOS, Linux
- `sqlite3` command-line tool — built into macOS and most Linux distributions
- Any spreadsheet application that supports ODBC/SQLite connections

```bash
# Open from the terminal
sqlite3 ~/random_graphs.db

# Useful queries inside the sqlite3 shell
SELECT model, COUNT(*) as runs FROM runs GROUP BY model;

SELECT id, model, mean_degree, clustering, avg_path_length
FROM runs
WHERE model = 'WS'
ORDER BY clustering DESC
LIMIT 10;

-- Exit the shell
.quit
```

---

## Output Files

All PNGs are saved to `OUT_DIR` (default: `./outputs/`).

| Filename | Content |
|---|---|
| `graph_er_single.png` | ER graph drawing + degree distribution, single instance |
| `graph_ws_single.png` | WS graph drawing + degree distribution, single instance |
| `graph_ba_single.png` | BA graph drawing + degree distribution, single instance |
| `ws_beta_sweep_visual.png` | WS graphs at β = 0, 0.1, 1.0 side-by-side (circular layout) |
| `er_metrics_vs_p.png` | ER metrics (⟨k⟩, C, L, giant) vs edge probability p |
| `ws_metrics_vs_beta.png` | WS metrics vs rewiring probability β |
| `ba_metrics_vs_m.png` | BA metrics vs attachment parameter m |
| `ws_small_world.png` | Normalised C(β)/C(0) and L(β)/L(0) — the small-world signature |
| `model_comparison.png` | Six-panel dashboard comparing all three models |
| `er_poisson_residuals.png` | ER(2000, 8/2000) degree distribution vs Poisson(λ) overlay + residual bar chart |

---

## Quick Reference

### All functions

| Function | Arguments | Returns |
|---|---|---|
| `make_erdos_renyi` | `n, p, seed=None` | `networkx.Graph` |
| `make_watts_strogatz` | `n, k, beta, seed=None` | `networkx.Graph` |
| `make_barabasi_albert` | `n, m, seed=None` | `networkx.Graph` |
| `compute_metrics` | `G` | `dict` of metrics |
| `init_db` | `path=DB_PATH` | `sqlite3.Connection` |
| `save_run` | `conn, model, params, seed, metrics` | `int` (row id) |
| `query_runs` | `conn, model, order_by, ascending, limit` | `list` of dicts |
| `print_table` | `rows, cols=None` | `None` (prints to stdout) |
| `visualise_graph` | `G, model, params, metrics, filename, layout` | `None` (saves PNG) |
| `bulk_simulate` | `conn, model, param_grid, reps, base_seed` | `list` of row ids |
| `bulk_simulate_parallel` | `conn, model, param_grid, reps, base_seed, max_workers` | `list` of row ids |
| `plot_metrics_vs_parameter` | `conn, model, sweep_param, filename` | `None` (saves PNG) |
| `plot_small_world_sweep` | `conn, filename` | `None` (saves PNG) |
| `plot_model_comparison` | `conn, filename` | `None` (saves PNG) |
| `plot_er_poisson_residuals` | `conn, filename` | `None` (saves PNG) |

### Typical parameter ranges

| Model | Parameter | Typical range |
|---|---|---|
| ER | `n` | 100 – 10,000 |
| ER | `p` | `1/n` (sparse) to `0.1` (moderately dense) |
| WS | `n` | 100 – 5,000 |
| WS | `k` | 4, 6, or 8 (must be even) |
| WS | `beta` | 0.0001 – 1.0 (log scale recommended for sweeps) |
| BA | `n` | 200 – 20,000 |
| BA | `m` | 1 – 20 |
