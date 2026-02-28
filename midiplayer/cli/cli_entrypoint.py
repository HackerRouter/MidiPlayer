import argparse
import json
import os
import sys

from midiplayer.song_parser import tr, parse_songs # type: ignore
from midiplayer.duration import extract_duration_from_zip # type: ignore


__all__ = ['cli_entry']


class CliEntrypoint:
    def cli_import_song_file(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    def cli_import_datapack_id_file(self, file_path):
        """Returns (id_text, durations_dict) where durations_dict maps id -> duration."""
        durations = {}
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read(), durations
        elif os.path.isdir(file_path):
            datapack_ids = []
            for filename in os.listdir(file_path):
                full_path = os.path.join(file_path, filename)
                if os.path.isfile(full_path):
                    name_no_ext = os.path.splitext(filename)[0]
                    formatted = name_no_ext.replace(" ", "_").lower()
                    datapack_ids.append(formatted)
                    if filename.endswith('.zip'):
                        dur = extract_duration_from_zip(full_path)
                        if dur is not None:
                            durations[formatted] = dur
            return "\n".join(datapack_ids), durations
        else:
            print(tr("file_not_exist"))
            return "", {}

    def export_songs_json(self, song_artist_file, datapack_id_file, output_path):
        song_lines = self.cli_import_song_file(song_artist_file).strip().split("\n")
        id_text, durations = self.cli_import_datapack_id_file(datapack_id_file)
        datapack_lines = id_text.strip().split("\n")

        parsed, _ = parse_songs(song_lines, datapack_lines, durations)

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        file_path = os.path.join(output_path, "songs.json")
        with open(file_path, 'w', encoding="utf-8") as json_file:
            json.dump(parsed, json_file, ensure_ascii=False, indent=4)

    def main(self):
        parser = argparse.ArgumentParser(description=tr("parser.description"),
        epilog=tr("parser.epilog"))

        parser.add_argument('song_artist_file_path', type=str, nargs='?',
            help=tr("song_artist_file_path_help"))
        parser.add_argument('datapack_id_file_path', type=str, nargs='?',
            help=tr("datapack_id_file_path_help"))
        parser.add_argument('output_path', type=str, nargs='?',
            default=os.getcwd(), help=tr("output_path_help"))
        parser.add_argument('--gui', action='store_true', help=tr("--gui_help"))

        args_parsed_successfully = False
        try:
            args = parser.parse_args()
            args_parsed_successfully = True
        except SystemExit as e:
            print(tr("correct_format_example"))
            if e.code != 0:
                args = None
            else:
                quit()

        if args_parsed_successfully and args.gui:
            print(tr("launch_gui"))
            self._launch_gui()

        elif args_parsed_successfully and args.song_artist_file_path is None and args.datapack_id_file_path is None and not args.gui:
            parser.print_help()
            print(tr("correct_format_example"))
            response = input(tr("ask_gui_launch")).strip().lower()
            if response == 'y':
                self._launch_gui()
            else:
                print(tr("quit"))
        elif args_parsed_successfully and (args.song_artist_file_path is None or args.datapack_id_file_path is None):
            parser.print_help()
            print(tr("correct_format_example"))

        elif args_parsed_successfully:
            print(tr("lauch_cli"))
            print(tr("song_artist_file_path") + args.song_artist_file_path)
            print(tr("datapack_id_file_path") + args.datapack_id_file_path)
            print(tr("output_path") + args.output_path)
            self.export_songs_json(args.song_artist_file_path, args.datapack_id_file_path, args.output_path)
        else:
            print(tr("correct_format_example"))
            response = input(tr("ask_gui_launch")).strip().lower()
            if response == 'y':
                self._launch_gui()
            else:
                print(tr("quit"))

    def _launch_gui(self):
        from midiplayer.gui.gui_entrypoint import gui_entry # type: ignore
        GUI = gui_entry(is_gui_mode=True)
        GUI.run_gui()

def cli_entry():
	CliEntrypoint().main()

if __name__ == "__main__":
    CliEntrypoint().main()
