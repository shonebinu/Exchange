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
    input_buffer: GtkSource.Buffer = Gtk.Template.Child()
    output_buffer: GtkSource.Buffer = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        manager = GtkSource.StyleSchemeManager.get_default()
        lang_manager = GtkSource.LanguageManager.get_default()
        scheme = manager.get_scheme("Adwaita-dark")

        self.input_buffer.set_style_scheme(scheme)
        self.input_buffer.set_language(lang_manager.get_language("xml"))
        self.output_buffer.set_style_scheme(scheme)
        self.output_buffer.set_language(lang_manager.get_language("blueprint"))

        self.convert_button.connect("clicked", self.on_convert_clicked)

    def on_convert_clicked(self, _):
        start, end = self.input_buffer.get_bounds()
        buffer_content = self.input_buffer.get_text(start, end, True)

        if not buffer_content.strip():
            print("Empty input.")
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input"
            output_file = Path(tmpdir) / "output"

            input_file.write_text(buffer_content)

            subprocess.run(
                [
                    "blueprint-compiler",
                    "decompile",
                    str(input_file),
                    "--output",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            ouput_text = output_file.read_text()

        self.output_buffer.set_text(ouput_text)
