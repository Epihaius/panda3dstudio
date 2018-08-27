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

    def add(self, subobjs, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_add = set(subobjs)
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

    def remove(self, subobjs, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_remove = set(subobjs)
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

    def replace(self, subobjs, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        new_sel = set(subobjs)
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
        self._mouse_end_pos = ()
        self._picked_point = None
        self._pixel_under_mouse = None
        self._color_id = None
        self._selections = {}
        self._can_select_single = False
        self._selection_border = self.__create_selection_border()
        self._selection_border_pos = ()
        self._draw_plane = Plane(Vec3.forward(), Point3())
        self._region_sel_cancelled = False
        self._region_toggle_sel = False
        cam = Camera("uv_region_selection_cam")
        cam.set_active(False)
        cam.set_scene(self.geom_root)
        self._region_sel_cam = self.cam.attach_new_node(cam)

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
        add_state("aux_viewport_resize", -200, interface_id="uv")
        add_state("region_selection_mode", -1, self.__enter_region_selection_mode,
                  self.__exit_region_selection_mode, interface_id="uv")

        mod_alt = GlobalData["mod_key_codes"]["alt"]
        mod_ctrl = GlobalData["mod_key_codes"]["ctrl"]
        bind = Mgr.bind_state
        bind("uv_edit_mode", "regular select uvs",
             "mouse1", self.__select, "uv")
        bind("uv_edit_mode", "toggle-select uvs", "{:d}|mouse1".format(mod_ctrl),
             lambda: self.__select(toggle=True), "uv")
        bind("uv_edit_mode", "region-select uvs", "{:d}|mouse1".format(mod_alt),
             lambda: Mgr.enter_state("region_selection_mode", "uv"), "uv")
        bind("uv_edit_mode", "region-toggle-select uvs",
             "{:d}|mouse1".format(mod_alt | mod_ctrl), self.__region_toggle_select, "uv")
        bind("uv_edit_mode", "transf off", "q",
             self.__set_active_transform_off, "uv")
        bind("picking_via_poly", "select subobj via poly",
             "mouse1-up", self.__select_subobj_via_poly, "uv")
        bind("picking_via_poly", "cancel subobj select via poly",
             "mouse3-up", self.__cancel_select_via_poly, "uv")
        bind("region_selection_mode", "cancel region-select", "mouse3-up",
             self.__cancel_region_selection, "uv")
        bind("region_selection_mode", "exit region-select", "mouse1-up",
             lambda: Mgr.exit_state("region_selection_mode", "uv"), "uv")

        def cancel_mouse_check():

            Mgr.enter_state("uv_edit_mode", "uv")
            self.__cancel_mouse_check()

        bind("checking_mouse_offset", "cancel mouse check uvs", "mouse1-up",
             cancel_mouse_check, "uv")

        picking_mask = UVMgr.get("picking_mask")
        self._selection_border.hide(picking_mask)

    def __create_selection_border(self):

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("selection_border", vertex_format, Geom.UH_dynamic)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.add_data3f(0., 0., 0.)
        pos_writer.add_data3f(0., 0., 1.)
        pos_writer.add_data3f(1., 0., 1.)
        pos_writer.add_data3f(1., 0., 0.)
        lines = GeomLines(Geom.UH_static)
        lines.add_vertices(0, 1)
        lines.add_vertices(1, 2)
        lines.add_vertices(2, 3)
        lines.add_vertices(3, 0)

        state_np = NodePath("state_np")
        state_np.set_depth_test(False)
        state_np.set_depth_write(False)
        state_np.set_bin("fixed", 101)
        state1 = state_np.get_state()
        state_np.set_bin("fixed", 100)
        state_np.set_color((0., 0., 0., 1.))
        state_np.set_render_mode_thickness(3)
        state2 = state_np.get_state()
        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        geom_node = GeomNode("selection_border")
        geom_node.add_geom(geom, state1)
        geom = geom.make_copy()
        geom_node.add_geom(geom, state2)

        return NodePath(geom_node)

    def __draw_selection_border(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        screen_pos = self.mouse_watcher.get_mouse()
        self._mouse_end_pos = (screen_pos.x, screen_pos.y)
        near_point = Point3()
        far_point = Point3()
        point = Point3()
        self.cam_lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.uv_space.get_relative_point(self.cam, point)
        self._draw_plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))

        x1, y1 = self._selection_border_pos
        x2, _, y2 = point
        sx = x2 - x1
        sx = .00001 if abs(sx) < .00001 else sx
        sy = y2 - y1
        sy = .00001 if abs(sy) < .00001 else sy
        self._selection_border.set_scale(sx, 1., sy)

        return task.cont

    def __enter_region_selection_mode(self, prev_state_id, is_active):

        if not self.mouse_watcher.has_mouse():
            return

        screen_pos = self.mouse_watcher.get_mouse()
        self._mouse_start_pos = (screen_pos.x, screen_pos.y)
        near_point = Point3()
        far_point = Point3()
        point = Point3()
        self.cam_lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.uv_space.get_relative_point(self.cam, point)
        self._draw_plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))

        x, y, z = point
        self._selection_border_pos = (x, z)
        self._selection_border.reparent_to(self.uv_space)
        self._selection_border.set_pos(point)

        Mgr.add_task(self.__draw_selection_border, "draw_selection_border", sort=3)

    def __exit_region_selection_mode(self, next_state_id, is_active):

        Mgr.remove_task("draw_selection_border")
        self._selection_border.detach_node()
        x1, y1 = self._mouse_start_pos
        x2, y2 = self._mouse_end_pos
        x1 = .5 + x1 * .5
        y1 = .5 + y1 * .5
        x2 = max(0., min(1., .5 + x2 * .5))
        y2 = max(0., min(1., .5 + y2 * .5))
        l, r = min(x1, x2), max(x1, x2)
        b, t = min(y1, y2), max(y1, y2)
        self.__region_select((l, r, b, t))

    def __cancel_region_selection(self):

        self._region_sel_cancelled = True
        Mgr.exit_state("region_selection_mode", "uv")
        self._region_sel_cancelled = False

    def __region_toggle_select(self):

        self._region_toggle_sel = True
        Mgr.enter_state("region_selection_mode", "uv")

    def __region_select(self, frame):

        if self._region_sel_cancelled:
            self._region_toggle_sel = False
            return

        lens = self.cam_lens
        w, h = lens.get_film_size()
        l, r, b, t = frame
        # compute film size and offset
        w_f = (r - l) * w
        h_f = (t - b) * h
        x_f = ((r + l) * .5 - .5) * w
        y_f = ((t + b) * .5 - .5) * h
        w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "uv" else "size"]
        # compute buffer size
        w_b = int(round((r - l) * w))
        h_b = int(round((t - b) * h))

        if min(w_b, h_b) < 2:
            return

        UVMgr.get("picking_cam").set_active(False)

        focal_len = lens.get_focal_length()
        lens = lens.make_copy()
        lens.set_film_size(w_f, h_f)
        lens.set_film_offset(x_f, y_f)
        lens.set_focal_length(focal_len)
        picking_mask = UVMgr.get("picking_mask")
        cam_np = self._region_sel_cam
        cam = cam_np.node()
        cam.set_lens(lens)
        cam.set_camera_mask(picking_mask)
        base = Mgr.get("base")
        bfr = base.win.make_texture_buffer("tex_buffer", w_b, h_b, Texture(""))
        cam.set_active(True)
        base.make_camera(bfr, useCamera=cam_np)
        cam_np.reparent_to(self.cam)

        toggle_select = self.mouse_watcher.is_button_down(KeyboardButton.control())
        toggle_select = toggle_select or self._region_toggle_sel
        new_sel = set()

        uv_set_id = self._uv_set_id
        obj_lvl = self._obj_lvl
        uv_data_objs = self._uv_data_objs[uv_set_id].values()
        subobjs = {}
        index_offset = 0

        for uv_data_obj in uv_data_objs:

            indexed_subobjs = uv_data_obj.get_indexed_subobjects(obj_lvl)

            for index, subobj in indexed_subobjs.items():
                subobjs[index + index_offset] = subobj

            uv_data_obj.get_origin().set_shader_input("index_offset", index_offset)
            index_offset += len(indexed_subobjs)

        obj_count = len(subobjs)

        tex = Texture()
        tex.setup_1d_texture(obj_count, Texture.T_int, Texture.F_r32i)
        tex.set_clear_color(0)
        vs = shader.region_sel_subobj.VERT_SHADER
        fs = shader.region_sel.FRAG_SHADER
        sh = Shader.make(Shader.SL_GLSL, vs, fs)
        state_np = NodePath("state_np")
        state_np.set_shader(sh, 1)
        state_np.set_shader_input("selections", tex, read=False, write=True, priority=1)
        state_np.set_light_off(1)
        state = state_np.get_state()
        cam.set_initial_state(state)

        pick_via_poly = GlobalData["uv_edit_options"]["pick_via_poly"]

        if pick_via_poly:
            Mgr.update_interface_locally("uv", "picking_via_poly", False)

        ge = base.graphics_engine
        ge.render_frame()

        if ge.extract_texture_data(tex, base.win.get_gsg()):

            texels = memoryview(tex.get_ram_image()).cast("I")
            sel_edges_by_seam = obj_lvl == "edge" and GlobalData["uv_edit_options"]["sel_edges_by_seam"]

            for i, mask in enumerate(texels):
                for j in range(32):
                    if mask & (1 << j):
                        index = 32 * i + j
                        subobj = subobjs[index].get_merged_object()
                        if not sel_edges_by_seam or len(subobj) == 1:
                            new_sel.update(subobj.get_special_selection())

        state_np.clear_shader()

        if pick_via_poly:
            Mgr.update_interface_locally("uv", "picking_via_poly", True)

        selection = self._selections[uv_set_id][obj_lvl]
        color_ids = set()

        if toggle_select:
            old_sel = set(selection)
            selection.remove(old_sel & new_sel)
            selection.add(new_sel - old_sel)
        else:
            selection.replace(new_sel)

        if obj_lvl == "poly":
            color_ids.update(poly.get_picking_color_id() for poly in selection)
        else:
            for subobj in selection:
                color_ids.update(subobj.get_picking_color_ids())

        self._world_sel_mgr.sync_selection(color_ids)

        cam.set_active(False)
        ge.remove_window(bfr)
        UVMgr.get("picking_cam").set_active()
        self._region_toggle_sel = False

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

                    selection.replace(subobj.get_special_selection())

                if check_mouse:
                    Mgr.enter_state("checking_mouse_offset", "uv")

            else:

                selection.replace(subobj.get_special_selection())

        else:

            selection.clear()

        if obj_lvl == "poly":
            color_ids.update(poly.get_picking_color_id() for poly in selection)
        else:
            for subobj in selection:
                color_ids.update(subobj.get_picking_color_ids())

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
        selection.replace(subobj.get_special_selection())

        if obj_lvl == "poly":
            color_ids.update(poly.get_picking_color_id() for poly in selection)
        else:
            for subobj in selection:
                color_ids.update(subobj.get_picking_color_ids())

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

            if subobj in selection:
                transform_allowed = False
            else:
                transform_allowed = GlobalData["active_uv_transform_type"]

            old_sel = set(selection)
            new_sel = set(subobj.get_special_selection())
            selection.remove(old_sel & new_sel)
            selection.add(new_sel - old_sel)

            if obj_lvl == "poly":
                color_ids.update(poly.get_picking_color_id() for poly in selection)
            else:
                for subobj in selection:
                    color_ids.update(subobj.get_picking_color_ids())

            self._world_sel_mgr.sync_selection(color_ids)

            if check_mouse and transform_allowed:
                Mgr.enter_state("checking_mouse_offset", "uv")

    def sync_selection(self, color_ids):

        obj_lvl = self._obj_lvl
        uv_set_id = self._uv_set_id
        uv_registry = self._uv_registry[uv_set_id][obj_lvl]
        selection = self._selections[uv_set_id][obj_lvl]
        subobjects = set(uv_registry[color_id].get_merged_object() for color_id in color_ids)
        selection.replace(subobjects)

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
