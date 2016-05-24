from ..base import *


class FileManager(object):

    def __init__(self, menubar):

        self._filename = ""
        file_data = {}

        handlers = {
            "new": self.__reset_scene,
            "open": self.__load_scene,
            "save": self.__save_scene,
            "save_as": self.__save_scene_as,
            "save_incr": self.__save_scene_incrementally,
            "export": self.__export_scene,
            "import": self.__import_scene,
        }
        descriptions = {
            "new": "New",
            "open": "Open...",
            "save": "Save",
            "save_as": "Save As...",
            "save_incr": "Save Incrementally",
            "export": "Export...",
            "import": "Import...",
        }

        for file_op, handler in handlers.iteritems():
            descr = descriptions[file_op]
            file_data[file_op] = {"descr": descr, "handler": handler}

        menubar.add_menu("file", "File")

        file_ops = ("new", "open", "save")
        accelerators = ("N", "O", "S")
        mod_code = wx.MOD_CONTROL
        hotkeys = [(ord(accel), mod_code) for accel in accelerators]

        for file_op, accel, hotkey in zip(file_ops, accelerators, hotkeys):
            data = file_data[file_op]
            menubar.add_menu_item("file", file_op, "%s\tCTRL+%s" % (data["descr"], accel),
                                  data["handler"], hotkey)

        file_ops = ("save_as", "save_incr")

        for file_op in file_ops:
            data = file_data[file_op]
            menubar.add_menu_item("file", file_op, data["descr"], data["handler"])

        menubar.add_menu_item_separator("file")

        file_ops = ("export", "import")

        for file_op in file_ops:
            data = file_data[file_op]
            menubar.add_menu_item("file", file_op, data["descr"], data["handler"])

        menubar.add_menu_item_separator("file")

        handler = Mgr.get("main_window").Close
        menubar.add_menu_item("file", "exit", "Exit\tALT+F4", handler)

        Mgr.add_app_updater("unsaved_scene", self.__set_scene_as_unsaved)

    def __reset_scene(self):

        if GlobalData["unsaved_scene"]:

            answer = wx.MessageBox("Save changes to current scene before resetting?",
                                   "Save changes",
                                   wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION)

            if GlobalData["ctrl_down"]:
                GlobalData["ctrl_down"] = False

            if answer == wx.YES:
                if not self.__save_scene():
                    return
            elif answer == wx.CANCEL:
                return

        Mgr.update_app("scene", "reset")
        self._filename = ""
        Mgr.do("set_scene_label", "New")

    def __load_scene(self):

        if GlobalData["unsaved_scene"]:

            answer = wx.MessageBox("Save changes to current scene before loading?",
                                   "Save changes",
                                   wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION)

            if answer == wx.YES:
                self.__save_scene()
            elif answer == wx.CANCEL:
                return

        filename = wx.FileSelector("Open scene",
                                   "", "", "p3ds", "*.p3ds",
                                   wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if filename:
            Mgr.update_app("scene", "load", filename)
            self._filename = filename
            Mgr.do("set_scene_label", self._filename)

        if GlobalData["ctrl_down"]:
            GlobalData["ctrl_down"] = False

    def __save_scene(self):

        if self._filename:

            if not GlobalData["unsaved_scene"]:
                return True

            Mgr.update_app("scene", "save", self._filename)
            Mgr.do("set_scene_label", self._filename)

            if GlobalData["ctrl_down"]:
                GlobalData["ctrl_down"] = False

            return True

        return self.__save_scene_as()

    def __save_scene_as(self):

        default_filename = self._filename if self._filename else ""
        filename = wx.FileSelector("Save scene as",
                                   "", default_filename, "p3ds", "*.p3ds",
                                   wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if GlobalData["ctrl_down"]:
            GlobalData["ctrl_down"] = False

        if filename:
            Mgr.update_app("scene", "save", filename)
            self._filename = filename
            Mgr.do("set_scene_label", self._filename)
            return True

        return False

    def __get_incremented_filename(self, filename, namestring):

        import re

        min_index = 1
        pattern = r"(.*?)(\s*)(\d*)$"
        basename, space, index_str = re.search(pattern, filename).groups()
        search_pattern = r"^%s\s*(\d+)$" % re.escape(basename)

        if index_str:
            min_index = int(index_str)
            zero_padding = len(index_str) if index_str.startswith("0") else 0
            naming_pattern = basename + space + "%0" + str(zero_padding) + "d"
        else:
            naming_pattern = basename + " %02d"

        names = re.finditer(search_pattern, namestring, re.M)
        inds = [int(name.group(1)) for name in names]
        max_index = min_index + len(inds)

        for i in xrange(min_index, max_index):
            if i not in inds:
                return naming_pattern % i

        return naming_pattern % max_index

    def __save_scene_incrementally(self):

        if not self._filename:
            return

        dirname, tail = os.path.split(self._filename)
        basename, ext = os.path.splitext(tail)
        names = [os.path.splitext(name)[0] for name in os.listdir(dirname)
                 if os.path.splitext(name)[1] == ext]
        namestring = "\n".join(names)
        filename = self.__get_incremented_filename(basename, namestring)
        self._filename = os.path.join(dirname, filename + ext)

        Mgr.update_app("scene", "save", self._filename)
        Mgr.do("set_scene_label", self._filename)

    def __set_scene_as_unsaved(self):

        scene_label = (self._filename if self._filename else "New")

        if GlobalData["unsaved_scene"]:
            scene_label += "*"

        Mgr.do("set_scene_label", scene_label)

    def __export_scene(self):

        wildcard = "Panda3D files (*.bam)|*.bam|Wavefront files (*.obj)|*.obj"
        filename = wx.FileSelector("Export scene", "", "", "bam", wildcard,
                                   wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if GlobalData["ctrl_down"]:
            GlobalData["ctrl_down"] = False

        if filename:
            Mgr.update_app("scene", "export", filename)

    def __import_scene(self):

        wildcard = "Panda3D files (*.bam;*.egg;*.egg.pz)|*.bam;*.egg;*.egg.pz"
        filename = wx.FileSelector("Import scene", "", "", "bam", wildcard,
                                   wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if GlobalData["ctrl_down"]:
            GlobalData["ctrl_down"] = False

        if filename:
            Mgr.update_app("scene", "import", filename)
            self.__set_scene_as_unsaved()

        if GlobalData["ctrl_down"]:
            GlobalData["ctrl_down"] = False

    def on_exit(self):

        if GlobalData["unsaved_scene"]:

            answer = wx.MessageBox("Save changes to current scene before exiting?",
                                   "Save changes",
                                   wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION)

            if answer == wx.YES:
                if not self.__save_scene():
                    return False
            elif answer == wx.CANCEL:
                return False

        return True
