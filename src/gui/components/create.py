from ..base import *
from .props.base import ObjectTypes


class CreationManager(object):

    def __init__(self, menubar):

        creation_data = {}

        def get_handler(object_type):

            def handler():

                if not GlobalData["active_creation_type"]:
                    GlobalData["active_creation_type"] = object_type
                    Mgr.enter_state("creation_mode")
                elif GlobalData["active_creation_type"] != object_type:
                    Mgr.update_app("interactive_creation", "changed")
                    GlobalData["active_creation_type"] = object_type
                    Mgr.enter_state("creation_mode")
                    Mgr.update_app("selected_obj_types", (object_type,))
                    Mgr.update_app("interactive_creation", "started")
                    Mgr.update_app("status", ["create", object_type, "idle"])

            return handler

        for object_type, object_type_name in ObjectTypes.get_types().items():
            handler = get_handler(object_type)
            creation_data[object_type] = {"name": object_type_name, "handler": handler}

        menu = menubar.add_menu("create", "Create")

        data = creation_data["plane"]
        menu.add("plane", "Create {}".format(data["name"]), data["handler"])

        obj_types = ("box", "sphere", "cylinder", "torus")
        accelerators = ("b", "s", "c", "t")
        mod_key_codes = GlobalData["mod_key_codes"]
        mod_code = mod_key_codes["shift"] | mod_key_codes["ctrl"]
        hotkeys = [(accel, mod_code) for accel in accelerators]

        for obj_type, accel, hotkey in zip(obj_types, accelerators, hotkeys):
            data = creation_data[obj_type]
            menu.add(obj_type, "Create {}".format(data["name"]), data["handler"])
            menu.set_item_hotkey(obj_type, "SHIFT+CTRL+{}".format(accel.upper()), hotkey)

        data = creation_data["cone"]
        menu.add("cone", "Create {}".format(data["name"]), data["handler"])

        menu.add("sep0", item_type="separator")

        obj_types = ("tex_projector", "dummy")
        accelerators = ("p", "d")
        hotkeys = [(accel, mod_code) for accel in accelerators]

        for obj_type, accel, hotkey in zip(obj_types, accelerators, hotkeys):
            data = creation_data[obj_type]
            menu.add(obj_type, "Create {}".format(data["name"]), data["handler"])
            menu.set_item_hotkey(obj_type, "SHIFT+CTRL+{}".format(accel.upper()), hotkey)

        data = creation_data["point_helper"]
        menu.add("point_helper", "Create {}".format(data["name"]), data["handler"])

    def setup(self):

        def enter_creation_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_create_objects")
            Mgr.do("enable_gui")

            if prev_state_id in ("selection_mode", "checking_creation_start", "processing"):
                task = lambda: Mgr.do("display_next_obj_color")
                PendingTasks.add(task, "display_next_obj_color", "ui")

        add_state = Mgr.add_state
        add_state("creation_mode", -10, enter_creation_mode)
        add_state("checking_creation_start", -11, lambda prev_state_id, is_active:
                  Mgr.do("enable_gui", False))
