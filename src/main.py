import asyncio
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")

from gi.events import GLibEventLoopPolicy
from gi.repository import Adw, Gio, GtkSource

from .window import ExchangeWindow


class ExchangeApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(
            application_id="io.github.shonebinu.Exchange",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            resource_base_path="/io/github/shonebinu/Exchange",
        )
        GtkSource.init()
        self.create_action("quit", lambda *_: self.quit(), ["<control>q"])
        self.create_action("about", self.on_about_action)

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = ExchangeWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog.new_from_appdata(
            "/io/github/shonebinu/Exchange/appdata.xml"
        )
        about.add_link("Donate with Ko-Fi", "https://ko-fi.com/shonebinu")
        about.add_link("Sponsor on Github", "https://github.com/sponsors/shonebinu")

        about.add_other_app(
            "io.github.shonebinu.Glyph", "Lipi", "Discover and install online fonts"
        )
        about.add_other_app(
            "io.github.shonebinu.Brief", "Brief", "Browse command-line cheatsheets"
        )

        about.present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    asyncio.set_event_loop_policy(GLibEventLoopPolicy())
    app = ExchangeApplication()
    return app.run(sys.argv)
