from .base import *


class CoordSysManager(BaseObject):

    def __init__(self):

        self._cs_obj = None
        self._cs_obj_picked = None
        self._cs_transformed = False

        Mgr.set_global("coord_sys_type", "world")
        Mgr.expose("coord_sys_obj", lambda: self._cs_obj)
        Mgr.accept("update_coord_sys", self.__update_coord_sys)
        Mgr.accept("notify_coord_sys_transformed", self.__notify_coord_sys_transformed)
        Mgr.add_app_updater("coord_sys", self.__set_coord_sys)

        self._pixel_under_mouse = VBase4()

    def setup(self):

        sort = PendingTasks.get_sort("update_selection", "ui")

        if sort is None:
            return False

        PendingTasks.add_task_id("coord_sys_update", "ui", sort)

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
        bind("coord_sys_picking_mode", "cancel coord sys picking", "mouse3-up",
             exit_coord_sys_picking_mode)

        status_data = Mgr.get_global("status_data")
        mode_text = "Pick coordinate system"
        info_text = "LMB to pick object; RMB to end"
        status_data["pick_coord_sys"] = {"mode": mode_text, "info": info_text}

        return True

    def __set_coord_sys(self, cs_type, obj=None):

        def reset():

            self._cs_obj = None

            Mgr.get(("grid", "origin")).clear_transform()
            Mgr.do("set_transf_gizmo_hpr", VBase3())
            Mgr.do("set_transf_gizmo_shear", VBase3())

            if Mgr.get_global("transf_center_type") == "cs_origin":
                Mgr.do("set_transf_gizmo_pos", Point3())

        Mgr.set_global("coord_sys_type", cs_type)
        selection = Mgr.get("selection", "top")

        if cs_type == "world":

            reset()

        elif cs_type == "screen":

            self._cs_obj = None
            shear = VBase3()
            Mgr.get(("grid", "origin")).set_shear(shear)
            Mgr.do("set_transf_gizmo_shear", shear)

        elif cs_type == "local":

            if obj:
                self._cs_obj = obj
            elif selection:
                self._cs_obj = selection[0]
            else:
                reset()

        elif cs_type == "object":

            self._cs_obj = obj

        if cs_type != "object":
            self._cs_obj_picked = None

        if self._cs_obj:
            self._cs_transformed = True

        self.__update_coord_sys()

        if len(selection) == 1:
            Mgr.update_remotely("transform_values", selection[0].get_transform_values())

    def __notify_coord_sys_transformed(self, transformed=True):

        self._cs_transformed = transformed

    def __update_coord_sys(self):

        cs_type = Mgr.get_global("coord_sys_type")
        tc_type = Mgr.get_global("transf_center_type")

        if cs_type == "screen":

            cam_target = Mgr.get(("cam", "target"))
            pos = cam_target.get_pos()
            quat = cam_target.get_quat()
            rotation = Quat()
            rotation.set_hpr(VBase3(0., 90., 0.))
            hpr = (rotation * quat).get_hpr()
            Mgr.get(("grid", "origin")).set_pos_hpr(pos, hpr)
            Mgr.do("set_transf_gizmo_hpr", hpr)

            if tc_type == "cs_origin":
                Mgr.do("set_transf_gizmo_pos", pos)

        elif cs_type in ("local", "object"):

            if self._cs_transformed and self._cs_obj:

                self._cs_transformed = False
                pivot = self._cs_obj.get_pivot()
                pos = pivot.get_pos(self.world)
                hpr = pivot.get_hpr(self.world)
                scale = VBase3(1., 1., 1.)
                shear = pivot.get_shear(self.world)
                Mgr.get(("grid", "origin")).set_pos_hpr_scale_shear(pos, hpr, scale, shear)
                Mgr.do("set_transf_gizmo_hpr", hpr)
                Mgr.do("set_transf_gizmo_shear", shear)

                if tc_type == "cs_origin":
                    Mgr.do("set_transf_gizmo_pos", pos)

        Mgr.do("update_grid")

    def __enter_picking_mode(self, prev_state_id, is_active):

        if Mgr.get_global("active_obj_level") != "top":
            Mgr.set_global("active_obj_level", "top")
            Mgr.update_app("active_obj_level")

        Mgr.add_task(self.__update_cursor, "update_cs_picking_cursor")
        Mgr.update_app("status", "pick_coord_sys")

    def __exit_picking_mode(self, next_state_id, is_active):

        if not is_active:

            if not self._cs_obj_picked:
                cs_type_prev = Mgr.get_global("coord_sys_type")
                obj = self._cs_obj
                name = obj.get_name() if obj else None
                Mgr.update_locally("coord_sys", cs_type_prev, obj)
                Mgr.update_remotely("coord_sys", cs_type_prev, name)

            self._cs_obj_picked = None

        self._pixel_under_mouse = VBase4() # force an update of the cursor
                                           # next time self.__update_cursor()
                                           # is called
        Mgr.remove_task("update_cs_picking_cursor")
        Mgr.set_cursor("main")

    def __pick(self):

        obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if obj:

            self._cs_obj_picked = obj
            Mgr.update_locally("coord_sys", "object", obj)
            Mgr.update_remotely("coord_sys", "object", obj.get_name())
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
