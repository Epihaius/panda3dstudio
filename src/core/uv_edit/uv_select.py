from .base import *
from .uv_transform import SelectionTransformBase


class UVSelection(SelectionTransformBase):

    def __init__(self, obj_level, subobjs=None):

        SelectionTransformBase.__init__(self)

        self._objs = [] if subobjs is None else subobjs
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

    def set(self, objs):

        self._objs = objs

    def get(self):

        return self._objs

    def get_uv_data_objects(self):

        uv_data_objs = set()

        for obj in self._objs:
            uv_data_objs.add(obj.get_uv_data_object())

        return uv_data_objs

    def add(self, obj, add_to_hist=True):

        sel = self._objs

        if obj in sel:
            return False

        sel.append(obj)
        uv_data_obj = obj.get_uv_data_object()
        uv_data_obj.set_selected(obj, True)

        self.update()

        return True

    def remove(self, obj, add_to_hist=True):

        sel = self._objs

        if obj not in sel:
            return False

        sel.remove(obj)
        uv_data_obj = obj.get_uv_data_object()
        uv_data_obj.set_selected(obj, False)

        self.update()

    def replace(self, obj, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        new_sel = set([obj])
        common = old_sel & new_sel

        if common:
            old_sel -= common
            new_sel -= common

        if not (old_sel or new_sel):
            return

        uv_data_objs = set()

        for old_obj in old_sel:
            sel.remove(old_obj)
            uv_data_obj = old_obj.get_uv_data_object()
            uv_data_obj.set_selected(old_obj, False)
            uv_data_objs.add(uv_data_obj)

        for new_obj in new_sel:
            uv_data_obj = new_obj.get_uv_data_object()
            uv_data_obj.set_selected(new_obj, True)
            uv_data_objs.add(uv_data_obj)

        sel.extend(new_sel)

        self.update()

    def clear(self, add_to_hist=True):

        if not self._objs:
            return

        obj_lvl = self._obj_level
        uv_data_objs = set()

        for obj in self._objs:
            uv_data_obj = obj.get_uv_data_object()
            uv_data_objs.add(uv_data_obj)

        for uv_data_obj in uv_data_objs:
            uv_data_obj.clear_selection(obj_lvl)

        self._objs = []

        self.update()

    def update(self):

        self.update_center_pos()
        self.update_ui()


class UVSelectionBase(BaseObject):

    def __init__(self):

        self._mouse_start_pos = ()
        self._picked_point = None
        self._pixel_under_mouse = VBase4()
        self._color_id = None
        self._selections = {}
        self._can_select_single = False

        self._sel_obj_ids = set()
        self._sel_count = 0
        GlobalData.set_default("uv_selection_count", 0)
        GlobalData.set_default("uv_cursor", "")

        UVMgr.expose("sel_obj_ids", lambda: self._sel_obj_ids)
        UVMgr.expose("selection_center",
                     lambda: self._selections[self._uv_set_id][self._obj_lvl].get_center_pos())
        UVMgr.accept("update_sel_obj_ids", self.__update_selected_object_ids)
        UVMgr.accept("update_active_selection", self.__update_active_selection)

        PendingTasks.add_task_id("update_selection", "uv_object")
        PendingTasks.add_task_id("update_selection", "uv_ui")

    def setup(self):

        add_state = Mgr.add_state
        add_state("uv_edit_mode", 0, self.__enter_selection_mode, self.__exit_selection_mode,
                  interface_id="uv_window")
        add_state("checking_mouse_offset", -1,
                  self.__start_mouse_check, interface_id="uv_window")

        bind = Mgr.bind_state
        bind("uv_edit_mode", "normal select uvs",
             "mouse1", self.__select, "uv_window")
        mod_ctrl = Mgr.get("mod_ctrl")
        bind("uv_edit_mode", "toggle-select uvs", "%d|mouse1" % mod_ctrl,
             lambda: self.__select(toggle=True), "uv_window")

        def cancel_mouse_check():

            Mgr.enter_state("uv_edit_mode", "uv_window")
            self.__cancel_mouse_check()

        bind("checking_mouse_offset", "cancel mouse check uvs", "mouse1-up",
             cancel_mouse_check, "uv_window")

    def __enter_selection_mode(self, prev_state_id, is_active):

        Mgr.add_task(self.__update_cursor, "update_cursor_uvs", sort=2)
        self._transf_gizmo.enable()

    def __exit_selection_mode(self, next_state_id, is_active):

        if next_state_id != "checking_mouse_offset":
            self._pixel_under_mouse = VBase4() # force an update of the cursor
                                               # next time self.__update_cursor()
                                               # is called
            Mgr.remove_task("update_cursor_uvs")
            self._set_cursor("main")

        self._transf_gizmo.disable()

    def __update_cursor(self, task):

        pixel_under_mouse = UVMgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            if pixel_under_mouse == VBase4():
                self._set_cursor("main")
            else:
                active_transf_type = GlobalData["active_uv_transform_type"]
                default_cursor_name = "select" if not active_transf_type else active_transf_type
                cursor_name = GlobalData["uv_cursor"]
                cursor_name = cursor_name if cursor_name else default_cursor_name
                self._set_cursor(cursor_name)

            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __update_selected_object_ids(self, obj_ids):

        self._sel_obj_ids = obj_ids

    def update_selection(self, recreate=False):

        selections = self._selections[self._uv_set_id]
        obj_lvl = self._obj_lvl

        if recreate:

            subobjs = []

            for uv_data_obj in self._uv_data_objs[self._uv_set_id].itervalues():
                subobjs.extend(uv_data_obj.get_selection(obj_lvl))

            selections[obj_lvl] = UVSelection(obj_lvl, subobjs)

        selections[obj_lvl].update()

    def __update_active_selection(self):

        self.update_selection(recreate=True)

    def __check_mouse_offset(self, task):
        """
        Delay start of transformation until user has moved mouse at least 3 pixels
        in any direction, to avoid accidental transforms.

        """

        mouse_pointer = self._window.get_pointer(0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = mouse_pointer.get_y()
        mouse_start_x, mouse_start_y = self._mouse_start_pos

        if max(abs(mouse_x - mouse_start_x), abs(mouse_y - mouse_start_y)) > 3:
            UVMgr.do("init_transform", self._picked_point)
            return task.done

        return task.cont

    def __start_mouse_check(self, prev_state_id, is_active):

        Mgr.add_task(self.__check_mouse_offset, "check_mouse_offset")
        Mgr.remove_task("update_cursor_uvs")

    def __cancel_mouse_check(self):

        Mgr.remove_task("check_mouse_offset")

        if self._can_select_single:
            self.__select_single()

    def __get_picked_object(self, color_id, obj_type_id):

        if not color_id:
            return "", None

        pickable_type = PickableTypes.get(obj_type_id)

        if not pickable_type:
            return "", None

        if pickable_type == "transf_gizmo":
            return "transf_gizmo", self._transf_gizmo.select_handle(color_id)

        picked_obj = self._uv_registry[self._uv_set_id][pickable_type].get(color_id)

        return (pickable_type, picked_obj) if picked_obj else ("", None)

    def __select(self, toggle=False):

        if not self.mouse_watcher.has_mouse():
            return

        self._can_select_single = False
        mouse_pointer = self._window.get_pointer(0)
        self._mouse_start_pos = (mouse_pointer.get_x(), mouse_pointer.get_y())

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b  # credit to coppertop @ panda3d.org
        pickable_type, picked_obj = self.__get_picked_object(color_id, a)
        self._picked_point = UVMgr.get("picked_point") if picked_obj else None

        if pickable_type == "transf_gizmo":
            transf_type = picked_obj.get_transform_type()
            GlobalData["active_uv_transform_type"] = transf_type
            Mgr.update_interface("uv_window", "active_transform_type", transf_type)
            Mgr.enter_state("checking_mouse_offset", "uv_window")
            return

        obj_lvl = self._obj_lvl

        if obj_lvl == "vert":
            obj = picked_obj.get_merged_vertex() if picked_obj else None
        elif obj_lvl == "edge":
            obj = picked_obj.get_merged_edge() if picked_obj else None
        elif obj_lvl == "poly":
            obj = picked_obj

        self._color_id = obj.get_picking_color_id() if obj else None

        if toggle:
            self.__toggle_select()
        else:
            self.__normal_select()

    def __normal_select(self):

        obj_lvl = self._obj_lvl
        uv_set_id = self._uv_set_id
        selection = self._selections[uv_set_id][obj_lvl]
        subobj = self._uv_registry[uv_set_id][obj_lvl].get(self._color_id)
        color_ids = set()

        if subobj:

            subobj = subobj.get_merged_object()
            uv_data_obj = subobj.get_uv_data_object()

            if GlobalData["active_uv_transform_type"]:

                if subobj in selection and len(selection) > 1:

                    # When the user clicks one of multiple selected subobjects, updating the
                    # selection must be delayed until it is clear whether he wants to
                    # transform the entire selection or simply have only this subobject
                    # selected (this is determined by checking if the mouse has moved at
                    # least a certain number of pixels by the time the left mouse button
                    # is released).

                    self._can_select_single = True

                else:

                    selection.replace(subobj)

                    if obj_lvl == "poly":
                        color_ids.add(self._color_id)
                    else:
                        color_ids.update(uv_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                                         for s_id in subobj)

                    self._world_sel_mgr.sync_selection(color_ids)

                Mgr.enter_state("checking_mouse_offset", "uv_window")

            else:

                selection.replace(subobj)

                if obj_lvl == "poly":
                    color_ids.add(self._color_id)
                else:
                    color_ids.update(uv_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                                     for s_id in subobj)

                self._world_sel_mgr.sync_selection(color_ids)

        else:

            selection.clear()
            self._world_sel_mgr.sync_selection(color_ids)

    def __select_single(self):

        # If multiple subobjects were selected and no transformation occurred, a single
        # subobject has been selected out of that previous selection.

        obj_lvl = self._obj_lvl
        uv_set_id = self._uv_set_id
        selection = self._selections[uv_set_id][obj_lvl]
        subobj = self._uv_registry[uv_set_id][obj_lvl].get(self._color_id)
        subobj = subobj.get_merged_object()
        uv_data_obj = subobj.get_uv_data_object()
        color_ids = set()
        selection.replace(subobj)

        if obj_lvl == "poly":
            color_ids.add(self._color_id)
        else:
            color_ids.update(uv_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                             for s_id in subobj)

        self._world_sel_mgr.sync_selection(color_ids)

    def __toggle_select(self):

        obj_lvl = self._obj_lvl
        uv_set_id = self._uv_set_id
        subobj = self._uv_registry[uv_set_id][obj_lvl].get(self._color_id)

        if subobj:

            selection = self._selections[uv_set_id][obj_lvl]
            subobj = subobj.get_merged_object()
            uv_data_obj = subobj.get_uv_data_object()
            color_ids = set()

            if obj_lvl == "poly":
                color_ids.add(self._color_id)
            else:
                color_ids.update(uv_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                                 for s_id in subobj)

            if subobj in selection:
                selection.remove(subobj)
                ids_to_keep = set([] if obj_lvl == "poly" else [i for x in selection for i in x])
                self._world_sel_mgr.sync_selection(color_ids, "remove", ids_to_keep)
                transform_allowed = False
            else:
                selection.add(subobj)
                self._world_sel_mgr.sync_selection(color_ids, "add")
                transform_allowed = GlobalData["active_uv_transform_type"]

            if transform_allowed:
                Mgr.enter_state("checking_mouse_offset", "uv_window")

    def sync_selection(self, color_ids, op="replace", keep=None):

        obj_lvl = self._obj_lvl
        uv_set_id = self._uv_set_id
        uv_registry = self._uv_registry[uv_set_id][obj_lvl]
        selection = self._selections[uv_set_id][obj_lvl]
        subobjects = set()

        for color_id in color_ids:
            subobjects.add(uv_registry[color_id].get_merged_object())

        if op == "replace":
            selection.clear()

        if op == "remove":

            ids_to_keep = keep if keep else set()

            for subobj in subobjects:
                if obj_lvl == "poly" or not ids_to_keep.intersection(subobj[:]):
                    selection.remove(subobj)

        else:

            for subobj in subobjects:
                selection.add(subobj)

    def create_selections(self):

        obj_lvls = ("vert", "edge", "poly")
        self._selections[self._uv_set_id] = dict((lvl, UVSelection(lvl)) for lvl in obj_lvls)

    def delete_selections(self):

        self._selections.clear()
