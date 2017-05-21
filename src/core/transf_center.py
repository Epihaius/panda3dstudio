from .base import *


class TransformCenterManager(BaseObject):

    def __init__(self):

        self._tc_obj = None
        self._tc_obj_picked = None
        self._tc_transformed = False
        self._user_obj_id = None

        GlobalData.set_default("transf_center_type", "adaptive")

        self._pixel_under_mouse = VBase4()
        Mgr.expose("adaptive_transf_center_type", self.__get_adaptive_transf_center)
        Mgr.expose("transf_center_obj", self.__get_transform_center_object)
        Mgr.expose("transf_center_pos", self.__get_transform_center_pos)
        Mgr.add_app_updater("transf_center", self.__set_transform_center)

        add_state = Mgr.add_state
        add_state("transf_center_picking_mode", -80,
                  self.__enter_picking_mode, self.__exit_picking_mode)

        def exit_transf_center_picking_mode():

            Mgr.exit_state("transf_center_picking_mode")

        bind = Mgr.bind_state
        bind("transf_center_picking_mode", "pick transf center -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("transf_center_picking_mode",
             "pick transf center", "mouse1", self.__pick)
        bind("transf_center_picking_mode", "exit transf center picking", "escape",
             exit_transf_center_picking_mode)
        bind("transf_center_picking_mode", "cancel transf center picking", "mouse3-up",
             exit_transf_center_picking_mode)

        status_data = GlobalData["status_data"]
        mode = "Pick transform center"
        info = "LMB to pick object; RMB to end"
        status_data["pick_transf_center"] = {"mode": mode, "info": info}

    def __get_adaptive_transf_center(self):

        if GlobalData["active_obj_level"] != "top" or len(Mgr.get("selection")) > 1:
            return "sel_center"

        return "pivot"

    def __get_transform_center_object(self, check_valid=False):

        if self._tc_obj and check_valid:

            cs_type = GlobalData["coord_sys_type"]
            tc_type = GlobalData["transf_center_type"]

            if tc_type == "adaptive":
                tc_type = self.__get_adaptive_transf_center()

            if tc_type == "pivot" or (cs_type == "local" and tc_type == "cs_origin"):
                if self._tc_obj not in Mgr.get("selection", "top"):
                    self._tc_obj = None

        return self._tc_obj

    def __set_transform_center(self, tc_type, obj=None):

        GlobalData["transf_center_type"] = tc_type

        self._tc_obj = obj

        if tc_type == "adaptive":
            _tc_type = self.__get_adaptive_transf_center()
        else:
            _tc_type = tc_type

        if _tc_type == "pivot" and not obj:

            if GlobalData["coord_sys_type"] == "local":
                self._tc_obj = Mgr.get("coord_sys_obj", check_valid=True)

            if not self._tc_obj:
                self._tc_obj = Mgr.get("selection").get_toplevel_object(get_group=True)

        if _tc_type != "object":

            self._tc_obj_picked = None
            user_obj = Mgr.get("object", self._user_obj_id)
            self._user_obj_id = None

            if user_obj:
                user_obj.get_name(as_object=True).remove_updater("transf_center")

        tc_pos = self.__get_transform_center_pos()
        Mgr.do("set_transf_gizmo_pos", tc_pos)

    def __get_transform_center_pos(self):

        tc_type = GlobalData["transf_center_type"]

        if tc_type == "adaptive" and self.__get_adaptive_transf_center() == "sel_center":
            pos = Mgr.get("selection").get_center_pos()
        elif self._tc_obj:
            pos = self._tc_obj.get_pivot().get_pos(self.world)
        elif tc_type == "cs_origin":
            pos = Mgr.get(("grid", "origin")).get_pos()
        else:
            pos = Mgr.get("selection").get_center_pos()

        return pos

    def __enter_picking_mode(self, prev_state_id, is_active):

        if GlobalData["active_obj_level"] != "top":
            GlobalData["active_obj_level"] = "top"
            Mgr.update_app("active_obj_level")

        Mgr.add_task(self.__update_cursor, "update_tc_picking_cursor")
        Mgr.update_app("status", "pick_transf_center")

    def __exit_picking_mode(self, next_state_id, is_active):

        if not is_active:

            if not self._tc_obj_picked:
                tc_type_prev = GlobalData["transf_center_type"]
                obj = self._tc_obj
                name = obj.get_name(as_object=True) if obj else None
                Mgr.update_locally("transf_center", tc_type_prev, obj)
                Mgr.update_remotely("transf_center", tc_type_prev, name)

            self._tc_obj_picked = None

        self._pixel_under_mouse = VBase4() # force an update of the cursor
                                           # next time self.__update_cursor()
                                           # is called
        Mgr.remove_task("update_tc_picking_cursor")
        Mgr.set_cursor("main")

    def __pick(self):

        obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if obj:

            obj_id = self._user_obj_id

            if obj_id == obj.get_id():
                return
            elif obj_id:
                user_obj = Mgr.get("object", obj_id)
                user_obj.get_name(as_object=True).remove_updater("transf_center")

            self._tc_obj_picked = obj
            Mgr.update_locally("transf_center", "object", obj)
            Mgr.update_remotely("transf_center", "object", obj.get_name(as_object=True))

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont


MainObjects.add_class(TransformCenterManager)
