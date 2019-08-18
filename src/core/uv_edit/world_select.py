from ..base import *
from .base import UVMgr


class SelectionManager:

    def __init__(self, uv_editor):

        self._uv_editor = uv_editor
        self._mouse_start_pos = ()
        self._pixel_under_mouse = None
        self._obj_lvl = "top"
        self._color_id = None
        self._models = []
        self._selections = {"vert": set(), "edge": set(), "poly": set()}
        self._selection_op = "replace"
        self._original_poly_sel = {}
        self._restore_pick_via_poly = False
        self._restore_pick_by_aiming = False

        # the following variables are used to pick a subobject using its polygon
        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._aux_pixel_under_mouse = None

        Mgr.expose("uv_selection_set", self.__get_selection_set)
        Mgr.accept("inverse_select_uvs", self.__inverse_select)
        Mgr.accept("select_all_uvs", self.__select_all)
        Mgr.accept("clear_uv_selection", self.__select_none)
        Mgr.accept("apply_uv_selection_set", self.__apply_selection_set)
        Mgr.accept("region_select_uvs", self.__region_select)

    def setup(self):

        add_state = Mgr.add_state
        add_state("uv_edit_mode", -10, self.__enter_edit_mode, self.__exit_edit_mode)
        add_state("uv_picking_via_poly", -11, self.__init_uv_picking_via_poly)

        mod_alt = GD["mod_key_codes"]["alt"]
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        mod_shift = GD["mod_key_codes"]["shift"]
        bind = Mgr.bind_state
        bind("uv_edit_mode", "select (replace) uvs", "mouse1", self.__init_select)
        bind("uv_edit_mode", "select (add) uvs", f"{mod_ctrl}|mouse1",
             lambda: self.__init_select(op="add"))
        bind("uv_edit_mode", "select (remove) uvs", f"{mod_shift}|mouse1",
             lambda: self.__init_select(op="remove"))
        bind("uv_edit_mode", "select (toggle) uvs", f"{mod_ctrl | mod_shift}|mouse1",
             lambda: self.__init_select(op="toggle"))
        bind("uv_edit_mode", "select (replace) uvs alt", f"{mod_alt}|mouse1",
             self.__init_select)
        bind("uv_edit_mode", "select (add) uvs alt", f"{mod_alt | mod_ctrl}|mouse1",
             lambda: self.__init_select(op="add"))
        bind("uv_edit_mode", "select (remove) uvs alt", f"{mod_alt | mod_shift}|mouse1",
             lambda: self.__init_select(op="remove"))
        bind("uv_edit_mode", "select (toggle) uvs alt", f"{mod_alt | mod_ctrl | mod_shift}|mouse1",
             lambda: self.__init_select(op="toggle"))
        bind("uv_edit_mode", "uv edit -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("uv_edit_mode", "uv edit -> center view on objects", "c",
             lambda: Mgr.do("center_view_on_objects"))
        bind("uv_edit_mode", "uv edit ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))
        bind("uv_picking_via_poly", "select uv via poly",
             "mouse1-up", self.__select_uv_via_poly)
        bind("uv_picking_via_poly", "cancel uv select via poly",
             "mouse3", self.__cancel_select_via_poly)

        status_data = GD["status"]
        mode_text = "Select UVs"
        info_text = "<Space> to navigate; (<Alt>-)LMB to (region-)select subobjects"
        status_data["edit_uvs"] = {"mode": mode_text, "info": info_text}

    def __get_models(self, objs):

        def get_grouped_models(group, models):

            for member in group.get_members():
                if member.type == "model" and member.geom_type != "basic_geom":
                    models.append(member)
                elif member.type == "group" and not (member.is_open()
                        or member.get_member_types_id() == "collision"):
                    get_grouped_models(member, models)

        models = []

        for obj in objs:
            if obj.type == "model" and obj.geom_type != "basic_geom":
                models.append(obj)
            elif obj.type == "group" and not (obj.is_open()
                    or obj.get_member_types_id() == "collision"):
                get_grouped_models(obj, models)

        return models

    def get_models(self):

        return self._models

    def __make_grouped_models_accessible(self, objs, accessible=True):

        selection = Mgr.get("selection_top")

        def process_grouped_models(group, selection):

            for member in group.get_members():
                if member.type == "model" and member.geom_type != "basic_geom":
                    if accessible:
                        selection.add([member], add_to_hist=False, update=False)
                        member.bbox.origin.detach_node()
                    else:
                        selection.remove([member], add_to_hist=False, update=False)
                        member.bbox.origin.reparent_to(member.origin)
                elif member.type == "group" and not (member.is_open()
                        or member.get_member_types_id() == "collision"):
                    process_grouped_models(member, selection)

        for obj in objs:
            if obj.type == "group" and not (obj.is_open()
                    or obj.get_member_types_id() == "collision"):
                process_grouped_models(obj, selection)

    def __enter_edit_mode(self, prev_state_id, active):

        if not active:

            if GD["subobj_edit_options"]["pick_via_poly"]:

                self._restore_pick_via_poly = True

                if not GD["uv_edit_options"]["pick_via_poly"]:
                    GD["subobj_edit_options"]["pick_via_poly"] = False
                    Mgr.update_interface("main", "picking_via_poly")

            elif GD["uv_edit_options"]["pick_via_poly"]:

                GD["subobj_edit_options"]["pick_via_poly"] = True
                Mgr.update_interface("main", "picking_via_poly", True)

            if GD["subobj_edit_options"]["pick_by_aiming"]:

                self._restore_pick_by_aiming = True

                if not GD["uv_edit_options"]["pick_by_aiming"]:
                    GD["subobj_edit_options"]["pick_by_aiming"] = False

            elif GD["uv_edit_options"]["pick_by_aiming"]:

                GD["subobj_edit_options"]["pick_by_aiming"] = True

            if GD["active_transform_type"]:
                GD["active_transform_type"] = ""
                Mgr.update_app("active_transform_type", "")

            selection = Mgr.get("selection_top")
            models = self._models = self.__get_models(selection)
            original_poly_sel = self._original_poly_sel

            for model in models:

                geom_data_obj = model.geom_obj.geom_data_obj
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

    def __exit_edit_mode(self, next_state_id, active):

        if not active:

            original_poly_sel = self._original_poly_sel

            for model in self._models:

                geom_data_obj = model.geom_obj.geom_data_obj

                for subobj_lvl in ("vert", "edge", "poly"):
                    geom_data_obj.clear_selection(subobj_lvl, update_verts_to_transf=False, force=True)
                    geom_data_obj.restore_selection_backup(subobj_lvl)

                poly_sel = original_poly_sel[geom_data_obj]
                geom_data_obj.update_selection("poly", poly_sel, [], False)

            if self._restore_pick_via_poly:
                GD["subobj_edit_options"]["pick_via_poly"] = True
            else:
                Mgr.update_interface_locally("main", "picking_via_poly", False)

            if self._restore_pick_by_aiming:
                GD["subobj_edit_options"]["pick_by_aiming"] = True
            else:
                GD["subobj_edit_options"]["pick_by_aiming"] = False

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
        GD["active_obj_level"] = obj_lvl
        obj_root = Mgr.get("object_root")
        picking_mask = Mgr.get("picking_mask")

        models = self._models

        if obj_lvl == "top":

            obj_root.show(picking_mask)

            for model in models:
                geom_data_obj = model.geom_obj.geom_data_obj
                geom_data_obj.show_top_level()

            Mgr.update_remotely("selection_set", "replace", obj_lvl)

        else:

            obj_root.hide(picking_mask)
            color = UVMgr.get("uv_selection_colors")["seam"]["unselected"]

            for model in models:
                geom_data_obj = model.geom_obj.geom_data_obj
                geom_data_obj.show_subobj_level(obj_lvl)
                geom_data_obj.show_tex_seams(obj_lvl, color)

            Mgr.update_remotely("selection_set", "replace", "uv_" + obj_lvl)

    def __update_cursor(self, task):

        obj_lvl = self._obj_lvl
        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            cursor_id = "main"

            if pixel_under_mouse != VBase4():

                if obj_lvl == "edge" and GD["uv_edit_options"]["sel_edges_by_seam"]:

                    r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b

                    if GD["uv_edit_options"]["pick_via_poly"]:

                        poly = Mgr.get("poly", color_id)

                        if poly:

                            geom_data_obj = poly.geom_data_obj
                            uv_data_obj = self._uv_editor.get_uv_data_object(geom_data_obj)
                            merged_edges = uv_data_obj.merged_edges

                            for edge_id in poly.edge_ids:
                                if len(merged_edges[edge_id]) == 1:
                                    cursor_id = "select"
                                    break

                    else:

                        edge = Mgr.get("edge", color_id)

                        if edge:

                            geom_data_obj = edge.geom_data_obj
                            uv_data_obj = self._uv_editor.get_uv_data_object(geom_data_obj)
                            merged_edge = uv_data_obj.get_merged_edge(edge.id)

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

    def __get_all_subobjs(self, obj_lvl):

        subobjs = []
        geom_data_objs = [model.geom_obj.geom_data_obj
                          for model in self._models]

        for geom_data_obj in geom_data_objs:
            subobjs.extend(geom_data_obj.get_subobjects(obj_lvl).values())

        return subobjs

    def __inverse_select(self):

        obj_lvl = self._obj_lvl
        selection = self._selections[obj_lvl]
        old_sel = set(selection)
        new_sel = set(self.__get_all_subobjs(obj_lvl))
        uv_edit_options = GD["uv_edit_options"]
        pick_via_poly = uv_edit_options["pick_via_poly"]

        if pick_via_poly:
            uv_edit_options["pick_via_poly"] = False

        new_sel = self.__get_selected_uv_objects(new_sel)

        if pick_via_poly:
            uv_edit_options["pick_via_poly"] = True

        selection.clear()
        selection.update(new_sel - old_sel)
        color_ids = set()

        if obj_lvl == "poly":
            color_ids.update(poly.picking_color_id for poly in selection)
        else:
            for subobj in selection:
                color_ids.update(subobj.picking_color_ids)

        self._uv_editor.sync_selection(color_ids)
        self.sync_selection(color_ids)

    def __select_all(self):

        obj_lvl = self._obj_lvl
        selection = self._selections[obj_lvl]
        selection.clear()
        new_sel = set(self.__get_all_subobjs(obj_lvl))
        uv_edit_options = GD["uv_edit_options"]
        pick_via_poly = uv_edit_options["pick_via_poly"]

        if pick_via_poly:
            uv_edit_options["pick_via_poly"] = False

        new_sel = self.__get_selected_uv_objects(new_sel)

        if pick_via_poly:
            uv_edit_options["pick_via_poly"] = True

        selection.update(new_sel)
        color_ids = set()

        if obj_lvl == "poly":
            color_ids.update(poly.picking_color_id for poly in selection)
        else:
            for subobj in selection:
                color_ids.update(subobj.picking_color_ids)

        self._uv_editor.sync_selection(color_ids)
        self.sync_selection(color_ids)

    def __select_none(self):

        obj_lvl = self._obj_lvl
        selection = self._selections[obj_lvl]
        selection.clear()
        self._uv_editor.sync_selection(set())
        self.sync_selection(set())

    def __get_selection_set(self):

        obj_lvl = self._obj_lvl
        selection = self._selections[obj_lvl]

        if obj_lvl == "poly":
            return set(obj.id for obj in selection)
        else:
            return set(obj_id for obj in selection for obj_id in obj)

    def __apply_selection_set(self, sel_set):

        obj_lvl = self._obj_lvl
        get_uv_data_obj = self._uv_editor.get_uv_data_object
        geom_data_objs = [model.geom_obj.geom_data_obj
                          for model in self._models]
        uv_objs = {}

        for geom_data_obj in geom_data_objs:

            uv_data_obj = get_uv_data_obj(geom_data_obj)

            if obj_lvl == "vert":
                uv_objs.update(uv_data_obj.merged_verts)
            elif obj_lvl == "edge":
                uv_objs.update(uv_data_obj.merged_edges)
            elif obj_lvl == "poly":
                uv_objs.update(uv_data_obj.get_subobjects(obj_lvl))

        new_sel = set(uv_objs.get(obj_id) for obj_id in sel_set)
        new_sel.discard(None)
        selection = self._selections[obj_lvl]
        selection.clear()
        selection.update(new_sel)
        color_ids = set()

        if obj_lvl == "poly":
            color_ids.update(poly.picking_color_id for poly in selection)
        else:
            for subobj in selection:
                color_ids.update(subobj.picking_color_ids)

        self._uv_editor.sync_selection(color_ids)
        self.sync_selection(color_ids, hide_sets=False)

    def __init_select(self, op="replace"):

        alt_down = GD.mouse_watcher.is_button_down("alt")
        region_select = not alt_down if GD["region_select"]["is_default"] else alt_down

        if region_select:
            Mgr.enter_state("inactive", "uv")
            Mgr.do("init_region_select", op)
            return

        if not (GD.mouse_watcher.has_mouse() and self._pixel_under_mouse):
            return

        self._selection_op = op
        screen_pos = Point2(GD.mouse_watcher.get_mouse())
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        self._mouse_start_pos = (mouse_pointer.x, mouse_pointer.y)

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b
        pickable_type, picked_obj = self.__get_picked_object(color_id, a)

        obj_lvl = self._obj_lvl

        if obj_lvl == "vert":

            if GD["uv_edit_options"]["pick_via_poly"]:
                obj = picked_obj if picked_obj and pickable_type == "poly" else None
                self._picked_poly = obj
            else:
                obj = picked_obj.merged_vertex if picked_obj else None

        elif obj_lvl == "edge":

            if GD["uv_edit_options"]["pick_via_poly"]:

                obj = picked_obj if picked_obj and pickable_type == "poly" else None

                if obj and GD["uv_edit_options"]["sel_edges_by_seam"]:

                    uv_data_obj = self._uv_editor.get_uv_data_object(obj.geom_data_obj)
                    merged_edges = uv_data_obj.merged_edges

                    for edge_id in obj.edge_ids:
                        if len(merged_edges[edge_id]) == 1:
                            break
                    else:
                        obj = None

                self._picked_poly = obj

            else:

                obj = picked_obj.merged_edge if picked_obj else None

                if obj and GD["uv_edit_options"]["sel_edges_by_seam"]:

                    uv_data_obj = self._uv_editor.get_uv_data_object(obj.geom_data_obj)
                    merged_edge = uv_data_obj.get_merged_edge(obj.id)

                    if len(merged_edge) > 1:
                        obj = None

        elif obj_lvl == "poly":
            obj = picked_obj

        if self._picked_poly:
            Mgr.enter_state("uv_picking_via_poly")
            return

        self._color_id = obj.picking_color_id if obj else None
        self.__select()

    def __get_selected_uv_objects(self, subobjs):

        obj_lvl = self._obj_lvl
        get_uv_data_obj = self._uv_editor.get_uv_data_object
        selected_uv_objs = set()

        if obj_lvl == "poly":

            for subobj in subobjs:
                geom_data_obj = subobj.geom_data_obj
                uv_data_obj = get_uv_data_obj(geom_data_obj)
                uv_poly = uv_data_obj.get_subobject("poly", subobj.id)
                selected_uv_objs.update(uv_poly.special_selection)

            return selected_uv_objs

        uv_edit_options = GD["uv_edit_options"]

        if uv_edit_options["pick_via_poly"]:
            subobj = subobjs[0]
            geom_data_obj = subobj.geom_data_obj
            uv_data_obj = get_uv_data_obj(geom_data_obj)
            merged_uv_objs = (uv_data_obj.merged_verts if obj_lvl == "vert"
                              else uv_data_obj.merged_edges)
            uv_subobj = merged_uv_objs[subobj.id]
            selected_uv_objs = set(merged_uv_objs[s.id]
                                   for s in uv_subobj.special_selection)
        else:
            if obj_lvl == "edge":
                sel_edges_by_seam = uv_edit_options["sel_edges_by_seam"]
                for subobj in subobjs:
                    geom_data_obj = subobj.geom_data_obj
                    uv_data_obj = get_uv_data_obj(geom_data_obj)
                    merged_edge = uv_data_obj.get_merged_edge(subobj.id)
                    if not sel_edges_by_seam or len(merged_edge) == 1:
                        merged_uv_objs = (uv_data_obj.merged_verts if obj_lvl == "vert"
                                          else uv_data_obj.merged_edges)
                        uv_subobjs = [merged_uv_objs[s_id] for s_id in subobj.merged_subobj]
                        selected_uv_objs.update(merged_uv_objs[s.id] for uv_s in uv_subobjs
                                                for s in uv_s.special_selection)
            else:
                for subobj in subobjs:
                    geom_data_obj = subobj.geom_data_obj
                    uv_data_obj = get_uv_data_obj(geom_data_obj)
                    merged_uv_objs = (uv_data_obj.merged_verts if obj_lvl == "vert"
                                      else uv_data_obj.merged_edges)
                    uv_subobjs = [merged_uv_objs[s_id] for s_id in subobj.merged_subobj]
                    selected_uv_objs.update(merged_uv_objs[s.id] for uv_s in uv_subobjs
                                            for s in uv_s.special_selection)

        return selected_uv_objs

    def __select(self):

        obj_lvl = self._obj_lvl
        selection = self._selections[obj_lvl]
        subobj = Mgr.get(obj_lvl, self._color_id)
        op = self._selection_op
        sync_selection = True

        if subobj:

            merged_subobj = subobj.merged_subobj
            geom_data_obj = subobj.geom_data_obj

            if obj_lvl != "poly" and GD["uv_edit_options"]["pick_via_poly"]:
                poly = self._picked_poly
                ids = set(poly.vertex_ids if obj_lvl == "vert" else poly.edge_ids)
                ids.intersection_update(merged_subobj)
                subobj = geom_data_obj.get_subobject(obj_lvl, ids.pop())

            if op == "replace":
                selection.clear()
                selection.update(self.__get_selected_uv_objects([subobj]))
            elif op == "add":
                selection |= self.__get_selected_uv_objects([subobj])
            elif op == "remove":
                selection -= self.__get_selected_uv_objects([subobj])
            elif op == "toggle":
                old_sel = set(selection)
                new_sel = self.__get_selected_uv_objects([subobj])
                selection -= old_sel & new_sel
                selection |= new_sel - old_sel

        elif op == "replace":

            selection.clear()

        else:

            sync_selection = False

        if sync_selection:

            color_ids = set()

            if obj_lvl == "poly":
                color_ids.update(poly.picking_color_id for poly in selection)
            else:
                for subobj in selection:
                    color_ids.update(subobj.picking_color_ids)

            self._uv_editor.sync_selection(color_ids)
            self.sync_selection(color_ids)

    def __region_select(self, cam, lens_exp, tex_buffer, ellipse_data, mask_tex, op):

        obj_lvl = self._obj_lvl

        subobjs = {}
        index_offset = 0

        for obj in self._models:

            geom_data_obj = obj.geom_obj.geom_data_obj
            indexed_subobjs = geom_data_obj.get_indexed_subobjects(obj_lvl)

            for index, subobj in indexed_subobjs.items():
                subobjs[index + index_offset] = subobj

            geom_data_obj.origin.set_shader_input("index_offset", index_offset)
            index_offset += len(indexed_subobjs)

        ge = GD.graphics_engine
        obj_count = len(subobjs)
        region_type = GD["region_select"]["type"]
        uv_edit_options = GD["uv_edit_options"]
        pick_via_poly = uv_edit_options["pick_via_poly"]

        if pick_via_poly:
            Mgr.update_locally("picking_via_poly", False)
            GD["uv_edit_options"]["pick_via_poly"] = False

        def region_select_objects(sel, enclose=False):

            tex = Texture()
            tex.setup_1d_texture(obj_count, Texture.T_int, Texture.F_r32i)
            tex.clear_color = (0., 0., 0., 0.)
            sh = shaders.region_sel
            vs = shaders.region_sel_subobj.VERT_SHADER

            if "rect" in region_type or "square" in region_type:
                fs = sh.FRAG_SHADER_INV if enclose else sh.FRAG_SHADER
            elif "ellipse" in region_type or "circle" in region_type:
                fs = sh.FRAG_SHADER_ELLIPSE_INV if enclose else sh.FRAG_SHADER_ELLIPSE
            else:
                fs = sh.FRAG_SHADER_FREE_INV if enclose else sh.FRAG_SHADER_FREE

            shader = Shader.make(Shader.SL_GLSL, vs, fs)
            state_np = NodePath("state_np")
            state_np.set_shader(shader, 1)
            state_np.set_shader_input("selections", tex, read=False, write=True)

            if "ellipse" in region_type or "circle" in region_type:
                state_np.set_shader_input("ellipse_data", Vec4(*ellipse_data))
            elif region_type in ("fence", "lasso", "paint"):
                if enclose:
                    img = PNMImage()
                    mask_tex.store(img)
                    img.expand_border(2, 2, 2, 2, (0., 0., 0., 0.))
                    mask_tex.load(img)
                state_np.set_shader_input("mask_tex", mask_tex)
            elif enclose:
                w_b, h_b = tex_buffer.get_size()
                state_np.set_shader_input("buffer_size", Vec2(w_b + 2, h_b + 2))

            state = state_np.get_state()
            cam.node().initial_state = state

            ge.render_frame()

            if ge.extract_texture_data(tex, GD.window.get_gsg()):

                texels = memoryview(tex.get_ram_image()).cast("I")

                for i, mask in enumerate(texels):
                    for j in range(32):
                        if mask & (1 << j):
                            index = 32 * i + j
                            subobj = subobjs[index]
                            sel.add(subobj)

            state_np.clear_attrib(ShaderAttrib)

        new_sel = set()
        region_select_objects(new_sel)
        ge.remove_window(tex_buffer)
        new_sel = self.__get_selected_uv_objects(new_sel)

        if GD["region_select"]["enclose"]:
            w_b, h_b = tex_buffer.get_size()
            bfr_exp = GD.window.make_texture_buffer("tex_buffer_exp", w_b + 4, h_b + 4)
            GD.showbase.make_camera(bfr_exp, useCamera=cam)
            cam.node().set_lens(lens_exp)
            inverse_sel = set()
            region_select_objects(inverse_sel, True)
            inverse_sel = self.__get_selected_uv_objects(inverse_sel)
            new_sel -= inverse_sel
            ge.remove_window(bfr_exp)

        if pick_via_poly:
            Mgr.update_locally("picking_via_poly", True)
            GD["uv_edit_options"]["pick_via_poly"] = True

        selection = self._selections[obj_lvl]
        color_ids = set()

        if op == "replace":
            selection.clear()
            selection.update(new_sel)
        elif op == "add":
            selection |= new_sel
        elif op == "remove":
            selection -= new_sel
        elif op == "toggle":
            old_sel = set(selection)
            selection -= old_sel & new_sel
            selection |= new_sel - old_sel

        if obj_lvl == "poly":
            color_ids.update(poly.picking_color_id for poly in selection)
        else:
            for subobj in selection:
                color_ids.update(subobj.picking_color_ids)

        self._uv_editor.sync_selection(color_ids)
        self.sync_selection(color_ids)

    def __init_uv_picking_via_poly(self, prev_state_id, active):

        Mgr.add_task(self.__hilite_subobj, "hilite_subobj")
        Mgr.remove_task("update_cursor")
        subobj_lvl = GD["active_obj_level"]

        if subobj_lvl == "edge" and GD["uv_edit_options"]["sel_edges_by_seam"]:
            category = "uv_seam"
        else:
            category = ""

        geom_data_obj = self._picked_poly.geom_data_obj
        merged_edges = self._uv_editor.get_uv_data_object(geom_data_obj).merged_edges
        geom_data_obj.init_subobj_picking_via_poly(subobj_lvl, self._picked_poly, category, merged_edges)
        # temporarily select picked poly
        geom_data_obj.update_selection("poly", [self._picked_poly], [], False)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.geom_obj.geom_data_obj

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable(False)

        Mgr.update_app("status", ["picking_via_poly"])

    def __hilite_subobj(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            if pixel_under_mouse != VBase4():

                r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                color_id = r << 16 | g << 8 | b
                geom_data_obj = self._picked_poly.geom_data_obj
                subobj_lvl = GD["active_obj_level"]

                # highlight temporary subobject
                if geom_data_obj.hilite_temp_subobject(subobj_lvl, color_id):
                    self._tmp_color_id = color_id

            self._pixel_under_mouse = pixel_under_mouse

        not_hilited = pixel_under_mouse in (VBase4(), VBase4(1., 1., 1., 1.))
        cursor_id = "main" if not_hilited else "select"

        if GD["uv_edit_options"]["pick_by_aiming"]:

            aux_pixel_under_mouse = Mgr.get("aux_pixel_under_mouse")

            if not_hilited or self._aux_pixel_under_mouse != aux_pixel_under_mouse:

                if not_hilited and aux_pixel_under_mouse != VBase4():

                    r, g, b, a = [int(round(c * 255.)) for c in aux_pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    geom_data_obj = self._picked_poly.geom_data_obj
                    subobj_lvl = GD["active_obj_level"]

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
        subobj_lvl = GD["active_obj_level"]
        geom_data_obj = self._picked_poly.geom_data_obj

        if self._tmp_color_id is None:

            obj = None

        else:

            if subobj_lvl == "vert":

                vert_id = Mgr.get("vert", self._tmp_color_id).id
                obj = geom_data_obj.get_merged_vertex(vert_id)

            elif subobj_lvl == "edge":

                edge_id = Mgr.get("edge", self._tmp_color_id).id
                obj = geom_data_obj.get_merged_edge(edge_id)

                if GD["uv_edit_options"]["sel_edges_by_seam"]:

                    uv_data_obj = self._uv_editor.get_uv_data_object(obj.geom_data_obj)
                    merged_edge = uv_data_obj.get_merged_edge(edge_id)

                    if len(merged_edge) > 1:
                        obj = None

        self._color_id = obj.picking_color_id if obj else None
        self.__select()

        geom_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.geom_obj.geom_data_obj

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

    def __cancel_select_via_poly(self):

        Mgr.remove_task("hilite_subobj")
        Mgr.enter_state("uv_edit_mode")
        subobj_lvl = GD["active_obj_level"]

        geom_data_obj = self._picked_poly.geom_data_obj
        geom_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.geom_obj.geom_data_obj

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

    def sync_selection(self, color_ids, object_level=None, hide_sets=True):

        obj_lvl = self._obj_lvl if object_level is None else object_level
        selection = self._selections[obj_lvl]
        selection.clear()
        subobjects = set()
        uv_objects = set()

        for color_id in color_ids:
            subobj = Mgr.get(obj_lvl, color_id)
            subobjects.add(subobj.merged_subobj)
            geom_data_obj = subobj.geom_data_obj
            uv_data_obj = self._uv_editor.get_uv_data_object(geom_data_obj)
            uv_objects.add(uv_data_obj.get_subobject(obj_lvl, subobj.id).merged_subobj)

        models = self._models
        subobj_sel = {}
        selection.update(uv_objects)

        if obj_lvl == "edge":

            uv_set_id = UVMgr.get("active_uv_set")
            colors = UVMgr.get("uv_selection_colors")["seam"]
            color = colors["unselected"]

            for model in models:
                geom_data_obj = model.geom_obj.geom_data_obj
                geom_data_obj.clear_tex_seam_selection(uv_set_id, color)

            for subobj in subobjects:
                geom_data_obj = subobj.geom_data_obj
                geom_data_obj.set_selected_tex_seam_edge(uv_set_id, colors, subobj, True)

        else:

            for model in models:
                geom_data_obj = model.geom_obj.geom_data_obj
                geom_data_obj.clear_selection(obj_lvl, False)

            for subobj in subobjects:
                geom_data_obj = subobj.geom_data_obj
                subobj_sel.setdefault(geom_data_obj, []).append(subobj)

        for geom_data_obj, subobjs in subobj_sel.items():
            geom_data_obj.update_selection(obj_lvl, subobjs, [], False)

        if hide_sets:
            Mgr.update_remotely("selection_set", "hide_name")
