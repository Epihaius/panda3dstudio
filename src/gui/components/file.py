from ..base import *
from ..dialog import *
from .import_dialog import ImportDialog


class FileManager(object):

    def __init__(self, menubar):

        file_data = {}

        handlers = {
            "new": self.__reset_scene,
            "open": self.__load_scene,
            "save": self.__save_scene,
            "save_as": self.__save_scene_as,
            "save_incr": self.__save_scene_incrementally,
            "export": self.__prepare_export,
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

        for file_op, handler in handlers.items():
            descr = descriptions[file_op]
            file_data[file_op] = {"descr": descr, "handler": handler}

        menu = menubar.add_menu("file", "File")

        file_ops = ("new", "open", "save")
        accelerators = ("n", "o", "s")
        mod_code = GlobalData["mod_key_codes"]["ctrl"]
        hotkeys = [(accel, mod_code) for accel in accelerators]

        for file_op, accel, hotkey in zip(file_ops, accelerators, hotkeys):
            data = file_data[file_op]
            menu.add(file_op, data["descr"], data["handler"])
            menu.set_item_hotkey(file_op, hotkey, "Ctrl+{}".format(accel.upper()))

        file_op = "save_as"
        data = file_data[file_op]
        menu.add(file_op, data["descr"], data["handler"])
        hotkey = ("s", mod_code | GlobalData["mod_key_codes"]["alt"])
        menu.set_item_hotkey(file_op, hotkey, "Ctrl+Alt+S")

        file_op = "save_incr"
        data = file_data[file_op]
        menu.add(file_op, data["descr"], data["handler"])

        menu.add("sep0", item_type="separator")

        file_ops = ("export", "import")

        for file_op in file_ops:
            data = file_data[file_op]
            menu.add(file_op, data["descr"], data["handler"])

        menu.add("sep1", item_type="separator")

        menu.add("exit", "Exit", self.on_exit)
        menu.set_item_hotkey("exit", None, "Alt+F4")

        Mgr.add_app_updater("export", self.__update_export)
        Mgr.add_app_updater("import", self.__import)
        Mgr.add_app_updater("scene_label", self.__set_scene_label)
        Mgr.add_app_updater("unsaved_scene", self.__set_scene_as_unsaved)
        Mgr.add_app_updater("scene_load_error", self.__handle_load_error)

    def __reset_scene(self):

        def task():

            reset = lambda: Mgr.update_app("scene", "reset")

            if GlobalData["unsaved_scene"]:
                on_yes = lambda: self.__save_scene(on_save=reset)
                MessageDialog(title="Save changes",
                              message="Save changes to current scene before resetting?",
                              choices="yesnocancel", on_yes=on_yes, on_no=reset,
                              icon_id="icon_exclamation")
            else:
                reset()

        Mgr.do("close_aux_viewport", task)

    def __set_scene_label(self, label):

        Mgr.do("set_scene_label", label)

    def __load_scene(self):

        def load():

            def on_yes(filename):

                Mgr.update_app("scene", "load", Filename.from_os_specific(filename).get_fullpath())
                Mgr.do("set_scene_label", filename)

            open_file = GlobalData["open_file"]
            default_filename = open_file if open_file else ""
            FileDialog(title="Open scene",
                       ok_alias="Open",
                       file_op="read",
                       on_yes=on_yes,
                       file_types=("Panda3D Studio|p3ds", "All types|*"),
                       default_filename=default_filename)

        def task():

            if GlobalData["unsaved_scene"]:
                on_yes = lambda: self.__save_scene(on_save=load)
                MessageDialog(title="Save changes",
                              message="Save changes to current scene before loading?",
                              choices="yesnocancel", on_yes=on_yes, on_no=load,
                              icon_id="icon_exclamation")
            else:
                load()

        Mgr.do("close_aux_viewport", task)

    def __handle_load_error(self, filename, error_type):

        if error_type == "read":
            MessageDialog(title="Error loading scene",
                          message="The following file could not be read:\n\n" \
                                  + Filename(filename).to_os_specific(),
                          choices="ok",
                          icon_id="icon_exclamation")
        elif error_type == "id":
            MessageDialog(title="Error loading scene",
                          message="The following file does not appear\nto be a valid scene file:\n\n" \
                                  + Filename(filename).to_os_specific(),
                          choices="ok",
                          icon_id="icon_exclamation")

    def __save_scene(self, on_save=None):

        open_file = GlobalData["open_file"]

        if open_file:

            if not GlobalData["unsaved_scene"]:
                return

            Mgr.update_app("scene", "save", open_file)
            Mgr.do("set_scene_label", Filename(open_file).to_os_specific())

            if on_save:
                on_save()

            return

        SaveAsDialog(on_save)

    def __save_scene_as(self, on_save=None):

        SaveAsDialog(on_save)

    def __save_scene_incrementally(self):

        open_file = GlobalData["open_file"]

        if not open_file:
            return

        dirname, tail = os.path.split(Filename(open_file).to_os_specific())
        basename, ext = os.path.splitext(tail)
        names = [b for b, e in (os.path.splitext(name) for name in os.listdir(dirname))
                 if e.lower() == ext.lower()]
        namestring = "\n".join(names)
        filename = get_incremented_filename(basename, namestring)
        path = os.path.join(dirname, filename + ext)

        Mgr.update_app("scene", "save", Filename.from_os_specific(path).get_fullpath())
        Mgr.do("set_scene_label", path)

    def __set_scene_as_unsaved(self):

        open_file = GlobalData["open_file"]
        scene_label = (Filename(open_file).to_os_specific() if open_file else "New")

        if GlobalData["unsaved_scene"]:
            scene_label += "*"

        Mgr.do("set_scene_label", scene_label)

    def __prepare_export(self):

        Mgr.update_remotely("export", "prepare")

    def __update_export(self, update_type, *args):

        if update_type == "confirm_entire_scene":
            on_yes = lambda: self.__update_export("export")
            MessageDialog(title="No selection",
                          message="No objects selected.\n\nExport entire scene?",
                          choices="yesno", on_yes=on_yes)
        elif update_type == "empty_scene":
            MessageDialog(title="Empty scene",
                          message="There are no objects to export.",
                          choices="ok",
                          icon_id="icon_exclamation")
        elif update_type == "export":
            # TODO: implement and show ExportDialog
            on_yes = lambda filename: Mgr.update_remotely("export", "export", filename)
            open_file = GlobalData["open_file"]
            default_filename = Filename(open_file).get_dirname() + "/" if open_file else ""
            FileDialog(title="Export scene",
                       ok_alias="Export",
                       file_op="write",
                       on_yes=on_yes,
                       file_types=("Panda3D model files|bam", "Wavefront files|obj", "All types|*"),
                       default_filename=default_filename)

    def __prepare_import(self):

        on_yes = lambda filename: Mgr.update_remotely("import", "prepare", filename)
        # TODO: show MessageDialog "Preparing import..." without OK button
        open_file = GlobalData["open_file"]
        default_filename = Filename(open_file).get_dirname() + "/" if open_file else ""
        FileDialog(title="Import scene",
                   ok_alias="Import",
                   file_op="read",
                   on_yes=on_yes,
                   file_types=("Panda3D model files|bam;egg;egg.pz",
                               "Wavefront files|obj", "All types|*"),
                   default_filename=default_filename)

    def __import(self, obj_data, new_obj_names):

        ImportDialog(obj_data, new_obj_names)

    def on_exit(self):

        if Dialog.get_dialogs():
            return

        Mgr.get("base").messenger.send("focus_loss")

        def on_exit():

            exit = lambda: Mgr.get("base").userExit()

            if GlobalData["unsaved_scene"]:
                on_yes = lambda: self.__save_scene(on_save=exit)
                MessageDialog(title="Save changes",
                              message="Save changes to current scene before exiting?",
                              choices="yesnocancel", on_yes=on_yes, on_no=exit,
                              icon_id="icon_exclamation")
            else:
                exit()

        Mgr.do("close_aux_viewport", on_exit)


class SaveAsDialog(FileDialog):

    def __init__(self, on_save=None):

        def on_yes(filename):

            Mgr.update_app("scene", "save", Filename.from_os_specific(filename).get_fullpath())
            Mgr.do("set_scene_label", filename)

            if on_save:
                on_save()

        open_file = GlobalData["open_file"]
        default_filename = open_file if open_file else ""

        FileDialog.__init__(self, title="Save scene as", choices="okcancel", ok_alias="Save",
                            on_yes=on_yes, on_no=None, file_op="write", incr_filename=True,
                            file_types=("Panda3D Studio|p3ds", "All types|*"),
                            default_filename=default_filename)
