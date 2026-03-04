import asyncio
import re
import subprocess
import tempfile
from pathlib import Path

import gi

gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, GtkSource

GtkSource.init()


@Gtk.Template(resource_path="/io/github/shonebinu/Exchange/window.ui")
class ExchangeWindow(Adw.ApplicationWindow):
    __gtype_name__ = "ExchangeWindow"

    convert_button: Gtk.Button = Gtk.Template.Child()
    direction_toggle_group: Adw.ToggleGroup = Gtk.Template.Child()
    input_source_view: GtkSource.View = Gtk.Template.Child()
    input_buffer: GtkSource.Buffer = Gtk.Template.Child()
    output_buffer: GtkSource.Buffer = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.input_source_view.grab_focus()

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

        try:
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

        except subprocess.CalledProcessError:
            # TODO: Make a toast
            print("Failed to")
        finally:
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

        # TODO: make toast

        start, end = self.output_buffer.get_bounds()
        buffer_content = self.output_buffer.get_text(start, end, True)

        self.clipboard.set(buffer_content)

    @Gtk.Template.Callback()
    def on_file_open_clicked(self, _):
        native = Gtk.FileDialog()
        native.open(self, None, self.on_open_response)

    def on_open_response(self, dialog, result):
        file = dialog.open_finish(result)
        # If the user selected a file
        if file is not None:
            self.open_file(file)

    def open_file(self, file):
        file.load_contents_async(None, self.open_file_complete)

    def open_file_complete(self, file, result):
        contents = file.load_contents_finish(result)

        # TODO: change to async and make toast
        if not contents[0]:
            path = file.peek_path()
            print(f"Unable to open {path}: {contents[1]}")
            return

        try:
            text = contents[1].decode("utf-8")
            self.input_buffer.set_text(text)
        except UnicodeError:
            path = file.peek_path()
            print(
                f"Unable to load the contents of {path}: the file is not encoded with UTF-8"
            )
            return

    @Gtk.Template.Callback()
    def on_file_save_clicked(self, _):
        # todo: if buffer empty avoid.
        native = Gtk.FileDialog()
        native.save(self, None, self.on_save_response)

    def on_save_response(self, dialog, result):
        file = dialog.save_finish(result)
        if file is not None:
            self.save_file(file)

    def save_file(self, file):

        # Retrieve the iterator at the start of the buffer
        start = self.output_buffer.get_start_iter()
        # Retrieve the iterator at the end of the buffer
        end = self.output_buffer.get_end_iter()
        # Retrieve all the visible text between the two bounds
        text = self.output_buffer.get_text(start, end, False)

        # If there is nothing to save, return early
        if not text:
            return

        bytes = GLib.Bytes.new(text.encode("utf-8"))

        # Start the asynchronous operation to save the data into the file
        file.replace_contents_bytes_async(
            bytes, None, False, Gio.FileCreateFlags.NONE, None, self.save_file_complete
        )

    def save_file_complete(self, file, result):
        res = file.replace_contents_finish(result)
        info = file.query_info("standard::display-name", Gio.FileQueryInfoFlags.NONE)
        if info:
            display_name = info.get_attribute_string("standard::display-name")
        else:
            display_name = file.get_basename()
        if not res:
            print(f"Unable to save {display_name}")

        # Todo: make toast


# todo: change to async pattern
# todo: open filetype annd save filetype
# todo: detect lang when pasting and opening file (xml, ui, blp)
# todo: set text shouldn't clear the save stack
