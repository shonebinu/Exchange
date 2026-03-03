import asyncio
import re
import subprocess
import tempfile
from pathlib import Path

import gi

gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gdk, Gio, Gtk, GtkSource

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

        self.clipboard = (
            display.get_clipboard() if (display := Gdk.Display.get_default()) else None
        )

        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self.update_style_scheme)

        self.update_style_scheme()
        self.update_languages()

        self.direction_toggle_group.connect(
            "notify::active-name",
            self.on_direction_changed,
        )

    def update_style_scheme(self, *_):
        scheme_name = "Adwaita-dark" if self.style_manager.get_dark() else "Adwaita"

        scheme = GtkSource.StyleSchemeManager.get_default().get_scheme(scheme_name)

        if scheme:
            self.input_buffer.set_style_scheme(scheme)
            self.output_buffer.set_style_scheme(scheme)

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

    async def convert_input_to_output(self):
        start, end = self.input_buffer.get_bounds()
        buffer_content = self.input_buffer.get_text(start, end, True)

        if not buffer_content.strip():
            print("Empty input.")
            return

        self.convert_button.set_sensitive(False)

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

            output_text = await asyncio.to_thread(output_file.read_text)

        self.output_buffer.set_text(
            self.remove_xml_header(output_text)
            if direction == "compile"
            else output_text
        )

        self.convert_button.set_sensitive(True)

    def remove_xml_header(self, xml_text: str) -> str:
        pattern = r"<!--\s*DO NOT EDIT!.*?-->\n?"
        cleaned_xml = re.sub(pattern, "", xml_text, flags=re.DOTALL)
        return cleaned_xml

    @Gtk.Template.Callback()
    def on_convert_clicked(self, _):
        asyncio.create_task(self.convert_input_to_output())

    @Gtk.Template.Callback()
    def on_paste_clicked(self, _):
        if not self.clipboard:
            return

        self.clipboard.read_text_async(callback=self.on_clipboard_read_finished)

    def on_clipboard_read_finished(
        self, clipboard: Gdk.Clipboard, result: Gio.AsyncResult
    ):
        if not (text := clipboard.read_text_finish(result)):
            return

        self.input_buffer.set_text(text)

    @Gtk.Template.Callback()
    def on_copy_clicked(self, _):
        if not self.clipboard:
            return

        start, end = self.output_buffer.get_bounds()
        buffer_content = self.output_buffer.get_text(start, end, True)

        self.clipboard.set(buffer_content)
