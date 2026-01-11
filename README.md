# 🍭 ONCE-TUBE

**ONCE-TUBE** is a high-performance Terminal User Interface (TUI) built for TWICE fans (ONCE) and terminal enthusiasts. It allows you to search and stream YouTube videos or audio-only directly from your terminal with a sleek, magenta-themed aesthetic.

Built with **Python**, **Textual**, and **yt-dlp**, with a heavy focus on system efficiency and low resource consumption.

![License](https://img.shields.io/badge/license-MIT-magenta)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![Bias](https://img.shields.io/badge/Bias-Jihyo-pink)

## ✨ Features

- **Blazing Fast Search**: Uses `yt-dlp` for efficient metadata scraping.
- **Optimized UI**: Built with Textual's modern engine, customized for ultra-low CPU usage.
- **Singleton Media Player**: Ensures only one instance of `mpv` is running at a time—no window clutter.
- **Hardware Acceleration**: Automatically utilizes GPU decoding (`--hwdec=auto`) to keep your CPU cool.
- **TWICE Themed**: Custom color palette (#FF5FA2, #FCC89B, #FF3B81) for the ultimate aesthetic.

## 🛠 Engineering & Optimization

As a developer focused on performance and system architecture, this project wasn't just about playing music; it was about solving common TUI bottlenecks:

- **CPU Optimization**: Reduced idle usage from **70% to ~5%** by implementing batch updates in `DataTable` and eliminating layout refresh loops.
- **Process Management**: Implemented a cleanup system to prevent "zombie processes" when the app or media player is closed.
- **Asynchronous Execution**: All network calls and process spawning are handled asynchronously to keep the UI responsive.

## 🚀 Installation

### Prerequisites

Make sure you have these system dependencies installed:
- [mpv](https://mpv.io/) (The media player)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (YouTube backend)

### 1. Using `uv` (Recommended)

If you use [uv](https://github.com/astral-sh/uv), just clone and run:

```bash
git clone [https://github.com/FarrelApriandry/once-tube.git](https://github.com/FarrelApriandry/once-tube.git)
cd once-tube
uv pip install -e .
once-tube

```

### 2. Using `pip`

```bash
pip install .
once-tube

```

## ⌨️ Keybindings

| Key | Action |
| --- | --- |
| `Enter` | Search or Select Video |
| `V` | Play Video Mode |
| `A` | Play Audio-Only Mode |
| `Esc` | Clear search input |
| `D` | Toggle Dark Mode |
| `Q` | Quit Application |

## 🎨 Configuration

The styling is handled via `once_tube.tcss`. You can customize the colors and layouts there to fit your terminal's vibe.

## 🛡 Security & Development Notes

- **Input Handling**: This tool uses `asyncio.create_subprocess_exec` for handling searches, which provides a layer of protection against common shell injection attacks by passing arguments as a list rather than a raw string.
  
- **Protection Layer**: This tool uses `asyncio.create_subprocess_exec` for handling searches, which provides a layer of protection against common shell injection attacks by passing arguments as a list rather than a raw string.

- **Query Sanitization Plan**: 
  > **Note:** Initial development included a plan to strictly sanitize and force-append "TWICE" to every query to ensure a focused experience. However, to maximize functionality and allow users the freedom to explore related content or other artists without breaking the core TUI logic, I decided to keep the search open-ended while maintaining a "TWICE-first" aesthetic.

---
