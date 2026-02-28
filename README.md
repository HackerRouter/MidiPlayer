[English](README.md) | [简体中文](README.zh-CN.md)

# MidiPlayer

An [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) plugin for playing music from datapacks converted from MIDI/`.nbs` files using [Note Block Studio](https://github.com/OpenNBS/NoteBlockStudio) in Minecraft servers.

Also includes GUI and CLI tools for generating the `songs.json` configuration file.

[demo](demo.png)

---

## Workflow

1. Prepare music files (`.mid`, `.nbs`)
2. Export as datapacks using [Note Block Studio](https://github.com/OpenNBS/NoteBlockStudio)
3. Use the GUI or CLI tool to export `songs.json`
4. Place `songs.json` in `./config/midiplayer`
5. Install the midiplayer plugin (e.g. drag `midiplayer.pyz` into `./plugins`)
6. Start [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) to load the plugin

---

## In-Game Plugin Usage

### Player Commands `!!mp`

| Command | Description |
|---------|-------------|
| `!!mp` | Show help |
| `!!mp list [page]` | Song list |
| `!!mp links [page]` | Link list |
| `!!mp search <keyword>` | Search songs |
| `!!mp play [keyword/index]` | Play a song |
| `!!mp pause` | Pause |
| `!!mp resume` | Resume playback |
| `!!mp now` | Now playing |
| `!!mp next` | Next song |
| `!!mp prev` | Previous song |
| `!!mp mode <mode>` | Play mode (single/random/sequential/loop) |
| `!!mp shuffle` | Shuffle queue |
| `!!mp add <keyword/index>` | Add to queue |
| `!!mp remove <keyword/index>` | Remove from queue |
| `!!mp queue [page]` | View queue |
| `!!mp queue search <keyword>` | Search queue |
| `!!mp clear` | Clear queue |

### Admin Commands `!!mpa`

| Command | Description |
|---------|-------------|
| `!!mpa add <name> <artists> <link>` | Add song |
| `!!mpa del <index>` | Delete song |
| `!!mpa copy <index>` | Copy song |
| `!!mpa set <index> name <name>` | Edit name |
| `!!mpa set <index> artist <artists>` | Edit artist |
| `!!mpa set <index> link <link>` | Edit link |
| `!!mpa set <index> duration <seconds>` | Edit duration |
| `!!mpa info [page]` | Song details list |
| `!!mpa debug [player]` | Debug info |
| `!!mpa timer <player> reset` | Reset timer |
| `!!mpa timer <player> interval <seconds>` | Set timer interval |
| `!!mpa timer <player> active <true/false>` | Toggle timer |

---

## GUI Tool

The GUI provides a visual interface for generating `songs.json`.

### Launch

```bash
python midiplayer.pyz --gui
```

### How to Use

1. Left panel: Enter `Song Name - Artist1, Artist2, ...` per line
2. Middle panel: Corresponding datapack IDs (line-by-line match with songs)
3. Right panel: Auto-generated JSON preview

- Click "Import Datapack" to import `.zip` datapack files — the function call name (referred to as "link") and duration are auto-detected
- Click "Export JSON" to save as `songs.json`
- Click "Import JSON" to load an existing `songs.json` for editing

---

## CLI Tool

Command-line mode for batch generating `songs.json`.

### Usage

```bash
python midiplayer.pyz <song-artist-file> <datapack-id-file-or-directory> [output-path]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `song-artist-file` | Text file with `Song Name - Artist` per line |
| `datapack-id-file-or-directory` | Text file with one datapack ID per line, or a directory containing `.zip` datapacks |
| `output-path` (optional) | Output directory for JSON, defaults to current directory |

### Examples

```bash
# Using text files
python midiplayer.pyz songs.txt datapacks.txt ./output

# Using a datapack directory (auto-detects links and durations from zips)
python midiplayer.pyz songs.txt ./datapacks/ ./output
```

---

## Building

### Build as MCDR Plugin + Standalone CLI/GUI Tool

Package as a `.pyz` (Python Zip Application), which works both as a standalone CLI/GUI tool and as an MCDR plugin:

```bash
cd midiplugin
zip -r ../midiplayer.pyz __main__.py midiplayer/ lang/
```

Usage:

If `.pyz` files are properly associated, you can double-click to launch the GUI directly.
```bash
python midiplayer.pyz --gui          # Launch GUI
python midiplayer.pyz songs.txt ./datapacks/  # CLI mode
```
Place the `.pyz` plugin file into MCDReforged's `plugins/` directory.

## Dependencies

- Python >= 3.8
- [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) >= 2.0.0-alpha.1 (only required for the in-game plugin)
- GUI/CLI tools have no extra dependencies (Python stdlib only: `tkinter`, `zipfile`, `json`, `argparse`, etc.)
