from ..base import *
from .props.base import ObjectTypes


class CreationManager(object):

    def __init__(self, menubar):

        creation_data = {}

        def get_handler(object_type):

            def handler():

                if not Mgr.get_global("active_creation_type"):
                    Mgr.set_global("active_creation_type", object_type)
                    Mgr.enter_state("creation_mode")
                elif Mgr.get_global("active_creation_type") != object_type:
                    Mgr.update_app("creation", "changed")
                    Mgr.set_global("active_creation_type", object_type)
                    Mgr.enter_state("creation_mode")
                    Mgr.update_app("selected_obj_type", object_type)
                    Mgr.update_app("creation", "started")
                    Mgr.update_app("status", "create", object_type, "idle")

            return handler

        for object_type, object_type_name in ObjectTypes.get_types().iteritems():
            handler = get_handler(object_type)
            creation_data[object_type] = {"name": object_type_name, "handler": handler}

        menubar.add_menu("create", "Create")

        obj_types = ("box", "sphere", "cylinder")
        accelerators = ("B", "S", "C")
        mod_code = wx.MOD_SHIFT | wx.MOD_CONTROL
        hotkeys = [(ord(accel), mod_code) for accel in accelerators]

        for obj_type, accel, hotkey in zip(obj_types, accelerators, hotkeys):
            data = creation_data[obj_type]
            menubar.add_menu_item("create", obj_type, "Create %s\tSHIFT+CTRL+%s" % (data["name"], accel),
                                  data["handler"], hotkey)

        menubar.add_menu_item_separator("create")

        obj_types = ("dummy", "tex_projector")
        accelerators = ("D", "P")
        hotkeys = [(ord(accel), mod_code) for accel in accelerators]

        for obj_type, accel, hotkey in zip(obj_types, accelerators, hotkeys):
            data = creation_data[obj_type]
            menubar.add_menu_item("create", obj_type, "Create %s\tSHIFT+CTRL+%s" % (data["name"], accel),
                                  data["handler"], hotkey)

    def setup(self):

        def enter_creation_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (220, 220, 100))
            Mgr.do("enable_components")

            if prev_state_id in ("selection_mode", "checking_creation_start"):
                Mgr.do("display_next_obj_color")

        add_state = Mgr.add_state
        add_state("creation_mode", -10, enter_creation_mode)
        add_state("checking_creation_start", -11, lambda prev_state_id, is_active:
                  Mgr.do("disable_components", show=False))
