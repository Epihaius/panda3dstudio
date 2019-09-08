from .base import *


class TransformCenterManager:

    def __init__(self):

        self._tc_custom_pos = None
        self._stored_pos = {}
        self._tc_obj = None
        self._tc_obj_id = None
        self._tc_obj_picked = None
        self._tc_transformed = False
        self._pixel_under_mouse = None

        GD.set_default("transf_center_type", "adaptive")

        Mgr.expose("adaptive_transf_center_type", self.__get_adaptive_transf_center)
        Mgr.expose("transf_center_obj", self.__get_transform_center_object)
        Mgr.expose("transf_center_pos", self.__get_transform_center_pos)
        Mgr.expose("custom_transf_center_transform", lambda: [self._tc_custom_pos])
        Mgr.expose("stored_transf_center_transforms", lambda: self._stored_pos)
        Mgr.accept("set_custom_transf_center_transform", self.__set_custom_pos)
        Mgr.accept("set_stored_transf_center_transforms", self.__set_stored_pos)
        Mgr.add_app_updater("transf_center", self.__set_transform_center)
        Mgr.add_app_updater("custom_transf_center_transform", self.__update_custom_pos)

        add_state = Mgr.add_state
        add_state("transf_center_picking_mode", -80,
                  self.__enter_picking_mode, self.__exit_picking_mode)

        def exit_transf_center_picking_mode():

            Mgr.exit_state("transf_center_picking_mode")

        bind = Mgr.bind_state
        bind("transf_center_picking_mode", "pick transf center -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("transf_center_picking_mode", "pick transf center", "mouse1", self.__pick)
        bind("transf_center_picking_mode", "exit transf center picking", "escape",
             exit_transf_center_picking_mode)
        bind("transf_center_picking_mode", "cancel transf center picking", "mouse3",
             exit_transf_center_picking_mode)
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("transf_center_picking_mode", "pick transf center ctrl-right-click",
             f"{mod_ctrl}|mouse3", lambda: Mgr.update_remotely("main_context"))

        status_data = GD["status"]
        mode = "Pick transf. center object"
        info = "LMB to pick object; RMB to cancel"
        status_data["pick_transf_center"] = {"mode": mode, "info": info}

    def __get_adaptive_transf_center(self):

        if GD["active_obj_level"] != "top" or len(Mgr.get("selection")) > 1:
            return "sel_center"

        return "pivot"

    def __get_transform_center_object(self, check_valid=False):

        if self._tc_obj and check_valid:

            cs_type = GD["coord_sys_type"]
            tc_type = GD["transf_center_type"]

            if tc_type == "adaptive":
                tc_type = self.__get_adaptive_transf_center()

            if tc_type == "pivot" or (cs_type == "local" and tc_type == "cs_origin"):
                if self._tc_obj not in Mgr.get("selection_top"):
                    self._tc_obj = None

        return self._tc_obj

    def __set_transform_center(self, tc_type, obj=None):

        GD["transf_center_type"] = tc_type

        self._tc_obj = obj

        if tc_type == "adaptive":
            _tc_type = self.__get_adaptive_transf_center()
        else:
            _tc_type = tc_type

        if _tc_type == "pivot" and not obj:

            if GD["coord_sys_type"] == "local":
                self._tc_obj = Mgr.get("coord_sys_obj", check_valid=True)

            if not self._tc_obj:
                self._tc_obj = Mgr.get("selection").get_toplevel_object(get_group=True)

        if _tc_type != "object":

            self._tc_obj_picked = None
            tc_obj = Mgr.get("object", self._tc_obj_id)
            self._tc_obj_id = None

            if tc_obj:
                tc_obj.name_obj.remove_updater("transf_center")

        tc_pos = self.__get_transform_center_pos()
        Mgr.get("transf_gizmo").pos = tc_pos

    def __get_transform_center_pos(self):

        tc_type = GD["transf_center_type"]

        if tc_type == "adaptive" and self.__get_adaptive_transf_center() == "sel_center":
            pos = Mgr.get("selection").get_center_pos()
        elif self._tc_obj:
            pos = self._tc_obj.pivot.get_pos(GD.world)
        elif tc_type == "custom":
            pos = self._tc_custom_pos
        elif tc_type == "cs_origin":
            pos = Mgr.get("grid").origin.get_pos()
        else:
            pos = Mgr.get("selection").get_center_pos()

        return pos

    def __set_custom_pos(self, pos=None):

        self._tc_custom_pos = pos

    def __set_stored_pos(self, stored_pos):

        self._stored_pos = stored_pos

    def __update_custom_pos(self, update_type, *args):

        if update_type == "init":
            pos = self.__get_transform_center_pos()
            x, y, z = Mgr.get("grid").origin.get_relative_point(GD.world, pos)
            current_pos = args[0]
            current_pos["x"] = x
            current_pos["y"] = y
            current_pos["z"] = z
        elif update_type == "set":
            pos = args[0]
            x, y, z = GD.world.get_relative_point(Mgr.get("grid").origin, pos)
            self._tc_custom_pos = Point3(x, y, z)
            Mgr.update_app("transf_center", "custom")
        elif update_type == "cancel":
            tc_type_prev = GD["transf_center_type"]
            obj = self._tc_obj
            name_obj = obj.name_obj if obj else None
            Mgr.update_locally("transf_center", tc_type_prev, obj)
            Mgr.update_remotely("transf_center", tc_type_prev, name_obj)
        elif update_type == "get_stored_names":
            names = args[0]
            names[:] = self._stored_pos
        elif update_type == "store":
            name = args[0]
            self._stored_pos[name] = self.__get_transform_center_pos()
        elif update_type == "restore":
            name = args[0]
            self._tc_custom_pos = self._stored_pos[name]
            Mgr.update_app("transf_center", "custom")
        elif update_type == "rename_stored":
            old_name, new_name = args
            pos = self._stored_pos[old_name]
            del self._stored_pos[old_name]
            self._stored_pos[new_name] = pos
        elif update_type == "delete_stored":
            name = args[0]
            del self._stored_pos[name]
        elif update_type == "clear_stored":
            self._stored_pos = {}

        if update_type in ("store", "rename_stored", "delete_stored", "clear_stored"):
            GD["unsaved_scene"] = True
            Mgr.update_app("unsaved_scene")
            Mgr.do("require_scene_save")

    def __enter_picking_mode(self, prev_state_id, active):

        Mgr.add_task(self.__update_cursor, "update_tc_picking_cursor")
        Mgr.update_app("status", ["pick_transf_center"])

        if not active:

            def handler(obj_ids):

                if obj_ids:
                    obj = Mgr.get("object", obj_ids[0])
                    self.__pick(picked_obj=obj)

            Mgr.update_remotely("selection_by_name", "", "Pick transform center object",
                                None, False, "Pick", handler)
            Mgr.get("gizmo_picking_cam").node().active = False
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = False

    def __exit_picking_mode(self, next_state_id, active):

        if not active:

            if not self._tc_obj_picked:
                tc_type_prev = GD["transf_center_type"]
                obj = self._tc_obj
                name_obj = obj.name_obj if obj else None
                Mgr.update_locally("transf_center", tc_type_prev, obj)
                Mgr.update_remotely("transf_center", tc_type_prev, name_obj)

            self._tc_obj_picked = None
            Mgr.get("gizmo_picking_cam").node().active = True
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = True
            Mgr.update_remotely("selection_by_name", "default")

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self.__update_cursor()
                                        # is called
        Mgr.remove_task("update_tc_picking_cursor")
        Mgr.set_cursor("main")

    def __pick(self, picked_obj=None):

        obj = picked_obj if picked_obj else Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if obj:

            obj_id = self._tc_obj_id

            if obj_id and obj_id != obj.id:
                tc_obj = Mgr.get("object", obj_id)
                tc_obj.name_obj.remove_updater("transf_center")

            self._tc_obj_picked = obj
            self._tc_obj_id = obj.id
            Mgr.exit_state("transf_center_picking_mode")
            Mgr.update_locally("transf_center", "object", obj)
            Mgr.update_remotely("transf_center", "object", obj.name_obj)

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont


MainObjects.add_class(TransformCenterManager)
