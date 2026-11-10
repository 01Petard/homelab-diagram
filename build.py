#!/usr/bin/env python3
"""Render the network diagram of one site.

    python3 build.py                     list the sites under sites/
    python3 build.py cbny                → sites/cbny/out/cbny.svg + cbny.png
    python3 build.py cbny --unredacted
    python3 build.py --all [--unredacted]

A **site** is a directory under `sites/` that keeps everything about one place
together: the content (`site.yaml`), the hand-placed coordinates for that network
(`layout.py`) and the pictures (`out/`). Adding a place is therefore a new directory,
not a flag — and editing a diagram means editing the one layout next to its data.

Each site's `layout.py` is a complete, standalone script: it knows its own
directory and needs nothing from the other sites. This one only finds them and runs
them, so `python3 sites/<name>/layout.py` works just as well.
"""
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent
SITES = ROOT / "sites"


def read_site(site_dir):
    """The site's site.yaml and its layout.py, both required."""
    cfg_path = site_dir / "site.yaml"
    layout = site_dir / "layout.py"
    if not cfg_path.is_file() or not layout.is_file():
        sys.exit(f"{site_dir.relative_to(ROOT)}: needs both site.yaml and layout.py")
    return yaml.safe_load(cfg_path.read_text()) or {}, layout


def find_sites():
    return sorted(p for p in SITES.iterdir() if (p / "site.yaml").is_file())


def show_sites():
    """What is there: name, title and the renders already on disk."""
    print("sites/")
    for site in find_sites():
        cfg, _ = read_site(site)
        title = (cfg.get("meta") or {}).get("title") or "—"
        rendered = sorted(p.name for p in (site / "out").glob("*.png")) if (site / "out").is_dir() else []
        print(f"  {site.name:<14} {title:<24} {', '.join(rendered) or 'not rendered yet'}")
    print("\n  python3 build.py <site> [--unredacted]   ·   python3 build.py --all [--unredacted]")


def render(site_dir, flags):
    _, layout = read_site(site_dir)
    print(f"[{site_dir.name}]")
    rc = subprocess.run([sys.executable, str(layout), *flags]).returncode
    if rc:
        sys.exit(rc)


def main():
    args = sys.argv[1:]
    flags = [a for a in args if a == "--unredacted"]
    names = [a for a in args if not a.startswith("--")]

    if names:
        targets = [SITES / n for n in names]
    elif "--all" in args:
        targets = find_sites()
    else:
        show_sites()
        return

    if not targets:
        sys.exit(f"no sites under {SITES.relative_to(ROOT)}/ — add one with site.yaml + layout.py, see README.md")

    for site_dir in targets:
        render(site_dir, flags)


if __name__ == "__main__":
    main()
