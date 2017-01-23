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
                    Mgr.update_app("status", "create", object_type, "idle")

            return handler

        for object_type, object_type_name in ObjectTypes.get_types().iteritems():
            handler = get_handler(object_type)
            creation_data[object_type] = {"name": object_type_name, "handler": handler}

        menubar.add_menu("create", "Create")

        obj_types = ("box", "sphere", "cylinder", "torus")
        accelerators = ("B", "S", "C", "T")
        mod_code = wx.MOD_SHIFT | wx.MOD_CONTROL
        hotkeys = [(ord(accel), mod_code) for accel in accelerators]

        for obj_type, accel, hotkey in zip(obj_types, accelerators, hotkeys):
            data = creation_data[obj_type]
            menubar.add_menu_item("create", obj_type, "Create %s\tSHIFT+CTRL+%s" % (data["name"], accel),
                                  data["handler"], hotkey)

        data = creation_data["cone"]
        menubar.add_menu_item("create", "cone", "Create %s" % data["name"], data["handler"])

        menubar.add_menu_item_separator("create")

        obj_types = ("tex_projector", "dummy")
        accelerators = ("P", "D")
        hotkeys = [(ord(accel), mod_code) for accel in accelerators]

        for obj_type, accel, hotkey in zip(obj_types, accelerators, hotkeys):
            data = creation_data[obj_type]
            menubar.add_menu_item("create", obj_type, "Create %s\tSHIFT+CTRL+%s" % (data["name"], accel),
                                  data["handler"], hotkey)

        data = creation_data["point_helper"]
        menubar.add_menu_item("create", "point_helper", "Create %s" % data["name"], data["handler"])

    def setup(self):

        def enter_creation_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (220, 220, 100))
            Mgr.do("enable_components")

            if prev_state_id in ("selection_mode", "checking_creation_start", "processing"):
                Mgr.do("display_next_obj_color")

        add_state = Mgr.add_state
        add_state("creation_mode", -10, enter_creation_mode)
        add_state("checking_creation_start", -11, lambda prev_state_id, is_active:
                  Mgr.do("disable_components", show=False))
