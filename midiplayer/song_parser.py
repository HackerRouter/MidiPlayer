"""Shared song parsing logic and i18n for CLI/GUI."""
import json
import locale
import pkgutil
import zipfile

_lang_data = None


def _detect_lang_file():
    lang = locale.getlocale()[0] or ''
    if 'Chinese' in lang or 'zh_CN' in lang or 'zh' in lang.lower():
        return 'lang_zh_cn.json'
    return 'lang_en_us.json'


def load_lang():
    global _lang_data
    if _lang_data is None:
        data = pkgutil.get_data('lang', _detect_lang_file())
        _lang_data = json.loads(data.decode('utf-8'))
    return _lang_data


def tr(key: str) -> str:
    return load_lang().get(key, key)


def extract_link_from_zip(zip_path):
    """Extract the function link prefix from a datapack zip.
    
    Looks for play.mcfunction inside the zip and derives the link
    from the directory structure: data/<ns>/functions/<path>/play.mcfunction
    -> link = "ns:path" (if path exists) or "ns" (if no path).
    
    The link is used as: /function {link}/play or /function {link}:play
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                # Find play.mcfunction
                if name.endswith('/play.mcfunction') and '/functions/' in name:
                    # e.g. "data/ns/functions/path/name/play.mcfunction"
                    # Split on "data/" and "functions/"
                    parts = name.split('/')
                    try:
                        data_idx = parts.index('data')
                        func_idx = parts.index('functions')
                    except ValueError:
                        continue
                    ns = '/'.join(parts[data_idx + 1:func_idx])
                    # path is everything between functions/ and play.mcfunction
                    path_parts = parts[func_idx + 1:-1]  # exclude "play.mcfunction"
                    if path_parts:
                        return f"{ns}:{'/'.join(path_parts)}"
                    else:
                        return ns
    except Exception:
        pass
    return None


def parse_songs(song_lines, datapack_lines, durations=None):
    """Parse song-artist lines and datapack ID lines into song entries.
    
    Returns list of dicts with name/link/artist/duration.
    Also returns updated song_lines (with auto-filled entries).
    """
    durations = durations or {}
    if song_lines == ['']:
        song_lines = []
    if datapack_lines == ['']:
        datapack_lines = []

    total = max(len(song_lines), len(datapack_lines))
    parsed = []
    filled_song_lines = list(song_lines)

    for i in range(total):
        song_line = song_lines[i] if i < len(song_lines) else ""
        datapack_name = datapack_lines[i] if i < len(datapack_lines) else ""

        parts = song_line.split("-")
        if len(parts) == 1:
            song_name = parts[0].strip()
            artist = [tr("anonymous")]
            # auto-fill missing artist
            if song_name:
                fill = f"{song_name} - {tr('anonymous')}"
                if i < len(filled_song_lines):
                    filled_song_lines[i] = fill
                else:
                    filled_song_lines.append(fill)
        else:
            song_name = parts[0].strip()
            artist = [a.strip() for a in parts[1].split(",")]

        if not song_name and datapack_name:
            song_name = datapack_name
            # auto-fill the song line
            fill = f"{datapack_name} - {tr('anonymous')}"
            if i < len(filled_song_lines):
                filled_song_lines[i] = fill
            else:
                filled_song_lines.append(fill)

        parsed.append({
            "name": song_name,
            "link": datapack_name.lower(),
            "artist": artist,
            "duration": durations.get(datapack_name.lower(), 0)
        })

    return parsed, filled_song_lines
