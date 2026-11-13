# homelab-diagram

[English](README.md) · [简体中文](README.zh-CN.md)

Render a homelab inventory as an SVG and PNG network diagram. The `origin` example
includes an ISP router, firewall, VLAN switch, Proxmox guests, TrueNAS pools,
public services and a media workflow.

![Example output](docs/example.png)

The upstream project was developed with Claude Code through repeated rendering
and visual feedback. This version keeps that approach: **YAML describes the
network; Python places the cards and cables.** Changing an inventory does not
automatically redesign the layout. AI can help you adapt it and check the result.

## Example files

Only the public `origin` example is described here.

```text
sites/
  origin/
    site.en.yaml          English inventory
    site.zh.yaml          Chinese inventory with the same network facts
    layout.py             Standalone layout, SVG drawing and PNG conversion
    out/                  Generated SVG and PNG files (ignored by Git)
build.py                  Site selection and command-line entry point
fetch_icons.py            Download third-party service icons
icons/                    Bundled glyphs and downloaded service icons
pyproject.toml, uv.lock    Python dependencies and lockfile
CLAUDE.md                 Context for AI-assisted customization
```

Keep IPs, hostnames, IDs, ports and topology consistent across the two language
files. Interface text is translated in the layout's `UI` configuration. Product
names and technical identifiers generally keep their original spelling.

## Requirements

- **Git**, if cloning the repository.
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** for Python and dependencies.
- **Python 3.11+**; uv can install a compatible interpreter if one is unavailable.
- **librsvg**, providing the `rsvg-convert` command used for PNG export.
- **fontconfig**, providing `fc-match` for font measurement.
- **Fira Sans** and **Fira Code** fonts. See [Fira](https://github.com/mozilla/Fira)
  and [Fira Code](https://github.com/tonsky/FiraCode).
- For Chinese: **PingFang SC** on macOS or **Noto Sans CJK SC** on Linux.

uv installs PyYAML and Pillow from the project's dependency declarations. It does
**not** install librsvg, fontconfig or system fonts.

On macOS with Homebrew:

```bash
brew install uv librsvg fontconfig
brew install --cask font-fira-sans font-fira-code
```

On Linux, install uv using its official installation guide, then install librsvg,
fontconfig and the fonts with your distribution's package manager. On
Debian/Ubuntu, the command package for librsvg is `librsvg2-bin`. Windows users can
use WSL2 and follow the Linux setup; native Windows rendering is not verified here.

After installing fonts, verify that fontconfig selects the intended families,
not an unrelated fallback:

```bash
uv --version
rsvg-convert --version
fc-match 'Fira Sans'
fc-match 'Fira Code'
# For Chinese, also check your installed CJK font, for example:
fc-match 'Noto Sans CJK SC'
```

## First run with uv

Open a terminal in the repository root, where `build.py` and `pyproject.toml` live.
If you have not cloned it, use your chosen repository URL and check out the branch
containing this README. No branch switch is needed for an already-open checkout.

```bash
# Create .venv and install the locked Python dependencies.
uv sync --locked

# Download third-party icons. Internet access is required on the first run.
uv run python fetch_icons.py

# Render the origin example in English and Chinese.
uv run python build.py origin --lang en
uv run python build.py origin --lang zh
```

You do not need to activate `.venv` manually. [uv sync and uv run](https://docs.astral.sh/uv/concepts/projects/sync/)
manage the project environment. Reuse the render commands after editing the inventory
or layout; icons only need downloading again if missing or new ones are required.

The generated files are:

```text
sites/origin/out/origin-en-dark.svg
sites/origin/out/origin-en-dark.png
sites/origin/out/origin-zh-dark.svg
sites/origin/out/origin-zh-dark.png
```

`origin` currently supports **dark mode only**. `--mode dark` is accepted by the
entry point, but `--mode light` is not supported for this example. The image at the
top is a historical preview; the commands above generate the current version.

## Useful commands

| Purpose | Command |
|---|---|
| Default English render | `uv run python build.py origin` |
| Chinese render | `uv run python build.py origin --lang zh` |
| Chinese render with original domain and SSIDs | `uv run python build.py origin --lang zh --unredacted` |
| Try an alternative inventory | `uv run python build.py origin --inventory /path/to/alternative.yaml` |
| Chinese UI with an alternative inventory | `uv run python build.py origin --lang zh --inventory /path/to/alternative.zh.yaml` |
| Run the layout directly | `uv run python sites/origin/layout.py --lang zh` |
| Run regression tests after code changes | `uv run python -m unittest discover -s tests -v` |

An alternative inventory must match the origin schema and can only target one
site at a time. It replaces the selected language's content file; `--lang` still
selects the interface language and font stack. It writes to the usual output names,
so save an output copy first if comparing different inventories.

## What redaction does

The origin inventory enables domain and SSID redaction by default:

- The configured domain is replaced with `redact.domain_placeholder`.
- The title uses `meta.title_redacted` when domain redaction is enabled.
- SSIDs use each entry's `redacted` label instead of its `name`.

`--unredacted` bypasses those replacements and adds `-unredacted` to the output
name, for example `origin-zh-dark-unredacted.png`.

**IP addresses, MAC addresses, device names, usernames/watermarks and arbitrary
notes are not automatically hidden.** Inspect both the SVG text and the PNG before
sharing. Redaction behavior depends on the inventory settings; it is not a promise
that an image is safe to publish.

## Let AI run the complete workflow

Open the repository in an AI coding tool with terminal and file access, such as
Codex or Claude Code. The AI needs permission to run commands and, when needed,
install system dependencies. It should read the actual code and treat `CLAUDE.md`
as project context. The prompts below are instructions you can copy into that tool;
they do not execute just by reading this README.

### One prompt: get the example running

```text
Help me run this repository from setup through verified output. Execute the work,
not just a list of commands for me to run.

1. Locate the repository. If it is not open or cloned, ask for the repository URL
   and destination directory. Inspect README.md, pyproject.toml, uv.lock,
   build.py, fetch_icons.py, and the origin layout and inventories. Check Git
   status and keep the current branch and existing edits.
2. Detect my OS. Check uv, Python >=3.11, rsvg-convert, fc-match, Fira Sans,
   Fira Code and a Chinese font. Explain any missing system dependencies and
   install them using the appropriate official/package-manager method within
   the environment's authorization rules. Do not install unrelated tools or
   change dependency versions to work around a missing system package.
3. Run `uv sync --locked`, then `uv run python fetch_icons.py`. If downloads or
   installation fail, inspect the actual error, fix what you can and retry.
   Never claim a step passed when it did not.
4. Run `uv run python build.py origin --lang en` and
   `uv run python build.py origin --lang zh`. Keep default redaction enabled.
   Do not request light mode: origin does not currently support it.
5. Open both generated PNGs and inspect the image, including crops of dense
   sections. Check for missing glyphs/icons, overlapping text and clipped cards
   or cables. Fix rendering defects without changing the example's network facts.
   If you change code, run the relevant regression tests and render again.
6. Report the actual commands, output paths, what you checked, and any remaining
   blocker. Link or display the images. Do not push, publish, probe a real
   network or modify any network device as part of this example run.
```

### Follow-up 1: make a diagram of my network

```text
The origin example renders successfully. Now help me create my own network diagram.
Read CLAUDE.md for context, but use only origin as the starting template. Ask me for
my preferred site name, languages, privacy requirements and any existing network
notes. Ask for missing facts in small rounds: internet/gateway, switches/VLANs,
clients, servers/guests, storage and public services.

Copy the origin template into a new site directory using my chosen name; do not
replace origin. Keep example devices out of my final diagram unless I confirm
that I own them. Mark unknown facts explicitly. Keep bilingual inventories
consistent if I choose both languages, and retain stable identifiers such as
DMZ group keys while translating display names.

Adapt layout.py to my actual topology and give the outputs explicit language and
mode names. Do not assume light mode exists merely because a CLI flag exists.
Reuse the glyphs and fetch any necessary service icons. Render, inspect the PNG,
fix overlaps and iterate. Ask for explicit scope and authorization before any
real network probe; never change router, switch or server settings for drawing.
Finally give me the images and exact regeneration commands. Do not push or publish.
```

### Follow-up 2: refine and prepare to share

```text
Review the latest diagram against my confirmed inventory. Inspect full-size PNGs
and crops of crowded areas. Fix clipped labels, overlapping cards and ambiguous
cables while keeping the topology, device facts and language versions consistent.

Generate the default redacted version. Check the SVG and PNG for my real domain,
SSIDs, addresses, MACs, hostnames and watermark; list anything that still remains
visible and ask how I want it handled. Do not describe default redaction as hiding
all private information. Keep the unredacted version separate if I request it.
Show the result, report the exact commands and file paths, and do not publish it.
```

## Features and customization boundaries

Line width represents negotiated link speed. Solid cables are physical; dotted
connections represent tunnels or internet paths. VLAN colors identify networks,
and the legend explains port ticks, trunks and access links.

The origin template also supports optional inventory fields adapted from
[upstream PR #1](https://github.com/Goblinmine/homelab-diagram/pull/1): compact ISP
boxes (`stub`), short switch-port labels (`short`), unknown-VLAN port styling,
PPSK SSIDs (`vlans`), guest `kind`/`node`/`vlan` labels, and storage usage warnings
(`warn`, default 85%). Disk groups can wrap, and overflow checks identify sections
that need more room. See [CLAUDE.md](CLAUDE.md) for the field and layout details.

Canvas height follows panel bottoms, but positions, panel widths and cable routes
still need site-specific edits. Start from origin and adjust the layout to the
confirmed topology; a new YAML file alone cannot accommodate every network.

## Troubleshooting

| Symptom | What to check |
|---|---|
| `uv` not found | Install uv and reopen the terminal, or check PATH. |
| `rsvg-convert` not found | Install librsvg; Python packages do not provide it. |
| Missing icon | Run `uv run python fetch_icons.py`; inspect any reported download failures. |
| Chinese squares or changed text spacing | Install the correct fonts and verify the families returned by `fc-match`. |
| Overflow assertion | Adjust the relevant panel dimensions/routes in `layout.py`, then render and inspect again. |
| `--mode light` fails | Origin currently supports dark mode only. |
| PNG exists but is stale | Check the command exit status and the explicit language/mode filename. An old file can survive a failed run. |

## Credits and license

- Original project: [Goblinmine/homelab-diagram](https://github.com/Goblinmine/homelab-diagram),
  developed with Claude Code; this version includes later adaptations.
- Code and bundled `glyph-*.svg` icons: MIT, see [LICENSE](LICENSE).
- Downloaded service icons: [homarr-labs/dashboard-icons](https://github.com/homarr-labs/dashboard-icons).
  Logos belong to their respective projects and are not bundled in this repository.
- Fonts: Fira Sans and Fira Code, distributed separately under their font licenses.
