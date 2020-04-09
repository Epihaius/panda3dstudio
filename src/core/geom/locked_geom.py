from ..base import *
from .material import render_state_to_material


def create_aux_geom(geom_data):

    import array

    sides = {}
    polys = []
    positions = {}
    vert_count = 0

    for poly_data in geom_data:

        poly = []
        poly_verts = set()
        edges = []
        sides[id(poly)] = poly_sides = []
        diagonals = []

        for tri_data in poly_data["tris"]:

            tri = []
            poly.append(tri)
            vert_count += 3

            for vert_data in tri_data:
                vert_id = id(vert_data)
                positions[vert_id] = vert_data["pos"]
                tri.append(vert_id)
                poly_verts.add(vert_id)

            for i, j in ((0, 1), (1, 2), (2, 0)):

                edge = {id(tri_data[i]), id(tri_data[j])}

                if edge in edges:
                    # if the edge appears twice, it's actually a diagonal
                    edges.remove(edge)
                    diagonals.append(edge)
                else:
                    edges.append(edge)

        for tri_data in poly_data["tris"]:
            vi1, vi2, vi3 = [id(vert_data) for vert_data in tri_data]
            # determine which triangle edges should be rendered (i.e. whether
            # they are polygon edges);
            # 1 indicates that an edge should be rendered, 0 that it shouldn't;
            # pack these values into a single int for space-efficient storing in
            # the "sides" vertex data column
            s1 = 0 if {vi1, vi2} in diagonals else 1
            s2 = 0 if {vi2, vi3} in diagonals else 1
            s3 = 0 if {vi3, vi1} in diagonals else 1
            poly_sides.append(s1 << 2 | s2 << 1 | s3)

        polys.append((poly, poly_verts))

    # Build auxiliary geom, used for wireframe display and snapping.

    vertex_format = Mgr.get("aux_locked_vertex_format")
    vertex_data = GeomVertexData("wireframe_data", vertex_format, Geom.UH_static)
    vertex_data.reserve_num_rows(vert_count)
    vertex_data.unclean_set_num_rows(vert_count)
    pos_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
    sides_view = memoryview(vertex_data.modify_array(1)).cast("B").cast("I")
    snap_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("f")
    pos_values = array.array("f", [])
    sides_values = array.array("I", [])
    snap_values = array.array("f", [])
    prim = GeomTriangles(Geom.UH_static)
    prim.set_index_type(Geom.NT_uint32)
    prim.reserve_num_vertices(vert_count)
    prim.add_next_vertices(vert_count)

    for poly, poly_verts in polys:

        pos = sum((Point3(*positions[v_id]) for v_id in poly_verts),
            Point3()) / len(poly_verts)

        for tri_vert_ids, tri_sides in zip(poly, sides[id(poly)]):
            for v_id in tri_vert_ids:
                x, y, z = positions[v_id]
                pos_values.extend((x, y, z))
                sides_values.append(tri_sides)
                snap_values.extend(pos)

    pos_view[:] = pos_values
    sides_view[:] = sides_values
    snap_view[:] = snap_values
    geom = Geom(vertex_data)
    geom.add_primitive(prim)
    geom_node = GeomNode("aux_geom")
    geom_node.add_geom(geom)
    aux_geom = NodePath(geom_node)

    return aux_geom


class MergedVertex:

    __slots__ = ("_ids",)

    def __init__(self, vert_id=None):

        self._ids = [] if vert_id is None else [vert_id]

    def __getitem__(self, index):

        return self._ids[index]

    def __len__(self):

        return len(self._ids)

    def append(self, vert_id):

        self._ids.append(vert_id)

    def extend(self, vert_ids):

        self._ids.extend(vert_ids)

    def remove(self, vert_id):

        self._ids.remove(vert_id)


class MergedUV:

    __slots__ = ("merged_vert", "uv")

    def __init__(self, merged_vert, u, v):

        self.merged_vert = merged_vert
        self.uv = [u, v]


class LockedGeomBase:

    def __getstate__(self):

        state = self.__dict__.copy()
        state["geom"] = self.geom_for_pickling
        state["aux_geom"] = self.aux_geom_for_pickling
        state["geom_root"] = NodePath("locked_geom_root")

        del state["model"]
        del state["_aux_state"]
        del state["is_tangent_space_initialized"]

        return state

    def __setstate__(self, state):

        self.__dict__ = state

        self.model = None
        shader = shaders.Shaders.locked_wireframe
        pickable_type_id = PickableTypes.get_id("locked_geom")
        picking_color = get_color_vec(self.picking_color_id, pickable_type_id)
        np = NodePath("state")
        np.set_color(picking_color, 1)
        np.set_shader(shader, 1)
        np.set_shader_input("inverted", self._inverted_geometry, 1)
        np.set_shader_input("two_sided", GD["two_sided"], 1)
        state = np.get_state()
        self._aux_state = state

        self.is_tangent_space_initialized = False

        if not self.geom_root:
            self.geom_root = NodePath("locked_geom_root")
            return

        aux_geom = self.aux_geom
        # add wireframe shader
        aux_geom.set_shader(shader)
        aux_geom.set_shader_input("inverted", self._inverted_geometry)
        aux_geom.set_shader_input("two_sided", GD["two_sided"])
        snap_type_id = PickableTypes.get_id("snap_geom") / 255.
        aux_geom.set_shader_input("snap_type_id", snap_type_id)
        aux_geom.hide(Mgr.get("render_mask"))
        aux_geom.hide(Mgr.get("picking_mask"))
        picking_col_id_str = str(self.picking_color_id)
        self.geom.set_tag("picking_color", picking_col_id_str)
        aux_geom.set_tag("picking_color", picking_col_id_str + "_wire")

    def __init__(self, model, geom, geom_data, picking_col_id):

        self.model = model
        self.geom_root = None
        self.geom = geom
        self.aux_geom = aux_geom = create_aux_geom(geom_data)
        self.geom_data = geom_data
        self.picking_color_id = picking_col_id
        self.is_tangent_space_initialized = False
        self._inverted_geometry = False
        self._geometry_unlock_started = False
        self._geometry_unlock_ended = False
        model.geom_obj = self

        self.setup_geoms()

        pickable_type_id = PickableTypes.get_id("locked_geom")
        picking_color = get_color_vec(picking_col_id, pickable_type_id)
        np = NodePath("state")
        np.set_color(picking_color, 1)
        state = np.get_state()
        picking_col_id_str = str(picking_col_id)
        Mgr.do("set_locked_geom_picking_color", picking_col_id_str, state)
        shader = shaders.Shaders.locked_wireframe
        np.set_shader(shader, 1)
        np.set_shader_input("inverted", False, 1)
        np.set_shader_input("two_sided", GD["two_sided"], 1)
        state = np.get_state()
        Mgr.do("set_locked_geom_picking_color", picking_col_id_str + "_wire", state)
        self._aux_state = state

    def setup_geoms(self):

        if self.geom_root:
            self.geom_root.get_children().detach()
        else:
            self.geom_root = self.model.origin.attach_new_node("locked_geom_root")

        geom = self.geom
        aux_geom = self.aux_geom
        geom.reparent_to(self.geom_root)
        aux_geom.reparent_to(self.geom_root)
        # set wireframe shader
        shader = shaders.Shaders.locked_wireframe
        aux_geom.set_shader(shader)
        aux_geom.set_shader_input("inverted", self._inverted_geometry)
        aux_geom.set_shader_input("two_sided", GD["two_sided"])
        snap_type_id = PickableTypes.get_id("snap_geom") / 255.
        aux_geom.set_shader_input("snap_type_id", snap_type_id)

        masks = Mgr.get("render_mask") | Mgr.get("picking_mask")
        geom.show(masks)
        aux_geom.hide(masks)
        picking_col_id_str = str(self.picking_color_id)
        geom.set_tag("picking_color", picking_col_id_str)
        aux_geom.set_tag("picking_color", picking_col_id_str + "_wire")
        self.update_selection_state(self.model.is_selected())

        if self.has_inverted_geometry():
            self.invert_geometry(True, force=True)

        if self.is_tangent_space_initialized:

            def task():

                flip_tangent, flip_bitangent = self.model.get_tangent_space_flip()
                self.update_tangent_space(flip_tangent, flip_bitangent)

            sort = PendingTasks.get_sort("set_normals", "object") + 1
            obj_id = self.model.id
            PendingTasks.add(task, "upd_tangent_space", "object", sort, id_prefix=obj_id)

        material = self.model.get_material()

        if material:

            vert_color_map = material.get_tex_map("vertex color")
            texture = vert_color_map.get_texture()

            if vert_color_map.active and texture:
                self.bake_texture(texture)

    @property
    def geom_for_pickling(self):

        geom = NodePath(self.geom.node().make_copy())
        geom.set_state(RenderState.make_empty())

        if self.has_inverted_geometry():
            g = geom.node().modify_geom(0)
            g.reverse_in_place()
            vertex_data = g.get_vertex_data().reverse_normals()
            g.set_vertex_data(vertex_data)

        return geom

    @property
    def aux_geom_for_pickling(self):

        geom = NodePath(self.aux_geom.node().make_copy())
        geom.set_state(RenderState.make_empty())

        return geom

    def destroy(self, unregister=True):

        self.geom_root.detach_node()
        self.geom_root = None
        self.geom = None
        self.aux_geom = None

        if unregister:
            Mgr.do("unregister_locked_geom", self)

        picking_col_id_str = str(self.picking_color_id)
        Mgr.do("clear_locked_geom_picking_color", picking_col_id_str)
        Mgr.do("clear_locked_geom_picking_color", picking_col_id_str + "_wire")

    def register(self, restore=True):

        Mgr.do("register_locked_geom", self, restore)

        if restore:
            pickable_type_id = PickableTypes.get_id("locked_geom")
            picking_color = get_color_vec(self.picking_color_id, pickable_type_id)
            np = NodePath("state")
            np.set_color(picking_color, 1)
            state = np.get_state()
            picking_col_id_str = str(self.picking_color_id)
            Mgr.do("set_locked_geom_picking_color", picking_col_id_str, state)
            Mgr.do("set_locked_geom_picking_color", picking_col_id_str + "_wire", self._aux_state)
            Mgr.notify("pickable_geom_altered", self.toplevel_obj)

    def unregister(self):

        Mgr.do("unregister_locked_geom", self)

    def restore_geom_root(self):

        geom_root = self.geom_root
        geom_root.reparent_to(self.model.origin)

        if self.geom:
            self.geom.reparent_to(geom_root)
            self.aux_geom.reparent_to(geom_root)

    def get_toplevel_object(self, get_group=False):

        return self.model.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def get_point_at_screen_pos(self, screen_pos):

        cam = GD.cam()
        normal = V3D(GD.world.get_relative_vector(cam, Vec3.forward()))
        point = self.geom.get_pos(GD.world)
        plane = Plane(normal, point)

        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.world.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point

    def update_tangent_space(self, flip_tangent, flip_bitangent):

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        vert_indices = self.geom.node().get_geom(0).get_primitive(0).get_vertex_list()

        pos_reader = GeomVertexReader(vertex_data, "vertex")
        normal_reader = GeomVertexReader(vertex_data, "normal")
        uv_reader = GeomVertexReader(vertex_data, "texcoord")
        tan_writer = GeomVertexWriter(vertex_data, "tangent")
        bitan_writer = GeomVertexWriter(vertex_data, "binormal")
        vert_handlers = (pos_reader, normal_reader, uv_reader, tan_writer, bitan_writer)

        processed_rows = []
        epsilon = 1.e-010

        for rows in (vert_indices[i:i + 3] for i in range(0, len(vert_indices), 3)):

            for row in rows:

                if row in processed_rows:
                    continue

                other_rows = list(rows)
                other_rows.remove(row)
                row1, row2 = other_rows

                for handler in vert_handlers:
                    handler.set_row(row)

                pos = pos_reader.get_data3()
                normal = normal_reader.get_data3()
                uv = uv_reader.get_data2()

                pos_reader.set_row(row1)
                pos1 = pos_reader.get_data3()
                pos_reader.set_row(row2)
                pos2 = pos_reader.get_data3()
                pos_vec1 = pos1 - pos
                pos_vec2 = pos2 - pos

                uv_reader.set_row(row1)
                uv1 = uv_reader.get_data2()
                uv_reader.set_row(row2)
                uv2 = uv_reader.get_data2()
                uv_vec1 = uv1 - uv
                uv_vec2 = uv2 - uv

                # compute a vector pointing in the +U direction, in texture space
                # and in world space

                if abs(uv_vec1.y) < epsilon:
                    u_vec_local = uv_vec1
                    u_vec_world = Vec3(pos_vec1)
                elif abs(uv_vec2.y) < epsilon:
                    u_vec_local = uv_vec2
                    u_vec_world = Vec3(pos_vec2)
                else:
                    scale = (uv_vec1.y / uv_vec2.y)
                    u_vec_local = uv_vec1 - uv_vec2 * scale
                    # u_vec_local.y will be 0 and thus point in the -/+U direction;
                    # replacing the texture-space vectors with the corresponding
                    # world-space vectors will therefore yield a world-space U-vector
                    u_vec_world = pos_vec1 - pos_vec2 * scale

                if u_vec_local.x < 0.:
                    u_vec_world *= -1.

                # compute a vector pointing in the +V direction, in texture space
                # and in world space

                if abs(uv_vec1.x) < epsilon:
                    v_vec_local = uv_vec1
                    v_vec_world = Vec3(pos_vec1)
                elif abs(uv_vec2.x) < epsilon:
                    v_vec_local = uv_vec2
                    v_vec_world = Vec3(pos_vec2)
                else:
                    scale = (uv_vec1.x / uv_vec2.x)
                    v_vec_local = uv_vec1 - uv_vec2 * scale
                    # v_vec_local.x will be 0 and thus point in the -/+V direction;
                    # replacing the texture-space vectors with the corresponding
                    # world-space vectors will therefore yield a world-space V-vector
                    v_vec_world = pos_vec1 - pos_vec2 * scale

                if v_vec_local.y < 0.:
                    v_vec_world *= -1.

                tangent_plane = Plane(normal, Point3())
                # the tangent vector is the world-space U-vector projected onto
                # the tangent plane
                tangent = Vec3(tangent_plane.project(Point3(u_vec_world)))

                if not tangent.normalize():
                    continue

                # the bitangent vector is the world-space V-vector projected onto
                # the tangent plane
                bitangent = Vec3(tangent_plane.project(Point3(v_vec_world)))

                if not bitangent.normalize():
                    continue

                if flip_tangent:
                    tangent *= -1.

                if flip_bitangent:
                    bitangent *= -1.

                tan_writer.set_data3(tangent)
                bitan_writer.set_data3(bitangent)
                processed_rows.append(row)

        self.is_tangent_space_initialized = True

    def init_tangent_space(self):

        if not self.is_tangent_space_initialized:
            if self.geom:
                flip_tangent, flip_bitangent = self.model.get_tangent_space_flip()
                self.update_tangent_space(flip_tangent, flip_bitangent)
            else:
                self.is_tangent_space_initialized = True

    def bake_texture(self, texture):

        def task():

            vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
            vertex_data_copy = vertex_data.set_color((1., 1., 1., 1.))
            array = vertex_data_copy.get_array(1)
            vertex_data.set_array(1, GeomVertexArrayData(array))
            geom_copy = self.geom.copy_to(GD.world)
            geom_copy.detach_node()
            geom_copy.set_texture(TextureStage.default, texture)
            geom_copy.flatten_light()
            geom_copy.apply_texture_colors()
            vertex_data_copy = geom_copy.node().modify_geom(0).modify_vertex_data()
            index = vertex_data_copy.format.get_array_with("color")
            array = vertex_data_copy.modify_array(index)
            vertex_data.set_array(1, array)

        if self.geom:
            task()
        else:
            sort = PendingTasks.get_sort("set_normals", "object") + 1
            obj_id = self.model.id
            PendingTasks.add(task, "bake_tex", "object", sort, id_prefix=obj_id)

    def get_subobj_selection(self, subobj_lvl):

        return []

    def set_wireframe_color(self, color): pass

    def update_selection_state(self, is_selected=True):

        if GD["render_mode"] == "shaded":
            return

        self.update_render_mode(is_selected)

    def update_render_mode(self, is_selected):

        render_mode = GD["render_mode"]
        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        geom = self.geom
        aux_geom = self.aux_geom

        if not geom:
            return

        if is_selected:
            aux_geom.set_color((1., 1., 1., 1.))
        else:
            aux_geom.set_color(self.model.get_color())

        if "wire" in render_mode:
            aux_geom.show(render_mask)
        else:
            aux_geom.hide(render_mask)

        if "shaded" in render_mode:
            geom.show(render_mask)
        else:
            geom.hide(render_mask)

        if is_selected or render_mode != "wire":
            aux_geom.hide(picking_mask)
            geom.show(picking_mask)
        else:
            aux_geom.show(picking_mask)
            geom.hide(picking_mask)

    def set_two_sided(self, two_sided=True):

        self.aux_geom.set_shader_input("two_sided", two_sided)
        np = NodePath("state")
        np.set_state(self._aux_state)
        np.set_shader_input("two_sided", two_sided, 1)
        state = np.get_state()
        picking_col_id_str = str(self.picking_color_id)
        Mgr.do("set_locked_geom_picking_color", picking_col_id_str + "_wire", state)
        self._aux_state = state

    def invert_geometry(self, invert=True, force=False):

        if not force and self._inverted_geometry == invert:
            return False

        geom = self.geom.node().modify_geom(0)
        geom.reverse_in_place()
        vertex_data = geom.get_vertex_data().reverse_normals()
        geom.set_vertex_data(vertex_data)
        self.aux_geom.set_shader_input("inverted", invert)
        np = NodePath("state")
        np.set_state(self._aux_state)
        np.set_shader_input("inverted", invert, 1)
        state = np.get_state()
        picking_col_id_str = str(self.picking_color_id)
        Mgr.do("set_locked_geom_picking_color", picking_col_id_str + "_wire", state)
        self._aux_state = state
        self._inverted_geometry = invert

        return True

    def has_inverted_geometry(self):

        return self._inverted_geometry

    def enable_snap(self, snap_target_type, enable=True):

        mask = Mgr.get("picking_mask", 1)
        geom = self.aux_geom
        geom.show_through(mask) if enable else geom.hide(mask)

        if enable:
            np = NodePath("state")
            np.set_shader(shaders.Shaders.snap[snap_target_type], 1)
            snap_type_id = PickableTypes.get_id("snap_geom") / 255.
            np.set_shader_input("snap_type_id", snap_type_id)
            np.set_shader_input("inverted", self._inverted_geometry, 1)
            np.set_shader_input("two_sided", GD["two_sided"], 1)
            state = np.get_state()
        else:
            state = self._aux_state

        picking_col_id_str = str(self.picking_color_id)
        Mgr.do("set_locked_geom_picking_color", picking_col_id_str + "_wire", state)

    def __update_normal_data(self):

        # Replace the initial normals with their current values.

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        normal_array = vertex_data.get_array(2)
        normal_view = memoryview(normal_array).cast("B").cast("f")
        sign = -1. if self.has_inverted_geometry() else 1.
        i = 0

        for p in self.geom_data:
            for v in p["verts"]:
                v["normal"] = Vec3(*normal_view[i:i+3]) * sign
                i += 3

    def __cancel_geometry_unlock(self, info):

        if self._geometry_unlock_started:
            self.model.geom_obj.geom_data_obj.cancel_creation()
        elif self._geometry_unlock_ended:
            self.model.geom_obj.geom_data_obj.destroy(unregister=False)

        if info == "geometry_unlock":
            self.model.geom_obj = self

    def unlock_geometry(self, unlocked_geom, update_normal_data=False):

        obj_id = self.toplevel_obj.id
        id_str = str(obj_id) + "geom_data"
        handler = self.__cancel_geometry_unlock
        Mgr.add_notification_handler("long_process_cancelled", id_str, handler, once=True)
        task = lambda: Mgr.remove_notification_handler("long_process_cancelled", id_str)
        task_id = "remove_notification_handler"
        PendingTasks.add(task, task_id, "object", id_prefix=id_str, sort=100)

        Mgr.do("create_registry_backups")
        Mgr.do("create_id_range_backups")
        Mgr.do("update_picking_col_id_ranges")
        Mgr.update_locally("screenshot_removal")

        def task():

            self._geometry_unlock_started = True
            self._geometry_unlock_ended = False

            geom_data = self.geom_data

            if update_normal_data:
                self.__update_normal_data()

            poly_count = len(geom_data)
            progress_steps = (poly_count // 20) * 4
            gradual = progress_steps > 80

            if gradual:
                Mgr.update_remotely("screenshot", "create")
                GD["progress_steps"] = progress_steps

            geom_data_obj = unlocked_geom.geom_data_obj
            vert_data = geom_data[0]["verts"][0]

            if "pos_ind" not in vert_data:
                for _ in self._define_connectivity(geom_data, gradual=gradual):
                    if gradual:
                        yield True

            for _ in geom_data_obj.process_geom_data(geom_data, gradual=gradual):
                if gradual:
                    yield True

            for _ in geom_data_obj.create_geometry("unlocked", gradual=gradual):
                if gradual:
                    yield True

            if self.has_inverted_geometry():
                geom_data_obj.invert_geometry(delay=False)

            geom_data_obj.finalize_geometry()
            geom_data_obj.update_poly_centers()
            geom_data_obj.register(restore=False)

            if self.model.has_tangent_space():
                geom_data_obj.init_tangent_space()

            geom_data_obj.init_normal_length()
            geom_data_obj.init_normal_sharing()

            for _ in geom_data_obj.update_smoothing(gradual):
                if gradual:
                    yield True

            geom_data_obj.set_initial_vertex_colors()
            geom_data_obj.update_vertex_colors()

            self._geometry_unlock_started = False
            self._geometry_unlock_ended = True

            Mgr.notify("pickable_geom_altered", self.toplevel_obj)

            yield False

        task_id = "set_geom_data"
        descr = "Unlocking geometry..."
        PendingTasks.add(task, task_id, "object", id_prefix=obj_id, gradual=True,
                         process_id="geometry_unlock", descr=descr, cancellable=True)

        def task():

            self.destroy()
            self.model.bbox.color = (1., 1., 1., 1.)

        task_id = "set_geom_data"
        PendingTasks.add(task, task_id, "object", 99, id_prefix=obj_id)

    def get_subdivision_data(self):

        vert_data = self.geom_data[0]["verts"][0]

        if "pos_ind" not in vert_data:
            for _ in self._define_connectivity(self.geom_data): pass

        positions = []
        faces = []
        uvs = []
        uv_faces = []
        sign = -1 if self.has_inverted_geometry() else 1

        for poly_data in self.geom_data:

            face = []
            uv_face = []

            for vert_data in poly_data["verts"]:

                index = vert_data["pos_ind"]
                face.append(index)

                if index == len(positions):
                    positions.append(list(vert_data["pos"]))

                uv_index = vert_data["uv_ind"]
                uv_face.append(uv_index)

                if uv_index == len(uvs):
                    uvs.append((list(vert_data["uvs"].get(0, (0., 0.))), index))

            faces.append(face[::sign])
            uv_faces.append(uv_face[::sign])

        return positions, uvs, faces, uv_faces

    def make_pickable(self, mask_index=0, pickable=True, show_through=True):

        mask = Mgr.get("picking_mask", mask_index)
        geom = self.geom
        aux_geom = self.aux_geom
        render_mode = GD["render_mode"]

        if pickable:
            if self.model.is_selected() or render_mode != "wire":
                geom.show_through(mask) if show_through else geom.show(mask)
            else:
                aux_geom.show_through(mask) if show_through else aux_geom.show(mask)
        else:
            if self.model.is_selected() or render_mode != "wire":
                geom.hide(mask)
            else:
                aux_geom.hide(mask)

    def get_property_ids(self, for_hist=False):

        return self._prop_ids + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids

    def get_property_to_store(self, prop_id, event_type=""):

        data = {prop_id: {"main": self.get_property(prop_id)}}

        return data

    def get_data_to_store(self, event_type, prop_id=""):

        data = {}

        if event_type == "creation":

            data["geom_obj"] = {"main": self}
            prop_ids = self.get_property_ids()

            for prop_id in prop_ids:
                data.update(self.get_property_to_store(prop_id))

        elif event_type == "prop_change":

            if prop_id in self.get_property_ids():
                data.update(self.get_property_to_store(prop_id))

        return data

    def restore_property(self, prop_id, restore_type, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id
        val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
        self.set_property(prop_id, val, restore_type)

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        if "self" in data_ids:

            self.restore_geom_root()

            for prop_id in self.get_property_ids():
                self.restore_property(prop_id, restore_type, old_time_id, new_time_id)

            self.register()
            self.update_render_mode(self.model.is_selected())

        else:

            for prop_id in self.get_property_ids():
                if prop_id in data_ids:
                    self.restore_property(prop_id, restore_type, old_time_id, new_time_id)
                    data_ids.remove(prop_id)


class LockedGeom(LockedGeomBase):

    def __getstate__(self):

        state = LockedGeomBase.__getstate__(self)
        del state["_initial_vertex_colors"]

        return state

    def __setstate__(self, state):

        LockedGeomBase.__setstate__(self, state)

        vertex_data = self.geom.node().get_geom(0).get_vertex_data()
        array = GeomVertexArrayData(vertex_data.get_array(1))
        self._initial_vertex_colors = array

    def __init__(self, model, geom, geom_data, picking_col_id,
                 materials=None, update_model=True):

        LockedGeomBase.__init__(self, model, geom, geom_data, picking_col_id)

        self._prop_ids = []
        self._type_prop_ids = ["uv_set_names", "inverted_geom", "normal_viz",
                               "normal_color", "normal_length"]
        self.type = "locked_geom"
        self._normals_shown = False
        self._normal_color = (.75, .75, 0., 1.)
        prim_count = geom.node().get_geom(0).get_primitive(0).get_num_primitives()
        bounds = geom.get_tight_bounds()

        if bounds:
            p1, p2 = bounds
            x, y, z = p2 - p1
            a = (x + y + z) / 3.
            self._normal_length = min(a * .25, max(.001, 500. * a / prim_count))
        else:
            self._normal_length = .001

        if update_model:
            model.pivot.set_transform(geom.get_transform())

        geom.clear_transform()
        render_state = geom.get_state()
        geom.set_state(RenderState.make_empty())
        src_vert_data = geom.node().get_geom(0).get_vertex_data()
        src_format = src_vert_data.format
        dest_format = Mgr.get("vertex_format_full")
        dest_vert_data = src_vert_data.convert_to(dest_format)
        self._initial_vertex_colors = dest_vert_data.get_array(1)
        geom.node().modify_geom(0).set_vertex_data(dest_vert_data)
        dest_vert_data = geom.node().modify_geom(0).modify_vertex_data()
        num_rows = src_vert_data.get_num_rows()
        uv_set_list = [InternalName.get_texcoord()]
        uv_set_list += [InternalName.get_texcoord_name(str(i)) for i in range(1, 8)]
        src_uv_set_names = ["", "1", "2", "3", "4", "5", "6", "7"]

        material, uv_set_names = render_state_to_material(render_state, src_format, materials)

        for src_uv_set, dest_uv_set in uv_set_names.items():

            uv_set_id = uv_set_list.index(dest_uv_set)
            uv_name = src_uv_set.name
            uv_name = "" if uv_name == "texcoord" else src_uv_set.basename
            src_uv_set_names[uv_set_id] = uv_name
            uv_reader = GeomVertexReader(src_vert_data, src_uv_set)
            uv_writer = GeomVertexWriter(dest_vert_data, dest_uv_set)

            for i in range(num_rows):
                uv = uv_reader.get_data2()
                uv_writer.set_data2(uv)

        self._uv_set_names = src_uv_set_names

        if model.has_tangent_space():
            self.init_tangent_space()

        if material:
            model.set_material(material)

        if update_model:
            color = tuple([random.random() * .4 + .5 for i in range(3)] + [1.])
            model.set_color(color, update_app=False)

        def update_render_mode():

            self.update_render_mode(False if update_model else model.is_selected())

        obj_id = model.id
        PendingTasks.add(update_render_mode, "update_render_mode", "object", 0, obj_id)

    def __del__(self):

        Notifiers.geom.debug('LockedGeom garbage-collected.')

    def reset_vertex_colors(self):

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        array = GeomVertexArrayData(self._initial_vertex_colors)
        vertex_data.set_array(1, array)

    def set_uv_set_name(self, uv_set_id, uv_set_name):

        uv_set_names = self._uv_set_names[:]
        del uv_set_names[uv_set_id]

        if uv_set_name == "" and "" in uv_set_names:
            uv_set_name = "0"

        if uv_set_name != "":
            uv_set_name = get_unique_name(uv_set_name, uv_set_names)

        change = True

        if self._uv_set_names[uv_set_id] == uv_set_name:
            change = False

        self._uv_set_names[uv_set_id] = uv_set_name
        Mgr.update_remotely("uv_set_name", self._uv_set_names)

        return change

    def set_uv_set_names(self, uv_set_names):

        if self._uv_set_names == uv_set_names:
            return False

        self._uv_set_names = uv_set_names

        return True

    def get_uv_set_names(self):

        return self._uv_set_names

    def show_normals(self, show=True):

        if self._normals_shown == show:
            return False

        if show:
            points_geom = self.geom.node().get_geom(0).make_points()
            node = GeomNode("normals_geom")
            node.add_geom(points_geom)
            node.set_bounds(OmniBoundingVolume())
            node.final = True
            normals_geom = self.geom_root.attach_new_node(node)
            shader = shaders.Shaders.normal
            normals_geom.set_shader(shader)
            normals_geom.set_shader_input("normal_length", self._normal_length)
            normals_geom.set_color(self._normal_color)
            normals_geom.hide(Mgr.get("picking_mask"))
        else:
            normals_geom = self.geom_root.find("**/normals_geom")
            normals_geom.detach_node()

        self._normals_shown = show

        return True

    def invert_geometry(self, invert=True):

        if not LockedGeomBase.invert_geometry(self, invert):
            return False

        if self._normals_shown:
            self.show_normals(False)
            self.show_normals()

        return True

    def set_normal_color(self, color):

        if self._normal_color == color:
            return False

        if self._normals_shown:
            normals_geom = self.geom.find("**/normals_geom")
            normals_geom.set_color(color)

        self._normal_color = color

        return True

    def set_normal_length(self, normal_length, state="done"):

        if self._normal_length == normal_length and state == "done":
            return False

        if self._normals_shown:
            normals_geom = self.geom.find("**/normals_geom")
            normals_geom.set_shader_input("normal_length", normal_length)

        if state == "done":
            self._normal_length = normal_length
            return True

        return False

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "uv_set_names":
            return self._uv_set_names
        elif prop_id == "inverted_geom":
            return self._inverted_geometry
        elif prop_id == "normal_viz":
            return self._normals_shown
        elif prop_id == "normal_color":
            if for_remote_update:
                return [x for x in self._normal_color][:3]
            else:
                return self._normal_color
        elif prop_id == "normal_length":
            return self._normal_length

    def set_property(self, prop_id, value, restore=""):

        if prop_id == "uv_set_names":
            r = self.set_uv_set_names(value)
        elif prop_id == "inverted_geom":
            r = self.invert_geometry(value)
        elif prop_id == "normal_viz":
            r = self.show_normals(value)
        elif prop_id == "normal_color":
            if restore:
                self.set_normal_color(value)
            else:
                r, g, b = value
                color = (r, g, b, 1.)
                r = self.set_normal_color(color)
                Mgr.update_remotely("selected_obj_prop", "locked_geom", prop_id, value)
        elif prop_id == "normal_length":
            r = self.set_normal_length(value)

        if restore:
            Mgr.update_remotely("selected_obj_prop", "locked_geom", prop_id, value)
        else:
            return r

    def __compute_indices(self, geom_data, verts, merged_verts, gradual=False):

        merged_uvs = {}
        processed_mvs = []
        processed_muvs = []

        for merged_vert in set(tuple(mv) for mv in merged_verts.values()):

            verts_by_uv = {}

            for vert_id in merged_vert:

                vert = verts[vert_id]
                uv = vert["uvs"].get(0, (0., 0.))

                if uv in verts_by_uv:
                    verts_by_uv[uv].append(vert_id)
                else:
                    verts_by_uv[uv] = [vert_id]

            for (u, v), vert_ids in verts_by_uv.items():
                merged_uv = MergedUV(merged_vert, u, v)
                merged_uvs.update({v_id: merged_uv for v_id in vert_ids})

        if gradual:
            poly_count = 0

        for poly_data in geom_data:

            for vert_data in poly_data["verts"]:

                vert_id = id(vert_data)
                merged_vertex = merged_verts[vert_id]
                merged_uv = merged_uvs[vert_id]

                if merged_vertex in processed_mvs:
                    vert_data["pos_ind"] = processed_mvs.index(merged_vertex)
                else:
                    vert_data["pos_ind"] = len(processed_mvs)
                    processed_mvs.append(merged_vertex)

                if merged_uv in processed_muvs:
                    vert_data["uv_ind"] = processed_muvs.index(merged_uv)
                else:
                    vert_data["uv_ind"] = len(processed_muvs)
                    processed_muvs.append(merged_uv)

            if gradual:

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

    def _define_connectivity(self, geom_data, gradual=False):

        def is_doublesided(edge_pos, poly_pos, other_poly_pos):

            p1, p2 = edge_pos
            i1 = poly_pos.index(p1)
            p3 = poly_pos[i1-1]
            i2 = poly_pos.index(p2)
            p4 = poly_pos[0 if i2 == len(poly_pos) - 1 else i2+1]
            i1 = other_poly_pos.index(p2)
            p5 = other_poly_pos[i1-1]
            i2 = other_poly_pos.index(p1)
            p6 = other_poly_pos[0 if i2 == len(other_poly_pos) - 1 else i2+1]

            return p3 in (p5, p6) or p4 in (p5, p6)

        connectivity = {}
        merged_verts = {}
        merged_edges = {}
        poly_pos = {}
        verts = {}
        edges = {}
        verts_by_pos = {}
        edges_by_pos = {}
        edge_ids_by_vert_id = {}
        polys_by_edge = {}
        ordered_poly_edges = []

        def check_valid_merge():

            mvs_to_check = []

            # Check how many edges are connected to both merged verts at the ends of a given edge.
            # If there are more than two, break the merged verts and split all of the merged edges
            # attached to them.

            if gradual:
                edge_count = 0

            for edge in edges.values():

                merged_vert1 = merged_verts[edge[0]]
                merged_vert2 = merged_verts[edge[1]]
                edge_ids1 = {e_id for v_id in merged_vert1 for e_id in edge_ids_by_vert_id[v_id]}
                edge_ids2 = {e_id for v_id in merged_vert2 for e_id in edge_ids_by_vert_id[v_id]}
                edge_ids = edge_ids1 & edge_ids2

                if len(edge_ids) > 2:
                    mvs = (merged_vert1, merged_vert2)
                    if merged_vert1 in mvs_to_check:
                        mvs_to_check.remove(merged_vert1)
                    if merged_vert2 in mvs_to_check:
                        mvs_to_check.remove(merged_vert2)
                    for edge_id in edge_ids1 | edge_ids2:
                        mv1, mv2 = [merged_verts[v_id] for v_id in edges[edge_id]]
                        if mv1 not in mvs and mv1 not in mvs_to_check:
                            mvs_to_check.append(mv1)
                        if mv2 not in mvs and mv2 not in mvs_to_check:
                            mvs_to_check.append(mv2)
                        merged_edges[edge_id] = [edge_id]
                    for vert_id in merged_vert1[:] + merged_vert2[:]:
                        merged_verts[vert_id] = MergedVertex(vert_id)

                if gradual:

                    edge_count += 1

                    if edge_count == 20:
                        yield
                        edge_count = 0

            # The above procedure might introduce a new issue: after splitting certain merged
            # edges, the merged verts at their ends could end up connecting multiple border
            # vertices. To fix this, start at any border edge connected to such a merged
            # vertex and follow the adjacent edges connected to that merged vertex, removing
            # from it vertices encountered along the way and adding them to new merged vertices.

            if gradual:
                vert_count = 0

            for merged_vert in mvs_to_check:

                edge_ids = {e_id for v_id in merged_vert for e_id in edge_ids_by_vert_id[v_id]}
                border_edge_ids = [e_id for e_id in edge_ids if len(merged_edges[e_id]) == 1]

                if len(border_edge_ids) > 2:

                    while border_edge_ids:

                        border_edge_id = border_edge_ids.pop()
                        edge1 = edges[border_edge_id]
                        new_merged_vert = MergedVertex()

                        while True:

                            v1_id, v2_id = edge1
                            vert_id = v1_id if merged_verts[v1_id] is merged_vert else v2_id
                            merged_vert.remove(vert_id)
                            new_merged_vert.append(vert_id)
                            merged_verts[vert_id] = new_merged_vert
                            e1_id, e2_id = edge_ids_by_vert_id[vert_id]
                            edge2_id = e1_id if e2_id == id(edge1) else e2_id
                            merged_edge = merged_edges[edge2_id]

                            if len(merged_edge) == 1:
                                border_edge_ids.remove(merged_edge[0])
                                break
                            else:
                                e1_id, e2_id = merged_edge
                                edge1 = edges[e1_id if e2_id == edge2_id else e2_id]

                if gradual:

                    vert_count += 1

                    if vert_count == 20:
                        yield
                        vert_count = 0

        if gradual:
            poly_count = 0

        for poly_data in geom_data:

            poly_id = id(poly_data)
            poly_pos[poly_id] = [Point3(*v["pos"]) for v in poly_data["verts"]]
            tmp_edges = []
            positions = {}
            poly_verts_by_pos = {}
            poly_edges_by_pos = {}
            poly_edges_by_vert_id = {}

            poly_edges = []
            poly_tris = []

            for tri_data in poly_data["tris"]:

                tri_vert_ids = []

                for vert_data in tri_data:

                    pos = vert_data["pos"]

                    if pos in poly_verts_by_pos:
                        vert_id = poly_verts_by_pos[pos]
                    else:
                        vert_id = id(vert_data)
                        verts[vert_id] = vert_data
                        poly_verts_by_pos[pos] = vert_id
                        positions[vert_id] = pos

                    tri_vert_ids.append(vert_id)

                poly_tris.append(tuple(tri_vert_ids))

                for i, j in ((0, 1), (1, 2), (2, 0)):

                    edge_vert_ids = (tri_vert_ids[i], tri_vert_ids[j])
                    reversed_vert_ids = edge_vert_ids[::-1]

                    if reversed_vert_ids in tmp_edges:
                        # if the edge appears twice, it's actually a diagonal
                        tmp_edges.remove(reversed_vert_ids)
                    else:
                        tmp_edges.append(edge_vert_ids)

            for edge_vert_ids in tmp_edges:
                vert1_id, vert2_id = edge_vert_ids
                poly_edges_by_vert_id[vert1_id] = edge_vert_ids
                edge_id = id(edge_vert_ids)
                edge_ids_by_vert_id.setdefault(vert1_id, []).append(edge_id)
                edge_ids_by_vert_id.setdefault(vert2_id, []).append(edge_id)

            # Define verts and edges in winding order

            vert1_id, vert2_id = edge_vert_ids = poly_edges_by_vert_id[poly_tris[0][0]]
            edge = edge_vert_ids
            edge1_id = id(edge)
            edges[edge1_id] = edge
            poly_edges.append(edge1_id)
            pos1 = positions[vert1_id]
            pos2 = positions[vert2_id]
            poly_edges_by_pos[(pos1, pos2)] = edge1_id

            while vert2_id != vert1_id:
                edge_vert_ids = poly_edges_by_vert_id[vert2_id]
                vert2_id = edge_vert_ids[1]
                edge = edge_vert_ids
                edge_id = id(edge)
                edges[edge_id] = edge
                poly_edges.append(edge_id)
                pos1 = pos2
                pos2 = positions[vert2_id]
                poly_edges_by_pos[(pos1, pos2)] = edge_id

            ordered_poly_edges.append(poly_edges)
            verts_by_pos[poly_id] = poly_verts_by_pos
            edges_by_pos[poly_id] = poly_edges_by_pos

            neighbor_count = {}
            poly_connections = {"neighbors": {}, "neighbor_count": neighbor_count}

            for edge_pos in list(poly_edges_by_pos):

                if edge_pos in polys_by_edge and len(polys_by_edge[edge_pos]) == 2:
                    val = poly_edges_by_pos[edge_pos]
                    edge_pos = (PosObj(edge_pos[0]), PosObj(edge_pos[1]))
                    poly_edges_by_pos[edge_pos] = val
                    polys_by_edge[edge_pos] = [poly_id]
                else:
                    polys_by_edge.setdefault(edge_pos, []).append(poly_id)

                poly_connections["neighbors"][edge_pos] = neighbors = []
                reversed_edge_pos = edge_pos[::-1]

                if reversed_edge_pos in polys_by_edge:

                    # one or more other polys form a continuous surface with this one

                    for other_poly_id in polys_by_edge[reversed_edge_pos]:

                        other_connections = connectivity[other_poly_id]
                        other_neighbors = other_connections["neighbors"][reversed_edge_pos]

                        if not is_doublesided(edge_pos, poly_pos[poly_id], poly_pos[other_poly_id]):
                            # the triangles of both polys connected by the current edge
                            # are not each other's inverse
                            neighbors.append(other_poly_id)
                            other_neighbors.append(poly_id)
                            neighbor_count.setdefault(other_poly_id, 0)
                            neighbor_count[other_poly_id] += 1
                            other_neighbor_count = other_connections["neighbor_count"]
                            other_neighbor_count.setdefault(poly_id, 0)
                            other_neighbor_count[poly_id] += 1

            connectivity[poly_id] = poly_connections

            if gradual:

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

        if gradual:
            poly_count = 0

        for poly_id, connections in connectivity.items():

            for edge_pos, neighbors in connections["neighbors"].items():

                edge_id = edges_by_pos[poly_id][edge_pos]

                if edge_id in merged_edges:
                    continue

                merged_edge = [edge_id]
                merged_edges[edge_id] = merged_edge

                if neighbors:

                    neighbor_to_keep = neighbors[0]

                    if len(neighbors) > 1:

                        neighbor_count = connections["neighbor_count"]

                        for neighbor_id in neighbors:
                            if neighbor_count[neighbor_id] > neighbor_count[neighbor_to_keep]:
                                neighbor_to_keep = neighbor_id

                        neighbors.remove(neighbor_to_keep)

                        for neighbor_id in neighbors:
                            connectivity[neighbor_id]["neighbors"][edge_pos[::-1]].remove(poly_id)
                            connectivity[neighbor_id]["neighbor_count"][poly_id] -= 1

                    neighbor_edge_id = edges_by_pos[neighbor_to_keep][edge_pos[::-1]]

                    if neighbor_edge_id not in merged_edges:
                        merged_edge.append(neighbor_edge_id)
                        merged_edges[neighbor_edge_id] = merged_edge

            if gradual:

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

        if gradual:
            poly_count = 0

        for poly_edges in ordered_poly_edges:

            for edge_id in poly_edges:

                merged_edge = merged_edges[edge_id]
                vert1_id, vert2_id = edges[edge_id]

                if vert1_id in merged_verts:
                    merged_vert1 = merged_verts[vert1_id]
                else:
                    merged_vert1 = MergedVertex(vert1_id)
                    merged_verts[vert1_id] = merged_vert1

                if vert2_id in merged_verts:
                    merged_vert2 = merged_verts[vert2_id]
                else:
                    merged_vert2 = MergedVertex(vert2_id)
                    merged_verts[vert2_id] = merged_vert2

                if len(merged_edge) > 1:

                    neighbor_edge_id = merged_edge[0 if merged_edge[1] == edge_id else 1]
                    neighbor_vert1_id, neighbor_vert2_id = edges[neighbor_edge_id]

                    if neighbor_vert1_id not in merged_vert2:

                        if neighbor_vert1_id in merged_verts:

                            merged_vert = merged_verts[neighbor_vert1_id]

                            for vert_id in merged_vert:
                                merged_vert2.append(vert_id)
                                merged_verts[vert_id] = merged_vert2

                        else:

                            merged_vert2.append(neighbor_vert1_id)
                            merged_verts[neighbor_vert1_id] = merged_vert2

                    if neighbor_vert2_id not in merged_vert1:

                        if neighbor_vert2_id in merged_verts:

                            merged_vert = merged_verts[neighbor_vert2_id]

                            for vert_id in merged_vert:
                                merged_vert1.append(vert_id)
                                merged_verts[vert_id] = merged_vert1

                        else:

                            merged_vert1.append(neighbor_vert2_id)
                            merged_verts[neighbor_vert2_id] = merged_vert1

            if gradual:

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

        for _ in check_valid_merge():
            yield

        for _ in self.__compute_indices(geom_data, verts, merged_verts, gradual):
            yield

        yield


class LockedGeomManagerBase(PickingColorIDManager):

    _inst = None
    id_generator = None
    aux_vertex_format = None

    @staticmethod
    def init(inst):

        PickingColorIDManager.__init__(inst)
        cls = LockedGeomManagerBase
        cls._inst = inst
        PickableTypes.add("locked_geom")

        cls.id_generator = id_generator()

        vertex_format = GeomVertexFormat()
        array_format = GeomVertexArrayFormat()
        array_format.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)
        vertex_format.add_array(array_format)
        array_format = GeomVertexArrayFormat()
        array_format.add_column(InternalName.make("sides"), 1, Geom.NT_int32, Geom.C_other)
        vertex_format.add_array(array_format)
        array_format = GeomVertexArrayFormat()
        array_format.add_column(InternalName.make("snap_pos"), 3, Geom.NT_float32, Geom.C_other)
        vertex_format.add_array(array_format)
        cls.aux_vertex_format = GeomVertexFormat.register_format(vertex_format)

        Mgr.expose("aux_locked_vertex_format", lambda: cls.aux_vertex_format)

    def __init__(self, initialize=False):

        if initialize:
            self.init(self)

    @staticmethod
    def get_next_picking_color_id():

        cls = LockedGeomManagerBase
        return PickingColorIDManager.get_next_picking_color_id(cls._inst)


class LockedGeomManager(ObjectManager, LockedGeomManagerBase):

    def __init__(self):

        ObjectManager.__init__(self, "locked_geom", self.__create, "sub", pickable=True)
        LockedGeomManagerBase.__init__(self, initialize=True)

        Mgr.accept("lock_geometry", self.__lock_geometry)
        Mgr.add_app_updater("uv_set_id", self.__update_uv_set_id)
        Mgr.add_app_updater("uv_set_name", self.__set_uv_set_name)
        Mgr.add_app_updater("normal_viz", self.__show_normals)
        Mgr.add_app_updater("normal_color", self.__set_normal_color)

    def __create(self, geom, geom_data, materials=None, name="", model=None):

        update_model = not model

        if not model:
            model_id = ("locked_geom",) + next(self.id_generator)
            model = Mgr.do("create_model", model_id, name, Point3(), (.7, .7, 1., 1.))

        picking_col_id = self.get_next_picking_color_id()
        locked_geom = LockedGeom(model, geom, geom_data,
            picking_col_id, materials, update_model)

        return locked_geom

    def __define_geom_data(self, geom_data_obj):

        geom_data = []
        verts = geom_data_obj.get_subobjects("vert")
        merged_verts = set(geom_data_obj.merged_verts.values())
        positions = {mv: PosObj(mv.get_pos()) for mv in merged_verts}
        merged_uvs = {}
        processed_data = {}
        processed_mvs = []
        processed_uv_mvs = []
        sign = -1 if geom_data_obj.owner.has_inverted_geometry() else 1

        for merged_vert in merged_verts:

            verts_by_uv = {}

            for vert_id in merged_vert:

                vert = verts[vert_id]
                uv = vert.get_uvs(0)

                if uv in verts_by_uv:
                    verts_by_uv[uv].append(vert_id)
                else:
                    verts_by_uv[uv] = [vert_id]

            for (u, v), vert_ids in verts_by_uv.items():
                merged_uv = MergedUV(merged_vert, u, v)
                merged_uvs.update({v_id: merged_uv for v_id in vert_ids})

        for poly in geom_data_obj.ordered_polys:

            for vert_id in poly.vertex_ids:

                vert = verts[vert_id]
                merged_vertex = vert.merged_vertex
                merged_uv = merged_uvs[vert_id]
                vert_data = {}
                vert_data["pos"] = positions[merged_vertex]
                vert_data["normal"] = Vec3(vert.normal) * sign
                vert_data["color"] = vert.color
                vert_data["uvs"] = vert.get_uvs()

                if merged_vertex in processed_mvs:
                    vert_data["pos_ind"] = processed_mvs.index(merged_vertex)
                else:
                    vert_data["pos_ind"] = len(processed_mvs)
                    processed_mvs.append(merged_vertex)

                if merged_uv in processed_uv_mvs:
                    vert_data["uv_ind"] = processed_uv_mvs.index(merged_uv)
                else:
                    vert_data["uv_ind"] = len(processed_uv_mvs)
                    processed_uv_mvs.append(merged_uv)

                processed_data[vert_id] = vert_data

            tris = []

            for tri_vert_ids in poly:
                tri_data = [processed_data[v_id] for v_id in tri_vert_ids[::sign]]
                tris.append(tri_data)

            poly_verts = [processed_data[v_id] for v_id in poly.vertex_ids]
            poly_data = {"verts": poly_verts, "tris": tris}
            geom_data.append(poly_data)

        return geom_data

    def __lock_geometry(self):

        Mgr.exit_states(min_persistence=-99)
        Mgr.do("update_history_time")
        obj_data = {}
        models = Mgr.get("selection_top")

        for model in models:
            geom_data_obj = model.geom_obj.geom_data_obj
            data = model.geom_obj.get_data_to_store("deletion")
            data.update(model.geom_obj.get_property_to_store("geom_data"))
            geom = Mgr.do("merge_duplicate_verts", geom_data_obj)
            geom_data = self.__define_geom_data(geom_data_obj)
            locked_geom = self.__create(geom, geom_data, model=model)
            locked_geom.register(restore=False)
            data.update(locked_geom.get_data_to_store("creation"))
            obj_data[model.id] = data
            geom_data_obj.destroy()
            model.bbox.color = (.7, .7, 1., 1.)

        if len(models) == 1:
            model = models[0]
            event_descr = f'Disable geometry editing of "{model.name}"'
        else:
            event_descr = 'Disable geometry editing of objects:\n'
            event_descr += "".join([f'\n    "{model.name}"' for model in models])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        Mgr.do("update_picking_col_id_ranges")
        Mgr.update_remotely("selected_obj_types", ("locked_geom",))
        models.update_obj_props(force=True)

    def __update_uv_set_id(self):

        selection = Mgr.get("selection_top")

        if len(selection) == 1:
            obj = selection[0]
            uv_set_names = obj.geom_obj.get_uv_set_names()
            Mgr.update_remotely("uv_set_name", uv_set_names)

    def __set_uv_set_name(self, uv_set_id, uv_set_name):

        selection = Mgr.get("selection_top")
        changed_objs = []

        for obj in selection:
            if obj.geom_obj.set_uv_set_name(uv_set_id, uv_set_name):
                changed_objs.append(obj)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in changed_objs:
            obj_data[obj.id] = obj.get_data_to_store("prop_change", "uv_set_names")

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'Change UV set name {uv_set_id} of "{obj.name}"'
            event_descr += f'\nto "{obj.geom_obj.get_uv_set_names()[uv_set_id]}"'
        else:
            event_descr = f'Change UV set name {uv_set_id} of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __show_normals(self, show=True):

        selection = Mgr.get("selection_top")
        changed_objs = []

        for obj in selection:
            if obj.geom_obj.show_normals(show):
                changed_objs.append(obj)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in changed_objs:
            obj_data[obj.id] = obj.get_data_to_store("prop_change", "normal_viz")

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'{"Show" if show else "Hide"} normals of "{obj.name}"'
        else:
            event_descr = f'{"Show" if show else "Hide"} normals of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __set_normal_color(self, color_values):

        r, g, b = color_values[:3]
        selection = Mgr.get("selection_top")
        changed_objs = []

        for obj in selection:
            if obj.geom_obj.set_property("normal_color", color_values[:3]):
                changed_objs.append(obj)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in changed_objs:
            obj_data[obj.id] = obj.get_data_to_store("prop_change", "normal_color")

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'Change normal color of "{obj.name}"'
            event_descr += f'\nto R:{r :.3f} | G:{g :.3f} | B:{b :.3f}'
        else:
            event_descr = 'Change normal color of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])
            event_descr += f'\n\nto R:{r :.3f} | G:{g :.3f} | B:{b :.3f}'

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(LockedGeomManager)
