from .base import *
from .transform import SelectionTransformBase


class Selection(SelectionTransformBase):

    def __init__(self):

        SelectionTransformBase.__init__(self)

        self._objs = []
        self._prev_obj_ids = set()

    def __getitem__(self, index):

        try:
            return self._objs[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __len__(self):

        return len(self._objs)

    def reset(self):

        self._objs = []

    def get_toplevel_object(self, get_group=False):
        """ Return a random top-level object """

        if self._objs:
            return self._objs[0].get_toplevel_object(get_group)

    def clear_prev_obj_ids(self):

        self._prev_obj_ids = None

    def update_obj_props(self, force=False):

        obj_ids = set(obj.get_id() for obj in self._objs)

        if not force and obj_ids == self._prev_obj_ids:
            return

        count = len(self._objs)

        if count == 1:
            sel = self._objs[0]

        if count:
            label = sel.get_name() if count == 1 else "%s Objects selected" % count
            Mgr.update_remotely("selected_obj_name", label)

        sel_colors = set(obj.get_color() for obj in self._objs if obj.has_color())
        sel_color_count = len(sel_colors)

        if sel_color_count == 1:
            color = sel_colors.pop()
            color_values = [x for x in color][:3]
            Mgr.update_remotely("selected_obj_color", color_values)

        GlobalData["sel_color_count"] = sel_color_count
        Mgr.update_app("sel_color_count")

        type_checker = lambda obj, main_type: obj.get_geom_type() if main_type == "model" else main_type
        obj_types = set(type_checker(obj, obj.get_type()) for obj in self._objs)
        Mgr.update_app("selected_obj_types", tuple(obj_types))

        if count == 1:

            obj_type = obj_types.pop()

            for prop_id in sel.get_type_property_ids():
                value = sel.get_property(prop_id, for_remote_update=True)
                Mgr.update_remotely("selected_obj_prop", obj_type, prop_id, value)

        self._prev_obj_ids = obj_ids

        Mgr.update_app("selection_count")

    def update(self):

        self.update_center_pos()
        self.update_ui()
        self.update_obj_props()

    def add(self, objs, add_to_hist=True, update=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_add = set(objs)
        common = old_sel & sel_to_add

        if common:
            sel_to_add -= common

        if not sel_to_add:
            return False

        sel.extend(sel_to_add)

        for obj in sel_to_add:
            obj.update_selection_state()

        if update:
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            count = len(sel_to_add)

            if count == 1:
                obj = sel_to_add.copy().pop()
                event_descr = 'Select "%s"' % obj.get_name()
            else:
                event_descr = 'Select %d objects:\n' % count
                event_descr += "".join(['\n    "%s"' % obj.get_name() for obj in sel_to_add])

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in sel_to_add:
                obj_data[obj.get_id()] = {"selection_state": {"main": True}}

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def remove(self, objs, add_to_hist=True, update=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_remove = set(objs)
        common = old_sel & sel_to_remove

        if not common:
            return False

        for obj in common:
            sel.remove(obj)
            obj.update_selection_state(False)

        if update:
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            count = len(common)

            if count == 1:
                obj = common.copy().pop()
                event_descr = 'Deselect "%s"' % obj.get_name()
            else:
                event_descr = 'Deselect %d objects:\n' % count
                event_descr += "".join(['\n    "%s"' % obj.get_name() for obj in common])

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in common:
                obj_data[obj.get_id()] = {"selection_state": {"main": False}}

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def replace(self, objs, add_to_hist=True, update=True):

        sel = self._objs
        old_sel = set(sel)
        new_sel = set(objs)
        common = old_sel & new_sel

        if common:
            old_sel -= common
            new_sel -= common

        if not (old_sel or new_sel):
            return False

        for old_obj in old_sel:
            sel.remove(old_obj)
            old_obj.update_selection_state(False)

        for new_obj in new_sel:
            sel.append(new_obj)
            new_obj.update_selection_state()

        if update:
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            event_descr = ''
            old_count = len(old_sel)
            new_count = len(new_sel)

            if new_sel:

                if new_count == 1:

                    event_descr += 'Select "%s"' % new_sel.copy().pop().get_name()

                else:

                    event_descr += 'Select %d objects:\n' % new_count

                    for new_obj in new_sel:
                        event_descr += '\n    "%s"' % new_obj.get_name()

            if old_sel:

                event_descr += '\n\n' if new_sel else ''

                if old_count == 1:

                    event_descr += 'Deselect "%s"' % old_sel.copy().pop().get_name()

                else:

                    event_descr += 'Deselect %d objects:\n' % old_count

                    for old_obj in old_sel:
                        event_descr += '\n    "%s"' % old_obj.get_name()

            if event_descr:

                obj_data = {}
                event_data = {"objects": obj_data}

                for old_obj in old_sel:
                    obj_data[old_obj.get_id()] = {"selection_state": {"main": False}}

                for new_obj in new_sel:
                    obj_data[new_obj.get_id()] = {"selection_state": {"main": True}}

                # make undo/redoable
                Mgr.do("add_history", event_descr, event_data)

        return True

    def clear(self, add_to_hist=True, update=True):

        sel = self._objs

        if not sel:
            return False

        for obj in sel:
            obj.update_selection_state(False)

        sel = sel[:]
        self._objs = []

        if update:
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            obj_count = len(sel)

            if obj_count > 1:

                event_descr = 'Deselect %d objects:\n' % obj_count

                for obj in sel:
                    event_descr += '\n    "%s"' % obj.get_name()

            else:

                event_descr = 'Deselect "%s"' % sel[0].get_name()

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in sel:
                obj_data[obj.get_id()] = {"selection_state": {"main": False}}

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def delete(self, add_to_hist=True, update=True):

        sel = self._objs

        if not sel:
            return False

        if update:
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            Mgr.do("update_history_time")
            obj_count = len(sel)

            if obj_count > 1:

                event_descr = 'Delete %d objects:\n' % obj_count

                for obj in sel:
                    event_descr += '\n    "%s"' % obj.get_name()

            else:

                event_descr = 'Delete "%s"' % sel[0].get_name()

            obj_data = {}
            event_data = {"objects": obj_data}
            groups = set()

            for obj in sel:

                obj_data[obj.get_id()] = obj.get_data_to_store("deletion")
                group = obj.get_group()

                if group and group not in sel:
                    groups.add(group)

        for obj in sel[:]:
            obj.destroy(add_to_hist=add_to_hist)

        if add_to_hist:
            Mgr.do("prune_empty_groups", groups, obj_data)
            event_data["object_ids"] = set(Mgr.get("object_ids"))
            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        return True


class SelectionManager(BaseObject):

    def __init__(self):

        obj_root = Mgr.get("object_root")
        sel_pivot = obj_root.attach_new_node("selection_pivot")
        Mgr.expose("selection_pivot", lambda: sel_pivot)

        self._mouse_start_pos = ()
        self._picked_point = None
        self._can_select_single = False

        self._obj_id = None
        self._selection = Selection()
        self._pixel_under_mouse = VBase4()

        GlobalData.set_default("selection_count", 0)
        GlobalData.set_default("sel_color_count", 0)

        Mgr.expose("selection", self.__get_selection)
        Mgr.expose("selection_top", lambda: self._selection)
        Mgr.accept("select_top", self.__select_toplvl_obj)
        Mgr.accept("select_single_top", self.__select_single)

        PendingTasks.add_task_id("update_selection", "object")
        PendingTasks.add_task_id("update_selection", "ui")

        def force_cursor_update(transf_type):

            self._pixel_under_mouse = VBase4() # force an update of the cursor
                                               # next time self.__update_cursor()
                                               # is called

        Mgr.add_app_updater("active_transform_type", force_cursor_update)
        Mgr.add_app_updater("active_obj_level", self.__update_active_selection,
                            kwargs=["restore"])
        Mgr.accept("update_active_selection", self.__update_active_selection)

        add_state = Mgr.add_state
        add_state("selection_mode", 0, self.__enter_selection_mode,
                  self.__exit_selection_mode)
        add_state("checking_mouse_offset", -1, self.__start_mouse_check)

        bind = Mgr.bind_state
        bind("selection_mode", "select -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("selection_mode", "normal select", "mouse1", self.__select)
        mod_ctrl = Mgr.get("mod_ctrl")
        bind("selection_mode", "toggle-select", "%d|mouse1" % mod_ctrl,
             lambda: self.__select(toggle=True))
        bind("selection_mode", "access obj props", "mouse3", self.__access_obj_props)
        bind("selection_mode", "del selection",
             "delete", self.__delete_selection)
        bind("selection_mode", "transf off", "q",
             lambda: self.__set_active_transform_type(""))

        def cancel_mouse_check():

            Mgr.enter_state("selection_mode")
            self.__cancel_mouse_check()

        bind("checking_mouse_offset", "cancel mouse check",
             "mouse1-up", cancel_mouse_check)

        status_data = GlobalData["status_data"]
        status_data["select"] = {}
        info_start = "(<Ctrl>-)LMB to (toggle-)select; <Del> to delete selection; "
        info = info_start + "<W>, <E>, <R> to set transform type"
        status_data["select"][""] = {"mode": "Select", "info": info}
        info_idle = info_start + "LMB-drag selection or gizmo handle to transform;" \
            " <Q> to disable transforms"
        info = "LMB-drag to transform selection; RMB to cancel transformation"

        for transf_type in ("translate", "rotate", "scale"):
            mode = "Select and %s" % transf_type
            status_data["select"][transf_type] = {}
            status_data["select"][transf_type]["idle"] = {"mode": mode, "info": info_idle}
            status_data["select"][transf_type]["in_progress"] = {"mode": mode, "info": info}

    def __get_selection(self, obj_lvl=""):

        lvl = obj_lvl if obj_lvl else GlobalData["active_obj_level"]

        return Mgr.get("selection_" + lvl)

    def __enter_selection_mode(self, prev_state_id, is_active):

        Mgr.add_task(self.__update_cursor, "update_cursor")
        Mgr.do("enable_transf_gizmo")

        transf_type = GlobalData["active_transform_type"]

        if transf_type:
            Mgr.update_app("status", "select", transf_type, "idle")
        else:
            Mgr.update_app("status", "select", "")

    def __exit_selection_mode(self, next_state_id, is_active):

        if next_state_id != "checking_mouse_offset":
            self._pixel_under_mouse = VBase4() # force an update of the cursor
                                               # next time self.__update_cursor()
                                               # is called
            Mgr.remove_task("update_cursor")
            Mgr.set_cursor("main")

        Mgr.do("disable_transf_gizmo")

    def __set_active_transform_type(self, transf_type):

        GlobalData["active_transform_type"] = transf_type
        Mgr.update_app("active_transform_type", transf_type)

        if transf_type:
            Mgr.update_app("status", "select", transf_type, "idle")
        else:
            Mgr.update_app("status", "select", "")

    def __update_active_selection(self, restore=False):

        obj_lvl = GlobalData["active_obj_level"]

        if obj_lvl != "top":

            self._selection.clear_prev_obj_ids()
            Mgr.do("update_selection_" + obj_lvl)

            toplvl_obj = self.__get_selection(obj_lvl).get_toplevel_object()

            if toplvl_obj:

                cs_type = GlobalData["coord_sys_type"]
                tc_type = GlobalData["transf_center_type"]

                if cs_type == "local":
                    Mgr.update_locally("coord_sys", cs_type, toplvl_obj)

                if tc_type == "pivot":
                    Mgr.update_locally("transf_center", tc_type, toplvl_obj)

        if restore:
            task = lambda: self.__get_selection().update()
            PendingTasks.add(task, "update_selection", "ui")
        else:
            self.__get_selection().update()

    def __delete_selection(self):

        selection = self.__get_selection()
        selection.delete()

        Mgr.do("update_picking_col_id_ranges")

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            if pixel_under_mouse == VBase4():
                Mgr.set_cursor("main")
            else:
                active_transform_type = GlobalData["active_transform_type"]
                cursor_name = "select" if not active_transform_type else active_transform_type
                Mgr.set_cursor(cursor_name)

            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __check_mouse_offset(self, task):
        """
        Delay start of transformation until user has moved mouse at least 3 pixels
        in any direction, to avoid accidental transforms.

        """

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = mouse_pointer.get_y()
        mouse_start_x, mouse_start_y = self._mouse_start_pos

        if max(abs(mouse_x - mouse_start_x), abs(mouse_y - mouse_start_y)) > 3:
            Mgr.do("init_transform", self._picked_point)
            return task.done

        return task.cont

    def __start_mouse_check(self, prev_state_id, is_active):

        Mgr.add_task(self.__check_mouse_offset, "check_mouse_offset")
        Mgr.remove_task("update_cursor")

    def __cancel_mouse_check(self):

        Mgr.remove_task("check_mouse_offset")

        active_transform_type = GlobalData["active_transform_type"]

        if active_transform_type == "rotate" \
                and GlobalData["axis_constraints"]["rotate"] == "trackball":
            prev_constraints = GlobalData["prev_axis_constraints_rotate"]
            Mgr.update_app("axis_constraints", "rotate", prev_constraints)

        if self._can_select_single:
            obj_lvl = GlobalData["active_obj_level"]
            Mgr.do("select_single_" + obj_lvl)

    def __get_picked_object(self, color_id, obj_type_id):

        if not color_id:
            return "", None

        pickable_type = PickableTypes.get(obj_type_id)

        if not pickable_type:
            return "", None

        if pickable_type == "transf_gizmo":
            return "transf_gizmo", Mgr.do("select_transf_gizmo_handle", color_id)

        picked_obj = Mgr.get(pickable_type, color_id)

        return (pickable_type, picked_obj) if picked_obj else ("", None)

    def __select(self, toggle=False):

        if not self.mouse_watcher.has_mouse():
            return

        self._can_select_single = False
        screen_pos = Point2(self.mouse_watcher.get_mouse())
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        self._mouse_start_pos = (mouse_pointer.get_x(), mouse_pointer.get_y())

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b  # credit to coppertop @ panda3d.org
        pickable_type, picked_obj = self.__get_picked_object(color_id, a)
        self._picked_point = picked_obj.get_point_at_screen_pos(screen_pos) if picked_obj else None

        if pickable_type == "transf_gizmo":
            Mgr.enter_state("checking_mouse_offset")
            return

        obj_lvl = GlobalData["active_obj_level"]
        can_select_single, start_mouse_checking = Mgr.do("select_" + obj_lvl, picked_obj, toggle)

        self._can_select_single = can_select_single

        if start_mouse_checking:
            Mgr.enter_state("checking_mouse_offset")

    def __select_toplvl_obj(self, picked_obj, toggle):

        obj = picked_obj.get_toplevel_object(get_group=True) if picked_obj else None
        self._obj_id = obj.get_id() if obj else None

        if toggle:
            ret = self.__toggle_select()
        else:
            ret = self.__normal_select()

        selection = self._selection

        if obj not in selection:
            obj = selection[0] if selection else None

        if obj:

            cs_type = GlobalData["coord_sys_type"]
            tc_type = GlobalData["transf_center_type"]

            if cs_type == "local":
                Mgr.update_locally("coord_sys", cs_type, obj)

            if tc_type == "pivot":
                Mgr.update_locally("transf_center", tc_type, obj)

        return ret

    def __normal_select(self):

        obj = Mgr.get("object", self._obj_id)
        selection = self._selection
        can_select_single = False
        start_mouse_checking = False

        if obj:

            if GlobalData["active_transform_type"]:

                if obj in selection and len(selection) > 1:

                    # When the user clicks one of multiple selected objects, updating the
                    # selection must be delayed until it is clear whether he wants to
                    # transform the entire selection or simply have only this object
                    # selected (this is determined by checking if the mouse has moved at
                    # least a certain number of pixels by the time the left mouse button
                    # is released).

                    can_select_single = True

                else:

                    selection.replace([obj])

                start_mouse_checking = True

            else:

                selection.replace([obj])

        else:

            selection.clear()

        return can_select_single, start_mouse_checking

    def __select_single(self):

        # If multiple objects were selected and no transformation occurred, a single
        # object has been selected out of that previous selection.

        obj = Mgr.get("object", self._obj_id)
        self._selection.replace([obj])

    def __toggle_select(self):

        obj = Mgr.get("object", self._obj_id)
        selection = self._selection
        start_mouse_checking = False

        if obj:

            if obj in selection:
                selection.remove([obj])
                transform_allowed = False
            else:
                selection.add([obj])
                transform_allowed = GlobalData["active_transform_type"]

            if transform_allowed:
                start_mouse_checking = True

        return False, start_mouse_checking

    def __access_obj_props(self):

        obj_lvl = GlobalData["active_obj_level"]

        if obj_lvl != "top" or not self.mouse_watcher.has_mouse():
            return

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b  # credit to coppertop @ panda3d.org
        pickable_type = PickableTypes.get(a)

        if not pickable_type or pickable_type == "transf_gizmo":
            return

        picked_obj = Mgr.get(pickable_type, color_id)
        obj = picked_obj.get_toplevel_object(get_group=True) if picked_obj else None

        if obj:
            Mgr.update_remotely("obj_props_access", obj.get_id())


MainObjects.add_class(SelectionManager)
