from .base import *


class CreationManager(BaseObject):

    def __init__(self):

        Mgr.set_global("active_creation_type", "")

        self._creation_start_mouse = (0, 0)
        self._origin_pos = None
        self._interactive_creation_started = False
        self._interactive_creation_ended = False
        self._mode_status = ""
        self._creation_type = ""
        Mgr.accept("notify_creation_started", lambda: setattr(self,
            "_interactive_creation_started", True))
        Mgr.accept("notify_creation_ended", lambda: setattr(self,
            "_interactive_creation_ended", True))

        status_data = Mgr.get_global("status_data")
        status_data["create"] = {}

        Mgr.add_app_updater("creation", self.__update_creation)
        Mgr.add_app_updater("instant_creation", self.__create_object_instantly)

    def setup(self):

        add_state = Mgr.add_state
        add_state("creation_mode", -10, self.__enter_creation_mode,
                  self.__exit_creation_mode)
        add_state("checking_creation_start", -11, lambda prev_state_id, is_active:
                  Mgr.do("enable_nav_gizmo", False))

        def cancel_creation():

            Mgr.remove_task("check_creation_start")
            self._interactive_creation_started = False
            self._interactive_creation_ended = True
            Mgr.enter_state("creation_mode")

        bind = Mgr.bind_state
        bind("creation_mode", "create -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("creation_mode", "create -> select", "escape",
             lambda: Mgr.exit_state("creation_mode"))
        bind("creation_mode", "exit creation mode", "mouse3-up",
             lambda: Mgr.exit_state("creation_mode"))
        bind("checking_creation_start", "quit creation", "escape", cancel_creation)
        bind("checking_creation_start", "cancel creation",
             "mouse3-up", cancel_creation)
        bind("checking_creation_start", "abort creation",
             "mouse1-up", cancel_creation)
        bind("creation_mode", "start object creation", "mouse1",
             self.__create_object)

        return True

    def __update_creation(self, mode_status):

        if mode_status == "started":

            creation_type = Mgr.get_global("active_creation_type")

            if self._mode_status != "suspended" or self._creation_type != creation_type:

                Mgr.update_app("selected_obj_type", creation_type)
                Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", creation_type))
                obj_prop_defaults = Mgr.get("%s_prop_defaults" % creation_type)

                for prop_id, value in obj_prop_defaults.iteritems():
                    Mgr.update_app("obj_prop_default", creation_type, prop_id, value)

            self._creation_type = creation_type

        elif mode_status == "ended":

            self._creation_type = ""

            selection = Mgr.get("selection")
            count = len(selection)
            type_checker = lambda obj, base_type: obj.get_geom_type() if base_type == "model" else base_type
            obj_types = set([type_checker(obj, obj.get_type()) for obj in selection])
            obj_type = obj_types.pop() if len(obj_types) == 1 else ""
            Mgr.update_app("selected_obj_type", obj_type)
            Mgr.update_app("selection_count")

            if count:
                label = selection[0].get_name() if count == 1 else "%s Objects selected" % count
                Mgr.update_remotely("selected_obj_name", label)

            sel_colors = set([obj.get_color() for obj in selection if obj.has_color()])
            sel_color_count = len(sel_colors)

            if sel_color_count == 1:
                color = sel_colors.pop()
                color_values = [x for x in color][:3]
                Mgr.update_remotely("selected_obj_color", color_values)

            Mgr.update_app("sel_color_count")

            if count == 1:

                obj = selection[0]

                for prop_id in obj.get_type_property_ids():
                    value = obj.get_property(prop_id, for_remote_update=True)
                    Mgr.update_remotely("selected_obj_prop", obj_type, prop_id, value)

        self._mode_status = mode_status

    def __enter_creation_mode(self, prev_state_id, is_active):

        Mgr.do("enable_nav_gizmo")

        if Mgr.get_global("active_obj_level") != "top":
            Mgr.set_global("active_obj_level", "top")
            Mgr.update_app("active_obj_level")

        if self._interactive_creation_ended:

            self._interactive_creation_ended = False

        else:

            if Mgr.get_global("transform_target_type") != "all":
                Mgr.set_global("transform_target_type", "all")
                Mgr.update_app("transform_target_type")

            Mgr.set_global("active_transform_type", "")
            Mgr.update_app("active_transform_type", "")
            Mgr.update_app("creation", "started")
            Mgr.set_cursor("create")

        creation_type = Mgr.get_global("active_creation_type")
        Mgr.update_app("status", "create", creation_type, "idle")

    def __exit_creation_mode(self, next_state_id, is_active):

        if self._interactive_creation_started:

            self._interactive_creation_started = False

        else:

            Mgr.set_cursor("main")

            if is_active:
                mode_status = "suspended"
            else:
                mode_status = "ended"
                Mgr.set_global("active_creation_type", "")

            Mgr.update_app("creation", mode_status)

    def __check_creation_start(self, task):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = mouse_pointer.get_y()
        mouse_start_x, mouse_start_y = self._creation_start_mouse

        if max(abs(mouse_x - mouse_start_x), abs(mouse_y - mouse_start_y)) > 3:
            object_type = Mgr.get_global("active_creation_type")
            Mgr.do("start_%s_creation" % object_type, self._origin_pos)
            return task.done

        return task.cont

    def __create_object(self):

        if not self.mouse_watcher.has_mouse():
            return

        mouse_pos = self.mouse_watcher.get_mouse()
        self._origin_pos = Mgr.get(("grid", "point_at_screen_pos"), mouse_pos)

        if not self._origin_pos:
            return

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = mouse_pointer.get_y()
        self._creation_start_mouse = (mouse_x, mouse_y)
        self._interactive_creation_started = True
        self._interactive_creation_ended = False

        Mgr.enter_state("checking_creation_start")
        Mgr.add_task(self.__check_creation_start, "check_creation_start", sort=3)

    def __create_object_instantly(self, pos_id):

        if pos_id == "grid_pos":
            origin_pos = Point3()
        elif pos_id == "cam_target_pos":
            grid_origin = Mgr.get(("grid", "origin"))
            origin_pos = Mgr.get(("cam", "target")).get_pos(grid_origin)

        object_type = Mgr.get_global("active_creation_type")
        Mgr.do("inst_create_%s" % object_type, origin_pos)


MainObjects.add_class(CreationManager)
