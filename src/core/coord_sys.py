from .base import *


class CoordSysManager:

    def __init__(self):

        self._cs_custom_pos = None
        self._cs_custom_hpr = None
        self._stored_pos_hpr = {}
        self._cs_obj = None
        self._cs_obj_id = None
        self._cs_obj_picked = None
        self._cs_transformed = False
        self._pixel_under_mouse = None

        GD.set_default("coord_sys_type", "world")

        Mgr.expose("coord_sys_obj", self.__get_coord_sys_object)
        Mgr.expose("custom_coord_sys_transform", self.__get_custom_transform)
        Mgr.expose("stored_coord_sys_transforms", lambda: self._stored_pos_hpr)
        Mgr.accept("set_custom_coord_sys_transform", self.__set_custom_transform)
        Mgr.accept("set_stored_coord_sys_transforms", self.__set_stored_transforms)
        Mgr.accept("update_coord_sys", self.__update_coord_sys)
        Mgr.accept("notify_coord_sys_transformed", self.__notify_coord_sys_transformed)
        Mgr.add_app_updater("coord_sys", self.__set_coord_sys)
        Mgr.add_app_updater("custom_coord_sys_transform", self.__update_custom_transform)

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
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("coord_sys_picking_mode", "cs pick ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))

        status_data = GD["status"]
        mode_text = "Pick coordinate system"
        info_text = "LMB to pick object; RMB to cancel"
        status_data["pick_coord_sys"] = {"mode": mode_text, "info": info_text}

    def __get_coord_sys_object(self, check_valid=False):

        if self._cs_obj and check_valid:
            if (GD["coord_sys_type"] == "local"
                    and self._cs_obj not in Mgr.get("selection_top")):
                self._cs_obj = None

        return self._cs_obj

    def __set_coord_sys(self, cs_type, obj=None):

        def reset():

            self._cs_obj = None

            Mgr.get("grid").origin.clear_transform()
            Mgr.get("transf_gizmo").hpr = VBase3()

            if GD["transf_center_type"] == "cs_origin":
                Mgr.get("transf_gizmo").pos = Point3()

        if GD["coord_sys_type"] == "view" and cs_type != "view":
            Mgr.get("grid").align_to_view(False)

        GD["coord_sys_type"] = cs_type
        self._cs_obj = obj

        if cs_type == "world":

            reset()

        elif cs_type == "view":

            self._cs_obj = None
            Mgr.get("grid").align_to_view()

        elif cs_type == "local":

            if not self._cs_obj:

                tc_type = GD["transf_center_type"]

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
            cs_obj = Mgr.get("object", self._cs_obj_id)
            self._cs_obj_id = None

            if cs_obj:
                cs_obj.name_obj.remove_updater("coord_sys")

        if self._cs_obj:
            self._cs_transformed = True

        self.__update_coord_sys()
        Mgr.get("selection").update_transform_values()

    def __notify_coord_sys_transformed(self, transformed=True):

        self._cs_transformed = transformed

    def __get_custom_transform(self):

        if GD["coord_sys_type"] != "custom":
            return []

        grid_origin = Mgr.get("grid").origin
        pos = grid_origin.get_pos() if self._cs_custom_pos is None else self._cs_custom_pos
        hpr = grid_origin.get_hpr() if self._cs_custom_hpr is None else self._cs_custom_hpr

        return [pos, hpr]

    def __set_custom_transform(self, pos=None, hpr=None):

        self._cs_custom_pos = pos
        self._cs_custom_hpr = hpr

    def __set_stored_transforms(self, stored_pos_hpr):

        self._stored_pos_hpr = stored_pos_hpr

    def __update_custom_transform(self, update_type, *args):

        grid_origin = Mgr.get("grid").origin

        if update_type == "init":
            x, y, z = grid_origin.get_pos()
            h, p, r = grid_origin.get_hpr()
            current_pos_hpr = args[0]
            current_pos_hpr["x"] = x
            current_pos_hpr["y"] = y
            current_pos_hpr["z"] = z
            current_pos_hpr["h"] = h
            current_pos_hpr["p"] = p
            current_pos_hpr["r"] = r
        elif update_type == "set":
            x, y, z, h, p, r = args[0]
            self._cs_custom_pos = Point3(x, y, z)
            self._cs_custom_hpr = VBase3(h, p, r)
            Mgr.update_app("coord_sys", "custom")
        elif update_type == "cancel":
            cs_type_prev = GD["coord_sys_type"]
            obj = self._cs_obj
            name_obj = obj.name_obj if obj else None
            Mgr.update_locally("coord_sys", cs_type_prev, obj)
            Mgr.update_remotely("coord_sys", cs_type_prev, name_obj)
        elif update_type == "get_stored_names":
            names = args[0]
            names[:] = self._stored_pos_hpr
        elif update_type == "store":
            name = args[0]
            pos = Point3(grid_origin.get_pos())
            hpr = VBase3(grid_origin.get_hpr())
            self._stored_pos_hpr[name] = (pos, hpr)
        elif update_type == "restore":
            name = args[0]
            pos, hpr = self._stored_pos_hpr[name]
            self._cs_custom_pos = pos
            self._cs_custom_hpr = hpr
            Mgr.update_app("coord_sys", "custom")
        elif update_type == "rename_stored":
            old_name, new_name = args
            pos_hpr = self._stored_pos_hpr[old_name]
            del self._stored_pos_hpr[old_name]
            self._stored_pos_hpr[new_name] = pos_hpr
        elif update_type == "delete_stored":
            name = args[0]
            del self._stored_pos_hpr[name]
        elif update_type == "clear_stored":
            self._stored_pos_hpr = {}

        if update_type in ("store", "rename_stored", "delete_stored", "clear_stored"):
            GD["unsaved_scene"] = True
            Mgr.update_app("unsaved_scene")
            Mgr.do("require_scene_save")

    def __update_coord_sys(self):

        cs_type = GD["coord_sys_type"]
        tc_type = GD["transf_center_type"]
        grid = Mgr.get("grid")

        if cs_type == "view":

            pos = GD.cam.pivot.get_pos()
            quat = GD.cam.target.get_quat(GD.world)
            rotation = Quat()
            rotation.set_hpr(VBase3(0., 90., 0.))
            hpr = (rotation * quat).get_hpr()
            grid.origin.set_pos_hpr(pos, hpr)
            Mgr.get("transf_gizmo").hpr = hpr

            if tc_type == "cs_origin":
                Mgr.get("transf_gizmo").pos = pos

        elif cs_type == "custom":

            grid_origin = grid.origin

            if self._cs_custom_pos is not None:

                grid_origin.set_pos(self._cs_custom_pos)

                if tc_type == "cs_origin":
                    Mgr.get("transf_gizmo").pos = self._cs_custom_pos

            if self._cs_custom_hpr is not None:
                grid_origin.set_hpr(self._cs_custom_hpr)
                Mgr.get("transf_gizmo").hpr = self._cs_custom_hpr

        elif cs_type in ("local", "object"):

            if self._cs_transformed and self._cs_obj:

                self._cs_transformed = False
                pivot = self._cs_obj.pivot
                pos = pivot.get_pos(GD.world)
                hpr = pivot.get_hpr(GD.world)
                grid.origin.set_pos_hpr(pos, hpr)
                Mgr.get("transf_gizmo").hpr = hpr

                if tc_type == "cs_origin":
                    Mgr.get("transf_gizmo").pos = pos

        grid.update()

    def __enter_picking_mode(self, prev_state_id, active):

        Mgr.add_task(self.__update_cursor, "update_cs_picking_cursor")
        Mgr.update_app("status", ["pick_coord_sys"])

        if not active:

            def handler(obj_ids):

                if obj_ids:
                    obj = Mgr.get("object", obj_ids[0])
                    self.__pick(picked_obj=obj)

            Mgr.update_remotely("selection_by_name", "", "Pick coordinate system object",
                                None, False, "Pick", handler)
            Mgr.get("gizmo_picking_cam").node().active = False
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = False

    def __exit_picking_mode(self, next_state_id, active):

        if not active:

            if not self._cs_obj_picked:
                cs_type_prev = GD["coord_sys_type"]
                obj = self._cs_obj
                name_obj = obj.name_obj if obj else None
                Mgr.update_locally("coord_sys", cs_type_prev, obj)
                Mgr.update_remotely("coord_sys", cs_type_prev, name_obj)

            self._cs_obj_picked = None
            Mgr.get("gizmo_picking_cam").node().active = True
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = True
            Mgr.update_remotely("selection_by_name", "default")

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self.__update_cursor()
                                        # is called
        Mgr.remove_task("update_cs_picking_cursor")
        Mgr.set_cursor("main")

    def __pick(self, picked_obj=None):

        obj = picked_obj if picked_obj else Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if obj:

            obj_id = self._cs_obj_id

            if obj_id and obj_id != obj.id:
                cs_obj = Mgr.get("object", obj_id)
                cs_obj.name_obj.remove_updater("coord_sys")

            self._cs_obj_picked = obj
            self._cs_obj_id = obj.id
            Mgr.exit_state("coord_sys_picking_mode")
            Mgr.update_locally("coord_sys", "object", obj)
            Mgr.update_remotely("coord_sys", "object", obj.name_obj)
            selection = Mgr.get("selection")

            if len(selection) == 1:
                Mgr.update_remotely("transform_values", selection[0].transform_values)

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont


MainObjects.add_class(CoordSysManager)
