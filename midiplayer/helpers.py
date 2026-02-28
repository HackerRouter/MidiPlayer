import json
import os

from mcdreforged.api.all import *

# ── globals (set by midiplayer.on_load) ──
data_folder = ''
songs_json_file = ''
queues_dir = ''
player_pages = {}
player_pages_queue = {}
player_current_song = {}
player_play_mode = {}        # {player: 'single'|'random'|'sequential'|'loop'}
player_paused = {}           # {player: bool}
player_auto_next_timer = {}  # {player: threading.Timer}
items_per_page = 8
PLAY_MODES = ('single', 'random', 'sequential', 'loop')


class Config(Serializable):
    edit_permission: int = 2
    items_per_page: int = 8


def tr(key, *args):
    return ServerInterface.psi().tr(f'midiplayer.{key}', *args)


# ── data helpers ──

def _ensure_songs_file():
    if not os.path.exists(songs_json_file):
        with open(songs_json_file, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=4)


def _load_songs():
    _ensure_songs_file()
    with open(songs_json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_songs(data):
    with open(songs_json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _queue_path(player):
    return os.path.join(queues_dir, f'{player}.json')


def _load_queue(player):
    path = _queue_path(player)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def _save_queue(player, queue):
    with open(_queue_path(player), 'w', encoding='utf-8') as f:
        json.dump(queue, f, ensure_ascii=False, indent=4)


def _has_queue(player):
    return os.path.exists(_queue_path(player))


def _fmt_duration(seconds):
    if not seconds:
        return ''
    m, s = divmod(int(seconds), 60)
    return f'{m}:{s:02d}'


# ── RText helpers ──

def _info_text(msg):
    """Create a dark_aqua colored RText for info messages."""
    return RText(str(msg), color=RColor.dark_aqua)


def _err_text(msg):
    """Create a red colored RText for error messages."""
    return RText(str(msg), color=RColor.red)


def _song_text(idx, song, *, clickable=True, show_duration=True, highlight=False, action=None):
    """Build an RText line for a song entry.

    Args:
        idx: 1-based display index
        song: song dict with 'name', 'artist', 'link', optional 'duration'
        clickable: if True, song name is clickable (suggest !!mp play <idx>)
        show_duration: if True, append [m:ss] duration
        highlight: if True, use aqua color + ◄ marker (current playing)
        action: 'add' for [+] button, 'remove' for [-] button, None for no button
    """
    artists = ', '.join(song['artist'])
    dur = _fmt_duration(song.get('duration')) if show_duration else ''
    dur_str = f' [{dur}]' if dur else ''
    name_color = RColor.aqua if highlight else RColor.green
    name_text = RText(song['name'], color=name_color)
    if clickable:
        name_text.c(RAction.suggest_command, f'!!mp play {idx}').h(str(tr('hover.play', song['name'])))
    marker = ' §e◄' if highlight else ''
    parts = [
        RText(f'{idx}. ', color=RColor.gray),
        name_text,
        RText(f' - {artists}{dur_str}{marker}'),
    ]
    if action == 'add':
        parts.append(RText(' [+]', color=RColor.green).c(RAction.suggest_command, f'!!mp add {idx}').h(str(tr('hover.add_queue'))))
    elif action == 'remove':
        parts.append(RText(' [-]', color=RColor.red).c(RAction.suggest_command, f'!!mp remove {idx}').h(str(tr('hover.remove_queue'))))
    return RTextList(*parts)


def _page_nav(page, total_pages, cmd_base):
    """Build clickable pagination navigation."""
    has_prev = page > 1
    has_next = page < total_pages
    prev_btn = RText('[← ]', color=RColor.gray if has_prev else RColor.dark_gray)
    if has_prev:
        prev_btn.c(RAction.suggest_command, f'{cmd_base} {page - 1}').h(f'{page - 1}')
    next_btn = RText('[ →]', color=RColor.gray if has_next else RColor.dark_gray)
    if has_next:
        next_btn.c(RAction.suggest_command, f'{cmd_base} {page + 1}').h(f'{page + 1}')
    return RTextList(prev_btn, RText(f' {page}/{total_pages} ', color=RColor.gold), next_btn)


# ── pagination helpers ──

def _get_page(data, player, pages_dict):
    total = len(data)
    total_pages = max(1, (total + items_per_page - 1) // items_per_page)
    page = pages_dict.get(player, 1)
    page = min(page, total_pages)
    start = (page - 1) * items_per_page
    end = min(page * items_per_page, total)
    return page, start, end, total_pages


def _show_song_page(source, songs, page, start, end, total_pages, cmd_base='!!mp list'):
    """Display a page of songs with clickable entries and pagination."""
    source.reply(_info_text(str(tr('msg.page_info', page, total_pages))))
    for idx in range(start, end):
        source.reply(_song_text(idx + 1, songs[idx], action='add'))
    source.reply(_page_nav(page, total_pages, cmd_base))


def _show_queue_page(source, queue, songs, page, start, end, total_pages, current_link=None):
    """Display a page of queue with clickable entries and pagination."""
    source.reply(_info_text(str(tr('msg.page_info', page, total_pages))))
    for idx in range(start, end):
        link = queue[idx]
        song = next((s for s in songs if s['link'] == link), None)
        if song:
            is_current = link == current_link
            # find global song index for remove command
            global_idx = next((i for i, s in enumerate(songs) if s['link'] == link), idx)
            source.reply(_song_text(global_idx + 1, song, highlight=is_current, action='remove'))
    source.reply(_page_nav(page, total_pages, '!!mp queue'))


def _show_search_results(source, matches):
    """Display search results with clickable song names."""
    source.reply(_info_text(str(tr('msg.found_songs', len(matches)))))
    for idx, song in matches:
        source.reply(_song_text(idx + 1, song, show_duration=False, action='add'))


# ── song matching ──

def _find_song(songs, user_input, raw=None):
    """Returns (song, index) or list of (index, song) matches, or None.
    raw is the original input before underscore replacement."""
    if user_input.isdigit():
        idx = int(user_input) - 1
        if 0 <= idx < len(songs):
            return songs[idx], idx
        return None
    raw = raw or user_input
    matches = [
        (i, s) for i, s in enumerate(songs)
        if user_input.lower() in s['name'].lower()
        or raw.lower() in s['name'].lower()
        or raw.lower() in s.get('link', '').lower()
        or any(user_input.lower() in a.lower() for a in s['artist'])
    ]
    if len(matches) == 1:
        return matches[0][1], matches[0][0]
    if matches:
        return matches
    return None


def _parse_multi_index(user_input, max_len):
    """Parse comma/range input like '1,3,5' or '1-5' into index list (0-based)."""
    indexes = []
    if ',' in user_input:
        for part in user_input.split(','):
            part = part.strip()
            if part.isdigit():
                indexes.append(int(part) - 1)
    elif '-' in user_input:
        parts = user_input.split('-', 1)
        if parts[0].strip().isdigit() and parts[1].strip().isdigit():
            s, e = int(parts[0].strip()), int(parts[1].strip())
            indexes = list(range(s - 1, e))
    return [i for i in indexes if 0 <= i < max_len]


def _send_help(source, key='help'):
    """Send help message with clickable command suggestions."""
    lines = str(tr(key)).split('\n')
    for line in lines:
        if not line.strip():
            continue
        if line.startswith('========'):
            source.reply(_info_text(line))
        elif line.startswith('!!'):
            parts = line.split(' - ', 1)
            cmd = parts[0].strip()
            # extract the base command (e.g. "!!mp list" from "!!mp list [page]")
            base_cmd = cmd.split('[')[0].split('<')[0].strip()
            desc = parts[1].strip() if len(parts) == 2 else ''
            text = RTextList(
                RText(cmd, color=RColor.gray).c(RAction.suggest_command, base_cmd).h(base_cmd),
                RText(f' - {desc}') if desc else RText(''),
            )
            source.reply(text)
        else:
            source.reply(line)
