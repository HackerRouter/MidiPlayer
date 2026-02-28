English | [简体中文](README.zh-CN.md)

# MidiPlayer

An [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) plugin for playing music from datapacks converted from MIDI/`.nbs` files using [Note Block Studio](https://github.com/OpenNBS/NoteBlockStudio) in Minecraft servers.

Also a GUI/CLI tool for generating the `songs.json` configuration file the plugin needs.

---

## Features

- In-game song request, pause, skip, queue management with four play modes: single / random / sequential / loop
- Auto-advances to the next song
- Admins can add, remove, or edit song info in real time from in-game
- Auto-detects datapack function call name (link) and song duration when importing `.zip` datapacks
- A single `.pyz` file serves as both an MCDR plugin and a standalone GUI/CLI tool to edit `songs.json`

![demo](demo.png)

---

## Workflow

1. Prepare music files (`.mid`, `.nbs`, or any file importable by [Note Block Studio](https://github.com/OpenNBS/NoteBlockStudio))

2. Export as datapacks using [Note Block Studio](https://github.com/OpenNBS/NoteBlockStudio).
(Yes, you can customize the namespace, path, and other export parameters however you like)

- Download and install Note Block Studio from the [NBS website](https://noteblock.studio/)

- Top-left: select `Open Song` (for `.nbs` files) / `Import from MIDI`

- Once opened, top-left: select `Export as Datapack`

- Choose the correct `Minecraft Version`, then click `Export`

3. Use the [GUI Tool](#gui-tool) or [CLI Tool](#cli-tool) to export `songs.json`

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
| `!!mp links [page]` | Link (datapack function call name) list |
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
| `!!mpa set <index> link <link>` | Edit link (datapack function call name) |
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

If `.pyz` files are properly associated, you can double-click to launch the GUI directly.

Or use the following command:
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
python midiplayer.pyz <song-artist-file> <datapack-id-file-or-directory> [output-path] [-d duration-file]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `song-artist-file` | Text file with `Song Name - Artist` per line |
| `datapack-id-file-or-directory` | Text file with one datapack ID per line, or a directory containing `.zip` datapacks |
| `output-path` (optional) | Output directory for JSON, defaults to current directory |
| `-d`/`--duration` (optional) | Text file with one duration (seconds) per line, matching songs line by line |

### Examples

```bash
# Using text files
python midiplayer.pyz songs.txt datapacks.txt ./output

# Using a datapack directory (auto-detects links and durations from zips)
python midiplayer.pyz songs.txt ./datapacks/ ./output

# Using text files + manually specified durations
python midiplayer.pyz songs.txt datapacks.txt ./output -d durations.txt
```

---

## Building

Package as a `.pyz` (Python Zip Application), which works both as a standalone CLI/GUI tool and as an MCDR plugin.

Run from the parent directory of `midiplugin`:

```bash
python -m zipapp midiplugin -o midiplayer.pyz
```

- `midiplugin` — source directory containing the `__main__.py` entry point
- `-o midiplayer.pyz` — specifies the output filename


---

## Dependencies

- Python >= 3.8
- [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) >= 2.0.0-alpha.1 (only required for the in-game plugin)
