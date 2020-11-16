from ..dialog import *
from .list_dialog import ListEntry, ListPane, ListDialog
from .message_dialog import MessageDialog
from functools import cmp_to_key


class Entry(ListEntry):

    def __init__(self, parent, name):

        ListEntry.__init__(self, parent)

        data = (("name", name, "left", 0, 0.),)
        self.set_data(data, Skin.layout.borders["skin_dialog_entry_data"])
        self.name = name


class Pane(ListPane):

    def __init__(self, parent, names):

        column_data = (("name", 1.),)
        borders = Skin.layout.borders["skin_dialog_entry_column"]
        frame_client_size = (
            Skin.options["skin_dialog_scrollpane_width"],
            Skin.options["skin_dialog_scrollpane_height"]
        )

        ListPane.__init__(self, parent, column_data, borders, frame_client_size,
            multi_select=False)

        for name in names:
            entry = Entry(self, name)
            self.entry_list.append(entry)

    def search_entries(self, text_id, substring, in_selection, match_case, part, find_next=False):

        entries = ListPane.search_entries(self, text_id, substring, in_selection,
                                          match_case, part, find_next)

        if not find_next:
            self.get_ancestor("dialog").set_name(entries[0].name if entries else None)

        return entries

    def find_next(self):

        entry = ListPane.find_next(self)
        self.get_ancestor("dialog").set_name(entry.name if entry else None)

    def set_selected_entry(self, entry):

        ListPane.set_selected_entry(self, entry)

        self.get_ancestor("dialog").set_name(entry.name)


class SkinSelectionDialog(ListDialog):

    def __init__(self):

        ListDialog.__init__(self, "", "okcancel", "Select", self.__on_yes,
                            multi_select=False)

        file_sys = VirtualFileSystem.get_global_ptr()
        dirlist = file_sys.scan_directory("skins")
        subdirnames = []

        if dirlist:
            for item in dirlist:
                if item.is_directory():
                    subdirnames.append(item.get_filename().get_basename())

        f = lambda x, y: (x.casefold() > y.casefold()) - (x.casefold() < y.casefold())
        self._names = sorted(subdirnames, key=cmp_to_key(f))

        self._selected_name = ""
        self._search_options = {"match_case": True, "part": "start"}

        widgets = Skin.layout.create(self, "skin_selection")

        self.setup_search_interface(widgets, self.__search_entries,
            self.__set_search_option, True, "start")

        placeholder_item = widgets["placeholders"]["pane"]
        parent = placeholder_item.sizer.owner_widget
        self.pane = pane = Pane(parent, subdirnames)
        frame = pane.frame
        placeholder_item.object = frame

        # the following code is necessary to update the width of the list entries
        client_sizer = self.client_sizer
        client_sizer.update_min_size()
        client_sizer.set_size(client_sizer.get_size())
        pane.finalize()
        self.finalize()

    def close(self, answer=""):

        def command():

            self.pane = None

            ListDialog.close(self, answer)

        if answer == "yes" and not self._selected_name:
            msg = "Please select a skin"
            MessageDialog(title="No selection",
                          message=msg,
                          choices="ok",
                          icon_id="icon_exclamation")
            return

        command()

    def __on_yes(self):

        config_data = GD["config"]
        config_data["skin"] = self._selected_name

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

        msg = "The chosen skin will be applied at\nthe next restart of the program."
        MessageDialog(title="Restart required",
                      message=msg,
                      choices="ok")

    def __set_search_option(self, option, value):

        self._search_options[option] = value

    def __search_entries(self, name):

        match_case = self._search_options["match_case"]
        part = self._search_options["part"]
        self.pane.search_entries("name", name, False, match_case, part)

    def set_name(self, name):

        self._selected_name = name
