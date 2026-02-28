from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog
from tkinter import messagebox
import json
import os
import sys

from midiplayer.duration import extract_duration_from_zip # type: ignore
from midiplayer.song_parser import tr, parse_songs # type: ignore


__all__ = ['gui_entry']


class WinGUI(Tk):
    def __init__(self, is_gui_mode=False):
        self.is_gui_mode = is_gui_mode
        self.durations = {}
        if self.is_gui_mode:
            super().__init__()
            self.__win()

            self.label_song_name = self.__tk_label_song_name(self)
            self.output_json = self.__tk_output_json(self)
            self.input_datapack_id = self.__tk_input_datapack_id(self)
            self.input_song = self.__tk_input_song(self)
            self.label_preview_datapack_id = self.__tk_label_preview_datapack_id(self)
            self.label_preview_json = self.__tk_label_preview_json(self)
            self.button_import_song = self.__tk_button_import_song(self)
            self.button_import_datapack = self.__tk_button_import_datapack(self)
            self.button_export_json = self.__tk_button_export_json(self)
            self.button_import_json = self.__tk_button_import_json(self)

            self.input_song.bind("<Return>", self.refresh_json_preview)
            self.input_datapack_id.bind("<Return>", self.refresh_json_preview)

            self.after(100, self._show_notice)

    def _show_notice(self):
        messagebox.showinfo(title=tr("gui.notice_title"), message=tr("gui.notice_msg"))
        self.lift()
        self.focus_force()

    def __win(self):
        self.title(tr("gui.title"))
        width = 788
        height = 458
        screenwidth = self.winfo_screenwidth()
        screenheight = self.winfo_screenheight()
        geometry = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        self.geometry(geometry)
        self.minsize(width=width, height=height)

    def run_gui(self):
        if self.is_gui_mode:
            self.mainloop()
        else:
            print(tr("gui.error_no_gui"))

    def __tk_label_song_name(self, parent):
        label = Label(parent, text=tr("gui.label_song"), anchor="w")
        label.place(relx=0.0266, rely=0.0218, relwidth=2, relheight=0.0655)
        return label

    def __tk_output_json(self, parent):
        ipt = Text(parent, wrap="word", height=5, width=20)
        ipt.place(relx=0.6789, rely=0.0983, relwidth=0.2970, relheight=0.7358)
        ipt.config(padx=5, pady=5, state="disabled")
        return ipt

    def __tk_input_datapack_id(self, parent):
        ipt = Text(parent, wrap="word", height=5, width=20)
        ipt.place(relx=0.3528, rely=0.0983, relwidth=0.2970, relheight=0.7358)
        ipt.config(padx=5, pady=5)
        return ipt

    def __tk_input_song(self, parent):
        ipt = Text(parent, wrap="word", height=5, width=20)
        ipt.place(relx=0.0266, rely=0.0983, relwidth=0.2970, relheight=0.7358)
        ipt.config(padx=5, pady=5)
        return ipt

    def __tk_label_preview_datapack_id(self, parent):
        label = Label(parent, text=tr("gui.label_datapack"), anchor="w")
        label.place(relx=0.3528, rely=0.0218, relwidth=2, relheight=0.0655)
        return label

    def __tk_label_preview_json(self, parent):
        label = Label(parent, text=tr("gui.label_json"), anchor="w")
        label.place(relx=0.6789, rely=0.0218, relwidth=2, relheight=0.0655)
        return label

    def __tk_button_import_song(self, parent):
        btn = Button(parent, text=tr("gui.btn_import_song"), takefocus=False, command=self.import_song_file)
        btn.place(relx=0.0266, rely=0.8755, relwidth=0.2970, relheight=0.0721)
        return btn

    def __tk_button_import_datapack(self, parent):
        btn = Button(parent, text=tr("gui.btn_import_datapack"), takefocus=False, command=self.import_datapack_file)
        btn.place(relx=0.3528, rely=0.8755, relwidth=0.2970, relheight=0.0721)
        return btn

    def __tk_button_export_json(self, parent):
        btn = Button(parent, text=tr("gui.btn_export_json"), takefocus=False, command=self.export_json_file)
        btn.place(relx=0.8452, rely=0.0172, relwidth=0.1294, relheight=0.0711)
        return btn

    def __tk_button_import_json(self, parent):
        btn = Button(parent, text=tr("gui.btn_import_json"), takefocus=False, command=self.import_json_file)
        btn.place(relx=0.6789, rely=0.8755, relwidth=0.2970, relheight=0.0721)
        return btn

    def import_song_file(self):
        file_path = filedialog.askopenfilename(title=tr("gui.select_song_file"), filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as file:
                self.input_song.insert(END, file.read())
                self.refresh_json_preview()

    def import_datapack_file(self):
        file_paths = filedialog.askopenfilenames(title=tr("gui.select_datapack_file"), filetypes=[("Zip Files", "*.zip"), ("Text Files", "*.txt")])
        if file_paths:
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                name_no_ext = os.path.splitext(file_name)[0]
                formatted = name_no_ext.replace(" ", "_")
                self.input_datapack_id.insert(END, formatted + "\n")
                if file_name.endswith('.zip'):
                    dur = extract_duration_from_zip(file_path)
                    if dur is not None:
                        self.durations[formatted.lower()] = dur
            self.refresh_json_preview()

    def parse_text(self, event=None):
        song_lines = self.input_song.get(1.0, END).strip().split("\n")
        datapack_lines = self.input_datapack_id.get(1.0, END).strip().split("\n")
        parsed, filled = parse_songs(song_lines, datapack_lines, self.durations)
        # auto-fill song input box
        current = self.input_song.get(1.0, END).strip().split("\n")
        if current == ['']:
            current = []
        if filled != current:
            self.input_song.delete(1.0, END)
            self.input_song.insert(END, "\n".join(filled) + ("\n" if filled else ""))
        return parsed

    def export_json_file(self):
        parsed_data = self.parse_text()
        if parsed_data:
            file_path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="songs.json", filetypes=[("JSON Files", "*.json")])
            if file_path:
                with open(file_path, 'w', encoding="utf-8") as json_file:
                    json.dump(parsed_data, json_file, ensure_ascii=False, indent=4)

    def export_json(self, parsed_data):
        if parsed_data:
            self.output_json.config(state="normal")
            self.output_json.delete(1.0, END)
            self.output_json.insert(END, json.dumps(parsed_data, ensure_ascii=False, indent=4))
            self.output_json.config(state="disabled")

    def process_datapack_ids(self):
        raw_text = self.input_datapack_id.get(1.0, END)
        lines = raw_text.strip().split("\n")
        processed_lines = []
        for line in lines:
            processed_line = line.strip().replace(" ", "_").lower()
            if processed_line:
                processed_lines.append(processed_line)
        final_processed_text = "\n".join(processed_lines) + "\n" if processed_lines else ""
        self.input_datapack_id.delete(1.0, END)
        self.input_datapack_id.insert(END, final_processed_text)

    def refresh_json_preview(self, event=None):
        self.process_datapack_ids()
        parsed_data = self.parse_text()
        self.export_json(parsed_data)

    def import_json_file(self):
        file_path = filedialog.askopenfilename(title=tr("gui.select_json_file"), filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as json_file:
                parsed_data = json.load(json_file)

                self.input_song.delete(1.0, END)
                self.input_datapack_id.delete(1.0, END)
                self.output_json.delete(1.0, END)
                self.durations.clear()

                for entry in parsed_data:
                    song_name = entry["name"]
                    artist = ", ".join(entry["artist"])
                    self.input_song.insert(END, f"{song_name} - {artist}\n")

                    datapack_name = entry["link"]
                    self.input_datapack_id.insert(END, f"{datapack_name}\n")

                    if entry.get("duration", 0) > 0:
                        self.durations[datapack_name] = entry["duration"]

                self.export_json(parsed_data)


def gui_entry(is_gui_mode):
    gui_instance = WinGUI(is_gui_mode=is_gui_mode)
    return gui_instance

if __name__ == "__main__":
    WinGUI()
