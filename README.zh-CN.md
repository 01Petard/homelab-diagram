# homelab-diagram

[English](README.md) · [简体中文](README.zh-CN.md)

根据 YAML 中的网络清单生成 SVG 和 PNG 网络拓扑图。公开示例 `origin` 包含运营商路由器、防火墙、VLAN 交换机、Proxmox 虚拟客户机、TrueNAS 存储池、公网服务及媒体处理流程。

![示例效果](docs/example.png)

原项目通过 Claude Code 编写代码、生成图片和反复反馈逐步完成。本版本延续这一方式：**YAML 描述网络内容，Python 决定卡片和连线的位置。** 修改清单不会自动重新设计布局，可以让 AI 根据实际网络调整并检查成图。

## 示例文件

本文仅介绍公开示例 `origin`。

```text
sites/
  origin/
    site.en.yaml          英文网络清单
    site.zh.yaml          中文网络清单，与英文版保持相同网络事实
    layout.py             独立布局、SVG 绘制和 PNG 转换脚本
    out/                  生成的 SVG 和 PNG，已被 Git 忽略
build.py                  站点选择与命令行入口
fetch_icons.py            第三方服务图标下载脚本
icons/                    项目自带线条图标及下载的服务图标
pyproject.toml, uv.lock    Python 依赖声明与锁文件
CLAUDE.md                 供 AI 适配网络时参考的项目说明
```

两种语言的 IP、主机名、ID、端口及拓扑应保持一致。绘图代码中的界面文字在 `UI` 配置中翻译，产品名称和技术标识通常保留原文。

## 环境要求

- **Git**：用于克隆仓库，已下载项目时可跳过克隆。
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)**：管理 Python 和项目依赖。
- **Python 3.11 或更高版本**：本机没有兼容版本时，uv 可以安装所需解释器。
- **librsvg**：提供 PNG 导出所需的 `rsvg-convert` 命令。
- **fontconfig**：提供字体测量时使用的 `fc-match` 命令。
- **Fira Sans、Fira Code** 字体：见 [Fira](https://github.com/mozilla/Fira) 和 [Fira Code](https://github.com/tonsky/FiraCode)。
- 中文版还需要中文字体：macOS 可用 **PingFang SC**，Linux 可用 **Noto Sans CJK SC**。

uv 根据项目依赖声明安装 PyYAML 和 Pillow，**不会替你安装 librsvg、fontconfig 或系统字体**。

macOS 已安装 Homebrew 时，可执行：

```bash
brew install uv librsvg fontconfig
brew install --cask font-fira-sans font-fira-code
```

Linux 请按 uv 官方安装指南安装 uv，再通过所用发行版的包管理器安装 librsvg、fontconfig 和字体。Debian/Ubuntu 中提供 librsvg 命令的包名为 `librsvg2-bin`。Windows 用户可在 WSL2 中按 Linux 流程运行；这里尚未验证原生 Windows 绘图。

安装字体后检查以下命令，确认 `fc-match` 返回的是目标字体，而不是无关的替代字体：

```bash
uv --version
rsvg-convert --version
fc-match 'Fira Sans'
fc-match 'Fira Code'
# 中文还需检查实际安装的中文字体，例如：
fc-match 'Noto Sans CJK SC'
```

## 使用 uv 首次运行

在项目根目录打开终端，也就是同时包含 `build.py` 和 `pyproject.toml` 的目录。尚未克隆时，使用你选择的仓库地址，并检出包含本 README 的分支；已经打开的仓库无须另行切换分支。

```bash
# 建立 .venv，按锁文件安装 Python 依赖
uv sync --locked

# 首次下载第三方服务图标，需要联网
uv run python fetch_icons.py

# 分别生成 origin 的英文和中文图
uv run python build.py origin --lang en
uv run python build.py origin --lang zh
```

不必手动激活 `.venv`。[uv sync 和 uv run](https://docs.astral.sh/uv/concepts/projects/sync/) 会管理项目环境。以后修改网络清单或布局后，重新执行出图命令即可；只有图标缺失或新增时才需要再次下载。

输出文件为：

```text
sites/origin/out/origin-en-dark.svg
sites/origin/out/origin-en-dark.png
sites/origin/out/origin-zh-dark.svg
sites/origin/out/origin-zh-dark.png
```

`origin` 目前**只支持深色模式**。命令行入口接受 `--mode dark`，但此示例不支持 `--mode light`。README 顶部图片是历史预览，以上命令生成的是当前版本。

## 常用命令

| 用途 | 命令 |
|---|---|
| 默认英文图 | `uv run python build.py origin` |
| 中文图 | `uv run python build.py origin --lang zh` |
| 保留真实域名和 SSID 的中文图 | `uv run python build.py origin --lang zh --unredacted` |
| 临时使用另一份清单 | `uv run python build.py origin --inventory /path/to/alternative.yaml` |
| 中文界面搭配另一份清单 | `uv run python build.py origin --lang zh --inventory /path/to/alternative.zh.yaml` |
| 直接运行布局脚本 | `uv run python sites/origin/layout.py --lang zh` |
| 代码修改后运行回归测试 | `uv run python -m unittest discover -s tests -v` |

替代清单必须符合 origin 的数据结构，且一次只能指定一个站点。它会覆盖默认选取的语言内容文件，`--lang` 仍负责选择界面语言和字体。输出仍使用通常的文件名，因此比较不同清单时，请先另存需要保留的图片。

## 默认脱敏具体做什么

origin 清单默认开启域名和 SSID 脱敏：

- 将配置的域名替换成 `redact.domain_placeholder`。
- 开启域名脱敏时，标题使用 `meta.title_redacted`。
- SSID 使用每项的 `redacted` 标签，而非原始 `name`。

加上 `--unredacted` 后跳过这些替换，输出文件名追加 `-unredacted`，例如 `origin-zh-dark-unredacted.png`。

**IP、MAC、设备名称、用户名或水印，以及其他说明文字，不会自动隐藏。** 分享之前应同时查看 SVG 文本与 PNG 图片。脱敏效果取决于清单配置，不能将默认出图理解为“所有隐私信息均已隐藏”。

## 让 AI 帮你执行完整流程

在支持终端和文件操作的 AI 编程工具中打开仓库，例如 Codex 或 Claude Code。AI 需要具备执行命令的权限；缺少系统依赖时还需要相应安装权限。应以实际代码为准，并将 `CLAUDE.md` 作为项目背景参考。

以下内容是可复制到 AI 工具中的提示词，不会因阅读 README 而自动执行。可以先使用完整提示词跑通示例，再按需发送后续提示词。

### 提示词一：从环境检查到生成示例图

```text
请帮我把这个仓库从环境准备一直运行到确认图片生成。请实际执行，不要只列出让我自行执行的命令。

1. 确认项目位置。若尚未打开或克隆，先向我询问仓库地址和保存目录。
   阅读 README.zh-CN.md、pyproject.toml、uv.lock、build.py、fetch_icons.py，
   以及 origin 的布局和中英文清单。检查 Git 状态，保留当前分支与已有修改。
2. 检测操作系统，检查 uv、Python >=3.11、rsvg-convert、fc-match、Fira Sans、
   Fira Code 和中文字体。缺少系统依赖时，说明缺项，并在环境允许的授权范围内
   使用官方方式或包管理器安装。不要安装无关工具，不要通过升级项目依赖来掩盖系统缺项。
3. 执行 uv sync --locked，再执行 uv run python fetch_icons.py。
   如果安装或下载失败，读取实际错误，修复能解决的问题后重试，不要将失败步骤报告为成功。
4. 执行 uv run python build.py origin --lang en 和
   uv run python build.py origin --lang zh，保留默认脱敏。
   origin 当前不支持浅色模式，不要传入 --mode light。
5. 打开两张生成的 PNG，并放大查看拥挤区域，检查字体缺字、图标缺失、文字重叠、
   卡片或连线被裁切等问题。若需修复，只调整绘图问题，不改变示例网络事实。
   修改代码后运行相关回归测试，再重新生成图片。
6. 给我实际执行的命令、生成文件路径、已检查内容和仍存在的阻碍，并展示或链接图片。
   本次仅运行示例，不推送、不公开发布、不探测真实网络，也不修改任何网络设备配置。
```

### 提示词二：把示例改成我的网络

```text
origin 示例已经能正常出图，请继续帮我制作自己的网络图。
先参考 CLAUDE.md 理解项目，但只以 origin 为起点模板。向我询问新站点名称、
需要的语言、隐私要求，以及是否有已有网络文档。缺失信息分小轮询问：互联网与网关、
交换机与 VLAN、客户机、服务器与虚拟客户机、存储和公网服务。

将 origin 模板复制到以我指定名称命名的新站点目录，不覆盖 origin。
示例设备只有经我确认确实拥有后才能出现在我的最终图里，不确定的事实明确标为未知。
如果需要中英文，保持两份清单的网络事实一致；翻译显示名称时保留 DMZ 分组 key 等稳定标识。

按实际拓扑调整 layout.py，并让输出文件名明确包含语言和模式。
不要因为存在命令行参数就假定布局已支持浅色模式。复用自带图标，并下载需要的服务图标。
生成 PNG、打开检查、修正重叠，再与我迭代。任何真实网络探测都应先明确范围并获得授权；
不要为了绘图修改路由器、交换机或服务器设置。
最后提供成图和准确的重新生成命令，不推送、不公开发布。
```

### 提示词三：优化成图并准备分享

```text
请根据我已确认的网络清单检查最新图片，查看原尺寸 PNG，并放大拥挤区域。
修正文字截断、卡片重叠和含义不清的连线，同时保持网络拓扑、设备事实和中英文版本一致。

生成默认脱敏版，同时检查 SVG 和 PNG 中的真实域名、SSID、地址、MAC、主机名和水印。
列出仍可见的信息，向我确认希望怎样处理，不要宣称默认脱敏会隐藏全部私人信息。
如果我要求保留未脱敏版本，请单独生成，不与脱敏版混淆。
展示最终图片，列出准确的命令和文件路径，不要公开发布。
```

## 绘图能力和适配边界

线宽表示实际协商的连接速率；实线代表物理连线，点线代表隧道或互联网连接。VLAN 通过颜色区分，图例解释干道、接入口和端口标记。

origin 模板还包含从 [上游 PR #1](https://github.com/Goblinmine/homelab-diagram/pull/1) 适配的可选字段：简化运营商设备框（`stub`）、端口短标签（`short`）、未知 VLAN 端口样式、PPSK 无线网络（`vlans`）、客户机 `kind`/`node`/`vlan` 标记，以及存储使用率警告（`warn`，默认 85%）。磁盘组可换行，溢出检查会提示哪些区域需要增加空间。字段及布局说明见 [CLAUDE.md](CLAUDE.md)。

画布高度随面板底部计算，但卡片位置、面板宽度和连线路径仍需按站点调整。应以 origin 为起点，根据确认的拓扑修改布局；仅更换 YAML 无法适配所有网络。

## 常见问题

| 现象 | 排查方式 |
|---|---|
| 找不到 `uv` | 安装 uv，重新打开终端或检查 PATH。 |
| 找不到 `rsvg-convert` | 安装 librsvg；Python 依赖不包含这个系统命令。 |
| 缺少图标 | 执行 `uv run python fetch_icons.py`，检查脚本报告的下载失败项。 |
| 中文变方框或文字间距异常 | 安装字体，检查 `fc-match` 实际返回的字体家族。 |
| 提示某个区域溢出 | 调整 `layout.py` 对应面板尺寸或连线路径，再出图并检查。 |
| `--mode light` 报错 | origin 当前只支持深色模式。 |
| 有 PNG 文件，但内容没有更新 | 检查命令是否成功退出，以及带语言和模式的实际文件名；运行失败后旧文件可能仍在。 |

## 致谢与许可证

- 原项目：[Goblinmine/homelab-diagram](https://github.com/Goblinmine/homelab-diagram)，通过 Claude Code 开发；本版本包含后续适配改进。
- 代码和自带 `glyph-*.svg` 图标：MIT，见 [LICENSE](LICENSE)。
- 下载的服务图标：[homarr-labs/dashboard-icons](https://github.com/homarr-labs/dashboard-icons)，标识归各自项目所有，不随本仓库分发。
- 字体：Fira Sans 和 Fira Code，单独按其字体许可证分发。
