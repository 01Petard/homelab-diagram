# homelab-diagram

The script behind the network diagram of my homelab that I posted on r/homelab. It turns a YAML file describing the lab into a big SVG/PNG diagram in the style of the diagrams you see on r/homelab.

![Example output](docs/example.png)

> [!IMPORTANT]
> **This is not a general tool.** The *content* comes from `site.yaml`, but the *layout* (where every box, port and cable goes) is hand-placed in that site's `layout.py` for exactly one network. If you want to use it for yours, expect to move coordinates around in the code. Think of it as a starting point, not a finished product.

> [!NOTE]
> **The code was written by AI.** I built this together with Claude (Anthropic) in Claude Code. I described what I wanted and gave feedback on every render, Claude wrote and changed the code. A few example prompts are at the end of this README.

## What it shows

- the path from the internet through the ISP router (with its real ports) and the firewall to the core switch
- every switch port with the VLANs on it (tall bar = untagged, short bars = tagged)
- cables whose **line width is the negotiated link speed** (10G / 2.5G / 1G / 100M), trunks drawn as a white cable with a dark core
- the devices with name, type, model, IP · hostname and OS
- the Proxmox host with its hardware, the VMs/CTs outside the DMZ, the TrueNAS pools (disks, vdevs, usage) and every DMZ container with its CT ID, IP and hostname
- containers that run several apps as one card with a row per app
- what's open to the internet, a legend, the networks table and a small "media pipeline" explainer

## How it works

- Each **site** is a directory under `sites/` holding everything about one place: `site.yaml` (everything the picture shows: VLANs, devices, switch ports, port forwards, hardware, containers, pools), `layout.py` (a complete standalone script: where every box and cable goes, the drawing itself, the PNG export) and `out/` (the pictures).
- Each `layout.py` is self-contained — it knows its own directory and imports nothing from the other sites. Changing one site cannot break another, which is the point: a layout is hand-placed for exactly one network.
- `build.py` only finds the sites and runs them; `python3 sites/<name>/layout.py` does the same thing directly.
- **Languages:** the picture is English by default. A site can ship a `site.zh.yaml` next to its `site.yaml`, and `--lang zh` renders that instead (`out/<site>-zh.png`). Interface labels this layout draws itself live in a small `UI` table at the top of `layout.py`; everything else is content. There is no partial translation: a language either has its own complete content file or the site says it does not.
- **Redaction:** by default the real domain is replaced with `redacted.com` and SSIDs get generic names, so the PNG can be posted publicly. `--unredacted` renders a private version with the real values from `site.yaml`.

## Requirements

- Python 3.11+ with **PyYAML** and **Pillow** (Pillow is optional, but makes label widths exact). Both are declared in `pyproject.toml`, so [uv](https://docs.astral.sh/uv/) installs them for you — see below.
- **rsvg-convert** (librsvg) for the PNG
- the fonts **Fira Sans** and **Fira Code** installed (found via fontconfig)
- only for `--lang zh`: a CJK font — **PingFang SC** on macOS, **Noto Sans CJK SC** on Linux. The layout puts it behind Fira in the font stack, so latin stays Fira and Chinese is handed to the system font per character; without one every Chinese glyph becomes an empty box. Chinese text is measured at one em per character, so the boxes still fit.

On Arch/CachyOS: `pacman -S python-yaml python-pillow librsvg ttf-fira-sans ttf-fira-code`
On Debian/Ubuntu: `apt install python3-yaml python3-pil librsvg2-bin fonts-firacode` plus Fira Sans
On macOS: `brew install librsvg`, then install the Fira fonts from [mozilla/Fira](https://github.com/mozilla/Fira) (e.g. `brew install --cask font-fira-code font-fira-sans`, if your Homebrew has them).

## Structure

One directory per place, and everything about that place inside it:

```
sites/
  cbny/                   the flat I live in now (春波南苑)
    site.yaml             content: router, clients, tailnet, network table
    layout.py             self-contained script: coordinates + drawing + PNG export
    out/                  cbny.svg + .png (git-ignored)
  hkzn/                   the office segment: 12 clients found by sweeping the /24
    site.yaml             content: gateway, 12 hosts, probe log, egress + overlays
    site.zh.yaml          the same content in Chinese
    layout.py             a client grid instead of a device row
    out/                  hkzn.svg + .png (and -zh.* for Chinese)
  origin/                 the upstream lab, kept as the sample of the full schema
    site.yaml             content: 7 VLANs, switch ports, Proxmox, DMZ, pools
    layout.py             self-contained script: the full panorama
    out/                  origin.svg + .png
build.py                  runs one site, or lists them
icons/, fetch_icons.py    the shared bits: third-party logos, downloaded once
```

Each `sites/<name>/layout.py` is a full program, not a plugin: it reads the `site.yaml` next to it, draws, and writes `out/`. Nothing is shared between sites except the icons and the fonts, so you can rewrite one household's diagram without thinking about the other, and a copied directory still works on its own.

Content and layout are separate *files* because they fail differently — a wrong fact is a `site.yaml` edit, a box that does not fit is a `layout.py` edit — but they are never separate *directories*. Anything in a `site.yaml` that is not verified is labelled as unknown rather than invented.

Adding a place copies a directory, so you also get a layout to start from:

```bash
cp -r sites/origin sites/mylab      # panorama + example content, then edit both files
uv run build.py mylab
```

## Usage

With [uv](https://docs.astral.sh/uv/) (creates `.venv` and installs the pinned dependencies from `uv.lock`):

```bash
uv sync                        # once: create .venv, install PyYAML + Pillow
uv run fetch_icons.py          # downloads the service icons into icons/ (once)

uv run build.py                # list the sites and what has been rendered so far
uv run build.py cbny           # → sites/cbny/out/cbny.svg + .png
uv run build.py cbny --unredacted            # same, with the real domain / SSIDs
uv run build.py hkzn --lang zh      # → hkzn-zh.svg + .png, from site.zh.yaml
uv run build.py --all          # every site
```

Or with a plain Python install of PyYAML: the same commands with `python3` instead of `uv run`.

The service icons are **not** in this repo, `fetch_icons.py` downloads them from [homarr-labs/dashboard-icons](https://github.com/homarr-labs/dashboard-icons). Only my own small glyphs (`icons/glyph-*.svg`: CPU, RAM, SSD, …) are included.

## Making it your own

1. `cp -r sites/origin sites/<your-place>` (full panorama) or `cp -r sites/cbny sites/<your-place>` (flat home network), then edit the `site.yaml` in it. Texts, IPs, ports, VLAN colors and the container groups come from that file.
2. Look at the render. Whatever doesn't fit is the `layout.py` next to it: in the flat layout the chain from the cloud down to the device row is placed by `RY`, `LAN_X`, `DY`; in the full one the top part (cloud, ISP router, firewall, switch, device row) and the column split inside the server card are coordinates there too (search for `fy, fh`, `ox, oy`, `bx, by`, `DY`, `MAD = …`).
3. New icons: drop an SVG into `icons/` and use its file name in the `site.yaml`.

## Using it with Claude Code

The repo contains a [`CLAUDE.md`](CLAUDE.md) with everything an AI agent needs to adapt it to your lab: how the code is structured, which parts of the layout are hardcoded, the questions to ask about your network, the render-and-check loop, and the design rules this diagram follows.

Clone the repo, open it with [Claude Code](https://claude.com/claude-code) and say something like *"help me make this diagram for my homelab"*. It will interview you about your network (or read your docs if you have some), write `sites/<name>/site.yaml`, adapt the layout and iterate on the render with you. Other agents can use the same file as context.

## How it was made

I had seen these diagrams on r/homelab for years and always wanted one for my own network. My setup was documented in an Obsidian vault (written by another Claude Code session, checked against the live systems), so the workflow was:

1. **Gathering the facts.** Claude Code read the documentation and filled the gaps with read-only checks on the live systems: link speeds from the switch, disk models and pool usage from TrueNAS, the router model from its info page, hostnames from DNS, the containers running in each CT.
2. **First draft.** Claude wrote `inventory.yaml` and `build.py`, rendered the PNG and looked at the image itself (plus zoomed-in crops) to catch overlaps before showing it to me.
3. **Iterating.** Then it was me giving feedback, Claude changing the code, re-rendering and checking again, about 60 rounds. Most of the design decisions (folder-shaped device cards, line width = speed, CT on top and IP below, no internal ports, …) came out of that back and forth.
4. **Publishing.** For this repo Claude made a cleaned-up copy (example domain, generic SSIDs), added the icon download script and checked that a fresh clone renders exactly the posted image.

Tools: Claude Code with Claude Opus 5.5, Python, librsvg, Pillow.

## Example prompts

About 60 prompts went into this. Three typical ones, to give an idea of how the back and forth looked:

**Getting started**
> Do you know the network diagrams people post on r/homelab? I'd like one for my own network. My setup is documented in my Obsidian vault, read it and check the live systems for anything that's missing.

**Design feedback**
> Use the line thickness to show the link speed and put a small speed label where each cable reaches a device. Also remove the interface names like em0 or igc0, nobody needs them on a diagram.

**Fixing the facts**
> That's not quite right yet: there are two shares. qBittorrent only downloads into the Torrents share, and when a download is done Sonarr/Radarr copy the file with the right name into the Media share. qBittorrent has no access to the Media share at all.

## Credits & license

- Code and the glyph icons in `icons/`: MIT, see [LICENSE](LICENSE).
- Service icons: [homarr-labs/dashboard-icons](https://github.com/homarr-labs/dashboard-icons), downloaded by `fetch_icons.py`, not part of this repo. The logos belong to their projects.
- Fonts: [Fira Sans / Fira Code](https://github.com/mozilla/Fira) (SIL Open Font License), not included.
