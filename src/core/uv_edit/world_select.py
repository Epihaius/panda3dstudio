from ..base import *
from .base import UVMgr


class SelectionManager(BaseObject):

    def __init__(self, uv_editor):

        self._uv_editor = uv_editor
        self._mouse_start_pos = ()
        self._pixel_under_mouse = None
        self._obj_lvl = "top"
        self._color_id = None
        self._models = []
        self._selections = {"vert": set(), "edge": set(), "poly": set()}
        self._original_poly_sel = {}
        self._restore_pick_via_poly = False
        self._restore_pick_by_aiming = False

        # the following variables are used to pick a subobject using its polygon
        self._picked_poly = None
        self._tmp_color_id = None
        self._toggle_select = False
        self._cursor_id = ""
        self._aux_pixel_under_mouse = None

    def setup(self):

        add_state = Mgr.add_state
        add_state("uv_edit_mode", -10, self.__enter_edit_mode, self.__exit_edit_mode)
        add_state("uv_picking_via_poly", -11, self.__start_uv_picking_via_poly)

        bind = Mgr.bind_state
        bind("uv_edit_mode", "uv edit -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("uv_edit_mode", "default select uvs", "mouse1", self.__select)
        mod_ctrl = GlobalData["mod_key_codes"]["ctrl"]
        bind("uv_edit_mode", "toggle-select uvs", "{:d}|mouse1".format(mod_ctrl),
             lambda: self.__select(toggle=True))
        bind("uv_edit_mode", "uv edit -> center view on objects", "c",
             lambda: Mgr.do("center_view_on_objects"))
        bind("uv_picking_via_poly", "select uv via poly",
             "mouse1-up", self.__select_uv_via_poly)
        bind("uv_picking_via_poly", "cancel uv select via poly",
             "mouse3-up", self.__cancel_select_via_poly)

        status_data = GlobalData["status_data"]
        mode_text = "Select UVs"
        info_text = "<Space> to navigate; (<Ctrl>-)LMB to (toggle-)select subobjects"
        status_data["edit_uvs"] = {"mode": mode_text, "info": info_text}

    def __get_models(self, objs):

        def get_grouped_models(group, models):

            for member in group.get_members():
                if member.get_type() == "model" and member.get_geom_type() != "basic_geom":
                    models.append(member)
                elif member.get_type() == "group" and not (member.is_open()
                        or member.get_member_types_id() == "collision"):
                    get_grouped_models(member, models)

        models = []

        for obj in objs:
            if obj.get_type() == "model" and obj.get_geom_type() != "basic_geom":
                models.append(obj)
            elif obj.get_type() == "group" and not (obj.is_open()
                    or obj.get_member_types_id() == "collision"):
                get_grouped_models(obj, models)

        return models

    def get_models(self):

        return self._models

    def __make_grouped_models_accessible(self, objs, accessible=True):

        selection = Mgr.get("selection_top")

        def process_grouped_models(group, selection):

            for member in group.get_members():
                if member.get_type() == "model" and member.get_geom_type() != "basic_geom":
                    if accessible:
                        selection.add([member], add_to_hist=False, update=False)
                        member.get_bbox().get_origin().detach_node()
                    else:
                        selection.remove([member], add_to_hist=False, update=False)
                        member.get_bbox().get_origin().reparent_to(member.get_origin())
                elif member.get_type() == "group" and not (member.is_open()
                        or member.get_member_types_id() == "collision"):
                    process_grouped_models(member, selection)

        for obj in objs:
            if obj.get_type() == "group" and not (obj.is_open()
                    or obj.get_member_types_id() == "collision"):
                process_grouped_models(obj, selection)

    def __enter_edit_mode(self, prev_state_id, is_active):

        if not is_active:

            if GlobalData["subobj_edit_options"]["pick_via_poly"]:

                self._restore_pick_via_poly = True

                if not GlobalData["uv_edit_options"]["pick_via_poly"]:
                    GlobalData["subobj_edit_options"]["pick_via_poly"] = False
                    Mgr.update_interface("", "picking_via_poly")

            elif GlobalData["uv_edit_options"]["pick_via_poly"]:

                GlobalData["subobj_edit_options"]["pick_via_poly"] = True
                Mgr.update_interface("", "picking_via_poly", True)

            if GlobalData["subobj_edit_options"]["pick_by_aiming"]:

                self._restore_pick_by_aiming = True

                if not GlobalData["uv_edit_options"]["pick_by_aiming"]:
                    GlobalData["subobj_edit_options"]["pick_by_aiming"] = False

            elif GlobalData["uv_edit_options"]["pick_by_aiming"]:

                GlobalData["subobj_edit_options"]["pick_by_aiming"] = True

            if GlobalData["active_obj_level"] != "top":
                GlobalData["active_obj_level"] = "top"
                Mgr.update_app("active_obj_level")

            if GlobalData["active_transform_type"]:
                GlobalData["active_transform_type"] = ""
                Mgr.update_app("active_transform_type", "")

            selection = Mgr.get("selection_top")
            models = self._models = self.__get_models(selection)
            original_poly_sel = self._original_poly_sel

            for model in models:

                geom_data_obj = model.get_geom_object().get_geom_data_object()
                original_poly_sel[geom_data_obj] = geom_data_obj.get_selection("poly")
                geom_data_obj.clear_selection("poly", False)

                for subobj_lvl in ("vert", "edge"):
                    geom_data_obj.create_selection_backup(subobj_lvl)
                    geom_data_obj.clear_selection(subobj_lvl, False)

            self.__make_grouped_models_accessible(selection)

            if prev_state_id == "navigation_mode":
                task = lambda: Mgr.enter_state("navigation_mode")
                task_id = "enter_nav_mode"
                PendingTasks.add(task, task_id, "ui", sort=100)

        Mgr.add_task(self.__update_cursor, "update_cursor")

        Mgr.update_app("status", ["edit_uvs"])

    def __exit_edit_mode(self, next_state_id, is_active):

        if not is_active:

            original_poly_sel = self._original_poly_sel

            for model in self._models:

                geom_data_obj = model.get_geom_object().get_geom_data_object()

                for subobj_lvl in ("vert", "edge", "poly"):
                    geom_data_obj.clear_selection(subobj_lvl, force=True)
                    geom_data_obj.restore_selection_backup(subobj_lvl)

                poly_sel = original_poly_sel[geom_data_obj]
                geom_data_obj.update_selection(subobj_lvl, poly_sel, [], False)

            if self._restore_pick_via_poly:
                GlobalData["subobj_edit_options"]["pick_via_poly"] = True
            else:
                Mgr.update_interface_locally("", "picking_via_poly", False)

            if self._restore_pick_by_aiming:
                GlobalData["subobj_edit_options"]["pick_by_aiming"] = True
            else:
                GlobalData["subobj_edit_options"]["pick_by_aiming"] = False

            self.__reset()
            selection = Mgr.get("selection_top")
            self.__make_grouped_models_accessible(selection, False)

        Mgr.remove_task("update_cursor")
        Mgr.set_cursor("main")

    def __reset(self):

        self._mouse_start_pos = ()
        self._pixel_under_mouse = None
        self._obj_lvl = "top"
        self._color_id = None
        self._models = []
        self._selections = {"vert": set(), "edge": set(), "poly": set()}
        self._original_poly_sel = {}
        self._restore_pick_via_poly = False
        self._restore_pick_by_aiming = False

    def set_object_level(self, obj_lvl):

        self._obj_lvl = obj_lvl
        GlobalData["active_obj_level"] = obj_lvl
        obj_root = Mgr.get("object_root")
        picking_masks = Mgr.get("picking_masks")

        models = self._models

        if obj_lvl == "top":

            obj_root.show(picking_masks["all"])

            for model in models:
                geom_data_obj = model.get_geom_object().get_geom_data_object()
                geom_data_obj.show_top_level()

        else:

            obj_root.hide(picking_masks["all"])

            for model in models:
                geom_data_obj = model.get_geom_object().get_geom_data_object()
                geom_data_obj.show_subobj_level(obj_lvl)
                geom_data_obj.show_tex_seams(obj_lvl)

    def __update_cursor(self, task):

        obj_lvl = self._obj_lvl
        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            cursor_id = "main"

            if pixel_under_mouse != VBase4():

                if (obj_lvl == "edge" and GlobalData["uv_edit_options"]["sel_edges_by_seam"]):

                    r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b

                    if GlobalData["uv_edit_options"]["pick_via_poly"]:

                        poly = Mgr.get("poly", color_id)

                        if poly:

                            geom_data_obj = poly.get_geom_data_object()
                            uv_data_obj = self._uv_editor.get_uv_data_object(geom_data_obj)
                            merged_edges = uv_data_obj.get_merged_edges()

                            for edge_id in poly.get_edge_ids():
                                if len(merged_edges[edge_id]) == 1:
                                    cursor_id = "select"
                                    break

                    else:

                        edge = Mgr.get("edge", color_id)

                        if edge:

                            geom_data_obj = edge.get_geom_data_object()
                            uv_data_obj = self._uv_editor.get_uv_data_object(geom_data_obj)
                            merged_edge = uv_data_obj.get_merged_edge(edge.get_id())

                            if len(merged_edge) == 1:
                                cursor_id = "select"

                else:

                    cursor_id = "select"

            Mgr.set_cursor(cursor_id)
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __get_picked_object(self, color_id, obj_type_id):

        if not color_id:
            return "", None

        pickable_type = PickableTypes.get(obj_type_id)

        if not pickable_type:
            return "", None

        picked_obj = Mgr.get(pickable_type, color_id)

        return (pickable_type, picked_obj) if picked_obj else ("", None)

    def __select(self, toggle=False):

        if not (self.mouse_watcher.has_mouse() and self._pixel_under_mouse):
            return

        screen_pos = Point2(self.mouse_watcher.get_mouse())
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        self._mouse_start_pos = (mouse_pointer.get_x(), mouse_pointer.get_y())

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b
        pickable_type, picked_obj = self.__get_picked_object(color_id, a)

        obj_lvl = self._obj_lvl

        if obj_lvl == "vert":

            if GlobalData["uv_edit_options"]["pick_via_poly"]:
                obj = picked_obj if picked_obj and pickable_type == "poly" else None
                self._picked_poly = obj
            else:
                obj = picked_obj.get_merged_vertex() if picked_obj else None

        elif obj_lvl == "edge":

            if GlobalData["uv_edit_options"]["pick_via_poly"]:

                obj = picked_obj if picked_obj and pickable_type == "poly" else None

                if obj and GlobalData["uv_edit_options"]["sel_edges_by_seam"]:

                    uv_data_obj = self._uv_editor.get_uv_data_object(obj.get_geom_data_object())
                    merged_edges = uv_data_obj.get_merged_edges()

                    for edge_id in obj.get_edge_ids():
                        if len(merged_edges[edge_id]) == 1:
                            break
                    else:
                        obj = None

                self._picked_poly = obj

            else:

                obj = picked_obj.get_merged_edge() if picked_obj else None

                if obj and GlobalData["uv_edit_options"]["sel_edges_by_seam"]:

                    uv_data_obj = self._uv_editor.get_uv_data_object(obj.get_geom_data_object())
                    merged_edge = uv_data_obj.get_merged_edge(obj.get_id())

                    if len(merged_edge) > 1:
                        obj = None

        elif obj_lvl == "poly":
            obj = picked_obj

        if self._picked_poly:
            self._toggle_select = toggle
            Mgr.enter_state("uv_picking_via_poly")
            return

        self._color_id = obj.get_picking_color_id() if obj else None

        if toggle:
            self.__toggle_select()
        else:
            self.__regular_select()

    def __get_selected_subobjects(self, subobj):

        obj_lvl = self._obj_lvl
        geom_data_obj = subobj.get_geom_data_object()
        uv_data_obj = self._uv_editor.get_uv_data_object(geom_data_obj)

        if obj_lvl == "poly":

            uv_poly = uv_data_obj.get_subobject("poly", subobj.get_id())
            selected_uv_objs = set(uv_poly.get_special_selection())
            selected_subobjs = selected_uv_objs.copy()

            return selected_subobjs, selected_uv_objs

        merged_subobjs = (geom_data_obj.get_merged_vertices() if obj_lvl == "vert"
                          else geom_data_obj.get_merged_edges())
        merged_uv_objs = (uv_data_obj.get_merged_vertices() if obj_lvl == "vert"
                          else uv_data_obj.get_merged_edges())

        if GlobalData["uv_edit_options"]["pick_via_poly"]:
            uv_subobj = merged_uv_objs[subobj.get_id()]
            selected_subobjs = set(merged_subobjs[s.get_id()]
                                   for s in uv_subobj.get_special_selection())
            selected_uv_objs = set(merged_uv_objs[s.get_id()]
                                   for s in uv_subobj.get_special_selection())
        else:
            uv_subobjs = [merged_uv_objs[s_id] for s_id in subobj.get_merged_object()]
            selected_subobjs = set(merged_subobjs[s.get_id()] for uv_s in uv_subobjs
                                   for s in uv_s.get_special_selection())
            selected_uv_objs = set(merged_uv_objs[s.get_id()] for uv_s in uv_subobjs
                                   for s in uv_s.get_special_selection())

        return selected_subobjs, selected_uv_objs

    def __regular_select(self):

        obj_lvl = self._obj_lvl
        models = self._models

        if obj_lvl == "edge":

            uv_set_id = UVMgr.get("active_uv_set")
            colors = UVMgr.get("uv_selection_colors")["seam"]
            color = colors["unselected"]

            for model in models:
                geom_data_obj = model.get_geom_object().get_geom_data_object()
                geom_data_obj.clear_tex_seam_selection(uv_set_id, color)

        else:

            for model in models:
                geom_data_obj = model.get_geom_object().get_geom_data_object()
                geom_data_obj.clear_selection(obj_lvl, False)

        selection = self._selections[obj_lvl]
        selection.clear()
        subobj = Mgr.get(obj_lvl, self._color_id)
        color_ids = set()

        if subobj:

            merged_subobj = subobj.get_merged_object()
            geom_data_obj = subobj.get_geom_data_object()

            if obj_lvl != "poly" and GlobalData["uv_edit_options"]["pick_via_poly"]:
                poly = self._picked_poly
                ids = set(poly.get_vertex_ids() if obj_lvl == "vert" else poly.get_edge_ids())
                ids.intersection_update(merged_subobj)
                subobj = geom_data_obj.get_subobject(obj_lvl, ids.pop())

            selected_subobjs, selected_uv_objs = self.__get_selected_subobjects(subobj)

            if obj_lvl == "edge":
                for s in selected_subobjs:
                    geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, s, True)
            else:
                geom_data_obj.update_selection(obj_lvl, selected_subobjs, [], False)

            selection.update(selected_uv_objs)

            if obj_lvl == "poly":
                color_ids.add(self._color_id)
            elif GlobalData["uv_edit_options"]["pick_via_poly"]:
                color_ids.add(subobj.get_picking_color_id())
            else:
                color_ids.update(geom_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                                 for s_id in merged_subobj)

        self._uv_editor.sync_selection(color_ids)

    def __toggle_select(self):

        obj_lvl = self._obj_lvl
        selection = self._selections[obj_lvl]

        subobj = Mgr.get(obj_lvl, self._color_id)

        if subobj:

            merged_subobj = subobj.get_merged_object()
            geom_data_obj = subobj.get_geom_data_object()
            uv_data_obj = self._uv_editor.get_uv_data_object(geom_data_obj)

            if obj_lvl != "poly" and GlobalData["uv_edit_options"]["pick_via_poly"]:
                poly = self._picked_poly
                ids = set(poly.get_vertex_ids() if obj_lvl == "vert" else poly.get_edge_ids())
                ids.intersection_update(merged_subobj)
                subobj = geom_data_obj.get_subobject(obj_lvl, ids.pop())

            merged_uv_obj = uv_data_obj.get_subobject(obj_lvl, subobj.get_id()).get_merged_object()
            selected_subobjs, selected_uv_objs = self.__get_selected_subobjects(subobj)
            color_ids = set()

            if obj_lvl == "poly":
                color_ids.add(self._color_id)
            elif GlobalData["uv_edit_options"]["pick_via_poly"]:
                color_ids.add(subobj.get_picking_color_id())
            else:
                color_ids.update(geom_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                                 for s_id in merged_subobj)

            if obj_lvl == "edge":
                uv_set_id = UVMgr.get("active_uv_set")
                colors = UVMgr.get("uv_selection_colors")["seam"]

            if merged_uv_obj in selection:

                selection.difference_update(selected_uv_objs)

                if obj_lvl != "poly":
                    merged_subobjs = (geom_data_obj.get_merged_vertices() if obj_lvl == "vert"
                                      else geom_data_obj.get_merged_edges())
                    sel_merged_subobjs = set(merged_subobjs[s_id] for s in selection for s_id in s
                                             if s_id in merged_subobjs)
                    # make sure that merged subobjects corresponding to at least one selected
                    # UV object stay selected
                    selected_subobjs -= sel_merged_subobjs

                if obj_lvl == "edge":
                    for s in selected_subobjs:
                        geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, s, False)
                else:
                    geom_data_obj.update_selection(obj_lvl, [], selected_subobjs, False)

                ids_to_keep = set([] if obj_lvl == "poly" else [i for x in selection for i in x])
                self._uv_editor.sync_selection(color_ids, "remove", ids_to_keep)

            else:

                if obj_lvl == "edge":
                    for s in selected_subobjs:
                        geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, s, True)
                else:
                    geom_data_obj.update_selection(obj_lvl, selected_subobjs, [], False)

                selection.update(selected_uv_objs)
                self._uv_editor.sync_selection(color_ids, "add")

    def __start_uv_picking_via_poly(self, prev_state_id, is_active):

        Mgr.add_task(self.__hilite_subobj, "hilite_subobj")
        Mgr.remove_task("update_cursor")
        subobj_lvl = GlobalData["active_obj_level"]

        if subobj_lvl == "edge" and GlobalData["uv_edit_options"]["sel_edges_by_seam"]:
            category = "uv_seam"
        else:
            category = ""

        geom_data_obj = self._picked_poly.get_geom_data_object()
        merged_edges = self._uv_editor.get_uv_data_object(geom_data_obj).get_merged_edges()
        geom_data_obj.init_subobj_picking_via_poly(subobj_lvl, self._picked_poly, category, merged_edges)
        # temporarily select picked poly
        geom_data_obj.update_selection("poly", [self._picked_poly], [], False)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.get_geom_object().get_geom_data_object()

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable(False)

        Mgr.update_app("status", ["picking_via_poly"])

    def __hilite_subobj(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            if pixel_under_mouse != VBase4():

                r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                color_id = r << 16 | g << 8 | b
                geom_data_obj = self._picked_poly.get_geom_data_object()
                subobj_lvl = GlobalData["active_obj_level"]

                # highlight temporary subobject
                if geom_data_obj.hilite_temp_subobject(subobj_lvl, color_id):
                    self._tmp_color_id = color_id

            self._pixel_under_mouse = pixel_under_mouse

        not_hilited = pixel_under_mouse in (VBase4(), VBase4(1., 1., 1., 1.))
        cursor_id = "main" if not_hilited else "select"

        if GlobalData["uv_edit_options"]["pick_by_aiming"]:

            aux_pixel_under_mouse = Mgr.get("aux_pixel_under_mouse")

            if not_hilited or self._aux_pixel_under_mouse != aux_pixel_under_mouse:

                if not_hilited and aux_pixel_under_mouse != VBase4():

                    r, g, b, a = [int(round(c * 255.)) for c in aux_pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    geom_data_obj = self._picked_poly.get_geom_data_object()
                    subobj_lvl = GlobalData["active_obj_level"]

                    # highlight temporary subobject
                    if geom_data_obj.hilite_temp_subobject(subobj_lvl, color_id):
                        self._tmp_color_id = color_id
                        cursor_id = "select"

                self._aux_pixel_under_mouse = aux_pixel_under_mouse

        if self._cursor_id != cursor_id:
            Mgr.set_cursor(cursor_id)
            self._cursor_id = cursor_id

        return task.cont

    def __select_uv_via_poly(self):

        Mgr.remove_task("hilite_subobj")
        Mgr.enter_state("uv_edit_mode")
        subobj_lvl = GlobalData["active_obj_level"]
        geom_data_obj = self._picked_poly.get_geom_data_object()

        if self._tmp_color_id is None:

            obj = None

        else:

            if subobj_lvl == "vert":

                vert_id = Mgr.get("vert", self._tmp_color_id).get_id()
                obj = geom_data_obj.get_merged_vertex(vert_id)

            elif subobj_lvl == "edge":

                edge_id = Mgr.get("edge", self._tmp_color_id).get_id()
                obj = geom_data_obj.get_merged_edge(edge_id)

                if GlobalData["uv_edit_options"]["sel_edges_by_seam"]:

                    uv_data_obj = self._uv_editor.get_uv_data_object(obj.get_geom_data_object())
                    merged_edge = uv_data_obj.get_merged_edge(edge_id)

                    if len(merged_edge) > 1:
                        obj = None

        self._color_id = obj.get_picking_color_id() if obj else None

        if self._toggle_select:
            self.__toggle_select()
        else:
            self.__regular_select()

        geom_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.get_geom_object().get_geom_data_object()

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._toggle_select = False
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

    def __cancel_select_via_poly(self):

        Mgr.remove_task("hilite_subobj")
        Mgr.enter_state("uv_edit_mode")
        subobj_lvl = GlobalData["active_obj_level"]

        geom_data_obj = self._picked_poly.get_geom_data_object()
        geom_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.get_geom_object().get_geom_data_object()

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._toggle_select = False
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

    def sync_selection(self, color_ids, op="replace", keep=None, object_level=None):

        # "keep" is a set of IDs of subobjects that must remain selected;
        # since it can happen that e.g. a selected merged vertex in the viewport of
        # the main window shares only some of the vertices with the merged vertices
        # that were deselected (by toggle-selection) in the UV Editor window, this
        # merged vertex itself should not be deselected; this can be determined by
        # checking the intersection of the "keep" parameter and the set of vertex
        # IDs associated with this selected merged vertex.

        obj_lvl = self._obj_lvl if object_level is None else object_level
        selection = self._selections[obj_lvl]
        subobjects = set()
        uv_objects = set()

        for color_id in color_ids:
            subobj = Mgr.get(obj_lvl, color_id)
            subobjects.add(subobj.get_merged_object())
            geom_data_obj = subobj.get_geom_data_object()
            uv_data_obj = self._uv_editor.get_uv_data_object(geom_data_obj)
            uv_objects.add(uv_data_obj.get_subobject(obj_lvl, subobj.get_id()).get_merged_object())

        if obj_lvl == "edge":
            uv_set_id = UVMgr.get("active_uv_set")
            colors = UVMgr.get("uv_selection_colors")["seam"]
            color = colors["unselected"]

        if op == "replace":

            selection.clear()
            models = self._models

            if obj_lvl == "edge":
                for model in models:
                    geom_data_obj = model.get_geom_object().get_geom_data_object()
                    geom_data_obj.clear_tex_seam_selection(uv_set_id, color)
            else:
                for model in models:
                    geom_data_obj = model.get_geom_object().get_geom_data_object()
                    geom_data_obj.clear_selection(obj_lvl, False)

        subobj_sel = {}

        if op == "remove":

            ids_to_keep = keep if keep else set()

            if obj_lvl == "edge":

                for subobj in subobjects:

                    if not ids_to_keep.intersection(subobj):
                        geom_data_obj = subobj.get_geom_data_object()
                        geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, subobj, False)

                    selection.difference_update(uv_objects)

            else:

                for subobj in subobjects:

                    if obj_lvl == "poly" or not ids_to_keep.intersection(subobj):
                        geom_data_obj = subobj.get_geom_data_object()
                        subobj_sel.setdefault(geom_data_obj, []).append(subobj)

                    selection.difference_update(uv_objects)

            for geom_data_obj, subobjs in subobj_sel.items():
                geom_data_obj.update_selection(obj_lvl, [], subobjs, False)

        else:

            if obj_lvl == "edge":
                for subobj in subobjects:
                    geom_data_obj = subobj.get_geom_data_object()
                    geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, subobj, True)
                    selection.update(uv_objects)
            else:
                for subobj in subobjects:
                    geom_data_obj = subobj.get_geom_data_object()
                    subobj_sel.setdefault(geom_data_obj, []).append(subobj)
                    selection.update(uv_objects)

            for geom_data_obj, subobjs in subobj_sel.items():
                geom_data_obj.update_selection(obj_lvl, subobjs, [], False)
