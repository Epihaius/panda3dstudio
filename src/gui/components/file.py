from ..base import *
import wx.lib.scrolledpanel as scrolled


class FileManager(object):

    def __init__(self, menubar):

        file_data = {}

        handlers = {
            "new": self.__reset_scene,
            "open": self.__load_scene,
            "save": self.__save_scene,
            "save_as": self.__save_scene_as,
            "save_incr": self.__save_scene_incrementally,
            "export": self.__export_scene,
            "import": self.__prepare_import,
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

        Mgr.add_app_updater("import", self.__import_scene)
        Mgr.add_app_updater("scene_label", self.__set_scene_label)
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

    def __set_scene_label(self, label):

        Mgr.do("set_scene_label", label)

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
            Mgr.do("set_scene_label", filename)

        if GlobalData["ctrl_down"]:
            GlobalData["ctrl_down"] = False

    def __save_scene(self):

        open_file = GlobalData["open_file"]

        if open_file:

            if not GlobalData["unsaved_scene"]:
                return True

            Mgr.update_app("scene", "save", open_file)
            Mgr.do("set_scene_label", open_file)

            if GlobalData["ctrl_down"]:
                GlobalData["ctrl_down"] = False

            return True

        return self.__save_scene_as()

    def __save_scene_as(self):

        open_file = GlobalData["open_file"]
        default_filename = open_file if open_file else ""
        filename = wx.FileSelector("Save scene as",
                                   "", default_filename, "p3ds", "*.p3ds",
                                   wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if GlobalData["ctrl_down"]:
            GlobalData["ctrl_down"] = False

        if filename:
            Mgr.update_app("scene", "save", filename)
            Mgr.do("set_scene_label", filename)
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

        open_file = GlobalData["open_file"]

        if not open_file:
            return

        dirname, tail = os.path.split(open_file)
        basename, ext = os.path.splitext(tail)
        names = [os.path.splitext(name)[0] for name in os.listdir(dirname)
                 if os.path.splitext(name)[1] == ext]
        namestring = "\n".join(names)
        filename = self.__get_incremented_filename(basename, namestring)
        path = os.path.join(dirname, filename + ext)

        Mgr.update_app("scene", "save", path)
        Mgr.do("set_scene_label", path)

    def __set_scene_as_unsaved(self):

        open_file = GlobalData["open_file"]
        scene_label = (open_file if open_file else "New")

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
            Mgr.update_app("export", filename)

    def __prepare_import(self):

        wildcard = "Panda3D files (*.bam;*.egg;*.egg.pz)|*.bam;*.egg;*.egg.pz"
        filename = wx.FileSelector("Import scene", "", "", "bam", wildcard,
                                   wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if GlobalData["ctrl_down"]:
            GlobalData["ctrl_down"] = False

        if filename:
            Mgr.update_remotely("import", "prepare", filename)

    def __import_scene(self, obj_data, new_obj_names):

        dialog = ImportDialog(Mgr.get("main_window"), obj_data, new_obj_names)
        answer = dialog.ShowModal()

        if answer == wx.ID_OK:
            Mgr.update_remotely("import", "start")
            self.__set_scene_as_unsaved()
        else:
            Mgr.update_remotely("import", "cancel")

        dialog.Destroy()

        if GlobalData["ctrl_down"]:
            GlobalData["ctrl_down"] = False

    def on_exit(self):

        if GlobalData["unsaved_scene"]:

            if GlobalData["long_process_running"]:

                answer = wx.MessageBox("Changes to the current scene cannot be saved right now!"\
                                       + "\n\nExit anyway?",
                                       "Exit",
                                       wx.YES_NO | wx.ICON_EXCLAMATION)

                if answer == wx.NO:
                    return False

            else:

                answer = wx.MessageBox("Save changes to current scene before exiting?",
                                       "Save changes",
                                       wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION)

                if answer == wx.YES:
                    if not self.__save_scene():
                        return False
                elif answer == wx.CANCEL:
                    return False

        return True


class ImportDialog(wx.Dialog):

    def __init__(self, parent, obj_data, new_obj_names):

        title = "Import options"
        size = (800, 700)

        wx.Dialog.__init__(self, parent, -1, title, size=size)

        self._obj_data = obj_data
        self._obj_names = new_obj_names
        self._name_fields = {}
        self._checkboxes = {}

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(self, -1,
                             "Please choose whether you want to import geometry as"
                             " basic or fully editable models."
                             "\nA new name can also be set for each object."
                            )
        main_sizer.Add(info, 0, wx.ALL, 14)

        get_name_handler = lambda obj_type, index: lambda evt: self.__commit_name(obj_type, index)
        get_editing_handler = lambda obj_type, index: lambda evt: self.__set_editing(obj_type, index)
        get_all_editing_handler = lambda obj_type: lambda evt: self.__set_all_editing(obj_type)

        for obj_type, descr in (("geom", "Regular geometry"), ("collision", "Collision geometry"),
                                ("other", "Other objects")):

            if obj_data[obj_type]:

                main_sizer.Add(wx.Size(0, 20))
                main_sizer.Add(wx.StaticText(self, -1, descr), 0, wx.ALIGN_CENTER)

                panel = wx.PyPanel(self, -1, style=wx.SUNKEN_BORDER)

                panel_sizer = wx.BoxSizer(wx.VERTICAL)
                panel.SetSizer(panel_sizer)
                main_sizer.Add(panel, 1, wx.ALL | wx.EXPAND, 10)

                col_count = 4 if obj_type == "other" else 5
                subsizer = wx.FlexGridSizer(rows=0, cols=col_count, hgap=10, vgap=5)
                subsizer.AddGrowableCol(2, 1)
                subsizer.AddGrowableCol(3, 1)
                subsizer.SetFlexibleDirection(wx.HORIZONTAL)

                subsizer.Add(wx.StaticText(panel, -1, "Index"), 0, wx.ALIGN_CENTER)
                subsizer.Add(wx.StaticText(panel, -1, "Parent index"), 0, wx.ALIGN_CENTER)
                subsizer.Add(wx.StaticText(panel, -1, "Imported name"), 0, wx.ALIGN_CENTER)
                subsizer.Add(wx.StaticText(panel, -1, "New name"), 0, wx.ALIGN_CENTER)

                if obj_type != "other":
                    subsizer.Add(wx.StaticText(panel, -1, "Fully editable"), 0, wx.ALIGN_CENTER)

                panel_sizer.Add(subsizer, 0, wx.ALL | wx.EXPAND, 10)

                scroll_sizer = wx.BoxSizer(wx.VERTICAL)
                col_count = 4 if obj_type == "other" else 6
                subsizer = wx.FlexGridSizer(rows=0, cols=col_count, hgap=10, vgap=5)
                subsizer.AddGrowableCol(2, 1)
                subsizer.AddGrowableCol(3, 1)
                subsizer.SetFlexibleDirection(wx.HORIZONTAL)

                scroll_panel = scrolled.ScrolledPanel(panel, -1, style=wx.SUNKEN_BORDER)

                if obj_type != "other":
                    all_editing = set()

                for index in sorted(obj_data[obj_type].iterkeys()):

                    data = obj_data[obj_type][index]
                    parent_index = data["parent_index"]
                    old_name = data["old_name"]
                    new_name = data["new_name"]

                    if obj_type != "other":
                        basic_or_full = data["editing"]
                        all_editing.add(basic_or_full)

                    label = wx.PyPanel(scroll_panel, -1, style=wx.SIMPLE_BORDER)
                    label_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    label_sizer.SetMinSize(wx.Size(20, 1))
                    label.SetSizer(label_sizer)
                    txt = wx.StaticText(label, -1, str(index))
                    label_sizer.Add(txt, 0, wx.ALL, 2)
                    subsizer.Add(label, 0, wx.EXPAND)
                    label = wx.PyPanel(scroll_panel, -1, style=wx.SIMPLE_BORDER)
                    label_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    label_sizer.SetMinSize(wx.Size(60, 1))
                    label.SetSizer(label_sizer)
                    txt = wx.StaticText(label, -1, str(parent_index) if parent_index else "-")
                    label_sizer.Add(txt, 0, wx.ALL, 2)
                    subsizer.Add(label, 0, wx.EXPAND)
                    label = wx.PyPanel(scroll_panel, -1, style=wx.SIMPLE_BORDER)
                    label_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    label.SetSizer(label_sizer)
                    old_name_txt = wx.StaticText(label, -1, old_name)
                    label_sizer.Add(old_name_txt, 0, wx.ALL, 2)
                    subsizer.Add(label, 0, wx.EXPAND)
                    name_field = wx.TextCtrl(scroll_panel, -1, new_name, style=wx.TE_PROCESS_ENTER)
                    name_field.SetInitialSize(wx.Size(300, 10))
                    handler = get_name_handler(obj_type, index)
                    name_field.Bind(wx.EVT_TEXT_ENTER, handler)
                    name_field.Bind(wx.EVT_KILL_FOCUS, handler)
                    self._name_fields[index] = name_field
                    subsizer.Add(name_field, 0, wx.EXPAND)

                    if obj_type != "other":
                        subsizer.Add(wx.Size(20, 0), 0, wx.EXPAND)
                        checkbox = wx.CheckBox(scroll_panel, -1)
                        checkbox.SetValue(True if basic_or_full == "full" else False)
                        handler = get_editing_handler(obj_type, index)
                        checkbox.Bind(wx.EVT_CHECKBOX, handler)
                        self._checkboxes[index] = checkbox
                        subsizer.Add(checkbox, 0, wx.RIGHT | wx.EXPAND, 20)

                scroll_sizer.Add(subsizer, 1, wx.ALL | wx.EXPAND, 10)
                scroll_panel.SetSizer(scroll_sizer)
                panel_sizer.Add(scroll_panel, 1, wx.EXPAND)
                scroll_panel.SetupScrolling()

                if obj_type != "other":

                    subsizer = wx.FlexGridSizer(rows=0, cols=3, hgap=10, vgap=5)
                    subsizer.AddGrowableCol(0, 1)
                    subsizer.SetFlexibleDirection(wx.HORIZONTAL)
                    subsizer.Add(wx.StaticText(panel, -1, "All"), 0, wx.ALIGN_RIGHT)
                    subsizer.Add(wx.Size(20, 0), 0, wx.EXPAND)
                    checkbox = wx.CheckBox(panel, -1, style=wx.CHK_3STATE)
                    handler = get_all_editing_handler(obj_type)
                    checkbox.Bind(wx.EVT_CHECKBOX, handler)
                    self._checkboxes[obj_type] = checkbox
                    subsizer.Add(checkbox, 0, wx.RIGHT | wx.EXPAND, 20)
                    panel_sizer.Add(subsizer, 0, wx.ALL | wx.EXPAND, 10)

                    if len(all_editing) > 1:
                        checkbox.Set3StateValue(wx.CHK_UNDETERMINED)
                    elif all_editing.pop() == "full":
                        checkbox.Set3StateValue(wx.CHK_CHECKED)
                    else:
                        checkbox.Set3StateValue(wx.CHK_UNCHECKED)

        self._panel = panel

        main_sizer.AddSpacer(20)

        main_btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(main_btn_sizer, 0, wx.ALL | wx.EXPAND, 8)

        self.SetSizer(main_sizer)
        self.SetClientSize(size)

    def __commit_name(self, obj_type, index):

        obj_names = GlobalData["obj_names"] + self._obj_names
        name = self._obj_data[obj_type][index]["new_name"]
        obj_names.remove(name)
        field = self._name_fields[index]
        new_name = field.GetValue()
        new_name = get_unique_name(new_name, obj_names)
        field.SetValue(new_name)

        if new_name != name:
            self._obj_data[obj_type][index]["new_name"] = new_name
            self._obj_names.remove(name)
            self._obj_names.append(new_name)

        self._panel.SetFocusIgnoringChildren()

    def __set_editing(self, obj_type, index):

        checkbox = self._checkboxes[index]
        is_checked = checkbox.IsChecked()
        data = self._obj_data[obj_type]
        data[index]["editing"] = "full" if is_checked else "basic"
        self._panel.SetFocusIgnoringChildren()
        all_editing = set([v["editing"] for v in data.itervalues()])

        if len(all_editing) > 1:
            self._checkboxes[obj_type].Set3StateValue(wx.CHK_UNDETERMINED)
        elif all_editing.pop() == "full":
            self._checkboxes[obj_type].Set3StateValue(wx.CHK_CHECKED)
        else:
            self._checkboxes[obj_type].Set3StateValue(wx.CHK_UNCHECKED)

    def __set_all_editing(self, obj_type):

        checkboxes = self._checkboxes
        checkbox = checkboxes[obj_type]
        is_checked = checkbox.Get3StateValue() == wx.CHK_CHECKED
        data = self._obj_data[obj_type]
        editing_val = "full" if is_checked else "basic"
        self._panel.SetFocusIgnoringChildren()

        for index, v in data.iteritems():
            v["editing"] = editing_val
            checkboxes[index].SetValue(is_checked)
