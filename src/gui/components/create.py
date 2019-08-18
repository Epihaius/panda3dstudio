from ..base import *
from .props.base import ObjectTypes


class CreationManager:

    def __init__(self, menubar):

        creation_data = {}

        def get_handler(object_type):

            def handler():

                if GD["active_obj_level"] != "top":
                    GD["active_obj_level"] = "top"
                    Mgr.update_app("active_obj_level")

                if not GD["active_creation_type"]:
                    GD["active_creation_type"] = object_type
                    Mgr.enter_state("creation_mode")
                elif GD["active_creation_type"] != object_type:
                    Mgr.update_app("interactive_creation", "changed")
                    GD["active_creation_type"] = object_type
                    Mgr.enter_state("creation_mode")
                    Mgr.update_app("selected_obj_types", (object_type,))
                    Mgr.update_app("interactive_creation", "started")
                    if GD["snap"]["on"]["creation"]:
                        Mgr.update_app("status", ["create", object_type, "snap_idle"])
                    else:
                        Mgr.update_app("status", ["create", object_type, "idle"])

            return handler

        for object_type, object_type_name in ObjectTypes.get_types().items():
            handler = get_handler(object_type)
            creation_data[object_type] = {"name": object_type_name, "handler": handler}

        menu = menubar.add_menu("create", "Create")

        data = creation_data["plane"]
        menu.add("plane", f'Create {data["name"]}', data["handler"])

        obj_types = ("box", "sphere", "cylinder", "torus")
        accelerators = ("b", "s", "c", "t")
        mod_key_codes = GD["mod_key_codes"]
        mod_code = mod_key_codes["shift"] | mod_key_codes["ctrl"]
        hotkeys = [(accel, mod_code) for accel in accelerators]

        for obj_type, accel, hotkey in zip(obj_types, accelerators, hotkeys):
            data = creation_data[obj_type]
            menu.add(obj_type, f'Create {data["name"]}', data["handler"])
            menu.set_item_hotkey(obj_type, hotkey, f"Shift+Ctrl+{accel.upper()}")

        data = creation_data["cone"]
        menu.add("cone", f'Create {data["name"]}', data["handler"])

        menu.add("sep0", item_type="separator")

        obj_types = ("tex_projector", "dummy")
        accelerators = ("p", "d")
        hotkeys = [(accel, mod_code) for accel in accelerators]

        for obj_type, accel, hotkey in zip(obj_types, accelerators, hotkeys):
            data = creation_data[obj_type]
            menu.add(obj_type, f'Create {data["name"]}', data["handler"])
            menu.set_item_hotkey(obj_type, hotkey, f"Shift+Ctrl+{accel.upper()}")

        data = creation_data["point_helper"]
        menu.add("point_helper", f'Create {data["name"]}', data["handler"])

    def setup(self):

        def enter_creation_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_create_objects")
            Mgr.do("enable_gui")

            if prev_state_id in ("selection_mode", "checking_creation_start", "processing"):
                task = lambda: Mgr.do("display_next_obj_color")
                PendingTasks.add(task, "display_next_obj_color", "ui")

            if not active:
                GD["snap"]["type"] = "creation"
                Mgr.update_locally("object_snap", "enable", True, False)

        def exit_creation_mode(next_state_id, active):

            if not active:
                GD["snap"]["type"] = ""
                Mgr.update_locally("object_snap", "enable", False, False)

        add_state = Mgr.add_state
        add_state("creation_mode", -10, enter_creation_mode, exit_creation_mode)
        add_state("checking_creation_start", -11, lambda prev_state_id, active:
                  Mgr.do("enable_gui", False))
