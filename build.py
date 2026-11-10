#!/usr/bin/env python3
"""Render the network diagram of one site.

    python3 build.py                    list the sites under sites/
    python3 build.py rental             → sites/rental/out/rental.svg + rental.png
    python3 build.py rental --unredacted
    python3 build.py --all [--unredacted]

A site is a directory under `sites/` holding a `site.yaml` and, after the render,
an `out/` with its SVG and PNG. The content and the pictures therefore stay
together, and adding a location (a flat, the lab at home, the office) is just
`mkdir sites/<name>` plus a `site.yaml` — no code change.

`site.yaml` picks the renderer with its `layout:` key: `home` for the trimmed
single-segment layout, `full` for the full lab panorama. The renderers in
`layouts/`, the icons and the fonts are shared by every site.
"""
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent
SITES = ROOT / "sites"
LAYOUTS = ROOT / "layouts"


def read_site(site_dir):
    """site.yaml of one site directory, the layout it names, and that renderer."""
    cfg_path = site_dir / "site.yaml"
    if not cfg_path.is_file():
        sys.exit(f"{site_dir}: no site.yaml in there")
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    layout = cfg.get("layout", "home")
    script = LAYOUTS / f"{layout}.py"
    if not script.is_file():
        sys.exit(f"{cfg_path}: layout {layout!r} has no renderer ({script.relative_to(ROOT)})")
    return cfg, layout, script


def find_sites():
    return sorted(p for p in SITES.iterdir() if (p / "site.yaml").is_file())


def show_sites():
    """List what is available: name, layout, title and the renders already on disk."""
    print("sites/")
    for site in find_sites():
        cfg, layout, _ = read_site(site)
        title = (cfg.get("meta") or {}).get("title") or "—"
        rendered = sorted(p.name for p in (site / "out").glob("*.png")) if (site / "out").is_dir() else []
        print(f"  {site.name:<14} layout={layout:<5} {title:<24} {', '.join(rendered) or 'not rendered yet'}")
    print("\n  python3 build.py <site> [--unredacted]   ·   python3 build.py --all [--unredacted]")


def render(site_dir, flags):
    _, layout, script = read_site(site_dir)
    print(f"[{site_dir.name}] layout={layout}")
    rc = subprocess.run([sys.executable, str(script), str(site_dir), *flags]).returncode
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
        sys.exit(f"no sites under {SITES.relative_to(ROOT)}/ — add one with a site.yaml, see README.md")

    for site_dir in targets:
        render(site_dir, flags)


if __name__ == "__main__":
    main()
