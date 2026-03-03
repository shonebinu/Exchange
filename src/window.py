import asyncio
import subprocess
import tempfile
from pathlib import Path

import gi

gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gtk, GtkSource

GtkSource.init()


@Gtk.Template(resource_path="/io/github/shonebinu/Exchange/window.ui")
class ExchangeWindow(Adw.ApplicationWindow):
    __gtype_name__ = "ExchangeWindow"

    convert_button: Gtk.Button = Gtk.Template.Child()
    direction_toggle_group: Adw.ToggleGroup = Gtk.Template.Child()
    input_buffer: GtkSource.Buffer = Gtk.Template.Child()
    output_buffer: GtkSource.Buffer = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        style_scheme = GtkSource.StyleSchemeManager.get_default().get_scheme(
            "Adwaita-dark"
        )
        self.input_buffer.set_style_scheme(style_scheme)
        self.output_buffer.set_style_scheme(style_scheme)

        self.update_languages()

        self.convert_button.connect("clicked", self.on_convert_clicked)
        self.direction_toggle_group.connect(
            "notify::active-name",
            self.on_direction_changed,
        )

    def update_languages(self):
        lang_manager = GtkSource.LanguageManager.get_default()
        active_toggle = self.direction_toggle_group.get_active_name()

        if active_toggle == "xml_to_blp":
            self.input_buffer.set_language(lang_manager.get_language("xml"))
            self.output_buffer.set_language(lang_manager.get_language("blueprint"))
        else:
            self.input_buffer.set_language(lang_manager.get_language("blueprint"))
            self.output_buffer.set_language(lang_manager.get_language("xml"))

    def on_direction_changed(self, *_):
        self.update_languages()

    def on_convert_clicked(self, _):
        asyncio.create_task(self.convert_input_to_output())

    async def convert_input_to_output(self):
        start, end = self.input_buffer.get_bounds()
        buffer_content = self.input_buffer.get_text(start, end, True)

        if not buffer_content.strip():
            print("Empty input.")
            return

        active_toggle = self.direction_toggle_group.get_active_name()
        direction = "decompile" if active_toggle == "xml_to_blp" else "compile"

        with await asyncio.to_thread(tempfile.TemporaryDirectory) as tmpdir:
            input_file = Path(tmpdir) / "input"
            output_file = Path(tmpdir) / "output"

            await asyncio.to_thread(input_file.write_text, buffer_content)

            await asyncio.to_thread(
                subprocess.run,
                [
                    "blueprint-compiler",
                    direction,
                    str(input_file),
                    "--output",
                    str(output_file),
                ],
                check=True,
            )

            ouput_text = await asyncio.to_thread(output_file.read_text)

        self.output_buffer.set_text(ouput_text)
