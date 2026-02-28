import random
import threading

from mcdreforged.api.all import *

from midiplayer.helpers import (
    tr, _load_songs, _save_songs, _load_queue, _save_queue, _has_queue,
    _fmt_duration, _info_text, _err_text, _song_text,
    _get_page, _show_song_page, _show_queue_page, _show_search_results,
    _find_song, _parse_multi_index, _send_help, _page_nav, _func_cmd,
    player_pages, player_pages_queue, player_current_song, player_play_mode,
    player_paused, player_auto_next_timer, PLAY_MODES,
)
from midiplayer import helpers


# ── helpers ──

def _tr_mode(m):
    """Translate a play mode key to localized display name."""
    return str(tr(f'mode.{m}'))

def _get_song_duration(songs, link):
    song = next((s for s in songs if s['link'] == link), None)
    return song.get('duration') if song else None


def _show_now_playing(source, songs, queue, current_idx):
    """Show prev/current/next using unified _song_text format."""
    for offset, label in [(-1, str(tr('label.prev'))), (0, None), (1, str(tr('label.next')))]:
        idx = (current_idx + offset) % len(queue)
        link = queue[idx]
        song = next((s for s in songs if s['link'] == link), None)
        if not song:
            continue
        global_idx = next((i for i, s in enumerate(songs) if s['link'] == link), idx)
        is_current = offset == 0
        prefix = f'§7{label}: ' if label else ''
        line = _song_text(global_idx + 1, song, highlight=is_current)
        if prefix:
            source.reply(RTextList(RText(prefix), line))
        else:
            source.reply(line)


def _play_song_and_timer(server, player, song, songs, _msgs=None):
    """Play a song and start auto-next timer if duration available."""
    from midiplayer.midiplayer import _start_auto_next
    server.execute(f'execute as {player} run function {_func_cmd(song["link"], "play")}')
    player_current_song[player] = song['link']
    player_paused[player] = False
    dur = song.get('duration')
    if dur:
        _start_auto_next(server, player, dur, songs, _msgs=_msgs)


def _validate_page(page, total_pages):
    """Return valid page number or None if invalid."""
    if page < 1 or page > total_pages:
        return None
    return page


# ── user commands ──

def cmd_help(source: CommandSource):
    _send_help(source)


def cmd_list(source: CommandSource, context=None):
    player = source.player if source.is_player else None
    if not player:
        return
    songs = _load_songs()
    if not songs:
        source.reply(_err_text(str(tr('msg.no_songs'))))
        return
    total_pages = max(1, (len(songs) + helpers.items_per_page - 1) // helpers.items_per_page)
    if context and 'page' in context:
        p = _validate_page(context['page'], total_pages)
        if p is None:
            source.reply(_err_text(str(tr('msg.invalid_page'))))
            return
        player_pages[player] = p
    elif player not in player_pages:
        player_pages[player] = 1
    page, start, end, total_pages = _get_page(songs, player, player_pages)
    _show_song_page(source, songs, page, start, end, total_pages)


def cmd_links(source: CommandSource, context=None):
    player = source.player if source.is_player else None
    if not player:
        return
    songs = _load_songs()
    if not songs:
        source.reply(_err_text(str(tr('msg.no_songs'))))
        return
    if context and 'page' in context:
        total_pages = max(1, (len(songs) + helpers.items_per_page - 1) // helpers.items_per_page)
        p = _validate_page(context['page'], total_pages)
        if p is None:
            source.reply(_err_text(str(tr('msg.invalid_page'))))
            return
        player_pages[player] = p
    elif player not in player_pages:
        player_pages[player] = 1
    page, start, end, total_pages = _get_page(songs, player, player_pages)
    source.reply(_info_text(str(tr('msg.page_info', page, total_pages))))
    for idx in range(start, end):
        song = songs[idx]
        source.reply(RTextList(
            RText(f'{idx + 1}. ', color=RColor.gray),
            RText(song['name'], color=RColor.green),
            RText(f' : {song["link"]}', color=RColor.gray),
        ))
    source.reply(_page_nav(page, total_pages, '!!mp links'))


def cmd_search(source: CommandSource, context):
    player = source.player if source.is_player else None
    if not player:
        return
    raw = context['keyword']
    keyword = raw.replace('_', ' ')
    songs = _load_songs()
    matches = [
        (i, s) for i, s in enumerate(songs)
        if keyword.lower() in s['name'].lower()
        or raw.lower() in s['name'].lower()
        or raw.lower() in s.get('link', '').lower()
        or any(keyword.lower() in a.lower() for a in s['artist'])
    ]
    if matches:
        _show_search_results(source, matches)
    else:
        source.reply(_err_text(str(tr('msg.no_match'))))


def cmd_play(source: CommandSource, context=None):
    player = source.player if source.is_player else None
    if not player:
        return
    server = source.get_server()
    songs = _load_songs()

    # !!mp play without args — play current or first in queue
    if context is None or 'keyword' not in context:
        current = player_current_song.get(player)
        if current:
            song = next((s for s in songs if s['link'] == current), None)
            song_name = song['name'] if song else current
            source.reply(_info_text(str(tr('msg.resumed', song_name))))
            if song:
                _play_song_and_timer(server, player, song, songs)
            else:
                server.execute(f'execute as {player} run function {_func_cmd(current, "play")}')
        else:
            queue = _load_queue(player)
            if queue:
                song = next((s for s in songs if s['link'] == queue[0]), None)
                if song:
                    source.reply(_info_text(str(tr('msg.playing', song['name']))))
                    _play_song_and_timer(server, player, song, songs)
            else:
                source.reply(_err_text(str(tr('msg.queue_empty'))))
        return

    raw = context['keyword']
    user_input = raw.replace('_', ' ')
    queue = _load_queue(player)
    result = _find_song(songs, user_input, raw)

    if result is None:
        source.reply(_err_text(str(tr('msg.no_match'))))
        return
    if isinstance(result, list):
        _show_search_results(source, result)
        return

    song, _ = result
    if song['link'] not in queue:
        queue.append(song['link'])
        _save_queue(player, queue)
    if player in player_current_song:
        server.execute(f'execute as {player} run function {_func_cmd(player_current_song[player], "stop")}')
    source.reply(RTextList(
        _info_text(str(tr('msg.found_song', song['name'], ', '.join(song['artist'])))),
    ))
    source.reply(_info_text(str(tr('msg.playing', song['name']))))
    _play_song_and_timer(server, player, song, songs)


def cmd_stop(source: CommandSource):
    player = source.player if source.is_player else None
    if not player:
        return
    server = source.get_server()
    from midiplayer.midiplayer import _cancel_auto_next
    _cancel_auto_next(player)
    if not _has_queue(player):
        source.reply(_err_text(str(tr('msg.queue_empty'))))
        return
    current = player_current_song.get(player)
    if current:
        server.execute(f'execute as {player} run function {_func_cmd(current, "pause")}')
        player_paused[player] = True
        songs = _load_songs()
        song = next((s for s in songs if s['link'] == current), None)
        song_name = song['name'] if song else current
        source.reply(_info_text(str(tr('msg.paused', song_name))))
    else:
        source.reply(_info_text(str(tr('msg.paused', '?'))))


def cmd_resume(source: CommandSource):
    player = source.player if source.is_player else None
    if not player:
        return
    server = source.get_server()
    if not _has_queue(player):
        source.reply(_err_text(str(tr('msg.queue_empty'))))
        return
    current = player_current_song.get(player)
    if current:
        server.execute(f'execute as {player} run function {_func_cmd(current, "play")}')
        player_paused[player] = False
        songs = _load_songs()
        song = next((s for s in songs if s['link'] == current), None)
        song_name = song['name'] if song else current
        source.reply(_info_text(str(tr('msg.resumed', song_name))))
    else:
        source.reply(_info_text(str(tr('msg.resumed', '?'))))


def cmd_now(source: CommandSource):
    player = source.player if source.is_player else None
    if not player:
        return
    mode = player_play_mode.get(player, 'sequential')
    current = player_current_song.get(player)
    if not current:
        source.reply(_err_text(str(tr('msg.no_current_song'))))
        source.reply(_info_text(str(tr('msg.current_mode', _tr_mode(mode)))))
        return
    songs = _load_songs()
    song = next((s for s in songs if s['link'] == current), None)
    if song:
        global_idx = next((i for i, s in enumerate(songs) if s['link'] == current), 0)
        source.reply(_song_text(global_idx + 1, song, highlight=True))
    else:
        source.reply(_info_text(str(tr('msg.now_playing', current, '', ''))))
    source.reply(_info_text(str(tr('msg.current_mode', _tr_mode(mode)))))
    # playback controls: ⏮  ⏸/▶  ⏭
    is_paused = player_paused.get(player, False)
    if is_paused:
        mid_btn = RText(' ▶ ', color=RColor.green).c(RAction.suggest_command, '!!mp resume').h(str(tr('label.resume')))
    else:
        mid_btn = RText(' ⏸ ', color=RColor.gold).c(RAction.suggest_command, '!!mp pause').h(str(tr('label.pause')))
    controls = RTextList(
        RText(' ⏮ ', color=RColor.gold).c(RAction.suggest_command, '!!mp prev').h(str(tr('label.prev'))),
        mid_btn,
        RText(' ⏭ ', color=RColor.gold).c(RAction.suggest_command, '!!mp next').h(str(tr('label.next'))),
    )
    source.reply(controls)


def cmd_mode(source: CommandSource, context=None):
    player = source.player if source.is_player else None
    if not player:
        return
    # no args: show current mode + clickable options
    if context is None or 'keyword' not in context:
        current_mode = player_play_mode.get(player, 'sequential')
        source.reply(_info_text(str(tr('msg.current_mode', _tr_mode(current_mode)))))
        btns = []
        for m in PLAY_MODES:
            color = RColor.aqua if m == current_mode else RColor.gray
            btn = RText(f'[{_tr_mode(m)}]', color=color)
            if m != current_mode:
                btn.c(RAction.suggest_command, f'!!mp mode {m}').h(_tr_mode(m))
            btns.append(btn)
            btns.append(RText(' '))
        source.reply(RTextList(*btns))
        return
    mode = context['keyword'].lower()
    if mode not in PLAY_MODES:
        source.reply(_err_text(str(tr('msg.invalid_mode'))))
        return
    player_play_mode[player] = mode
    source.reply(_info_text(str(tr('msg.mode_set', _tr_mode(mode)))))


def cmd_next(source: CommandSource):
    player = source.player if source.is_player else None
    if not player:
        return
    server = source.get_server()
    from midiplayer.midiplayer import _cancel_auto_next
    _cancel_auto_next(player)
    songs = _load_songs()
    queue = _load_queue(player)
    if not queue:
        source.reply(_err_text(str(tr('msg.queue_empty'))))
        return
    if len(queue) == 1:
        source.reply(_err_text(str(tr('msg.queue_one_song_no_next'))))
        return
    current = player_current_song.get(player)
    if current:
        server.execute(f'execute as {player} run function {_func_cmd(current, "stop")}')

    mode = player_play_mode.get(player, 'sequential')
    if mode == 'random':
        candidates = [q for q in queue if q != current]
        if not candidates:
            candidates = list(queue)
        link = random.choice(candidates)
    else:
        if current and current in queue:
            idx = (queue.index(current) + 1) % len(queue)
        else:
            idx = 0
        link = queue[idx]

    idx = queue.index(link) if link in queue else 0
    song = next((s for s in songs if s['link'] == link), None)
    if song:
        source.reply(_info_text(str(tr('msg.next_playing', song['name']))))
        _play_song_and_timer(server, player, song, songs)
        _show_now_playing(source, songs, queue, idx)
    else:
        player_current_song[player] = link
        server.execute(f'execute as {player} run function {_func_cmd(link, "play")}')


def cmd_prev(source: CommandSource):
    player = source.player if source.is_player else None
    if not player:
        return
    server = source.get_server()
    from midiplayer.midiplayer import _cancel_auto_next
    _cancel_auto_next(player)
    songs = _load_songs()
    queue = _load_queue(player)
    if not queue:
        source.reply(_err_text(str(tr('msg.queue_empty'))))
        return
    if len(queue) == 1:
        source.reply(_err_text(str(tr('msg.queue_one_song_no_prev'))))
        return
    current = player_current_song.get(player)
    if current:
        server.execute(f'execute as {player} run function {_func_cmd(current, "stop")}')

    mode = player_play_mode.get(player, 'sequential')
    if mode == 'random':
        candidates = [q for q in queue if q != current]
        if not candidates:
            candidates = list(queue)
        link = random.choice(candidates)
        idx = queue.index(link) if link in queue else 0
    else:
        if current and current in queue:
            idx = (queue.index(current) - 1) % len(queue)
        else:
            idx = 0
    link = queue[idx]
    song = next((s for s in songs if s['link'] == link), None)
    if song:
        source.reply(_info_text(str(tr('msg.prev_playing', song['name']))))
        _play_song_and_timer(server, player, song, songs)
        _show_now_playing(source, songs, queue, idx)
    else:
        player_current_song[player] = link
        server.execute(f'execute as {player} run function {_func_cmd(link, "play")}')


def cmd_shuffle(source: CommandSource):
    player = source.player if source.is_player else None
    if not player:
        return
    if not _has_queue(player):
        source.reply(_err_text(str(tr('msg.queue_empty'))))
        return
    queue = _load_queue(player)
    random.shuffle(queue)
    _save_queue(player, queue)
    source.reply(_info_text(str(tr('msg.queue_shuffled'))))


def cmd_add_to_queue(source: CommandSource, context):
    player = source.player if source.is_player else None
    if not player:
        return
    songs = _load_songs()
    raw = context['keyword']
    user_input = raw.replace('_', ' ')
    queue = _load_queue(player)

    # try multi-index
    if ',' in user_input or ('-' in user_input and not user_input.replace('-', '').replace(',', '').replace(' ', '').isalpha()):
        indexes = _parse_multi_index(user_input, len(songs))
        if not indexes:
            source.reply(_err_text(str(tr('msg.invalid_range'))))
        else:
            for i in indexes:
                song = songs[i]
                if song['link'] not in queue:
                    queue.append(song['link'])
                    source.reply(_info_text(str(tr('msg.added_to_queue', song['name']))))
                else:
                    source.reply(_err_text(str(tr('msg.already_in_queue'))))
            _save_queue(player, queue)
        return

    result = _find_song(songs, user_input, raw)
    if result is None:
        source.reply(_err_text(str(tr('msg.no_match'))))
        return
    if isinstance(result, list):
        _show_search_results(source, result)
        return

    song, _ = result
    if song['link'] not in queue:
        queue.append(song['link'])
        _save_queue(player, queue)
        source.reply(_info_text(str(tr('msg.added_to_queue', song['name']))))
    else:
        source.reply(_err_text(str(tr('msg.already_in_queue'))))


def cmd_queue(source: CommandSource, context=None):
    player = source.player if source.is_player else None
    if not player:
        return
    queue = _load_queue(player)
    if not queue:
        source.reply(_err_text(str(tr('msg.queue_empty'))))
        return
    songs = _load_songs()
    total_pages = max(1, (len(queue) + helpers.items_per_page - 1) // helpers.items_per_page)
    if context and 'page' in context:
        p = _validate_page(context['page'], total_pages)
        if p is None:
            source.reply(_err_text(str(tr('msg.invalid_page'))))
            return
        player_pages_queue[player] = p
    elif player not in player_pages_queue:
        player_pages_queue[player] = 1
    page, start, end, total_pages = _get_page(queue, player, player_pages_queue)
    current_link = player_current_song.get(player)
    _show_queue_page(source, queue, songs, page, start, end, total_pages, current_link)


def cmd_queue_search(source: CommandSource, context):
    player = source.player if source.is_player else None
    if not player:
        return
    raw = context['keyword']
    keyword = raw.replace('_', ' ')
    queue = _load_queue(player)
    songs = _load_songs()
    matches = []
    for _qi, link in enumerate(queue):
        song = next((s for s in songs if s['link'] == link), None)
        if song and (keyword.lower() in song['name'].lower() or raw.lower() in song['name'].lower() or raw.lower() in link.lower() or any(keyword.lower() in a.lower() for a in song['artist'])):
            # use global song index so !!mp play <idx> targets the correct song
            global_idx = next((i for i, s in enumerate(songs) if s['link'] == link), _qi)
            matches.append((global_idx, song))
    if matches:
        source.reply(_info_text(str(tr('msg.found_songs', len(matches)))))
        for idx, song in matches:
            source.reply(_song_text(idx + 1, song, show_duration=False, action='remove'))
    else:
        source.reply(_err_text(str(tr('msg.no_match'))))


def cmd_remove_from_queue(source: CommandSource, context):
    player = source.player if source.is_player else None
    if not player:
        return
    songs = _load_songs()
    raw = context['keyword']
    user_input = raw.replace('_', ' ')
    queue = _load_queue(player)
    if not queue:
        source.reply(_err_text(str(tr('msg.queue_empty'))))
        return

    # try multi-index
    if ',' in user_input or ('-' in user_input and not user_input.replace('-', '').replace(',', '').replace(' ', '').isalpha()):
        indexes = _parse_multi_index(user_input, len(songs))
        if not indexes:
            source.reply(_err_text(str(tr('msg.invalid_range'))))
        else:
            for i in indexes:
                link = songs[i]['link']
                if link in queue:
                    queue.remove(link)
                    source.reply(_info_text(str(tr('msg.removed_from_queue', songs[i]['name']))))
            _save_queue(player, queue)
        return

    result = _find_song(songs, user_input, raw)
    if result is None:
        source.reply(_err_text(str(tr('msg.no_match'))))
        return
    if isinstance(result, list):
        _show_search_results(source, result)
        return

    song, _ = result
    if song['link'] in queue:
        queue.remove(song['link'])
        _save_queue(player, queue)
        source.reply(_info_text(str(tr('msg.removed_from_queue', song['name']))))
    else:
        source.reply(_err_text(str(tr('msg.not_in_queue'))))


def cmd_clear(source: CommandSource):
    player = source.player if source.is_player else None
    if not player:
        return
    server = source.get_server()
    from midiplayer.midiplayer import _cancel_auto_next
    _cancel_auto_next(player)
    current = player_current_song.get(player)
    if current:
        server.execute(f'execute as {player} run function {_func_cmd(current, "stop")}')
    _save_queue(player, [])
    player_current_song.pop(player, None)
    source.reply(_info_text(str(tr('msg.queue_cleared'))))


# ── admin commands ──

def cmd_admin_add(source: CommandSource, context):
    name = context['song_name'].replace('_', ' ')
    artists_str = context['song_artists'].replace('_', ' ')
    link = context['song_link']
    artists = [a.strip() for a in artists_str.split(',')]
    songs = _load_songs()
    songs.append({'name': name, 'link': link, 'artist': artists})
    _save_songs(songs)
    source.reply(_info_text(str(tr('msg.song_added', name))))


def cmd_admin_del(source: CommandSource, context):
    idx = context['index'] - 1
    songs = _load_songs()
    if 0 <= idx < len(songs):
        songs.pop(idx)
        _save_songs(songs)
        source.reply(_info_text(str(tr('msg.song_deleted'))))
    else:
        source.reply(_err_text(str(tr('msg.invalid_index'))))


def cmd_admin_copy(source: CommandSource, context):
    idx = context['index'] - 1
    songs = _load_songs()
    if 0 <= idx < len(songs):
        songs.append(songs[idx].copy())
        _save_songs(songs)
        source.reply(_info_text(str(tr('msg.song_copied'))))
    else:
        source.reply(_err_text(str(tr('msg.invalid_index'))))


def cmd_admin_set_name(source: CommandSource, context):
    idx = context['index'] - 1
    songs = _load_songs()
    if 0 <= idx < len(songs):
        songs[idx]['name'] = context['song_name'].replace('_', ' ')
        _save_songs(songs)
        source.reply(_info_text(str(tr('msg.name_edited'))))
    else:
        source.reply(_err_text(str(tr('msg.invalid_index'))))


def cmd_admin_set_artist(source: CommandSource, context):
    idx = context['index'] - 1
    songs = _load_songs()
    if 0 <= idx < len(songs):
        songs[idx]['artist'] = [a.strip() for a in context['song_artists'].replace('_', ' ').split(',')]
        _save_songs(songs)
        source.reply(_info_text(str(tr('msg.artist_edited'))))
    else:
        source.reply(_err_text(str(tr('msg.invalid_index'))))


def cmd_admin_set_link(source: CommandSource, context):
    idx = context['index'] - 1
    songs = _load_songs()
    if 0 <= idx < len(songs):
        songs[idx]['link'] = context['song_link']
        _save_songs(songs)
        source.reply(_info_text(str(tr('msg.link_edited'))))
    else:
        source.reply(_err_text(str(tr('msg.invalid_index'))))


def cmd_admin_info(source: CommandSource, context=None):
    """!!mpa info [page] — show song details with editable fields."""
    songs = _load_songs()
    if not songs:
        source.reply(_err_text(str(tr('msg.no_songs'))))
        return
    page = context.get('page', 1) if context else 1
    per_page = getattr(helpers, 'items_per_page', 8)
    total_pages = max(1, (len(songs) + per_page - 1) // per_page)
    if page < 1 or page > total_pages:
        source.reply(_err_text(str(tr('msg.invalid_page'))))
        return
    start = (page - 1) * per_page
    end = min(start + per_page, len(songs))
    source.reply(_info_text(str(tr('msg.page_info', page, total_pages))))
    for i in range(start, end):
        s = songs[i]
        idx = i + 1
        name = s.get('name', '?')
        artist = ', '.join(s.get('artist', ['?']))
        link = s.get('link', '?')
        dur = s.get('duration')
        dur_str = _fmt_duration(dur) if dur else '?'
        line = RTextList(
            RText(f'{idx}. ', color=RColor.gold),
            RText(name, color=RColor.green)
                .c(RAction.suggest_command, f'!!mpa set {idx} name ')
                .h(str(tr('hover.edit_name'))),
            RText(f' - ', color=RColor.dark_gray),
            RText(artist, color=RColor.gray)
                .c(RAction.suggest_command, f'!!mpa set {idx} artist ')
                .h(str(tr('hover.edit_artist'))),
            RText(f' [', color=RColor.dark_gray),
            RText(dur_str, color=RColor.aqua)
                .c(RAction.suggest_command, f'!!mpa set {idx} duration ')
                .h(str(tr('hover.edit_duration'))),
            RText(f']', color=RColor.dark_gray),
            RText(f' ', color=RColor.dark_gray),
            RText(link, color=RColor.yellow)
                .c(RAction.suggest_command, f'!!mpa set {idx} link ')
                .h(str(tr('hover.edit_link'))),
            RText(' [©]', color=RColor.aqua)
                .c(RAction.suggest_command, f'!!mpa copy {idx}')
                .h(str(tr('hover.copy_song'))),
            RText(' [-]', color=RColor.red)
                .c(RAction.suggest_command, f'!!mpa del {idx}')
                .h(str(tr('hover.delete_song'))),
        )
        source.reply(line)
    if total_pages > 1:
        source.reply(_page_nav(page, total_pages, '!!mpa info'))


def cmd_admin_set_duration(source: CommandSource, context):
    idx = context['index'] - 1
    songs = _load_songs()
    if 0 <= idx < len(songs):
        try:
            val = int(context['duration_value'])
            songs[idx]['duration'] = val
            _save_songs(songs)
            source.reply(_info_text(str(tr('msg.duration_edited', _fmt_duration(val)))))
        except (ValueError, TypeError):
            source.reply(_err_text(str(tr('msg.duration_invalid'))))
    else:
        source.reply(_err_text(str(tr('msg.invalid_index'))))


def cmd_admin_debug(source: CommandSource, context=None):
    """!!mpa debug [player] — show player state for debugging."""
    target = context.get('target_player') if context else None
    if not target:
        if source.is_player:
            target = source.player
        else:
            source.reply(_err_text(str(tr('msg.debug_usage'))))
            return

    source.reply(_info_text(str(tr('msg.debug_header', target))))

    # current song
    current = player_current_song.get(target, None)
    none_text = str(tr('msg.debug_none'))
    source.reply(RText(str(tr('msg.debug_current_song', current or none_text)), color=RColor.white))

    # play mode
    mode = player_play_mode.get(target, 'sequential')
    source.reply(RText(str(tr('msg.debug_play_mode', _tr_mode(mode))), color=RColor.white))

    # auto-next timer
    timer = player_auto_next_timer.get(target, None)
    if timer:
        alive = timer.is_alive()
        source.reply(RText(str(tr('msg.debug_timer_active', alive, timer.interval)), color=RColor.white))
    else:
        source.reply(RText(str(tr('msg.debug_timer_none')), color=RColor.gray))

    # queue
    queue = _load_queue(target)
    source.reply(RText(str(tr('msg.debug_queue', len(queue))), color=RColor.white))
    songs = _load_songs()
    for i, link in enumerate(queue):
        song = next((s for s in songs if s['link'] == link), None)
        name = song['name'] if song else '?'
        marker = ' §e◄' if link == current else ''
        source.reply(RText(f'  {i+1}. {name} ({link}){marker}', color=RColor.gray))


def _get_timer(source, target):
    timer = player_auto_next_timer.get(target, None)
    if not timer:
        source.reply(_err_text(str(tr('msg.timer_not_found', target))))
    return timer


def cmd_admin_timer_reset(source: CommandSource, context):
    target = context['target_player']
    timer = _get_timer(source, target)
    if timer:
        timer.cancel()
        player_auto_next_timer.pop(target, None)
        source.reply(_info_text(str(tr('msg.timer_reset', target))))


def cmd_admin_timer_interval(source: CommandSource, context):
    target = context['target_player']
    timer = _get_timer(source, target)
    if not timer:
        return
    try:
        val = float(context['timer_value'])
    except (ValueError, TypeError):
        source.reply(_err_text(str(tr('msg.timer_interval_invalid'))))
        return
    timer.cancel()
    t = threading.Timer(val, timer.function, args=timer.args or (), kwargs=timer.kwargs or {})
    t.daemon = True
    t.start()
    player_auto_next_timer[target] = t
    source.reply(_info_text(str(tr('msg.timer_interval_set', target, val))))


def cmd_admin_timer_active(source: CommandSource, context):
    target = context['target_player']
    timer = _get_timer(source, target)
    if not timer:
        return
    flag = context['timer_value'].lower()
    if flag in ('true', '1', 'on'):
        if timer.is_alive():
            source.reply(_info_text(str(tr('msg.timer_already_active', target))))
            return
        t = threading.Timer(timer.interval, timer.function, args=timer.args or (), kwargs=timer.kwargs or {})
        t.daemon = True
        t.start()
        player_auto_next_timer[target] = t
        source.reply(_info_text(str(tr('msg.timer_reactivated', target, timer.interval))))
    elif flag in ('false', '0', 'off'):
        if not timer.is_alive():
            source.reply(_info_text(str(tr('msg.timer_already_inactive', target))))
            return
        timer.cancel()
        source.reply(_info_text(str(tr('msg.timer_deactivated', target, timer.interval))))
    else:
        source.reply(_err_text(str(tr('msg.timer_value_invalid'))))
