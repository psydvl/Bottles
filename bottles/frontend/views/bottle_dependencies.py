# bottle_installers.py
#
# Copyright 2022 brombinmirko <send@mirko.pm>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import time
from gettext import gettext as _
from gi.repository import Gtk, GLib, Adw

from bottles.frontend.utils.threading import RunAsync
from bottles.frontend.utils.common import open_doc_url
from bottles.frontend.widgets.dependency import DependencyEntry


@Gtk.Template(resource_path='/com/usebottles/bottles/details-dependencies.ui')
class DependenciesView(Adw.Bin):
    __gtype_name__ = 'DetailsDependencies'
    __registry = []

    # region Widgets
    list_dependencies = Gtk.Template.Child()
    btn_report = Gtk.Template.Child()
    btn_help = Gtk.Template.Child()
    entry_search = Gtk.Template.Child()
    actions = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    ev_controller = Gtk.EventControllerKey.new()

    # endregion

    def __init__(self, details, config, **kwargs):
        super().__init__(**kwargs)

        # common variables and references
        self.window = details.window
        self.manager = details.window.manager
        self.config = config
        self.queue = details.queue

        self.ev_controller.connect("key-released", self.__search_dependencies)

        self.entry_search.add_controller(self.ev_controller)
        self.search_bar.set_key_capture_widget(self.window)

        self.btn_report.connect("clicked", open_doc_url, "contribute/missing-dependencies")
        self.btn_help.connect("clicked", open_doc_url, "bottles/dependencies")

    def __search_dependencies(self, *_args):
        """
        This function search in the list of dependencies the
        text written in the search entry.
        """
        terms = self.entry_search.get_text()
        self.list_dependencies.set_filter_func(self.__filter_dependencies,  terms)

    @staticmethod
    def __filter_dependencies(row, terms=None):
        text = row.get_title().lower() + row.get_subtitle().lower()
        if terms.lower() in text:
            return True
        return False

    def empty_list(self):
        for r in self.__registry:
            if r.get_parent() is not None:
                r.get_parent().remove(r)
        self.__registry = []

    def update(self, widget=False, config=None):
        """
        This function update the dependencies list with the
        supported by the manager.
        """
        if config is None:
            config = {}
        self.config = config
        dependencies = self.manager.supported_dependencies

        self.list_dependencies.set_sensitive(False)

        def new_dependency(dependency, plain=False):
            entry = DependencyEntry(
                    window=self.window,
                    config=self.config,
                    dependency=dependency,
                    plain=plain
            )
            self.__registry.append(entry)
            self.list_dependencies.append(entry)

        def callback(result, error=False):
            self.list_dependencies.set_sensitive(True)

        def process_dependencies():
            time.sleep(.6)  # workaround for freezing bug on bottle load
            GLib.idle_add(self.empty_list)

            if len(dependencies.keys()) > 0:
                for dep in dependencies.items():
                    if dep[0] in self.config.get("Installed_Dependencies"):
                        continue  # Do not list already installed dependencies'

                    if dep[1].get("Arch", "win64") != self.config.get("Arch"):
                        # NOTE: avoid listing dependencies not supported by the bottle arch
                        continue

                    GLib.idle_add(new_dependency, dep)

            if len(self.config.get("Installed_Dependencies")) > 0:
                for dep in self.config.get("Installed_Dependencies"):
                    if dep in dependencies:
                        dep = (dep, dependencies[dep])
                        GLib.idle_add(new_dependency, dep, plain=True)

        RunAsync(process_dependencies, callback=callback)
