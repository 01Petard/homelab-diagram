#!/usr/bin/env python3
"""Render the network diagram of one site.

    python3 build.py                     list the sites under sites/
    python3 build.py cbny                → sites/cbny/out/cbny.svg + cbny.png
    python3 build.py cbny --unredacted
    python3 build.py cbny --lang zh      → cbny-zh.png, from the site's site.zh.yaml
    python3 build.py hkzn --mode light   → hkzn-en-light.png
    python3 build.py --all [--unredacted] [--lang zh]

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
    print("\n  python3 build.py <site> [--lang en|zh] [--mode dark|light] [--unredacted]   ·   python3 build.py --all [--unredacted]")


def render(site_dir, flags):
    _, layout = read_site(site_dir)
    print(f"[{site_dir.name}]")
    rc = subprocess.run([sys.executable, str(layout), *flags]).returncode
    if rc:
        sys.exit(rc)


def main():
    args = sys.argv[1:]
    flags, names = [], []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--lang", "--inventory", "--mode"):  # option values are not site names
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                sys.exit(f"{a} needs a value")
            flags += [a, args[i + 1]]
            i += 2
            continue
        if a == "--unredacted" or a.startswith(("--lang=", "--inventory=", "--mode=")):
            flags.append(a)
        elif not a.startswith("--"):
            names.append(a)
        i += 1

    lang = flags[flags.index("--lang") + 1] if "--lang" in flags else \
        next((f.split("=", 1)[1] for f in flags if f.startswith("--lang=")), "en")
    if lang not in ("en", "zh"):
        sys.exit(f"unknown --lang '{lang}' (en | zh)")

    mode = flags[flags.index("--mode") + 1] if "--mode" in flags else \
        next((f.split("=", 1)[1] for f in flags if f.startswith("--mode=")), "dark")
    if mode not in ("dark", "light"):
        sys.exit(f"unknown --mode '{mode}' (dark | light)")

    if names:
        targets = [SITES / n for n in names]
    elif "--all" in args:
        targets = find_sites()
    else:
        show_sites()
        return

    if mode == "light" and any(site.name != "hkzn" for site in targets):
        sys.exit("--mode light is currently supported only for hkzn; select hkzn explicitly")

    if not targets:
        sys.exit(f"no sites under {SITES.relative_to(ROOT)}/ — add one with site.yaml + layout.py, see README.md")

    if any(f == "--inventory" or f.startswith("--inventory=") for f in flags) and len(targets) != 1:
        sys.exit("--inventory requires exactly one site (layouts have different schemas)")

    for site_dir in targets:
        if not any(f == "--inventory" or f.startswith("--inventory=") for f in flags) and lang != "en" and not (site_dir / f"site.{lang}.yaml").is_file():
            # --all walks over sites that may not have a translation yet; a site
            # named on the command line was asked for explicitly, so say so.
            if names:
                sys.exit(f"{site_dir.name}: no site.{lang}.yaml — the {lang} version needs its own content file")
            print(f"[{site_dir.name}] skipped: no site.{lang}.yaml")
            continue
        render(site_dir, flags)


if __name__ == "__main__":
    main()
