from .base import *


class CoordSysManager(BaseObject):

    def __init__(self):

        self._cs_custom_pos = None
        self._cs_custom_hpr = None
        self._cs_obj = None
        self._cs_obj_picked = None
        self._cs_transformed = False
        self._user_obj_id = None
        self._pixel_under_mouse = None

        GlobalData.set_default("coord_sys_type", "world")

        Mgr.expose("coord_sys_obj", self.__get_coord_sys_object)
        Mgr.expose("custom_coord_sys_transform", self.__get_custom_coord_sys_transform)
        Mgr.accept("set_custom_coord_sys_transform", self.__set_custom_coord_sys_transform)
        Mgr.accept("update_coord_sys", self.__update_coord_sys)
        Mgr.accept("notify_coord_sys_transformed", self.__notify_coord_sys_transformed)
        Mgr.add_app_updater("coord_sys", self.__set_coord_sys)

        add_state = Mgr.add_state
        add_state("coord_sys_picking_mode", -80, self.__enter_picking_mode,
                  self.__exit_picking_mode)

        def exit_coord_sys_picking_mode():

            Mgr.exit_state("coord_sys_picking_mode")

        bind = Mgr.bind_state
        bind("coord_sys_picking_mode", "pick coord sys -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("coord_sys_picking_mode", "pick coord sys", "mouse1", self.__pick)
        bind("coord_sys_picking_mode", "exit coord sys picking", "escape",
             exit_coord_sys_picking_mode)
        bind("coord_sys_picking_mode", "cancel coord sys picking", "mouse3",
             exit_coord_sys_picking_mode)
        mod_ctrl = GlobalData["mod_key_codes"]["ctrl"]
        bind("coord_sys_picking_mode", "cs pick ctrl-right-click", "{:d}|mouse3".format(mod_ctrl),
             lambda: Mgr.update_remotely("main_context"))

        status_data = GlobalData["status_data"]
        mode_text = "Pick coordinate system"
        info_text = "LMB to pick object; RMB to cancel"
        status_data["pick_coord_sys"] = {"mode": mode_text, "info": info_text}

    def __get_coord_sys_object(self, check_valid=False):

        if self._cs_obj and check_valid:
            if (GlobalData["coord_sys_type"] == "local"
                    and self._cs_obj not in Mgr.get("selection_top")):
                self._cs_obj = None

        return self._cs_obj

    def __set_coord_sys(self, cs_type, obj=None):

        def reset():

            self._cs_obj = None

            Mgr.get(("grid", "origin")).clear_transform()
            Mgr.do("set_transf_gizmo_hpr", VBase3())

            if GlobalData["transf_center_type"] == "cs_origin":
                Mgr.do("set_transf_gizmo_pos", Point3())

        if GlobalData["coord_sys_type"] == "view" and cs_type != "view":
            Mgr.do("align_grid_to_view", False)

        GlobalData["coord_sys_type"] = cs_type
        self._cs_obj = obj

        if cs_type == "world":

            reset()

        elif cs_type == "view":

            self._cs_obj = None
            Mgr.do("align_grid_to_view")

        elif cs_type == "local":

            if not self._cs_obj:

                tc_type = GlobalData["transf_center_type"]

                if tc_type == "adaptive" and Mgr.get("adaptive_transf_center_type") == "pivot":
                    tc_type = "pivot"

                if tc_type == "pivot":
                    self._cs_obj = Mgr.get("transf_center_obj", check_valid=True)

            if not self._cs_obj:
                self._cs_obj = Mgr.get("selection").get_toplevel_object(get_group=True)

            if not self._cs_obj:
                reset()

        if cs_type != "object":

            self._cs_obj_picked = None
            user_obj = Mgr.get("object", self._user_obj_id)
            self._user_obj_id = None

            if user_obj:
                user_obj.get_name(as_object=True).remove_updater("coord_sys")

        if self._cs_obj:
            self._cs_transformed = True

        self.__update_coord_sys()
        Mgr.get("selection").update_transform_values()

    def __notify_coord_sys_transformed(self, transformed=True):

        self._cs_transformed = transformed

    def __set_custom_coord_sys_transform(self, pos=None, hpr=None):

        self._cs_custom_pos = pos
        self._cs_custom_hpr = hpr

    def __get_custom_coord_sys_transform(self):

        if GlobalData["coord_sys_type"] != "snap_pt":
            return []

        grid_origin = Mgr.get(("grid", "origin"))
        pos = grid_origin.get_pos() if self._cs_custom_pos is None else self._cs_custom_pos
        hpr = grid_origin.get_hpr() if self._cs_custom_hpr is None else self._cs_custom_hpr

        return [pos, hpr]

    def __update_coord_sys(self):

        cs_type = GlobalData["coord_sys_type"]
        tc_type = GlobalData["transf_center_type"]

        if cs_type == "view":

            pos = self.cam.pivot.get_pos()
            quat = self.cam.target.get_quat(self.world)
            rotation = Quat()
            rotation.set_hpr(VBase3(0., 90., 0.))
            hpr = (rotation * quat).get_hpr()
            Mgr.get(("grid", "origin")).set_pos_hpr(pos, hpr)
            Mgr.do("set_transf_gizmo_hpr", hpr)

            if tc_type == "cs_origin":
                Mgr.do("set_transf_gizmo_pos", pos)

        elif cs_type == "snap_pt":

            grid_origin = Mgr.get(("grid", "origin"))

            if self._cs_custom_pos is not None:

                grid_origin.set_pos(self._cs_custom_pos)

                if tc_type == "cs_origin":
                    Mgr.do("set_transf_gizmo_pos", self._cs_custom_pos)

            if self._cs_custom_hpr is not None:
                grid_origin.set_hpr(self._cs_custom_hpr)
                Mgr.do("set_transf_gizmo_hpr", self._cs_custom_hpr)

        elif cs_type in ("local", "object"):

            if self._cs_transformed and self._cs_obj:

                self._cs_transformed = False
                pivot = self._cs_obj.get_pivot()
                pos = pivot.get_pos(self.world)
                hpr = pivot.get_hpr(self.world)
                scale = VBase3(1., 1., 1.)
                Mgr.get(("grid", "origin")).set_pos_hpr_scale(pos, hpr, scale)
                Mgr.do("set_transf_gizmo_hpr", hpr)

                if tc_type == "cs_origin":
                    Mgr.do("set_transf_gizmo_pos", pos)

        Mgr.do("update_grid")

    def __enter_picking_mode(self, prev_state_id, is_active):

        Mgr.add_task(self.__update_cursor, "update_cs_picking_cursor")
        Mgr.update_app("status", ["pick_coord_sys"])

        if not is_active:

            def handler(obj_ids):

                if obj_ids:
                    obj = Mgr.get("object", obj_ids[0])
                    self.__pick(picked_obj=obj)

            Mgr.update_remotely("selection_by_name", "", "Pick coordinate system object",
                                None, False, "Pick", handler)
            Mgr.get("gizmo_picking_cam").node().set_active(False)
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).set_active(False)

    def __exit_picking_mode(self, next_state_id, is_active):

        if not is_active:

            if not self._cs_obj_picked:
                cs_type_prev = GlobalData["coord_sys_type"]
                obj = self._cs_obj
                name = obj.get_name(as_object=True) if obj else None
                Mgr.update_locally("coord_sys", cs_type_prev, obj)
                Mgr.update_remotely("coord_sys", cs_type_prev, name)

            self._cs_obj_picked = None
            Mgr.get("gizmo_picking_cam").node().set_active(True)
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).set_active(True)
            Mgr.update_remotely("selection_by_name", "default")

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self.__update_cursor()
                                        # is called
        Mgr.remove_task("update_cs_picking_cursor")
        Mgr.set_cursor("main")

    def __pick(self, picked_obj=None):

        obj = picked_obj if picked_obj else Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if obj:

            obj_id = self._user_obj_id

            if obj_id == obj.get_id():
                return
            elif obj_id:
                user_obj = Mgr.get("object", obj_id)
                user_obj.get_name(as_object=True).remove_updater("coord_sys")

            self._cs_obj_picked = obj
            self._user_obj_id = obj.get_id()
            Mgr.exit_state("coord_sys_picking_mode")
            Mgr.update_locally("coord_sys", "object", obj)
            Mgr.update_remotely("coord_sys", "object", obj.get_name(as_object=True))
            selection = Mgr.get("selection")

            if len(selection) == 1:
                Mgr.update_remotely("transform_values", selection[0].get_transform_values())

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont


MainObjects.add_class(CoordSysManager)
