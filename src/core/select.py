from .base import *
from .transform import SelectionTransformBase


class Selection(SelectionTransformBase):

    def __init__(self, obj_level, objs=None):

        SelectionTransformBase.__init__(self, obj_level)

        self._objs = [] if objs is None else objs
        self._obj_level = obj_level

    def __getitem__(self, index):

        try:
            return self._objs[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __len__(self):

        return len(self._objs)

    def get_object_level(self):

        return self._obj_level

    def get(self):

        return self._objs

    def clear(self):

        self._objs = []

    def update(self):

        self.update_center()
        self.update_ui()


class TopLevelSelection(Selection):

    def __init__(self, objs=None):

        Selection.__init__(self, "top", objs)

    def add(self, obj, add_to_hist=True):

        sel = self.get()

        if obj in sel:
            return False

        sel.append(obj)
        obj.update_selection_state()
        PendingTasks.add(self.update, "update_selection", "ui")

        if add_to_hist:
            event_descr = 'Select "%s"' % obj.get_name()
            obj_data = {}
            event_data = {"objects": obj_data}
            obj_data[obj.get_id()] = {"selection_state": {"main": True}}
            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def remove(self, obj, add_to_hist=True):

        sel = self.get()

        if obj not in sel:
            return False

        sel.remove(obj)
        obj.update_selection_state(False)
        PendingTasks.add(self.update, "update_selection", "ui")

        if add_to_hist:
            event_descr = 'Deselect "%s"' % obj.get_name()
            obj_data = {}
            event_data = {"objects": obj_data}
            obj_data[obj.get_id()] = {"selection_state": {"main": False}}
            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

    def replace(self, obj, add_to_hist=True):

        sel = self.get()
        old_sel = set(sel)
        new_sel = set([obj])
        common = old_sel & new_sel

        if common:
            old_sel -= common
            new_sel -= common

        for old_obj in old_sel:
            sel.remove(old_obj)
            old_obj.update_selection_state(False)

        for new_obj in new_sel:
            sel.append(new_obj)
            new_obj.update_selection_state()

        PendingTasks.add(self.update, "update_selection", "ui")

        if add_to_hist:

            event_descr = ''
            old_count = len(old_sel)

            if new_sel:

                event_descr += 'Select "%s"' % obj.get_name()

            if old_count:

                event_descr += '\n\n' if new_sel else ''

                if old_count > 1:

                    event_descr += 'Deselect %d objects:\n' % old_count

                    for old_obj in old_sel:
                        event_descr += '\n    "%s"' % old_obj.get_name()

                else:

                    event_descr += 'Deselect "%s"' % list(old_sel)[0].get_name()

            if event_descr:

                obj_data = {}
                event_data = {"objects": obj_data}

                for old_obj in old_sel:
                    obj_data[old_obj.get_id()] = {"selection_state": {"main": False}}

                for new_obj in new_sel:
                    obj_data[new_obj.get_id()] = {"selection_state": {"main": True}}

                # make undo/redoable
                Mgr.do("add_history", event_descr, event_data)

    def clear(self, add_to_hist=True):

        sel = self.get()

        if not sel:
            return

        for obj in sel:
            obj.update_selection_state(False)

        sel = sel[:]
        Selection.clear(self)

        PendingTasks.add(self.update, "update_selection", "ui")

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

    def delete(self, add_to_hist=True):

        sel = self.get()

        if not sel:
            return

        PendingTasks.add(self.update, "update_selection", "ui")

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

            for obj in sel:
                obj_data[obj.get_id()] = obj.get_data_to_store("deletion")

        for obj in sel[:]:
            obj.destroy()

        if add_to_hist:
            event_data["object_ids"] = set(Mgr.get("object_ids"))
            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data, update_time_id=False)


class SubLevelSelection(Selection):

    def __init__(self, obj_level, subobjs=None):

        Selection.__init__(self, obj_level, subobjs)

        self._groups = {}

        for obj in subobjs:
            self._groups.setdefault(obj.get_toplevel_object().get_id(), []).append(obj)

    def add(self, subobj, add_to_hist=True):

        sel = self.get()
        old_sel = set(sel)
        sel_to_add = set(subobj.get_special_selection())
        common = old_sel & sel_to_add

        if common:
            sel_to_add -= common

        if not sel_to_add:
            return False

        geom_data_objs = set()
        groups = self._groups

        for obj in sel_to_add:
            geom_data_obj = obj.get_geom_data_object()
            geom_data_obj.set_selected(obj, True)
            geom_data_objs.add(geom_data_obj)
            groups.setdefault(obj.get_toplevel_object().get_id(), []).append(obj)

        sel.extend(sel_to_add)

        PendingTasks.add(self.update, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon"}
            event_descr = 'Add to %s selection' % subobj_descr[self.get_object_level()]
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def remove(self, subobj, add_to_hist=True):

        sel = self.get()
        old_sel = set(sel)
        sel_to_remove = set(subobj.get_special_selection())
        common = old_sel & sel_to_remove

        if not common:
            return False

        geom_data_objs = set()
        groups = self._groups

        for obj in common:
            sel.remove(obj)
            geom_data_obj = obj.get_geom_data_object()
            geom_data_obj.set_selected(obj, False)
            geom_data_objs.add(geom_data_obj)

            topobj_id = obj.get_toplevel_object().get_id()
            groups[topobj_id].remove(obj)

            if not groups[topobj_id]:
                del groups[topobj_id]

        PendingTasks.add(self.update, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon"}
            event_descr = 'Remove from %s selection' % subobj_descr[self.get_object_level()]
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def replace(self, subobj, add_to_hist=True):

        sel = self.get()
        old_sel = set(sel)
        new_sel = set(subobj.get_special_selection())
        common = old_sel & new_sel

        if common:
            old_sel -= common
            new_sel -= common

        if not (old_sel or new_sel):
            return False

        geom_data_objs = set()

        for old_obj in old_sel:
            sel.remove(old_obj)
            geom_data_obj = old_obj.get_geom_data_object()
            geom_data_obj.set_selected(old_obj, False)
            geom_data_objs.add(geom_data_obj)

        for new_obj in new_sel:
            geom_data_obj = new_obj.get_geom_data_object()
            geom_data_obj.set_selected(new_obj, True)
            geom_data_objs.add(geom_data_obj)

        sel.extend(new_sel)

        self._groups = groups = {}

        for obj in common | new_sel:
            groups.setdefault(obj.get_toplevel_object().get_id(), []).append(obj)

        PendingTasks.add(self.update, "update_selection", "ui")

        if add_to_hist and geom_data_objs:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon"}
            event_descr = 'Replace %s selection' % subobj_descr[self.get_object_level()]
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def clear(self, add_to_hist=True):

        if not self.get():
            return False

        obj_lvl = self.get_object_level()
        geom_data_objs = []

        for obj_id in self._groups:
            geom_data_obj = Mgr.get("object", obj_id).get_geom_object().get_geom_data_object()
            geom_data_obj.clear_selection(obj_lvl)
            geom_data_objs.append(geom_data_obj)

        self._groups = {}
        Selection.clear(self)

        PendingTasks.add(self.update, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon"}
            event_descr = 'Clear %s selection' % subobj_descr[obj_lvl]
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def delete(self, add_to_hist=True):

        if not self.get():
            return False

        obj_lvl = self.get_object_level()
        geom_data_objs = []

        for obj_id in self._groups:
            geom_data_obj = Mgr.get("object", obj_id).get_geom_object().get_geom_data_object()
            geom_data_objs.append(geom_data_obj)

        self._groups = {}
        Selection.clear(self)

        PendingTasks.add(self.update, "update_selection", "ui")

        for geom_data_obj in geom_data_objs:
            geom_data_obj.delete_selection(obj_lvl)

        if add_to_hist:

            Mgr.do("update_history_time")

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon"}
            event_descr = 'Delete %s selection' % subobj_descr[obj_lvl]
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("subobj_change")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        return True


class SelectionManager(BaseObject):

    def __init__(self):

        self._mouse_start_pos = ()
        self._picked_point = None
        self._update_needed = False

        self._obj_id = None
        self._sel_obj_ids = set()
        self._selection = TopLevelSelection()
        self._subobj_selection = None
        self._pixel_under_mouse = VBase4()

        Mgr.set_global("selection_count", 0)
        Mgr.set_global("sel_color_count", 0)

        Mgr.expose("selection", self.__get_selection)
        Mgr.expose("sel_obj_ids", lambda: self._sel_obj_ids)

        PendingTasks.add_task_id("update_selection", "object")
        PendingTasks.add_task_id("update_selection", "ui")

    def setup(self):

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

        status_data = Mgr.get_global("status_data")
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

        def force_cursor_update(transf_type):

            self._pixel_under_mouse = VBase4() # force an update of the cursor
                                               # next time self.__update_cursor()
                                               # is called

        Mgr.add_app_updater("active_transform_type", force_cursor_update)
        Mgr.add_app_updater("active_obj_level", self.__update_subobj_selection,
                            kwargs=["restore"])
        Mgr.accept("update_subobj_selection", self.__update_subobj_selection)
        Mgr.accept("update_sel_obj_ids", self.__update_selected_object_ids)

        return True

    def __get_selection(self, obj_lvl=""):

        if obj_lvl == "top":
            return self._selection

        active_obj_lvl = Mgr.get_global("active_obj_level")

        return self._selection if active_obj_lvl == "top" else self._subobj_selection

    def __enter_selection_mode(self, prev_state_id, is_active):

        Mgr.add_task(self.__update_cursor, "update_cursor")
        Mgr.do("enable_transf_gizmo")

        transf_type = Mgr.get_global("active_transform_type")

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

        Mgr.set_global("active_transform_type", transf_type)
        Mgr.update_app("active_transform_type", transf_type)

        if transf_type:
            Mgr.update_app("status", "select", transf_type, "idle")
        else:
            Mgr.update_app("status", "select", "")

    def __update_subobj_selection(self, restore=False):

        obj_lvl = Mgr.get_global("active_obj_level")

        if obj_lvl == "top":

            self._subobj_selection = None

        else:

            if Mgr.get_global("transform_target_type") != "all":
                Mgr.set_global("transform_target_type", "all")
                Mgr.update_app("transform_target_type")

            subobjs = []

            for obj in self._selection:
                subobjs.extend(obj.get_subobj_selection(obj_lvl))

            self._subobj_selection = SubLevelSelection(obj_lvl, subobjs)

        if restore:
            task = lambda: self.__get_selection().update()
            PendingTasks.add(task, "update_selection", "ui")
        else:
            self.__get_selection().update()

    def __update_selected_object_ids(self):

        self._sel_obj_ids = set([obj.get_id() for obj in self.__get_selection()])

    def __delete_selection(self):

        selection = self.__get_selection()
        selection.delete()

        PendingTasks.handle(["object", "ui"], True)
        Mgr.do("update_picking_col_id_ranges")

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            if pixel_under_mouse == VBase4():
                Mgr.set_cursor("main")
            else:
                active_transform_type = Mgr.get_global("active_transform_type")
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

        active_transform_type = Mgr.get_global("active_transform_type")

        if active_transform_type == "rotate" \
                and Mgr.get_global("axis_constraints_rotate") == "trackball":
            prev_constraints = Mgr.get_global("prev_axis_constraints_rotate")
            Mgr.update_app("axis_constraints", "rotate", prev_constraints)

        if self._update_needed:
            self.__update_selection()

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

        self._update_needed = False
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

        obj_lvl = Mgr.get_global("active_obj_level")

        if obj_lvl == "top":

            obj = picked_obj.get_toplevel_object() if picked_obj else None

            cs_type = Mgr.get_global("coord_sys_type")
            tc_type = Mgr.get_global("transf_center_type")

            if cs_type == "local":
                Mgr.update_locally("coord_sys", cs_type, obj)

            if tc_type == "pivot":
                Mgr.update_locally("transf_center", tc_type, obj)

        elif obj_lvl == "vert":

            obj = picked_obj.get_merged_vertex() if picked_obj else None

        elif obj_lvl == "edge":

            obj = picked_obj.get_merged_edge() if picked_obj else None

        elif obj_lvl == "poly":

            obj = picked_obj

        if obj_lvl == "top":
            self._obj_id = obj.get_id() if obj else None
        else:
            self._obj_id = obj.get_picking_color_id() if obj else None

        if toggle:
            self.__toggle_select()
        else:
            self.__normal_select()

    def __normal_select(self):

        obj_lvl = Mgr.get_global("active_obj_level")
        obj_type = "object" if obj_lvl == "top" else obj_lvl
        obj = Mgr.get(obj_type, self._obj_id)

        if obj_type == "vert":
            obj = obj.get_merged_vertex() if obj else None
        elif obj_type == "edge":
            obj = obj.get_merged_edge() if obj else None

        selection = self._selection if obj_lvl == "top" else self._subobj_selection

        if obj:

            if Mgr.get_global("active_transform_type"):

                if obj in selection and len(selection) > 1:

                    # When the user clicks one of multiple selected objects, updating the
                    # selection must be delayed until it is clear whether he wants to
                    # transform the entire selection or simply have only this object
                    # selected (this is determined by checking if the mouse has moved at
                    # least a certain number of pixels by the time the left mouse button
                    # is released).

                    self._update_needed = True

                else:

                    selection.replace(obj)

                Mgr.enter_state("checking_mouse_offset")

            else:

                selection.replace(obj)

        else:

            selection.clear()

    def __update_selection(self):

        # If multiple objects were selected and no transformation occurred, a single
        # object has been selected out of that previous selection.

        obj_lvl = Mgr.get_global("active_obj_level")
        obj_type = "object" if obj_lvl == "top" else obj_lvl
        obj = Mgr.get(obj_type, self._obj_id)

        if obj_type == "vert":
            obj = obj.get_merged_vertex() if obj else None
        elif obj_type == "edge":
            obj = obj.get_merged_edge() if obj else None

        selection = self._selection if obj_lvl == "top" else self._subobj_selection
        selection.replace(obj)

    def __toggle_select(self):

        obj_lvl = Mgr.get_global("active_obj_level")
        obj_type = "object" if obj_lvl == "top" else obj_lvl
        obj = Mgr.get(obj_type, self._obj_id)

        if obj_type == "vert":
            obj = obj.get_merged_vertex() if obj else None
        elif obj_type == "edge":
            obj = obj.get_merged_edge() if obj else None

        selection = self._selection if obj_lvl == "top" else self._subobj_selection

        if obj:

            if obj in selection:
                selection.remove(obj)
                transform_allowed = False
            else:
                selection.add(obj)
                transform_allowed = Mgr.get_global("active_transform_type")

            if transform_allowed:
                Mgr.enter_state("checking_mouse_offset")

    def __access_obj_props(self):

        obj_lvl = Mgr.get_global("active_obj_level")

        if obj_lvl != "top" or not self.mouse_watcher.has_mouse():
            return

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b  # credit to coppertop @ panda3d.org
        pickable_type = PickableTypes.get(a)

        if not pickable_type or pickable_type == "transf_gizmo":
            return

        picked_obj = Mgr.get(pickable_type, color_id)
        obj = picked_obj.get_toplevel_object() if picked_obj else None

        if obj:
            Mgr.update_remotely("obj_props_access", obj.get_id())


MainObjects.add_class(SelectionManager)
