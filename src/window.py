import asyncio
import subprocess

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, GtkSource

from .compiler import BlueprintCompiler


@Gtk.Template(resource_path="/io/github/shonebinu/Exchange/window.ui")
class ExchangeWindow(Adw.ApplicationWindow):
    __gtype_name__ = "ExchangeWindow"

    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
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

    def read_buffer(self, buffer: GtkSource.Buffer) -> str:
        start, end = buffer.get_bounds()
        return buffer.get_text(start, end, True)

    def write_buffer(self, buffer: GtkSource.Buffer, text: str):
        buffer.begin_user_action()

        start_iter, end_iter = buffer.get_bounds()
        buffer.delete(start_iter, end_iter)
        buffer.insert(buffer.get_start_iter(), text)

        buffer.end_user_action()

    async def convert_input_to_output(self):
        input_text = self.read_buffer(self.input_buffer)

        if not input_text.strip():
            self.toast_overlay.add_toast(Adw.Toast(title="Empty input buffer"))
            return

        self.convert_button.set_sensitive(False)

        active_toggle = self.direction_toggle_group.get_active_name()
        direction = "decompile" if active_toggle == "xml_to_blp" else "compile"

        try:
            output_text = await asyncio.to_thread(
                BlueprintCompiler.process, input_text, direction
            )
            self.write_buffer(self.output_buffer, output_text)

        except Exception as err:
            error_msg = "Conversion failed"
            if not isinstance(err, subprocess.SubprocessError):
                error_msg += f" : {err}"

            self.toast_overlay.add_toast(Adw.Toast(title=error_msg))
        finally:
            self.convert_button.set_sensitive(True)

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

        self.write_buffer(self.input_buffer, text)

    @Gtk.Template.Callback()
    def on_copy_clicked(self, _):
        if not self.clipboard:
            return

        if not (buffer_content := self.read_buffer(self.output_buffer)):
            return

        self.clipboard.set(buffer_content)
        self.toast_overlay.add_toast(Adw.Toast(title="Copied to clipboard"))

    @Gtk.Template.Callback()
    def on_file_open_clicked(self, _):

        files_filter = Gtk.FileFilter(
            name="UI Definition Files (.ui, .blp, .xml)",
            suffixes=["ui", "blp", "xml"],
            mime_types=[
                "application/x-gtk-builder",
                "text/x-blueprint",
                "application/xml",
                "text/xml",
            ],
        )
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(files_filter)

        file_dialog = Gtk.FileDialog(filters=filters)

        file_dialog.open(self, None, self.on_open_response)

    def on_open_response(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult):
        # If user selected a file
        if file := dialog.open_finish(result):
            file.load_contents_async(None, self.open_file_complete)

    def open_file_complete(self, file: Gio.File, result: Gio.AsyncResult):
        try:
            success, data, _ = file.load_contents_finish(result)

            if not success:
                raise Exception("File could not be read.")

            path = file.get_path()
            path_lower = path.lower() if path else ""
            info = file.query_info(
                "standard::content-type", Gio.FileQueryInfoFlags.NONE
            )
            mime = info.get_content_type() or ""

            is_xml = path_lower.endswith((".ui", ".xml")) or mime in (
                "application/x-gtk-builder",
                "text/xml",
                "application/xml",
            )
            is_blp = path_lower.endswith(".blp") or mime == "text/x-blueprint"

            if is_xml:
                self.direction_toggle_group.set_active_name("xml_to_blp")
            elif is_blp:
                self.direction_toggle_group.set_active_name("blp_to_xml")

            self.write_buffer(self.input_buffer, data.decode("utf-8"))
        except Exception as err:
            self.toast_overlay.add_toast(Adw.Toast(title=f"Failed to load file: {err}"))

    @Gtk.Template.Callback()
    def on_file_save_clicked(self, _):
        if not self.read_buffer(self.output_buffer).strip():
            self.toast_overlay.add_toast(Adw.Toast(title="Empty output buffer"))
            return

        file_extension = (
            "blp"
            if self.direction_toggle_group.get_active_name() == "xml_to_blp"
            else "ui"
        )

        file_dialog = Gtk.FileDialog(
            title=f"Save {file_extension} file",
            initial_name=f"untitled.{file_extension}",
        )

        file_dialog.save(self, None, self.on_save_response)

    def on_save_response(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult):
        text = self.read_buffer(self.output_buffer)

        if file := dialog.save_finish(result):
            bytes = GLib.Bytes.new(text.encode("utf-8"))

            file.replace_contents_bytes_async(
                contents=bytes,
                etag=None,
                make_backup=False,
                flags=Gio.FileCreateFlags.NONE,
                callback=self.save_file_complete,
            )

    def save_file_complete(self, file: Gio.File, result: Gio.AsyncResult):
        success, _ = file.replace_contents_finish(result)

        info = file.query_info("standard::display-name", Gio.FileQueryInfoFlags.NONE)

        display_name = (
            info.get_attribute_string("standard::display-name")
            if info
            else file.get_basename()
        )

        if success:
            toast_msg = f"Saved {display_name}"
        else:
            toast_msg = f"Unable to save {display_name}"

        self.toast_overlay.add_toast(Adw.Toast(title=toast_msg))


# todo: detect lang when pasting and opening file (xml, ui, blp)
