from ..base import *
from .props.base import ObjectTypes


class CreationButtons(BaseObject):

    def __init__(self):

        self._btns = []
        self._active_btn = ""

        def get_handler(object_type_id):

            def handler():

                if self._active_btn == "create_%s" % object_type_id:
                    Mgr.enter_state("selection_mode")
                elif self._active_btn:
                    Mgr.update_app("creation", "changed")
                    Mgr.set_global("active_creation_type", object_type_id)
                    Mgr.update_app("selected_obj_type", object_type_id)
                    Mgr.update_app("creation", "started")
                    Mgr.update_app("status", "create", object_type_id, "idle")
                else:
                    Mgr.set_global("active_creation_type", object_type_id)
                    Mgr.enter_state("creation_mode")

            return handler

        for object_type_id, object_type_name in ObjectTypes.get_types().iteritems():
            btn_id = "create_%s" % object_type_id
            label = "Create %s" % object_type_name
            icon_path = os.path.join(
                GFX_PATH, "icon_" + object_type_id + ".png")
            btn_props = (label, icon_path)
            Mgr.do("add_deepshelf_btn", btn_id,
                   btn_props, get_handler(object_type_id))

        Mgr.add_app_updater("creation", self.__update_creation)

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

    def __update_creation(self, creation_status):

        self.deactivate()

        if creation_status == "started":
            creation_type = Mgr.get_global("active_creation_type")
            self._active_btn = "create_%s" % creation_type
            Mgr.do("toggle_deepshelf_btn", self._active_btn)

    def deactivate(self):

        if self._active_btn:
            Mgr.do("toggle_deepshelf_btn", self._active_btn)
            self._active_btn = ""
