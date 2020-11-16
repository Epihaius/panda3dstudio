from ..dialog import *
from .message_dialog import MessageDialog
from ..menu import Menu
from direct.stdpy.file import *
from direct.stdpy.glob import *
from functools import cmp_to_key


def get_incremented_filename(filename, namestring):

    import re

    min_index = 1
    pattern = r"(.*?)(\s*)(\d*)$"
    basename, space, index_str = re.search(pattern, filename).groups()
    search_pattern = fr"^{re.escape(basename)}\s*(\d+)$"

    if index_str:
        min_index = int(index_str)
        zero_padding = len(index_str) if index_str.startswith("0") else 0
        naming_pattern = basename + space + "{:0" + str(zero_padding) + "d}"
    else:
        naming_pattern = basename + " {:02d}"

    names = re.finditer(search_pattern, namestring, re.I | re.M)
    inds = [int(name.group(1)) for name in names]
    max_index = min_index + len(inds)

    for i in range(min_index, max_index):
        if i not in inds:
            return naming_pattern.format(i)

    return naming_pattern.format(max_index)


class FileButton(Button):

    _file_icon = None
    _dir_icon = None
    _candidate_btn = None
    selected_btn = None
    _clock = ClockObject()
    _popup_menu = None

    @classmethod
    def __create_popup_menu(cls):

        def edit_file(edit_op):

            selected_btn = cls.selected_btn

            if selected_btn:
                if edit_op == "rename":
                    selected_btn.show_name_field()
                elif edit_op == "remove":
                    selected_btn.remove_file()

        cls._popup_menu = menu = Menu()
        menu.add("rename", "Rename", lambda: edit_file("rename"))
        menu.set_item_hotkey("rename", None, "F2")
        menu.add("remove", "Delete", lambda: edit_file("remove"))
        menu.set_item_hotkey("remove", None, "Shift+Del")
        menu.update()

    @classmethod
    def __check_candidate_filebutton(cls, task):

        if cls._clock.real_time > .5:

            if cls.selected_btn:
                cls.selected_btn.active = False

            cls.selected_btn = cls._candidate_btn
            cls.selected_btn.active = True
            cls.__set_candidate_button(None)

        return task.cont

    @classmethod
    def __set_candidate_button(cls, button):

        if cls._candidate_btn is button:
            return

        cls._candidate_btn = button
        cls._clock.reset()

        if button:
            Mgr.add_task(cls.__check_candidate_filebutton, "check_candidate_filebutton")
        else:
            Mgr.remove_task("check_candidate_filebutton")

    @classmethod
    def set_selected_filebutton(cls, button):

        if cls.selected_btn:
            cls.selected_btn.active = False

        if button:
            button.active = True

        cls.selected_btn = button
        cls.__set_candidate_button(None)

    def __init__(self, parent, filename, on_select=None, command=None, is_dir=False):

        gfx_ids = Skin.atlas.gfx_ids["file_button"]

        if not self._file_icon:
            gfx_id = gfx_ids["icon_file"][0][0]
            x, y, w, h = Skin.atlas.regions[gfx_id]
            FileButton._file_icon = img = PNMImage(w, h, 4)
            img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)

        if not self._dir_icon:
            gfx_id = gfx_ids["icon_folder"][0][0]
            x, y, w, h = Skin.atlas.regions[gfx_id]
            FileButton._dir_icon = img = PNMImage(w, h, 4)
            img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)

        if not self._popup_menu:
            self.__create_popup_menu()

        gfx_ids = Skin.atlas.gfx_ids["file_button"]

        Button.__init__(self, parent, gfx_ids, filename, text_alignment="left",
                        button_type="file_button")

        self.widget_type = "file_button"
        self.command = command

        self.node.reparent_to(parent.widget_root_node)
        self.mouse_region.sort = parent.sort + 1
        self._filename = filename
        self._on_select = on_select if on_select else lambda filename: None
        self._is_dir = is_dir

        self._is_name_field_shown = False

    def destroy(self):

        Button.destroy(self)

        self._on_select = lambda filename: None

    def set_filename(self, filename):

        Button.set_text(self, filename)

        self.sizer.min_size = self.get_min_size(ignore_sizer=True)
        self._filename = filename

    def get_filename(self):

        return self._filename

    def is_directory(self):

        return self._is_dir

    def get_image(self, state=None, composed=True):

        image = Button.get_image(self, state, composed)

        if self._is_name_field_shown:
            field = self.parent.get_filename_field()
            field_img = field.get_image()
            image.copy_sub_image(field_img, 0, 0, 0, 0)

        l, r, b, t = Skin.atlas.outer_borders["icon_file"]

        if self._is_dir:
            image.blend_sub_image(self._dir_icon, l, t, 0, 0)
        else:
            image.blend_sub_image(self._file_icon, l, t, 0, 0)

        return image

    def show_name_field(self, show=True):

        if self._is_name_field_shown == show:
            return

        field = self.parent.get_filename_field()

        if show:

            if self.selected_btn is not self:
                self.set_selected_filebutton(self)

            file_type = "folder" if self._is_dir else "file"
            open_file = GD["open_file"]

            if open_file:

                current_dir = self.parent.get_directory()
                path = join(current_dir, self._filename)

                if file_type == "file" and path == open_file:
                    MessageDialog(title="Cannot rename file",
                                  message="The file is open in this application,"
                                          "\nso it cannot be renamed.",
                                  choices="ok",
                                  icon_id="icon_exclamation")
                    return

            field.parent = self
            sizer = Sizer("horizontal")
            sizer.add(field, proportions=(1., 0.))
            size = self.get_size()
            self.sizer = sizer
            sizer.default_size = size
            sizer.set_size(size)
            sizer.update_positions()
            sizer.update_images()
            sizer.update_mouse_region_frames()
            field.set_text(self._filename)
            field.on_left_down()
            field._on_left_up()

        else:

            sizer = self.sizer
            sizer.remove_cell(sizer.cells[0])
            sizer.destroy()
            self.sizer = None
            field.parent = None

        self._is_name_field_shown = show
        Button.on_leave(self, force=True)

    def is_name_field_shown(self):

        return self._is_name_field_shown

    def remove_file(self):

        def command():

            if self.parent.remove_file(self):
                self.set_selected_filebutton(None)

        file_type = "folder" if self._is_dir else "file"
        open_file = GD["open_file"]

        if open_file:

            current_dir = self.parent.get_directory()
            path = join(current_dir, self._filename)

            if file_type == "file" and path == open_file:
                MessageDialog(title="Cannot delete file",
                              message="The file is open in this application,"
                                      "\nso it cannot be deleted.",
                              choices="ok",
                              icon_id="icon_exclamation")
                return

        MessageDialog(title=f"Confirm delete {file_type}",
                      message=f"You have chosen to PERMANENTLY delete this {file_type}!"
                              "\n\nAre you sure?",
                      choices="yesno", on_yes=command,
                      icon_id="icon_exclamation")

    def on_enter(self):

        Button.on_enter(self)

        if self.selected_btn is not self:
            self.__set_candidate_button(self)

    def on_leave(self):

        if not Button.on_leave(self):
            return

        if self.selected_btn is not self:
            self.__set_candidate_button(None)

    def on_left_up(self):

        if self.selected_btn is not self:
            self.set_selected_filebutton(self)
        else:
            self._on_select(self._filename)

        Button.on_left_up(self)

    def on_right_up(self):

        Button.on_right_up(self)

        if self.selected_btn is not self:
            self.set_selected_filebutton(self)

        self._popup_menu.show_at_mouse_pos()

    def set_active(self, active):

        if Button.set_active(self, active) and active:
            self._on_select(self._filename)


class FileButtonInputField(DialogInputField):

    _alt_borders = ()
    _alt_offset = (0, 0)
    _ref_node = NodePath("reference_node")

    @classmethod
    def __set_alt_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["filename_field"]
        cls._alt_borders = (l, r, b, t)
        cls._alt_offset = (-l, -t)

    @classmethod
    def set_ref_node_pos(cls, pos):

        cls._ref_node.set_pos(pos)

    def __init__(self, parent, handler, width, font=None, text_color=None, back_color=None):

        if not self._alt_borders:
            self.__set_alt_borders()

        gfx_ids = Skin.atlas.gfx_ids["file_button"]["field"]

        DialogInputField.__init__(self, parent, width, font, text_color, back_color,
                                  self._alt_borders, gfx_ids, self._alt_offset)

        self.value_id = "filename"
        self.value_type = "string"
        self.set_value_handler(handler)
        self.set_on_accept(self.__hide_name_field)
        self.set_on_reject(self.__hide_name_field)
        self.parent = None

    def __hide_name_field(self, *args):

        FileButton.selected_btn.show_name_field(False)


class FilePane(DialogScrollPane):

    def __init__(self, parent, path_handler, file_selection_handler, file_command, extensions,
                 default_filename):

        gfx_id = Skin.atlas.gfx_ids["file_button"]["normal"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        height = h * Skin.options["file_row_count"]
        frame_client_size = (Skin.options["file_dialog_scrollpane_width"], height)

        DialogScrollPane.__init__(self, parent, "file_pane", "horizontal", frame_client_size)

        self._path_handler = path_handler
        self._file_selection_handler = file_selection_handler
        self._file_command = file_command
        self._extensions = extensions
        self._file_sys = file_sys = VirtualFileSystem.get_global_ptr()

        if default_filename:
            self._current_path = Filename(default_filename).get_dirname()
        else:
            self._current_path = file_sys.get_cwd().get_fullpath()

        self._btns = []

        def handler(value_id, value, state="done"):

            if not self._filename_field.parent.is_directory():
                file_selection_handler(value)

        dialog = parent.get_ancestor("dialog")
        field = FileButtonInputField(dialog, handler, 1)
        field.set_input_parser(self.__rename_file)
        field.set_scissor_effect(self.scissor_effect)
        self._filename_field = field

        self._btn_sizer = Sizer("vertical", Skin.options["file_row_count"],
            (Skin.options["file_btn_h_gap"], Skin.options["file_btn_v_gap"]))
        self.sizer.add(self._btn_sizer)

        self.__update_directory_list(update_layout=False)

    def _copy_widget_images(self, pane_image):

        root_node = self.widget_root_node

        for btn in self._btns:
            x, y = btn.get_pos(ref_node=root_node)
            offset_x, offset_y = btn.image_offset
            pane_image.copy_sub_image(btn.get_image(), x + offset_x, y + offset_y, 0, 0)

    def _can_scroll(self):

        if not self.get_dialog().is_top_dialog() or Mgr.get("active_input_field") or Menu.is_menu_shown():
            return False

        return True

    def destroy(self):

        DialogScrollPane.destroy(self)

        Mgr.remove_task("check_candidate_filebutton")

        self._path_handler = None
        self._file_selection_handler = None
        self._file_command = None
        self._filename_field.destroy()
        self._filename_field = None
        self._btns = None

        FileButton.set_selected_filebutton(None)

    def get_filename_field(self):

        return self._filename_field

    def __update_directory_list(self, update_layout=True):

        directory_path = self._current_path
        filenames = []

        for ext in self._extensions.split(";"):
            pattern = "*" if ext == "*" else f"*.{ext}"
            names = glob(Filename(join(directory_path, pattern)).to_os_specific_w())
            filenames.extend(Filename.from_os_specific_w(name).get_basename() for name in names
                             if not Filename(name).is_directory())

        dirlist = self._file_sys.scan_directory(directory_path)

        self._path_handler(directory_path)
        subdirnames = []

        if dirlist:
            for item in dirlist:
                if item.is_directory():
                    subdirnames.append(item.get_filename().get_basename())

        self._btns = btns = []
        sizer = self._btn_sizer
        sizer.clear(destroy_cells=True)

        FileButton.set_selected_filebutton(None)

        f = lambda x, y: (x.casefold() > y.casefold()) - (x.casefold() < y.casefold())

        for name in sorted(subdirnames, key=cmp_to_key(f)):
            path = join(directory_path, name)
            command = lambda p=path: self.set_directory(p)
            btns.append(FileButton(self, name, command=command, is_dir=True))

        for name in sorted(filenames, key=cmp_to_key(f)):
            btns.append(FileButton(self, name, self._file_selection_handler, self._file_command))

        for btn in btns:
            sizer.add(btn)

        if update_layout:
            self.update_layout()

    def set_extensions(self, extensions):

        if self._extensions != extensions:
            self._extensions = extensions
            self.__update_directory_list()

    def set_directory(self, directory_path):

        if self._current_path != directory_path:
            self._current_path = directory_path
            self.__update_directory_list()

    def get_directory(self):

        return self._current_path

    def __rename_file(self, filename):

        button = FileButton.selected_btn
        old_name = button.get_filename()

        if filename.strip() in ("", old_name):
            return

        old_path = Filename(join(self._current_path, old_name)).to_os_specific()
        new_path = Filename(join(self._current_path, filename)).to_os_specific()
        file_type = "folder" if button.is_directory() else "file"

        try:
            if filename.lower() != old_name.lower() and os.path.exists(new_path):
                MessageDialog(title=f"Rename {file_type}",
                              message="File or folder with that name already exists!",
                              choices="ok",
                              icon_id="icon_exclamation")
                return
            else:
                os.rename(old_path, new_path)
        except:
            MessageDialog(title=f"Rename {file_type}",
                          message=f"Could not rename {file_type}!",
                          choices="ok",
                          icon_id="icon_exclamation")
            return

        button.set_filename(filename)

        if file_type == "folder":
            dir_path = join(self._current_path, filename)
            button.command = lambda: self.set_directory(dir_path)

        self.update_layout()

        return filename

    def remove_file(self, button):

        filename = button.get_filename()
        path = Filename(join(self._current_path, filename)).to_os_specific()
        file_type = "folder" if button.is_directory() else "file"
        command = os.rmdir if button.is_directory() else os.remove

        try:
            command(path)
        except:
            MessageDialog(title=f"Delete {file_type}",
                          message=f"Could not delete {file_type}!",
                          choices="ok",
                          icon_id="icon_exclamation")
            return False

        self._btn_sizer.remove_cell(button.sizer_cell)
        self._btns.remove(button)
        button.destroy()
        self.update_layout()

        return True

    def create_subdirectory(self):

        dirlist = self._file_sys.scan_directory(self._current_path)

        if dirlist:
            names = (f"_{name[10:]}"
                for name in (item.get_filename().get_basename() for item in dirlist)
                if name.lower().startswith("new folder"))
            dir_name = get_unique_name("_", names)
            dir_name = dir_name.replace("_", "New folder", 1)
        else:
            dir_name = "New folder"

        dir_path = join(self._current_path, dir_name)
        path = Filename(dir_path).to_os_specific()

        try:
            os.mkdir(path)
        except:
            MessageDialog(title="Create folder",
                          message="Could not create folder!",
                          choices="ok",
                          icon_id="icon_exclamation")
            return

        command = lambda: self.set_directory(dir_path)
        btn = FileButton(self, dir_name, command=command, is_dir=True)
        self._btns.append(btn)
        self._btn_sizer.add(btn)
        self.update_layout()
        w_virt = self.virtual_size[0]
        self.scrollthumb.set_offset(w_virt)
        btn.show_name_field()


class FileDialog(Dialog):

    _file_listener = DirectObject()

    @classmethod
    def accept_extra_dialog_events(cls):

        def show_filename_field():

            btn = FileButton.selected_btn

            if btn:
                btn.show_name_field()

        def remove_file():

            btn = FileButton.selected_btn
            shift_down = Mgr.get("mouse_watcher").is_button_down("shift")

            if btn and shift_down:
                btn.remove_file()

        cls._file_listener.accept("gui_f2", show_filename_field)
        cls._file_listener.accept("gui_delete", remove_file)

    @classmethod
    def ignore_extra_dialog_events(cls):

        cls._file_listener.ignore("gui_f2")
        cls._file_listener.ignore("gui_delete")

    def __init__(self, title="", choices="okcancel", ok_alias="OK", on_yes=None,
                 on_no=None, on_cancel=None, file_op="read", incr_filename=False,
                 file_types=("All types|*",), default_filename="", extra_button_data=()):

        def command():

            if on_yes:
                on_yes(Filename(join(self._current_path, self._filename)).to_os_specific())

        if file_op == "write" and incr_filename:
            w = Skin.options["file_dialog_incr_save_btn_width"]
            extra_button_data += (("+", "Save incrementally", self.__save_incrementally, w, 1.),)

        Dialog.__init__(self, title, choices, ok_alias, command, on_no, on_cancel,
                        extra_button_data)

        widgets = Skin.layout.create(self, "file")
        pane_cell = widgets["placeholders"]["pane"]
        self._fields = fields = widgets["fields"]
        comboboxes = widgets["comboboxes"]
        btns = widgets["buttons"]

        self.accept_extra_dialog_events()

        self._current_path = ""
        self._filename = ""

        self._file_op = file_op
        self._extensions = file_types[0].split("|")[1]

        self._dir_combobox = dir_combobox = comboboxes["directory"]
        val_id = "dir_path"
        handler = lambda *args: self.__handle_dir_path(args[1])
        field = dir_combobox.set_input_field(val_id, "string", handler)
        field.set_input_parser(self.__parse_dir_input)
        field.set_value_parser(self.__parse_dir_path)
        fields["dir_path"] = field

        self._dir_up_btn = up_btn = btns["dir_up"]  # DialogToolButton
        up_btn.command = self.__directory_up

        self._file_pane = pane = FilePane(self, self.__set_current_path, self.set_filename,
                                          lambda: self.close(answer="yes"), self._extensions,
                                          default_filename)
        pane_cell.object = pane.frame

        self._new_dir_btn = new_btn = btns["new_dir"]  # DialogToolButton
        new_btn.command = self._file_pane.create_subdirectory

        file_sys = VirtualFileSystem.get_global_ptr()
        cwd = file_sys.get_cwd()
        homedir = Filename.get_home_directory()
        self._recent_dirs = [cwd.get_fullpath(), homedir.get_fullpath()]

        def set_path(item_id, path):

            if self._current_path != path:

                if not Filename(path).exists():
                    command = lambda: self.__remove_dir_path(item_id, path)
                    MessageDialog(title="Invalid folder",
                                  message="The chosen folder does not exist."
                                          "\n\nDo you want to remove it from the list?",
                                  choices="yesno", on_yes=command,
                                  icon_id="icon_exclamation")
                    return

                dir_combobox.select_item(item_id)
                fields["dir_path"].set_value(path, handle_value=True)
                path_up = Filename(path).get_dirname()

                if path_up == "/":
                    up_btn.enable(False)
                else:
                    up_btn.enable()
                    tooltip_text = f'Up to "{Filename(path_up).to_os_specific()}"'
                    up_btn.tooltip_text = tooltip_text

        dir_combobox.add_item("cwd", cwd.to_os_specific(),
            lambda: set_path("cwd", cwd.get_fullpath()), persistent=True)
        recent_dirs = GD["config"]["recent_dirs"]
        self._recent_dirs.extend(recent_dirs)

        for i, path in enumerate(recent_dirs):
            item_id = str(i)
            command = lambda i=item_id, p=path: set_path(i, p)
            dir_combobox.add_item(item_id, Filename(path).to_os_specific(),
                command, persistent=True)

        dir_combobox.add_item("homedir", homedir.to_os_specific(),
            lambda: set_path("homedir", homedir.get_fullpath()), persistent=True, update=True)

        field = fields["filename"]
        field.value_id = "filename"
        field.value_type = "string"
        field.set_on_key_enter(lambda: self.close(answer="yes"))
        field.set_on_key_escape(self.close)
        field.set_input_parser(self.__parse_filename_input)
        field.set_value_parser(self.__parse_filename)

        type_combobox = comboboxes["file_type"]

        def set_extensions(item_id, extensions):

            if self._extensions != extensions:
                type_combobox.select_item(item_id)
                self._extensions = extensions
                pane.set_extensions(extensions)

        for i, type_data in enumerate(file_types):
            type_descr, extensions = type_data.split("|")
            item_id = str(i)
            item_text = f'{type_descr} ({";".join(f"*.{ext}" for ext in extensions.split(";"))})'
            command = lambda i=item_id, e=extensions: set_extensions(i, e)
            type_combobox.add_item(item_id, item_text, command)

        type_combobox.update_popup_menu()

        self.finalize()

        def task():

            self._fields["dir_path"].set_text("")
            path = Filename(self._current_path).to_os_specific()
            self._fields["dir_path"].set_text(path)

            if default_filename:
                self._filename = filename = Filename(default_filename).get_basename()
                self._fields["filename"].set_text(filename)

            if file_op == "write":
                self._fields["filename"].on_left_down()
                self._fields["filename"]._on_left_up()

        PendingTasks.add(task, "update_dir_path")

    def __save_incrementally(self):

        path = self.get_current_filename()

        if path.endswith("/"):
            return

        dirname, tail = os.path.split(Filename(path).to_os_specific())
        basename, ext = os.path.splitext(tail)
        names = [b for b, e in (os.path.splitext(name)
                 for name in os.listdir(dirname)) if e.lower() == ext.lower()]

        if basename[-1].isdigit():
            names.append(basename)

        namestring = "\n".join(names)
        new_name = get_incremented_filename(basename, namestring) + ext
        self.set_filename(new_name)
        self.close(answer="yes")

    def close(self, answer=""):

        def add_recent_directory():

            config_data = GD["config"]
            recent_dirs = config_data["recent_dirs"]
            path = self._current_path

            if path in self._recent_dirs:
                return

            recent_dirs.append(path)

            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

        def command():

            if answer == "yes":
                add_recent_directory()

            self.ignore_extra_dialog_events()
            self._dir_combobox = None
            self._fields = None
            self._dir_up_btn = None
            self._new_dir_btn = None
            self._file_pane = None

            Dialog.close(self, answer)

        if answer == "yes":

            path = join(self._current_path, self._filename)

            if self._file_op == "read":
                try:
                    with open(Filename(path).to_os_specific(), "r"): pass
                except IOError:
                    MessageDialog(title="Open file",
                                  message="Could not open file!",
                                  choices="ok",
                                  icon_id="icon_exclamation")
                    return
            elif self._file_op == "write":
                try:
                    with open(Filename(path).to_os_specific(), "r"): pass
                    MessageDialog(title="Confirm overwrite file",
                                  message="File already exists!\n\nOverwrite?",
                                  choices="yesno", on_yes=command,
                                  icon_id="icon_exclamation")
                    return
                except IOError:
                    try:
                        with open(Filename(path).to_os_specific(), "w"): pass
                    except IOError:
                        MessageDialog(title="Write file",
                                      message="Could not write file!",
                                      choices="ok",
                                      icon_id="icon_exclamation")
                        return

        command()

    def __set_current_path(self, path):

        self._current_path = path
        self._fields["dir_path"].set_text(Filename(path).to_os_specific())
        path_up = Filename(path).get_dirname()
        up_btn = self._dir_up_btn

        if path_up == "/":
            up_btn.enable(False)
        else:
            up_btn.enable()
            tooltip_text = f'Up to "{Filename(path_up).to_os_specific()}"'
            up_btn.tooltip_text = tooltip_text

    def set_filename(self, filename):

        self._fields["filename"].set_text(filename)
        self._filename = filename

    def __directory_up(self):

        path = Filename(self._current_path).get_dirname()

        if path != "/":
            self._file_pane.set_directory(path)

    def __parse_dir_input(self, input_text):

        path_obj = Filename.from_os_specific(input_text.strip())
        path_obj.make_true_case()
        path = path_obj.get_fullpath()

        if path != "/" and path_obj.exists() and path_obj.is_directory() \
                and path_obj.is_fully_qualified() and self._current_path != path:
            return path

    def __parse_dir_path(self, path):

        return Filename(path).to_os_specific()

    def __parse_filename_input(self, input_text):

        path_obj = Filename(join(self._current_path, input_text.strip()))

        if input_text and self._extensions != "*" and not path_obj.get_extension():
            extension = self._extensions.split(";")[0]
            path_obj.set_extension(extension)

        return path_obj.get_basename()

    def __parse_filename(self, filename):

        self._filename = filename

        return filename

    def __handle_dir_path(self, dir_path):

        self._file_pane.set_directory(dir_path)

    def __remove_dir_path(self, item_id, dir_path):

        config_data = GD["config"]
        recent_dirs = config_data["recent_dirs"]
        recent_dirs.remove(dir_path)

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

        self._dir_combobox.remove_item(item_id)
        self._recent_dirs.remove(dir_path)

    def get_current_filename(self):

        return join(self._current_path, self._filename)

    def update_widget_positions(self):

        self._file_pane.update_quad_pos()
        x, y = self._file_pane.get_pos(from_root=True)
        FileButtonInputField.set_ref_node_pos((-x, 0, y))
