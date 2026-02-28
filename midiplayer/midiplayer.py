import os
import random
import threading

from mcdreforged.api.all import *
from mcdreforged.api.command import SimpleCommandBuilder, Integer, Text

from midiplayer import helpers
from midiplayer.helpers import (
    Config, tr, _ensure_songs_file, _load_songs, _load_queue,
    _send_help, _info_text,
    player_current_song, player_play_mode, player_auto_next_timer,
    player_pages, player_pages_queue, PLAY_MODES,
)
from midiplayer.commands import (
    cmd_help, cmd_list, cmd_links, cmd_search, cmd_play,
    cmd_stop, cmd_resume, cmd_now, cmd_mode, cmd_next, cmd_prev,
    cmd_shuffle, cmd_add_to_queue, cmd_remove_from_queue,
    cmd_queue, cmd_queue_search, cmd_clear,
    cmd_admin_add, cmd_admin_del, cmd_admin_copy,
    cmd_admin_set_name, cmd_admin_set_artist, cmd_admin_set_link,
    cmd_admin_set_duration, cmd_admin_info, cmd_admin_debug,
    cmd_admin_timer_reset, cmd_admin_timer_interval, cmd_admin_timer_active,
    _play_song_and_timer,
)


# ── auto-advance timer ──

def _cancel_auto_next(player):
    t = player_auto_next_timer.pop(player, None)
    if t:
        t.cancel()


def _start_auto_next(server, player, duration, songs, _msgs=None):
    _cancel_auto_next(player)

    # pre-fetch translation templates on plugin thread; Timer thread can't call tr()
    # msg.auto_next contains {0} placeholder — pass a unique marker so MCDR's
    # .format() succeeds, then replace the marker back to {0} for later use.
    if _msgs is None:
        _MARKER = '\x00SONG\x00'
        tpl = str(tr('msg.auto_next', _MARKER)).replace(_MARKER, '{0}')
        _msgs = (tpl, str(tr('msg.sequential_end')))
    tpl_auto_next, msg_seq_end = _msgs

    def _next_song(song, current):
        if current:
            server.execute(f'execute as {player} run function {current}:stop')
        try:
            msg = tpl_auto_next.format(song['name'])
        except (IndexError, KeyError):
            msg = tpl_auto_next
        server.tell(player, _info_text(msg))
        _play_song_and_timer(server, player, song, songs, _msgs=_msgs)

    def callback():
        player_auto_next_timer.pop(player, None)
        queue = _load_queue(player)
        if not queue:
            return
        mode = player_play_mode.get(player, 'sequential')
        current = player_current_song.get(player)

        if mode == 'single':
            if current:
                song = next((s for s in songs if s['link'] == current), None)
                if song:
                    _next_song(song, None)
        elif mode == 'random':
            candidates = [q for q in queue if q != current]
            if not candidates:
                candidates = list(queue)
            random.shuffle(candidates)
            song = None
            for link in candidates:
                song = next((s for s in songs if s['link'] == link), None)
                if song:
                    break
            if song:
                _next_song(song, current)
        elif mode == 'loop':
            idx = (queue.index(current) + 1) % len(queue) if current and current in queue else 0
            song = next((s for s in songs if s['link'] == queue[idx]), None)
            if song:
                _next_song(song, current)
        else:  # sequential
            if current and current in queue:
                idx = queue.index(current) + 1
                if idx >= len(queue):
                    server.tell(player, _info_text(msg_seq_end))
                    return
            else:
                idx = 0
            song = next((s for s in songs if s['link'] == queue[idx]), None)
            if song:
                _next_song(song, current)

    t = threading.Timer(duration + 1, callback)
    t.daemon = True
    t.start()
    player_auto_next_timer[player] = t


# ── lifecycle ──

def on_load(server: PluginServerInterface, prev_module):
    # data paths
    helpers.data_folder = server.get_data_folder()
    helpers.songs_json_file = os.path.join(helpers.data_folder, 'songs.json')
    helpers.queues_dir = os.path.join(helpers.data_folder, 'queues')
    os.makedirs(helpers.queues_dir, exist_ok=True)
    _ensure_songs_file()

    # config
    config = server.load_config_simple(target_class=Config)
    helpers.items_per_page = config.items_per_page

    # preserve state across reloads
    if prev_module is not None:
        helpers.player_pages.update(getattr(prev_module, 'player_pages', getattr(getattr(prev_module, 'helpers', None), 'player_pages', {})))
        helpers.player_current_song.update(getattr(prev_module, 'player_current_song', getattr(getattr(prev_module, 'helpers', None), 'player_current_song', {})))
        helpers.player_pages_queue.update(getattr(prev_module, 'player_pages_queue', getattr(getattr(prev_module, 'helpers', None), 'player_pages_queue', {})))
        helpers.player_play_mode.update(getattr(prev_module, 'player_play_mode', getattr(getattr(prev_module, 'helpers', None), 'player_play_mode', {})))
        # cancel old timers
        old_timers = getattr(prev_module, 'player_auto_next_timer', getattr(getattr(prev_module, 'helpers', None), 'player_auto_next_timer', {}))
        for t in old_timers.values():
            t.cancel()

    # ── user commands !!mp ──
    b = SimpleCommandBuilder()
    b.command('!!mp', cmd_help)
    b.command('!!mp list', cmd_list)
    b.command('!!mp list <page>', cmd_list)
    b.command('!!mp links', cmd_links)
    b.command('!!mp links <page>', cmd_links)
    b.command('!!mp search <keyword>', cmd_search)
    b.command('!!mp play', cmd_play)
    b.command('!!mp play <keyword>', cmd_play)
    b.command('!!mp pause', cmd_stop)
    b.command('!!mp resume', cmd_resume)
    b.command('!!mp now', cmd_now)
    b.command('!!mp mode', cmd_mode)
    b.command('!!mp mode <keyword>', cmd_mode)
    b.command('!!mp next', cmd_next)
    b.command('!!mp prev', cmd_prev)
    b.command('!!mp shuffle', cmd_shuffle)
    b.command('!!mp add <keyword>', cmd_add_to_queue)
    b.command('!!mp remove <keyword>', cmd_remove_from_queue)
    b.command('!!mp queue', cmd_queue)
    b.command('!!mp queue <page>', cmd_queue)
    b.command('!!mp queue search <keyword>', cmd_queue_search)
    b.command('!!mp clear', cmd_clear)

    b.arg('keyword', Text)
    b.arg('page', Integer)
    b.register(server)

    # ── admin commands !!mpa ──
    a = SimpleCommandBuilder()
    a.command('!!mpa', lambda src: _send_help(src, key='help_admin'))
    a.command('!!mpa add <song_name> <song_artists> <song_link>', cmd_admin_add)
    a.command('!!mpa del <index>', cmd_admin_del)
    a.command('!!mpa copy <index>', cmd_admin_copy)
    a.command('!!mpa set <index> name <song_name>', cmd_admin_set_name)
    a.command('!!mpa set <index> artist <song_artists>', cmd_admin_set_artist)
    a.command('!!mpa set <index> link <song_link>', cmd_admin_set_link)
    a.command('!!mpa set <index> duration <duration_value>', cmd_admin_set_duration)
    a.command('!!mpa info', cmd_admin_info)
    a.command('!!mpa info <page>', cmd_admin_info)
    a.command('!!mpa debug', cmd_admin_debug)
    a.command('!!mpa debug <target_player>', cmd_admin_debug)
    a.command('!!mpa timer <target_player> reset', cmd_admin_timer_reset)
    a.command('!!mpa timer <target_player> interval <timer_value>', cmd_admin_timer_interval)
    a.command('!!mpa timer <target_player> active <timer_value>', cmd_admin_timer_active)

    a.arg('song_name', Text)
    a.arg('song_artists', Text)
    a.arg('song_link', Text)
    a.arg('index', Integer)
    a.arg('duration_value', Integer)
    a.arg('page', Integer)
    a.arg('target_player', Text)
    a.arg('timer_value', Text)
    a.register(server)

    server.register_help_message('!!mp', tr('help_short'))
