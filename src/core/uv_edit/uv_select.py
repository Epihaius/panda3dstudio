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
        self._selection_op = "replace"
        cam = Camera("uv_region_selection_cam")
        cam.set_active(False)
        cam.set_scene(self.geom_root)
        self._region_sel_cam = self.cam.attach_new_node(cam)
        self._sel_mask_tex = None
        self._sel_mask_buffer = None
        self._sel_mask_listener = None
        self._sel_mask_triangle_vertex = 1  # index of the triangle vertex to move
        self._sel_mask_triangle_coords = []
        self._mouse_prev = (0., 0.)
        self._sel_shape_pos = (0., 0.)
        self._region_center_pos = ()
        self._region_sel_cancelled = False
        self._draw_plane = Plane(Vec3.forward(), Point3())
        self._fence_initialized = False
        self._fence_points = None
        self._fence_point_color_id = 1
        self._fence_point_coords = {}
        self._fence_mouse_coords = [[], []]
        self._fence_point_pick_lens = lens = OrthographicLens()
        lens.set_film_size(30.)
        lens.set_near(-10.)

        # the following variables are used to pick a subobject using its polygon
        self._picked_poly = None
        self._tmp_color_id = None
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
        info_start = "RMB to pan, MWheel or LMB+RMB to zoom; (<Alt>-)LMB to (region-)select subobjects; "
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

        info_text = "LMB-drag to draw shape; RMB or <Escape> to cancel"
        status_data["region"] = {"mode": "Draw selection shape", "info": info_text}
        info_text = "Click to add point; <Backspace> to remove point; click existing point or" \
            " <Enter> to finish; RMB or <Escape> to cancel"
        status_data["fence"] = {"mode": "Draw selection shape", "info": info_text}

    def setup(self):

        add_state = Mgr.add_state
        add_state("uv_edit_mode", 0, self.__enter_selection_mode, self.__exit_selection_mode,
                  interface_id="uv")
        add_state("checking_mouse_offset", -1, self.__start_mouse_check,
                  interface_id="uv")
        add_state("picking_via_poly", -1, self.__init_subobj_picking_via_poly,
                  interface_id="uv")
        add_state("aux_viewport_resize", -200, interface_id="uv")
        add_state("region_selection_mode", -1, self.__enter_region_selection_mode,
                  self.__exit_region_selection_mode, interface_id="uv")
        add_state("inactive", -1000, interface_id="uv")

        mod_alt = GlobalData["mod_key_codes"]["alt"]
        mod_ctrl = GlobalData["mod_key_codes"]["ctrl"]
        mod_shift = GlobalData["mod_key_codes"]["shift"]
        bind = Mgr.bind_state
        bind("uv_edit_mode", "select (replace) uvs", "mouse1",
             self.__init_select, "uv")
        bind("uv_edit_mode", "select (add) uvs", "{:d}|mouse1".format(mod_ctrl),
             lambda: self.__init_select(op="add"), "uv")
        bind("uv_edit_mode", "select (remove) uvs", "{:d}|mouse1".format(mod_shift),
             lambda: self.__init_select(op="remove"), "uv")
        bind("uv_edit_mode", "select (toggle) uvs", "{:d}|mouse1".format(mod_ctrl | mod_shift),
             lambda: self.__init_select(op="toggle"), "uv")
        bind("uv_edit_mode", "select (replace) uvs alt", "{:d}|mouse1".format(mod_alt),
             self.__init_select, "uv")
        bind("uv_edit_mode", "select (add) uvs alt", "{:d}|mouse1".format(mod_alt | mod_ctrl),
             lambda: self.__init_select(op="add"), "uv")
        bind("uv_edit_mode", "select (remove) uvs alt", "{:d}|mouse1".format(mod_alt | mod_shift),
             lambda: self.__init_select(op="remove"), "uv")
        bind("uv_edit_mode", "select (toggle) uvs alt", "{:d}|mouse1".format(mod_alt | mod_ctrl | mod_shift),
             lambda: self.__init_select(op="toggle"), "uv")
        bind("picking_via_poly", "select subobj via poly",
             "mouse1-up", self.__select_subobj_via_poly, "uv")
        bind("picking_via_poly", "cancel subobj select via poly",
             "mouse3-up", self.__cancel_select_via_poly, "uv")
        bind("region_selection_mode", "quit region-select", "escape",
             self.__cancel_region_select, "uv")
        bind("region_selection_mode", "cancel region-select", "mouse3-up",
             self.__cancel_region_select, "uv")
        bind("region_selection_mode", "abort region-select", "focus_loss",
             self.__cancel_region_select, "uv")
        bind("region_selection_mode", "handle region-select mouse1-up", "mouse1-up",
             self.__handle_region_select_mouse_up, "uv")

        def cancel_mouse_check():

            Mgr.enter_state("uv_edit_mode", "uv")
            self.__cancel_mouse_check()

        bind("checking_mouse_offset", "cancel mouse check uvs", "mouse1-up",
             cancel_mouse_check, "uv")

    def __get_fence_point_under_mouse(self, cam):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        cam.set_pos(mouse_pointer.get_x(), 0., -mouse_pointer.get_y())

    def __init_fence_point_picking(self, mouse_x, mouse_y):

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("fence_points", vertex_format, Geom.UH_dynamic)
        points = GeomPoints(Geom.UH_static)
        geom = Geom(vertex_data)
        geom.add_primitive(points)
        geom_node = GeomNode("fence_points")
        geom_node.add_geom(geom)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.add_data3f(mouse_x, 0., mouse_y)
        col_writer = GeomVertexWriter(vertex_data, "color")
        color_vec = get_color_vec(1, 255)
        col_writer.add_data4f(color_vec)
        points.add_vertex(0)
        self._fence_points = fence_points = NodePath(geom_node)
        picking_cam = UVMgr.get("picking_cam")
        picking_cam().reparent_to(fence_points)
        picking_cam().node().set_lens(self._fence_point_pick_lens)
        picking_cam.set_pixel_fetcher(self.__get_fence_point_under_mouse)

    def __draw_selection_shape(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        screen_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        point = Point3()
        self.cam_lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.uv_space.get_relative_point(self.cam, point)
        self._draw_plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))

        x1, y1 = self._sel_shape_pos
        x2, _, y2 = point

        shape_type = GlobalData["region_select"]["type"]
        selection_shapes = Mgr.get("selection_shapes")

        if shape_type in ("fence", "lasso"):

            shape = selection_shapes["free"]

            if shape_type == "lasso":

                mouse_pointer = Mgr.get("mouse_pointer", 0)
                mouse_x = mouse_pointer.get_x()
                mouse_y = mouse_pointer.get_y()
                prev_x, prev_y = self._mouse_prev
                d_x = abs(mouse_x - prev_x)
                d_y = abs(mouse_y - prev_y)

                if max(d_x, d_y) > 5:
                    self.__add_selection_shape_vertex()

            for i in (0, 1):
                vertex_data = shape.node().modify_geom(i).modify_vertex_data()
                row = vertex_data.get_num_rows() - 1
                pos_writer = GeomVertexWriter(vertex_data, "vertex")
                pos_writer.set_row(row)
                pos_writer.set_data3f(x2 - x1, 0., y2 - y1)

        else:

            sx = x2 - x1
            sy = y2 - y1
            shape = selection_shapes[shape_type]
            w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "uv" else "size"]

            if "square" in shape_type or "circle" in shape_type:

                if "centered" in shape_type:
                    s = max(.00001, math.sqrt(sx * sx + sy * sy))
                    shape.set_scale(s, 1., s)
                    center_x, center_y = self._region_center_pos
                    d_x = screen_pos.x - center_x
                    d_y = (screen_pos.y - center_y) * h/w
                    d = math.sqrt(d_x * d_x + d_y * d_y)
                    self._mouse_start_pos = (center_x - d, center_y - d * w/h)
                    self._mouse_end_pos = (center_x + d, center_y + d * w/h)
                else:
                    f = max(.00001, abs(sx), abs(sy))
                    sx = f * (-1. if sx < 0. else 1.)
                    sy = f * (-1. if sy < 0. else 1.)
                    shape.set_scale(sx, 1., sy)
                    mouse_start_x, mouse_start_y = self._mouse_start_pos
                    d_x = screen_pos.x - mouse_start_x
                    d_y = screen_pos.y - mouse_start_y
                    d = max(abs(d_x), abs(d_y) * h/w)
                    d_x = d * (-1. if d_x < 0. else 1.)
                    d_y = d * (-1. if d_y < 0. else 1.)
                    self._mouse_end_pos = (mouse_start_x + d_x, mouse_start_y + d_y * w/h)

            else:

                sx = .00001 if abs(sx) < .00001 else sx
                sy = .00001 if abs(sy) < .00001 else sy
                shape.set_scale(sx, 1., sy)
                self._mouse_end_pos = (screen_pos.x, screen_pos.y)

                if "centered" in shape_type:
                    center_x, center_y = self._region_center_pos
                    d_x = screen_pos.x - center_x
                    d_y = screen_pos.y - center_y
                    self._mouse_start_pos = (center_x - d_x, center_y - d_y)

        return task.cont

    def __add_selection_shape_vertex(self, add_fence_point=False, coords=None):

        if not self.mouse_watcher.has_mouse():
            return

        x, y = self.mouse_watcher.get_mouse()

        if add_fence_point:
            mouse_coords_x, mouse_coords_y = self._fence_mouse_coords
            mouse_coords_x.append(x)
            mouse_coords_y.append(y)

        x1, y1 = self._mouse_start_pos
        x2, y2 = self._mouse_end_pos

        if x < x1:
            x1 = x
        elif x > x2:
            x2 = x

        if y < y1:
            y1 = y
        elif y > y2:
            y2 = y

        self._mouse_start_pos = (x1, y1)
        self._mouse_end_pos = (x2, y2)

        if coords:
            mouse_x, mouse_y = coords
        else:
            mouse_pointer = Mgr.get("mouse_pointer", 0)
            mouse_x = mouse_pointer.get_x()
            mouse_y = -mouse_pointer.get_y()
            self._mouse_prev = (mouse_x, mouse_y)

        screen_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        point = Point3()
        self.cam_lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.uv_space.get_relative_point(self.cam, point)
        self._draw_plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))
        start_x, start_y = self._sel_shape_pos
        new_x, _, new_y = point
        shape = Mgr.get("selection_shapes")["free"]
        sel_mask_data = Mgr.get("selection_mask_data")
        triangle = sel_mask_data["triangle"]
        background = sel_mask_data["background"]

        for i in (0, 1):

            vertex_data = shape.node().modify_geom(i).modify_vertex_data()
            count = vertex_data.get_num_rows()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(count - 1)
            pos_writer.add_data3f(new_x - start_x, 0., new_y - start_y)
            pos_writer.add_data3f(new_x - start_x, 0., new_y - start_y)
            prim = shape.node().modify_geom(i).modify_primitive(0)
            array = prim.modify_vertices()
            row_count = array.get_num_rows()

            if row_count > 2:
                array.set_num_rows(row_count - 2)

            prim.add_vertices(count - 1, count)
            prim.add_vertices(count, 0)

        vertex_data = triangle.node().modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        if count == 2:
            self._sel_mask_triangle_vertex = 1
        elif count > 2:
            self._sel_mask_triangle_vertex = 3 - self._sel_mask_triangle_vertex

        pos_writer.set_row(self._sel_mask_triangle_vertex)
        pos_writer.set_data3f(mouse_x, 0., mouse_y)

        if min(x2 - x1, y2 - y1) == 0:
            triangle.hide()
        elif count >= 3:
            triangle.show()
            Mgr.do_next_frame(lambda task: triangle.hide(), "hide_sel_mask_triangle")

        if count == 3:
            background.set_color((1., 1., 1., 1.))
            background.set_texture(self._sel_mask_tex)

        if add_fence_point:

            node = self._fence_points.node()
            vertex_data = node.modify_geom(0).modify_vertex_data()
            row = vertex_data.get_num_rows()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(row)
            pos_writer.add_data3f(mouse_x, 0., mouse_y)
            col_writer = GeomVertexWriter(vertex_data, "color")
            col_writer.set_row(row)
            self._fence_point_color_id += 1
            self._fence_point_coords[self._fence_point_color_id] = (mouse_x, mouse_y)
            color_vec = get_color_vec(self._fence_point_color_id, 255)
            col_writer.add_data4f(color_vec)
            prim = node.modify_geom(0).modify_primitive(0)
            prim.add_vertex(row)
            self._sel_mask_triangle_coords.append((mouse_x, mouse_y))

            if count == 2:
                self._sel_mask_listener.accept("backspace-up", self.__remove_fence_vertex)

    def __remove_fence_vertex(self):

        if GlobalData["region_select"]["type"] != "fence":
            return

        mouse_coords_x, mouse_coords_y = self._fence_mouse_coords
        mouse_coords_x.pop()
        mouse_coords_y.pop()
        x_min = min(mouse_coords_x)
        x_max = max(mouse_coords_x)
        y_min = min(mouse_coords_y)
        y_max = max(mouse_coords_y)
        self._mouse_start_pos = (x_min, y_min)
        self._mouse_end_pos = (x_max, y_max)

        shape = Mgr.get("selection_shapes")["free"]
        sel_mask_data = Mgr.get("selection_mask_data")
        triangle = sel_mask_data["triangle"]

        for i in (0, 1):

            vertex_data = shape.node().modify_geom(i).modify_vertex_data()
            count = vertex_data.get_num_rows() - 1
            vertex_data.set_num_rows(count)
            prim = shape.node().modify_geom(i).modify_primitive(0)
            array = prim.modify_vertices()
            row_count = array.get_num_rows()

            if row_count > 2:
                array.set_num_rows(row_count - 4)

            if row_count > 6:
                prim.add_vertices(count - 1, 0)

        self._mouse_prev = self._sel_mask_triangle_coords.pop()

        if count == 2:
            self._sel_mask_listener.ignore("backspace-up")
        elif count == 3:
            background = sel_mask_data["background"]
            background.clear_texture()
            background.set_color((0., 0., 0., 1.))
            triangle.hide()
            self._sel_mask_triangle_vertex = 1
        elif count > 3:
            self._sel_mask_triangle_vertex = 3 - self._sel_mask_triangle_vertex
            vertex_data = triangle.node().modify_geom(0).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(self._sel_mask_triangle_vertex)
            prev_x, prev_y = self._sel_mask_triangle_coords[-1]
            pos_writer.set_data3f(prev_x, 0., prev_y)

        if min(x_max - x_min, y_max - y_min) == 0:
            triangle.hide()
        elif count > 3:
            triangle.show()
            Mgr.do_next_frame(lambda task: triangle.hide(), "hide_sel_mask_triangle")

        node = self._fence_points.node()
        vertex_data = node.modify_geom(0).modify_vertex_data()
        count = vertex_data.get_num_rows() - 1
        vertex_data.set_num_rows(count)
        del self._fence_point_coords[self._fence_point_color_id]
        self._fence_point_color_id -= 1
        prim = node.modify_geom(0).modify_primitive(0)
        array = prim.modify_vertices()
        array.set_num_rows(count)

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

        x, _, z = point
        self._sel_shape_pos = (x, z)

        shape_type = GlobalData["region_select"]["type"]
        selection_shapes = Mgr.get("selection_shapes")
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = -mouse_pointer.get_y()

        if "centered" in shape_type:
            self._region_center_pos = (screen_pos.x, screen_pos.y)

        if shape_type == "fence":
            self.__init_fence_point_picking(mouse_x, mouse_y)
            self._fence_point_coords[1] = (mouse_x, mouse_y)
            mouse_coords_x, mouse_coords_y = self._fence_mouse_coords
            mouse_coords_x.append(screen_pos.x)
            mouse_coords_y.append(screen_pos.y)
            Mgr.add_task(self.__update_cursor, "update_cursor_uvs", sort=2)
            Mgr.update_app("status", ["select", "fence"], "uv")
        else:
            Mgr.update_app("status", ["select", "region"], "uv")

        if shape_type in ("fence", "lasso"):
            Mgr.enter_state("inactive")
            selection_shapes["free"] = shape = Mgr.get("free_selection_shape")
            sel_mask_data = Mgr.get("selection_mask_data")
            geom_root = sel_mask_data["geom_root"]
            geom_root.clear_transform()
            self._sel_mask_tex = tex = Texture()
            tri = sel_mask_data["triangle"]
            tri.set_pos(0., 1.5, 0.)
            vertex_data = tri.node().modify_geom(0).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(0)
            pos_writer.set_data3f(mouse_x, 0., mouse_y)
            sh = shaders.region_sel
            vs = sh.VERT_SHADER_MASK
            fs = sh.FRAG_SHADER_MASK
            shader = Shader.make(Shader.SL_GLSL, vs, fs)
            tri.set_shader(shader)
            tri.set_shader_input("prev_tex", tex)
            base = Mgr.get("base")
            w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "uv" else "size"]
            x, y = GlobalData["viewport"]["pos_aux" if GlobalData["viewport"][2] == "uv" else "pos"]
            self._sel_mask_buffer = bfr = base.win.make_texture_buffer(
                                                                       "sel_mask_buffer",
                                                                       w, h,
                                                                       tex,
                                                                       to_ram=True
                                                                      )
            bfr.set_clear_color((0., 0., 0., 1.))
            bfr.set_clear_color_active(True)
            cam = sel_mask_data["cam"]
            base.make_camera(bfr, useCamera=cam)
            cam.node().set_active(True)
            cam.reparent_to(sel_mask_data["root"])
            cam.set_scale(w * .5, 1., h * .5)
            cam.set_pos(x + w * .5, 0., -y - h * .5)
            background = sel_mask_data["background"]
            background.set_scale(w, 1., h)
            background.set_pos(x, 2., -y)
            self._sel_mask_listener = listener = DirectObject()
            listener.accept("enter-up", lambda: Mgr.exit_state("region_selection_mode", "uv"))
            self._mouse_end_pos = (screen_pos.x, screen_pos.y)
        else:
            shape = selection_shapes[shape_type]

        shape.reparent_to(self.uv_space)
        shape.set_pos(point)
        picking_mask = UVMgr.get("picking_mask")
        shape.hide(picking_mask)

        Mgr.add_task(self.__draw_selection_shape, "draw_selection_shape", sort=3)

    def __exit_region_selection_mode(self, next_state_id, is_active):

        Mgr.remove_task("draw_selection_shape")

        shape_type = GlobalData["region_select"]["type"]
        selection_shapes = Mgr.get("selection_shapes")

        if shape_type == "fence":
            Mgr.remove_task("update_cursor_uvs")
            picking_cam = UVMgr.get("picking_cam")
            picking_cam().reparent_to(self.cam)
            picking_cam.restore_lens()
            picking_cam.set_pixel_fetcher(None)
            self._fence_points.remove_node()
            self._fence_points = None
            self._fence_point_color_id = 1
            self._fence_point_coords = {}
            self._fence_mouse_coords = [[], []]
            self._fence_initialized = False
            self._sel_mask_triangle_coords = []

        if shape_type in ("fence", "lasso"):
            shape = selection_shapes["free"]
            shape.remove_node()
            del selection_shapes["free"]
            self._sel_mask_listener.ignore_all()
            self._sel_mask_listener = None
            sel_mask_data = Mgr.get("selection_mask_data")
            sel_mask_data["cam"].node().set_active(False)
            base = Mgr.get("base")
            base.graphics_engine.remove_window(self._sel_mask_buffer)
            self._sel_mask_buffer = None
            tri = sel_mask_data["triangle"]
            tri.hide()
            tri.clear_attrib(ShaderAttrib)
            vertex_data = tri.node().modify_geom(0).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(0)
            pos_writer.set_data3f(0., 0., 0.)
            background = sel_mask_data["background"]
            background.clear_texture()
            background.set_color((0., 0., 0., 1.))
            background.set_pos(0., 2., 0.)
            Mgr.exit_state("inactive")
        else:
            shape = selection_shapes[shape_type]
            shape.detach_node()

        x1, y1 = self._mouse_start_pos
        x2, y2 = self._mouse_end_pos
        x1 = max(0., min(1., .5 + x1 * .5))
        y1 = max(0., min(1., .5 + y1 * .5))
        x2 = max(0., min(1., .5 + x2 * .5))
        y2 = max(0., min(1., .5 + y2 * .5))
        l, r = min(x1, x2), max(x1, x2)
        b, t = min(y1, y2), max(y1, y2)
        self.__region_select((l, r, b, t))

    def __handle_region_select_mouse_up(self):

        shape_type = GlobalData["region_select"]["type"]

        if shape_type == "fence":

            pixel_under_mouse = UVMgr.get("pixel_under_mouse")

            if self._fence_initialized:
                if pixel_under_mouse != VBase4():
                    r, g, b, _ = [int(round(c * 255.)) for c in pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    self.__add_selection_shape_vertex(coords=self._fence_point_coords[color_id])
                    Mgr.get("base").graphics_engine.render_frame()
                    Mgr.exit_state("region_selection_mode", "uv")
                else:
                    self.__add_selection_shape_vertex(add_fence_point=True)
            else:
                self._fence_initialized = True

        else:

            Mgr.exit_state("region_selection_mode", "uv")

    def __cancel_region_select(self):

        self._region_sel_cancelled = True
        Mgr.exit_state("region_selection_mode", "uv")
        self._region_sel_cancelled = False

    def __init_region_select(self, op="replace"):

        self._selection_op = op
        Mgr.enter_state("region_selection_mode", "uv")

    def __region_select(self, frame):

        region_type = GlobalData["region_select"]["type"]

        if self._region_sel_cancelled:
            if region_type in ("fence", "lasso"):
                self._sel_mask_tex = None
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
        viewport_size = (w, h)
        # compute buffer size
        w_b = int(round((r - l) * w))
        h_b = int(round((t - b) * h))

        if min(w_b, h_b) < 2:
            return

        def get_off_axis_lens(film_size):

            lens = self.cam_lens
            focal_len = lens.get_focal_length()
            lens = lens.make_copy()
            lens.set_film_size(film_size)
            lens.set_film_offset(x_f, y_f)
            lens.set_focal_length(focal_len)

            return lens

        def get_expanded_region_lens():

            l, r, b, t = frame
            w, h = viewport_size
            l_exp = (int(round(l * w)) - 2) / w
            r_exp = (int(round(r * w)) + 2) / w
            b_exp = (int(round(b * h)) - 2) / h
            t_exp = (int(round(t * h)) + 2) / h
            # compute expanded film size
            lens = self.cam_lens
            w, h = lens.get_film_size()
            w_f = (r_exp - l_exp) * w
            h_f = (t_exp - b_exp) * h

            return get_off_axis_lens((w_f, h_f))

        enclose = GlobalData["region_select"]["enclose"]
        lens_exp = get_expanded_region_lens() if enclose else None

        if "ellipse" in region_type or "circle" in region_type:
            x1, y1 = self._mouse_start_pos
            x2, y2 = self._mouse_end_pos
            x1 = .5 + x1 * .5
            y1 = .5 + y1 * .5
            x2 = .5 + x2 * .5
            y2 = .5 + y2 * .5
            offset_x = (l - min(x1, x2)) * w
            offset_y = (b - min(y1, y2)) * h
            d = abs(x2 - x1) * w
            radius = d * .5
            aspect_ratio = d / (abs(y2 - y1) * h)
            ellipse_data = (radius, aspect_ratio, offset_x, offset_y)
        else:
            ellipse_data = ()

        if region_type in ("fence", "lasso"):
            img = PNMImage()
            self._sel_mask_tex.store(img)
            cropped_img = PNMImage(w_b, h_b)
            cropped_img.copy_sub_image(img, 0, 0, int(round(l * w)), int(round((1. - t) * h)))
            self._sel_mask_tex.load(cropped_img)

        UVMgr.get("picking_cam").set_active(False)

        lens = get_off_axis_lens((w_f, h_f))
        picking_mask = UVMgr.get("picking_mask")
        cam_np = self._region_sel_cam
        cam = cam_np.node()
        cam.set_lens(lens)
        cam.set_camera_mask(picking_mask)
        base = Mgr.get("base")
        bfr = base.win.make_texture_buffer("tex_buffer", w_b, h_b)
        bfr.set_one_shot(True)
        cam.set_active(True)
        base.make_camera(bfr, useCamera=cam_np)
        cam_np.reparent_to(self.cam)
        ge = base.graphics_engine

        ctrl_down = self.mouse_watcher.is_button_down(KeyboardButton.control())
        shift_down = self.mouse_watcher.is_button_down(KeyboardButton.shift())

        if ctrl_down:
            op = "toggle" if shift_down else "add"
        elif shift_down:
            op = "remove"
        else:
            op = self._selection_op

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
        uv_edit_options = GlobalData["uv_edit_options"]
        pick_via_poly = uv_edit_options["pick_via_poly"]

        if pick_via_poly:
            Mgr.update_interface_locally("uv", "picking_via_poly", False)

        def region_select_objects(sel, enclose=False):

            tex = Texture()
            tex.setup_1d_texture(obj_count, Texture.T_int, Texture.F_r32i)
            tex.set_clear_color(0)
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
            state_np.set_shader_input("selections", tex, read=False, write=True, priority=1)

            if "ellipse" in region_type or "circle" in region_type:
                state_np.set_shader_input("ellipse_data", Vec4(*ellipse_data))
            elif region_type in ("fence", "lasso"):
                if enclose:
                    img = PNMImage()
                    self._sel_mask_tex.store(img)
                    img.expand_border(2, 2, 2, 2, (0., 0., 0., 1.))
                    self._sel_mask_tex.load(img)
                state_np.set_shader_input("mask_tex", self._sel_mask_tex)
            elif enclose:
                state_np.set_shader_input("buffer_size", Vec2(w_b + 2, h_b + 2))

            state = state_np.get_state()
            cam.set_initial_state(state)

            ge.render_frame()

            if ge.extract_texture_data(tex, base.win.get_gsg()):

                texels = memoryview(tex.get_ram_image()).cast("I")
                sel_edges_by_seam = obj_lvl == "edge" and uv_edit_options["sel_edges_by_seam"]

                for i, mask in enumerate(texels):
                    for j in range(32):
                        if mask & (1 << j):
                            index = 32 * i + j
                            subobj = subobjs[index].get_merged_object()
                            if not sel_edges_by_seam or len(subobj) == 1:
                                sel.update(subobj.get_special_selection())

            state_np.clear_attrib(ShaderAttrib)

        new_sel = set()
        region_select_objects(new_sel)

        if enclose:
            bfr_exp = base.win.make_texture_buffer("tex_buffer_exp", w_b + 4, h_b + 4)
            base.make_camera(bfr_exp, useCamera=cam_np)
            cam_np.reparent_to(self.cam)
            cam.set_lens(lens_exp)
            inverse_sel = set()
            region_select_objects(inverse_sel, True)
            new_sel -= inverse_sel
            ge.remove_window(bfr_exp)

        if region_type in ("fence", "lasso"):
            self._sel_mask_tex = None

        if pick_via_poly:
            Mgr.update_interface_locally("uv", "picking_via_poly", True)

        selection = self._selections[uv_set_id][obj_lvl]
        color_ids = set()

        if op == "replace":
            selection.replace(new_sel)
        elif op == "add":
            selection.add(new_sel)
        elif op == "remove":
            selection.remove(new_sel)
        elif op == "toggle":
            old_sel = set(selection)
            selection.remove(old_sel & new_sel)
            selection.add(new_sel - old_sel)

        if obj_lvl == "poly":
            color_ids.update(poly.get_picking_color_id() for poly in selection)
        else:
            for subobj in selection:
                color_ids.update(subobj.get_picking_color_ids())

        self._world_sel_mgr.sync_selection(color_ids)

        cam.set_active(False)
        ge.remove_window(bfr)
        UVMgr.get("picking_cam").set_active()

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

                if Mgr.get_state_id("uv") == "region_selection_mode":

                    cursor_id = "select"

                else:

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

    def __init_select(self, op="replace"):

        alt_down = self.mouse_watcher.is_button_down(KeyboardButton.alt())
        region_select = not alt_down if GlobalData["region_select"]["is_default"] else alt_down

        if region_select:
            self.__init_region_select(op)
            return

        if not (self.mouse_watcher.has_mouse() and self._pixel_under_mouse):
            return

        self._selection_op = op
        self._can_select_single = False
        mouse_pointer = Mgr.get("base").win.get_pointer(0)
        self._mouse_start_pos = (mouse_pointer.get_x(), mouse_pointer.get_y())
        obj_lvl = self._obj_lvl

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b
        pickable_type, picked_obj = self.__get_picked_object(color_id, a)

        if (GlobalData["active_uv_transform_type"] and obj_lvl != pickable_type == "poly"
                and GlobalData["uv_edit_options"]["pick_via_poly"]):
            self.__init_selection_via_poly(picked_obj)
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
            Mgr.enter_state("picking_via_poly", "uv")
            return

        self._color_id = obj.get_picking_color_id() if obj else None
        self.__select()

    def __select(self, check_mouse=True, ignore_transform=False):

        obj_lvl = self._obj_lvl
        uv_set_id = self._uv_set_id
        selection = self._selections[uv_set_id][obj_lvl]
        subobj = self._uv_registry[uv_set_id][obj_lvl].get(self._color_id)
        subobj = subobj.get_merged_object() if subobj else None
        sync_selection = True
        op = self._selection_op

        if subobj:

            if op == "replace":

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

            elif op == "add":

                new_sel = set(subobj.get_special_selection())
                selection.add(new_sel)
                transform_allowed = GlobalData["active_uv_transform_type"]

                if check_mouse and transform_allowed:
                    Mgr.enter_state("checking_mouse_offset", "uv")

            elif op == "remove":

                new_sel = set(subobj.get_special_selection())
                selection.remove(new_sel)

            elif op == "toggle":

                old_sel = set(selection)
                new_sel = set(subobj.get_special_selection())
                selection.remove(old_sel & new_sel)
                selection.add(new_sel - old_sel)

                if subobj in selection:
                    transform_allowed = GlobalData["active_uv_transform_type"]
                else:
                    transform_allowed = False

                if check_mouse and transform_allowed:
                    Mgr.enter_state("checking_mouse_offset", "uv")

        elif op == "replace":

            selection.clear()

        else:

            sync_selection = False

        if sync_selection:

            color_ids = set()

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
        color_ids = set()
        selection.replace(subobj.get_special_selection())

        if obj_lvl == "poly":
            color_ids.update(poly.get_picking_color_id() for poly in selection)
        else:
            for subobj in selection:
                color_ids.update(subobj.get_picking_color_ids())

        self._world_sel_mgr.sync_selection(color_ids)

    def sync_selection(self, color_ids):

        obj_lvl = self._obj_lvl
        uv_set_id = self._uv_set_id
        uv_registry = self._uv_registry[uv_set_id][obj_lvl]
        selection = self._selections[uv_set_id][obj_lvl]
        subobjects = set(uv_registry[color_id].get_merged_object() for color_id in color_ids)
        selection.replace(subobjects)

    def __init_selection_via_poly(self, picked_poly):

        if picked_poly:
            self._picked_poly = picked_poly
            Mgr.enter_state("picking_via_poly", "uv")

    def __init_subobj_picking_via_poly(self, prev_state_id, is_active):

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

        ignore_transform = not transform
        self.__select(False, ignore_transform)

        uv_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for other_uv_data_obj in self._uv_data_objs[self._uv_set_id].values():
            if other_uv_data_obj is not uv_data_obj:
                other_uv_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
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
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

        self._transf_gizmo.set_pickable()

    def create_selections(self):

        obj_lvls = ("vert", "edge", "poly")
        self._selections[self._uv_set_id] = dict((lvl, UVSelection(lvl)) for lvl in obj_lvls)

    def delete_selections(self):

        self._selections.clear()
