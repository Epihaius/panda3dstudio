from ..base import *
from .props.base import ObjectTypes


class CreationManager(object):

    def __init__(self):

        self._data = {}

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
            self._data[object_type] = {"name":object_type_name, "handler":handler}

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

    def get_data(self):

        return self._data
