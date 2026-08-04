Watts–Strogatz small-world generator

This repository contains a simple implementation of the Watts–Strogatz model in
`watts_Strogatz_Manual.py`.

Quick start

1. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

2. Run the script:

```powershell
python watts_Strogatz_Manual.py
```

This will generate a small-world network (default n=30, k=4, p=0.3), display a
plot, and print basic statistics.

Planned improvements

- Add CLI options (`--n`, `--k`, `--p`, `--seed`, `--save`) using `argparse`.
- Add unit tests and packaging instructions (PyInstaller) for Windows `.exe`.

If you want me to proceed, I can add the CLI and tests next.

Run and test

- Run the script with defaults:

```powershell
python watts_Strogatz_Manual.py
```

- Run with options (no display, save image):

```powershell
python watts_Strogatz_Manual.py --no-show --save out.png --seed 42 --n 30 --k 4 --p 0.3
```

- Run tests with `pytest` (install via `pip install pytest` or use `requirements.txt`):

```powershell
python -m pytest -q
```

Packaging (optional)

To create a Windows executable using PyInstaller:

```powershell
pip install pyinstaller
pyinstaller --onefile watts_Strogatz_Manual.py
```

This produces a single `dist\watts_Strogatz_Manual.exe` you can distribute.
