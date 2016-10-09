from ..base import *
from .base import UVMgr


class SelectionManager(BaseObject):

    def __init__(self, uv_editor):

        self._uv_editor = uv_editor
        self._mouse_start_pos = ()
        self._pixel_under_mouse = VBase4()
        self._obj_lvl = "top"
        self._obj_id = None
        self._models = []
        self._selections = {"vert": set(), "edge": set(), "poly": set()}
        self._original_sel = {}

    def setup(self):

        add_state = Mgr.add_state
        add_state("uv_edit_mode", -10, self.__enter_edit_mode, self.__exit_edit_mode)

        bind = Mgr.bind_state
        bind("uv_edit_mode", "uv edit -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("uv_edit_mode", "normal select subobjs", "mouse1", self.__select)
        mod_ctrl = Mgr.get("mod_ctrl")
        bind("uv_edit_mode", "toggle-select subobjs", "%d|mouse1" % mod_ctrl,
             lambda: self.__select(toggle=True))

        status_data = GlobalData["status_data"]
        mode_text = "Edit UVs"
        info_text = "(<Ctrl>-)LMB to (toggle-)select subobjects; <space> to navigate"
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

        selection = Mgr.get("selection", "top")

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

            if GlobalData["active_obj_level"] != "top":
                GlobalData["active_obj_level"] = "top"
                Mgr.update_app("active_obj_level")

            if GlobalData["active_transform_type"]:
                GlobalData["active_transform_type"] = ""
                Mgr.update_app("active_transform_type", "")

            selection = Mgr.get("selection", "top")
            models = self._models = self.__get_models(selection)
            original_selections = self._original_sel

            for model in models:

                geom_data_obj = model.get_geom_object().get_geom_data_object()
                original_selections[geom_data_obj] = orig_sel = {}

                for subobj_lvl in ("vert", "edge", "poly"):
                    orig_sel[subobj_lvl] = geom_data_obj.get_selection(subobj_lvl)
                    geom_data_obj.clear_selection(subobj_lvl, False)

            self.__make_grouped_models_accessible(selection)

        Mgr.add_task(self.__update_cursor, "update_cursor")

        Mgr.update_app("status", "edit_uvs")

    def __exit_edit_mode(self, next_state_id, is_active):

        if not is_active:

            for geom_data_obj, orig_sel in self._original_sel.iteritems():

                for subobj_lvl in ("vert", "edge", "poly"):

                    geom_data_obj.clear_selection(subobj_lvl, False)

                    for subobj in orig_sel[subobj_lvl]:
                        geom_data_obj.set_selected(subobj, True, False)

            self.__reset()
            selection = Mgr.get("selection", "top")
            self.__make_grouped_models_accessible(selection, False)

        Mgr.remove_task("update_cursor")
        Mgr.set_cursor("main")

    def __reset(self):

        self._mouse_start_pos = ()
        self._pixel_under_mouse = VBase4()
        self._obj_lvl = "top"
        self._color_id = None
        self._selections = {"vert": set(), "edge": set(), "poly": set()}
        self._original_sel = {}
        self._models = []

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

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
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

        if not self.mouse_watcher.has_mouse():
            return

        screen_pos = Point2(self.mouse_watcher.get_mouse())
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        self._mouse_start_pos = (mouse_pointer.get_x(), mouse_pointer.get_y())

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b  # credit to coppertop @ panda3d.org
        pickable_type, picked_obj = self.__get_picked_object(color_id, a)

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

            subobj = subobj.get_merged_object()
            geom_data_obj = subobj.get_geom_data_object()

            if obj_lvl == "edge":
                geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, subobj, True)
            else:
                geom_data_obj.set_selected(subobj, True, False)

            selection.add(subobj)

            if obj_lvl == "poly":
                color_ids.add(self._color_id)
            else:
                color_ids.update(geom_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                                 for s_id in subobj)

        self._uv_editor.sync_selection(color_ids)

    def __toggle_select(self):

        obj_lvl = self._obj_lvl
        selection = self._selections[obj_lvl]

        subobj = Mgr.get(obj_lvl, self._color_id)

        if subobj:

            subobj = subobj.get_merged_object()
            color_ids = set()
            geom_data_obj = subobj.get_geom_data_object()

            if obj_lvl == "poly":
                color_ids.add(self._color_id)
            else:
                color_ids.update(geom_data_obj.get_subobject(obj_lvl, s_id).get_picking_color_id()
                                 for s_id in subobj)

            if obj_lvl == "edge":
                uv_set_id = UVMgr.get("active_uv_set")
                colors = UVMgr.get("uv_selection_colors")["seam"]

            if subobj in selection:

                if obj_lvl == "edge":
                    geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, subobj, False)
                else:
                    geom_data_obj.set_selected(subobj, False, False)

                selection.remove(subobj)
                ids_to_keep = set([] if obj_lvl == "poly" else [i for x in selection for i in x])
                self._uv_editor.sync_selection(color_ids, "remove", ids_to_keep)

            else:

                if obj_lvl == "edge":
                    geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, subobj, True)
                else:
                    geom_data_obj.set_selected(subobj, True, False)

                selection.add(subobj)
                self._uv_editor.sync_selection(color_ids, "add")

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

        for color_id in color_ids:
            subobjects.add(Mgr.get(obj_lvl, color_id).get_merged_object())

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

        if op == "remove":

            ids_to_keep = keep if keep else set()

            if obj_lvl == "edge":
                for subobj in subobjects:
                    if not ids_to_keep.intersection(subobj[:]):
                        geom_data_obj = subobj.get_geom_data_object()
                        geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, subobj, False)
                        selection.discard(subobj)
            else:
                for subobj in subobjects:
                    if obj_lvl == "poly" or not ids_to_keep.intersection(subobj[:]):
                        geom_data_obj = subobj.get_geom_data_object()
                        geom_data_obj.set_selected(subobj, False, False)
                        selection.discard(subobj)

        else:

            if obj_lvl == "edge":
                for subobj in subobjects:
                    geom_data_obj = subobj.get_geom_data_object()
                    geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, subobj, True)
                    selection.add(subobj)
            else:
                for subobj in subobjects:
                    geom_data_obj = subobj.get_geom_data_object()
                    geom_data_obj.set_selected(subobj, True, False)
                    selection.add(subobj)
