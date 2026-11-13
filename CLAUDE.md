# CLAUDE.md – adapting this diagram to someone else's homelab

You are helping a user turn **their** homelab into a diagram like `docs/example.png`. The repo ships with the original author's lab (`sites/origin/`) and a trimmed single-segment example (`sites/cbny/`). Your job: find out what their lab looks like, write `sites/<name>/site.yaml` and the matching `sites/<name>/layout.py`, and iterate on the render with them until they are happy.

Start by telling the user briefly how this works (interview → site.yaml → layout → render/feedback rounds), then begin the interview. Don't ask everything at once.

## How the repo works

- One **site** = one directory under `sites/`, holding `site.yaml` (all content), `layout.py` (a complete standalone script: coordinates, drawing, PNG export) and `out/` (its renders). Copying a site directory gives you both files to start from.
- `site.yaml` – all content: VLANs, devices, switch ports, port forwards, server hardware, VMs/containers, storage pools, the media pipeline.
- **Language** – English is the default and reads `site.yaml`. A site that should also render in Chinese ships `site.zh.yaml` with the same schema; `--lang zh` renders that to `out/<name>-zh.png`. Interface labels the layout draws itself (panel headings, legend entries, "unknown host") live in the `UI` dict at the top of `layout.py`, keyed `en`/`zh` — that is the only place those need translating. Keep a translation whole: a half-translated picture is worse than an English one.
- `layout.py` – self-contained: it locates its own directory, reads the `site.yaml` next to it, draws an SVG with absolute coordinates (logical canvas `W = 2400`, height `H`), embeds icons as base64 and converts to PNG with `rsvg-convert -z 1.6` (so PNG pixels = SVG units × 1.6). Nothing is imported from the other sites; shared code would be duplicated, and that is deliberate.
- `build.py` – entry point that finds the sites and runs their `layout.py`; `python3 build.py` alone lists them. `python3 sites/<name>/layout.py` renders one directly.
- `sites/origin/layout.py` – the panorama layout, and the schema reference for every field. `sites/cbny/layout.py` – the trimmed layout for a flat home network.
- `fetch_icons.py` – downloads service icons into `icons/` (dashboard-icons). Own glyphs `icons/glyph-*.svg` are in the repo.
- Output: `sites/<name>/out/<name>.png` (redacted, safe to post), `<name>-unredacted.png` (`--unredacted`) and `<name>-zh.png` (`--lang zh`).

### What is generic and what is hardcoded

Generic (driven by the YAML): VLAN table, legend, "Open to the internet" card, cloud services, OPNsense hardware/services lists, switch ports (labels, VLAN ticks, colors), device cards, SSIDs, server hardware tiles, guest cards, DMZ groups and their chips, multi-app container cards, storage pools, the media pipeline nodes and shares.

Hardcoded in each site’s `layout.py` (you will almost certainly edit these):

| Section (search for) | What's fixed | Typical change |
|---|---|---|
| `# TOP: edge chain` | positions `CX`, `cy0`, `fy, fh` (ISP router), `ox, oy, ow, oh` (firewall), `bx, by, bw, bh` (switch) | different heights/widths, no ISP router (bridge mode), no separate firewall |
| ISP router block (`FBX`, `COAX_X`, `FB_PORTS`) | a cable modem with a coax port + LAN ports, firewall in `opnsense_port` | DSL/fiber/ONT: rename the coax port or remove it, change port list |
| `port_x()`, `PX0, PITCH` | switch with 8 RJ45 + 2 SFP+ in one row | other port counts, second switch |
| `# device row`: `DY`, `MAD/KVM/AP/ZB` tuples and the `device("madcat", …)` calls | which devices sit under the switch, their x/width/height, and the cable routing to them (`MAD_10G`, `KVM_IN`, `AP_IN`, `ZB_IN`, the `S.line(... PORTS["etherN"] ...)` calls) | add/remove devices, re-route cables so they don't cross |
| `# terra` | the big server card: `tx0, ty0`, `GY`, `ZH`, hardware column width `HWW`, guest column `gx, gw` | several servers, other column split |
| other-VLAN guests | `og["truenas"]`, `og["haos"]`, `og["unifi"]`, `og["bliss"]` drawn one below another with fixed heights | different VMs outside the DMZ |
| `# DMZ zone`: `NCOL` and the `column(i, [group names])` calls | which DMZ group goes into which column | rebalance columns for their groups |
| `# media pipeline` | an *arr/Jellyfin explainer panel | remove the whole section if they don't want it, or reuse it for another flow |
| `W` / `# canvas height` | canvas width and lowest-panel calculation | canvas height follows the site’s panel bottoms; include new panels in that calculation |

Safety nets: `assert`s at the end of sections fail loudly when a column/panel overflows. Text widths come from `measure()` (Pillow + the real font) or the rough estimate `tw()`. Always check visually.

## The interview

Ask in rounds of 3–6 questions, grouped by topic, and offer defaults. If the user has documentation (wiki, notes, a docs repo) or you have shell access to their systems, offer to read that first and only ask for the gaps. **Only run read-only commands, and ask before touching any system.**

1. **Purpose & privacy:** public post (e.g. Reddit) or private? Real domain to hide? Real SSID names to hide? Username watermark? Title and date?
2. **Internet edge:** ISP connection type and speed (down/up), modem/router model, its ports and which one the firewall uses, bridge mode or double NAT/exposed host, DNS provider, offsite backup target.
3. **Firewall/router:** hardware (CPU, RAM, NICs), OS + version, management IP/hostname, services (DNS, DHCP, VPN, IDS/IPS, …), LACP/bonds.
4. **Switch(es):** model, OS/version, management IP, and per port: connected device, negotiated speed, untagged VLAN, tagged VLANs. (Many switches can print this, e.g. RouterOS `/interface ethernet monitor [find] once` and `/interface bridge vlan print`.)
5. **VLANs:** ID, name, subnet, one-line policy ("internet only", "services, no LAN access", …). Colors: keep the defaults unless they want others.
6. **Other devices:** workstation(s), KVM, access points (SSIDs → VLANs), IoT radios/coordinators, NAS boxes, anything with a cable.
7. **Server(s):** hypervisor + version, CPU, RAM, GPU, NICs, every disk (model/size) and whether it's passed through to a VM.
8. **Guests:** every VM/container: ID, IP, VLAN, what runs in it. Containers running several apps (often Docker) become one card with a row per app. Which apps are public (behind a reverse proxy, shown as `app.domain`), which LAN-only, which have no web UI (`name.internal`)?
9. **Storage:** pools/vdevs/disks, used/free, shares and who mounts them.
10. **Port forwards:** port, protocol, target, purpose.
11. **Extras:** remote access/VPN, cloud services, a flow worth explaining (like the media pipeline), anything they're proud of or want to highlight.

Useful read-only commands if you have access (ask first): Proxmox `pct list`, `qm list`, `pct config <id>`; `docker ps`; `ip -br a`; ZFS `zpool list -v`, `zfs list`; TrueNAS `midclt call pool.query`, `midclt call disk.query`; `lspci`; `lsblk -o NAME,MODEL,SIZE`.

## The work loop

1. `cp -r sites/origin sites/<name>` (full panorama) or `cp -r sites/cbny sites/<name>` (flat home network), then write their lab into `sites/<name>/site.yaml` (keep the schema; extend it when needed and teach the layout the new fields).
2. Adapt `sites/<name>/layout.py`: decide which panels exist, adjust the hardcoded positions above, remove sections they don't need. It is a standalone script — keep it that way rather than importing helpers from another site.
3. `python3 fetch_icons.py` (add new icons to `ICON_MAP` first: local name → name in [dashboard-icons](https://github.com/homarr-labs/dashboard-icons); dark icons need a `-light` variant or an entry in `RECOLOR`).
4. `python3 build.py <name>`, then **look at `sites/<name>/out/<name>.png` yourself** before showing it. Zoom into busy areas: `magick sites/<name>/out/<name>.png -crop 1400x600+X+Y +repage -resize 70% /tmp/crop.png` (X/Y in PNG pixels = SVG coordinates × 1.6). Look for overlapping text, cables crossing cards, text running out of boxes, empty gaps.
5. Show the user, take feedback, change, re-render. Expect many small rounds, that's normal.
6. Before they share it: render without `--unredacted` and `grep` `sites/<name>/out/<name>.svg` for their real domain, SSID names and anything private.

## Design rules (keep them unless the user wants otherwise)

- **Line width = negotiated link speed** (`SPEED_W`), plus a small speed tag where a cable reaches a device. Trunks (tagged VLANs) are a white cable with a dark core; access links use the VLAN color.
- Only **physical cables are solid lines**. Dotted = logical, over the internet (VPN, cloud services). Dashed grey = KVM console.
- **Card border = the device's VLAN color**; devices on a trunk (firewall, switch, hypervisor, APs with several SSIDs) get the neutral `TRUNK_BORDER`.
- **Physical devices** use the folder-tab card: tab = `name · type`; body = icon, full model name (or what it is, for self-built machines), `IP · hostname` in the VLAN color, OS + version.
- **Hardware tiles** have the tan bar on the left; label = type (CPU, MEMORY, SSD, …), value = the part, sub line = extra info or `passthrough → <guest>`.
- **DMZ chips:** `CT <id>` top-right, `.<last octet>` below it; third line = hostname: blue `app.domain` if public via the reverse proxy, `name.internal` otherwise, plus a `LAN` pill when the public hostname is LAN/VPN-only.
- **Multi-app containers** are one taller card with a row per app. The Docker badge only appears on multi-app Docker containers.
- **No internal-only ports** (API ports etc.); only what's forwarded from the internet appears, in the "Open to the internet" card.
- ZFS sizes in TiB/GiB (what ZFS reports), disk sizes in TB as sold.
- Keep text plain and short; no marketing-style subtitles.

## Gotchas

- Fonts: **Fira Sans** and **Fira Code** must be installed, otherwise rsvg falls back and every width calculation is off.
- jsDelivr sometimes refuses single icons with 403; `fetch_icons.py` falls back to raw GitHub.
- When content grows, adjust section heights like `ZH`; canvas height follows the lowest panels.
- A device whose cable enters from above must have its entry point right of its folder tab (see how `KVM_IN`/`AP_IN` use `tab_width()`).

## Optional rendering fields (adapted from upstream PR #1)

All layouts accept `python3 build.py <site> --inventory FILE` (also `--inventory=FILE`).
The override is relative to the working directory and must match that site’s schema.
It replaces the content file selected by `--lang`; the language still selects interface
labels and fonts. Only one site can be selected with an inventory override.

The origin panorama additionally supports:

| Field | Location | Effect |
|---|---|---|
| `stub: true` | `fritzbox` | compact unmanaged ISP box, without port row |
| `short` | `switch.ports[]` | shorter port destination label |
| no VLAN fields | used switch port | grey unknown-VLAN styling |
| `kind`, `node`, `vlan` | DMZ guest | VM/CT label, cluster node and VLAN accent |
| `vlans` | `ssids[]` | PPSK VLAN dots; single `vlan` becomes optional |
| `warn` | storage pool | orange usage bar at threshold (default 85%) |

RJ45 ports precede SFP+ ports; the count is derived, but cable routing remains
site-specific. Extra ports may require card width and route adjustments. Pool disk
groups wrap when necessary and assert if the box is too short. Hardware text scales
to its tile width; cbny/hkzn retain their mixed Chinese/Latin measurement and fonts.

Source: https://github.com/Goblinmine/homelab-diagram/pull/1

## hkzn display modes

hkzn supports `--mode dark|light` (default dark), independently of `--lang en|zh`.
Its theme palette is in `THEMES` in `sites/hkzn/layout.py`. Keep mode-specific colors
there, including cloud, hardware and LAN surfaces. Inventory accents are adapted
for light backgrounds at render time; do not duplicate YAML files per mode. Local
glyph colors adapt in memory, while external brand icons keep their original colors.
Both modes retain the same font metrics and coordinates.

hkzn output filenames always include language and mode:
`hkzn-<en|zh>-<dark|light>[-unredacted].svg` / `.png`. This overrides the general
filename examples above for hkzn. Other sites retain their current naming and do
not yet support light mode. Check all four hkzn language/mode combinations visually.
