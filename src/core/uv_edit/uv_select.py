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

    def add(self, subobj, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_add = set(subobj.get_special_selection())
        common = old_sel & sel_to_add

        if common:
            sel_to_add -= common

        if not sel_to_add:
            return False

        uv_data_objs = {}

        for obj in sel_to_add:
            uv_data_obj = obj.get_uv_data_object()
            uv_data_objs.setdefault(uv_data_obj, []).append(obj)

        for uv_data_obj, objs in uv_data_objs.items():
            uv_data_obj.update_selection(self._obj_level, objs, [])

        sel.extend(sel_to_add)
        self.update()

        return True

    def remove(self, subobj, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_remove = set(subobj.get_special_selection())
        common = old_sel & sel_to_remove

        if not common:
            return False

        uv_data_objs = {}

        for obj in common:
            sel.remove(obj)
            uv_data_obj = obj.get_uv_data_object()
            uv_data_objs.setdefault(uv_data_obj, []).append(obj)

        for uv_data_obj, objs in uv_data_objs.items():
            uv_data_obj.update_selection(self._obj_level, [], objs)

        self.update()

    def replace(self, subobj, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        new_sel = set(subobj.get_special_selection())
        common = old_sel & new_sel

        if common:
            old_sel -= common
            new_sel -= common

        if not (old_sel or new_sel):
            return

        uv_data_objs = {}

        for old_obj in old_sel:
            sel.remove(old_obj)
            uv_data_obj = old_obj.get_uv_data_object()
            uv_data_objs.setdefault(uv_data_obj, {"sel": [], "desel": []})["desel"].append(old_obj)

        for new_obj in new_sel:
            uv_data_obj = new_obj.get_uv_data_object()
            uv_data_objs.setdefault(uv_data_obj, {"sel": [], "desel": []})["sel"].append(new_obj)

        for uv_data_obj, objs in uv_data_objs.items():
            uv_data_obj.update_selection(self._obj_level, objs["sel"], objs["desel"])

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
        self._pixel_under_mouse = None
        self._color_id = None
        self._selections = {}
        self._can_select_single = False

        # the following variables are used to pick a subobject using its polygon
        self._picked_poly = None
        self._tmp_color_id = None
        self._toggle_select = False
        self._cursor_id = ""
        self._aux_pixel_under_mouse = None

        self._sel_obj_ids = set()
        self._sel_count = 0
        GlobalData.set_default("uv_selection_count", 0)
        GlobalData.set_default("uv_cursor", "")

        UVMgr.expose("sel_obj_ids", lambda: self._sel_obj_ids)
        UVMgr.expose("selection_center",
                     lambda: self._selections[self._uv_set_id][self._obj_lvl].get_center_pos())
        UVMgr.accept("update_sel_obj_ids", self.__update_selected_object_ids)
        UVMgr.accept("update_active_selection", self.__update_active_selection)

        GlobalData["status_data"]["select_uvs"] = status_data = {}
        info_start = "RMB to pan, MWheel or LMB+RMB to zoom; (<Ctrl>-)LMB to (toggle-)select subobjects; "
        info_text = info_start + "<W>, <E>, <R> to set transform type"
        status_data[""] = {"mode": "Select UVs", "info": info_text}
        info_idle = info_start + "LMB-drag selection or gizmo handle to transform;" \
            " <Q> to disable transforms"
        info_text = "LMB-drag to transform selection; RMB to cancel transformation"

        for transf_type in ("translate", "rotate", "scale"):
            mode_text = "Select and {} UVs".format(transf_type)
            status_data[transf_type] = {}
            status_data[transf_type]["idle"] = {"mode": mode_text, "info": info_idle}
            status_data[transf_type]["in_progress"] = {"mode": mode_text, "info": info_text}

    def setup(self):

        add_state = Mgr.add_state
        add_state("uv_edit_mode", 0, self.__enter_selection_mode, self.__exit_selection_mode,
                  interface_id="uv")
        add_state("checking_mouse_offset", -1, self.__start_mouse_check,
                  interface_id="uv")
        add_state("picking_via_poly", -1, self.__start_subobj_picking_via_poly,
                  interface_id="uv")

        bind = Mgr.bind_state
        bind("uv_edit_mode", "normal select uvs",
             "mouse1", self.__select, "uv")
        mod_ctrl = GlobalData["mod_key_codes"]["ctrl"]
        bind("uv_edit_mode", "toggle-select uvs", "{:d}|mouse1".format(mod_ctrl),
             lambda: self.__select(toggle=True), "uv")
        bind("uv_edit_mode", "transf off", "q",
             self.__set_active_transform_off, "uv")
        bind("picking_via_poly", "select subobj via poly",
             "mouse1-up", self.__select_subobj_via_poly, "uv")
        bind("picking_via_poly", "cancel subobj select via poly",
             "mouse3-up", self.__cancel_select_via_poly, "uv")

        def cancel_mouse_check():

            Mgr.enter_state("uv_edit_mode", "uv")
            self.__cancel_mouse_check()

        bind("checking_mouse_offset", "cancel mouse check uvs", "mouse1-up",
             cancel_mouse_check, "uv")

    def __enter_selection_mode(self, prev_state_id, is_active):

        Mgr.add_task(self.__update_cursor, "update_cursor_uvs", sort=2)
        self._transf_gizmo.enable()

        transf_type = GlobalData["active_uv_transform_type"]

        if transf_type:
            Mgr.update_app("status", ["select_uvs", transf_type, "idle"], "uv")
        else:
            Mgr.update_app("status", ["select_uvs", ""], "uv")

    def __exit_selection_mode(self, next_state_id, is_active):

        if next_state_id != "checking_mouse_offset":
            self._pixel_under_mouse = None  # force an update of the cursor
                                            # next time self.__update_cursor()
                                            # is called
            Mgr.remove_task("update_cursor_uvs")
            Mgr.set_cursor("main", "viewport2")

        self._transf_gizmo.enable(False)

    def __update_cursor(self, task):

        pixel_under_mouse = UVMgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            cursor_id = "main"

            if pixel_under_mouse != VBase4():

                if (self._obj_lvl == "edge" and
                        GlobalData["uv_edit_options"]["sel_edges_by_seam"]):

                    r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    pickable_type = PickableTypes.get(a)
                    registry = self._uv_registry[self._uv_set_id]

                    if pickable_type == "transf_gizmo":

                        cursor_id = "select"

                    elif GlobalData["uv_edit_options"]["pick_via_poly"]:

                        poly = registry["poly"].get(color_id)

                        if poly:

                            merged_edges = poly.get_uv_data_object().get_merged_edges()

                            for edge_id in poly.get_edge_ids():
                                if len(merged_edges[edge_id]) == 1:
                                    cursor_id = "select"
                                    break

                    else:

                        edge = registry["edge"].get(color_id)
                        merged_edge = edge.get_merged_edge() if edge else None

                        if merged_edge and len(merged_edge) == 1:
                            cursor_id = "select"

                else:

                    cursor_id = "select"

                if cursor_id == "select":

                    active_transform_type = GlobalData["active_uv_transform_type"]

                    if active_transform_type:
                        cursor_id = active_transform_type

                gizmo_cursor_id = GlobalData["uv_cursor"]
                cursor_id = gizmo_cursor_id if gizmo_cursor_id else cursor_id

            Mgr.set_cursor(cursor_id, "viewport2")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __set_active_transform_off(self):

        GlobalData["active_uv_transform_type"] = ""
        Mgr.update_interface("uv", "active_transform_type", "")
        Mgr.update_app("status", ["select_uvs", ""], "uv")

    def __update_selected_object_ids(self, obj_ids):

        self._sel_obj_ids = obj_ids

    def update_selection(self, recreate=False):

        selections = self._selections[self._uv_set_id]
        obj_lvl = self._obj_lvl

        if recreate:

            subobjs = []

            for uv_data_obj in self._uv_data_objs[self._uv_set_id].values():
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

        mouse_pointer = Mgr.get("base").win.get_pointer(0)
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

        if not (self.mouse_watcher.has_mouse() and self._pixel_under_mouse):
            return

        self._can_select_single = False
        mouse_pointer = Mgr.get("base").win.get_pointer(0)
        self._mouse_start_pos = (mouse_pointer.get_x(), mouse_pointer.get_y())
        obj_lvl = self._obj_lvl

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b
        pickable_type, picked_obj = self.__get_picked_object(color_id, a)

        if (GlobalData["active_uv_transform_type"] and obj_lvl != pickable_type == "poly"
                and GlobalData["uv_edit_options"]["pick_via_poly"]):
            self.__start_selection_via_poly(picked_obj, toggle)
            return

        self._picked_point = UVMgr.get("picked_point") if picked_obj else None

        if pickable_type == "transf_gizmo":
            transf_type = picked_obj.get_transform_type()
            GlobalData["active_uv_transform_type"] = transf_type
            Mgr.update_interface("uv", "active_transform_type", transf_type)
            Mgr.enter_state("checking_mouse_offset", "uv")
            return

        if obj_lvl == "vert":

            if GlobalData["uv_edit_options"]["pick_via_poly"]:
                obj = picked_obj if picked_obj and picked_obj.get_type() == "poly" else None
                self._picked_poly = obj
            else:
                obj = picked_obj.get_merged_vertex() if picked_obj else None

        elif obj_lvl == "edge":

            if GlobalData["uv_edit_options"]["pick_via_poly"]:

                obj = picked_obj if picked_obj and picked_obj.get_type() == "poly" else None

                if obj and GlobalData["uv_edit_options"]["sel_edges_by_seam"]:

                    merged_edges = obj.get_uv_data_object().get_merged_edges()

                    for edge_id in obj.get_edge_ids():
                        if len(merged_edges[edge_id]) == 1:
                            break
                    else:
                        obj = None

                self._picked_poly = obj

            else:

                obj = picked_obj.get_merged_edge() if picked_obj else None

                if obj and GlobalData["uv_edit_options"]["sel_edges_by_seam"] and len(obj) > 1:
                    obj = None

        elif obj_lvl == "poly":

            obj = picked_obj

        if self._picked_poly:
            self._toggle_select = toggle
            Mgr.enter_state("picking_via_poly", "uv")
            return

        self._color_id = obj.get_picking_color_id() if obj else None

        if toggle:
            self.__toggle_select()
        else:
            self.__regular_select()

    def __regular_select(self, check_mouse=True, ignore_transform=False):

        obj_lvl = self._obj_lvl
        uv_set_id = self._uv_set_id
        selection = self._selections[uv_set_id][obj_lvl]
        subobj = self._uv_registry[uv_set_id][obj_lvl].get(self._color_id)
        color_ids = set()

        if subobj:

            subobj = subobj.get_merged_object()
            uv_data_obj = subobj.get_uv_data_object()

            if GlobalData["active_uv_transform_type"] and not ignore_transform:

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
                        color_ids.update(poly.get_picking_color_id()
                                         for poly in subobj.get_special_selection())
                    else:
                        color_ids.update(uv_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                                         for s in subobj.get_special_selection() for s_id in s)

                    self._world_sel_mgr.sync_selection(color_ids)

                if check_mouse:
                    Mgr.enter_state("checking_mouse_offset", "uv")

            else:

                selection.replace(subobj)

                if obj_lvl == "poly":
                    color_ids.update(poly.get_picking_color_id()
                                     for poly in subobj.get_special_selection())
                else:
                    color_ids.update(uv_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                                     for s in subobj.get_special_selection() for s_id in s)

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
            color_ids.update(poly.get_picking_color_id()
                             for poly in subobj.get_special_selection())
        else:
            color_ids.update(uv_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                             for s in subobj.get_special_selection() for s_id in s)

        self._world_sel_mgr.sync_selection(color_ids)

    def __toggle_select(self, check_mouse=True):

        obj_lvl = self._obj_lvl
        uv_set_id = self._uv_set_id
        subobj = self._uv_registry[uv_set_id][obj_lvl].get(self._color_id)

        if subobj:

            selection = self._selections[uv_set_id][obj_lvl]
            subobj = subobj.get_merged_object()
            uv_data_obj = subobj.get_uv_data_object()
            color_ids = set()

            if obj_lvl == "poly":
                color_ids.update(poly.get_picking_color_id()
                                 for poly in subobj.get_special_selection())
            else:
                color_ids.update(uv_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                                 for s in subobj.get_special_selection() for s_id in s)

            if subobj in selection:
                selection.remove(subobj)
                ids_to_keep = set([] if obj_lvl == "poly" else [i for x in selection for i in x])
                self._world_sel_mgr.sync_selection(color_ids, "remove", ids_to_keep)
                transform_allowed = False
            else:
                selection.add(subobj)
                self._world_sel_mgr.sync_selection(color_ids, "add")
                transform_allowed = GlobalData["active_uv_transform_type"]

            if check_mouse and transform_allowed:
                Mgr.enter_state("checking_mouse_offset", "uv")

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
                if obj_lvl == "poly" or not ids_to_keep.intersection(subobj):
                    selection.remove(subobj)

        else:

            for subobj in subobjects:
                selection.add(subobj)

    def __start_selection_via_poly(self, picked_poly, toggle):

        if picked_poly:
            self._picked_poly = picked_poly
            self._toggle_select = toggle
            Mgr.enter_state("picking_via_poly", "uv")

    def __start_subobj_picking_via_poly(self, prev_state_id, is_active):

        self._transf_gizmo.set_pickable(False)
        Mgr.add_task(self.__hilite_subobj, "hilite_subobj")
        Mgr.remove_task("update_cursor_uvs")
        subobj_lvl = self._obj_lvl

        if subobj_lvl == "edge" and GlobalData["uv_edit_options"]["sel_edges_by_seam"]:
            category = "seam"
        else:
            category = ""

        uv_data_obj = self._picked_poly.get_uv_data_object()
        uv_data_obj.init_subobj_picking_via_poly(subobj_lvl, self._picked_poly, category)
        # temporarily select picked poly
        uv_data_obj.update_selection("poly", [self._picked_poly], [], False)

        for other_uv_data_obj in self._uv_data_objs[self._uv_set_id].values():
            if other_uv_data_obj is not uv_data_obj:
                other_uv_data_obj.set_pickable(False)

    def __hilite_subobj(self, task):

        pixel_under_mouse = UVMgr.get("pixel_under_mouse")
        active_transform_type = GlobalData["active_uv_transform_type"]

        if self._pixel_under_mouse != pixel_under_mouse:

            if pixel_under_mouse == VBase4():

                if active_transform_type and self._tmp_color_id is not None:
                    self.__select_subobj_via_poly(transform=True)
                    return

            else:

                r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                color_id = r << 16 | g << 8 | b
                uv_data_obj = self._picked_poly.get_uv_data_object()
                subobj_lvl = self._obj_lvl

                # highlight temporary subobject
                if uv_data_obj.hilite_temp_subobject(subobj_lvl, color_id):
                    self._tmp_color_id = color_id

            self._pixel_under_mouse = pixel_under_mouse

        not_hilited = pixel_under_mouse in (VBase4(), VBase4(1., 1., 1., 1.))
        cursor_id = "main" if not_hilited else ("select" if not active_transform_type
                                                else active_transform_type)

        if GlobalData["uv_edit_options"]["pick_by_aiming"]:

            aux_pixel_under_mouse = UVMgr.get("aux_pixel_under_mouse")

            if not_hilited or self._aux_pixel_under_mouse != aux_pixel_under_mouse:

                if not_hilited and aux_pixel_under_mouse != VBase4():

                    r, g, b, a = [int(round(c * 255.)) for c in aux_pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    uv_data_obj = self._picked_poly.get_uv_data_object()
                    subobj_lvl = self._obj_lvl

                    # highlight temporary subobject
                    if uv_data_obj.hilite_temp_subobject(subobj_lvl, color_id):
                        self._tmp_color_id = color_id
                        cursor_id = "select" if not active_transform_type else active_transform_type

                self._aux_pixel_under_mouse = aux_pixel_under_mouse

        if self._cursor_id != cursor_id:
            Mgr.set_cursor(cursor_id, "viewport2")
            self._cursor_id = cursor_id

        return task.cont

    def __select_subobj_via_poly(self, transform=False):

        Mgr.remove_task("hilite_subobj")
        Mgr.enter_state("uv_edit_mode", "uv")
        subobj_lvl = self._obj_lvl
        uv_data_obj = self._picked_poly.get_uv_data_object()

        if self._tmp_color_id is None:

            obj = None

        else:

            if subobj_lvl == "vert":
                vert_id = Mgr.get("vert", self._tmp_color_id).get_id()
                obj = uv_data_obj.get_merged_vertex(vert_id)
            elif subobj_lvl == "edge":
                edge_id = Mgr.get("edge", self._tmp_color_id).get_id()
                obj = uv_data_obj.get_merged_edge(edge_id)
                obj = (None if GlobalData["uv_edit_options"]["sel_edges_by_seam"]
                       and len(obj) > 1 else obj)

        self._color_id = obj.get_picking_color_id() if obj else None

        if self._toggle_select:
            self.__toggle_select(False)
        else:
            ignore_transform = not transform
            self.__regular_select(False, ignore_transform)

        uv_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for other_uv_data_obj in self._uv_data_objs[self._uv_set_id].values():
            if other_uv_data_obj is not uv_data_obj:
                other_uv_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._toggle_select = False
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None
        active_transform_type = GlobalData["active_uv_transform_type"]

        if transform and obj and obj.get_uv_data_object().is_selected(obj):

            if active_transform_type == "translate":
                picked_point = obj.get_center_pos(self.uv_space)
                picked_point.y = 0.
            else:
                picked_point = UVMgr.get("picked_point")

            UVMgr.do("init_transform", picked_point)
            Mgr.set_cursor(active_transform_type, "viewport2")

        self._transf_gizmo.set_pickable()

    def __cancel_select_via_poly(self):

        Mgr.remove_task("hilite_subobj")
        Mgr.enter_state("uv_edit_mode", "uv")
        subobj_lvl = self._obj_lvl

        uv_data_obj = self._picked_poly.get_uv_data_object()
        uv_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for other_uv_data_obj in self._uv_data_objs[self._uv_set_id].values():
            if other_uv_data_obj is not uv_data_obj:
                other_uv_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._toggle_select = False
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

        self._transf_gizmo.set_pickable()

    def create_selections(self):

        obj_lvls = ("vert", "edge", "poly")
        self._selections[self._uv_set_id] = dict((lvl, UVSelection(lvl)) for lvl in obj_lvls)

    def delete_selections(self):

        self._selections.clear()
