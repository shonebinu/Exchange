from gi.repository import Adw, Gtk


@Gtk.Template(resource_path="/io/github/shonebinu/Exchange/logs-dialog.ui")
class LogsDialog(Adw.Dialog):
    __gtype_name__ = "LogsDialog"

    logs_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_logs(self, text: str):
        self.logs_label.set_markup(f"<tt>{text}</tt>")
