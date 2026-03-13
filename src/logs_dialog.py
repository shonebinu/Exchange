from gi.repository import Adw, Gtk


@Gtk.Template(resource_path="/io/github/shonebinu/Exchange/logs-dialog.ui")
class LogsDialog(Adw.Dialog):
    __gtype_name__ = "LogsDialog"

    text_buffer: Gtk.TextBuffer = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_logs(self, text: str):
        self.text_buffer.set_text(text)
