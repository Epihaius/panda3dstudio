from .base import *
import array


class UVPrimitivePart:

    def __init__(self, picking_color_id, owner, data_row_range, start_positions,
                 default_positions, geom_prim, pos):

        self.picking_color_id = picking_color_id
        self.id = picking_color_id
        self.owner = owner
        self.data_row_range = data_row_range
        self.start_positions = start_positions
        self.default_positions = default_positions
        self.geom_prim = geom_prim
        self.is_selected = False
        self.default_pos = Point3(pos)
        self.center_pos = pos
        self.mat = Mat4(Mat4.translate_mat(pos))

    def copy(self, owner):

        part = UVPrimitivePart(self.picking_color_id, owner, self.data_row_range,
            self.start_positions, self.default_positions, self.geom_prim,
            Point3(self.default_pos))
        part.mat = Mat4(self.mat)
        part.center_pos = Point3(self.center_pos)

        return part

    def get_center_pos(self, ref_node=None):

        return self.center_pos

    def get_pos(self):

        transform = TransformState.make_mat(self.mat)
        u, _, v = transform.get_pos()

        return u, v

    def get_rotation(self):

        transform = TransformState.make_mat(self.mat)
        rotation = transform.get_hpr()[2]

        return rotation

    def get_scale(self):

        transform = TransformState.make_mat(self.mat)
        su, _, sv = transform.get_scale()

        return su, sv

    def transform(self, mat, is_rel_value=True):

        if not is_rel_value:
            self.center_pos = Point3()
            self.mat = Mat4(Mat4.ident_mat())

        mat.xform_point_in_place(self.center_pos)
        self.mat *= mat

    def set_default_transform(self):

        def_pos = self.default_positions
        count = len(def_pos) // 3
        pos = sum([Point3(*def_pos[i*3:i*3+3]) for i in range(count)], Point3()) / count
        self.default_pos = Point3(pos)
        self.center_pos = pos
        self.mat = Mat4(Mat4.translate_mat(pos))


class UVPrimitive:

    def __init__(self, uv_set_id, part_registry=None, primitive=None, data_copy=None):

        self.uv_set_id = uv_set_id
        self._pos_array_start = None
        self._rows_to_transf = SparseArray()

        if data_copy:
            self._primitive = data_copy["primitive"]
            self.parts = data_copy["parts"]
            self.geom = data_copy["geom"]
        else:
            self._primitive = primitive
            self.parts = []
            self.geom = None
            self.__create_geometry(part_registry)

    def destroy(self, destroy_world_parts=True):

        self.parts = []
        self.geom.detach_node()
        self.geom = None

        if destroy_world_parts:
            self._primitive.destroy_parts()

        self._primitive = None
        self._pos_array_start = None
        self._rows_to_transf = None

    def copy(self, uv_set_id=None):

        data_copy = {"primitive": self._primitive}
        data_copy["parts"] = parts = []
        geom_node = self.geom.node()
        vertex_data = GeomVertexData(geom_node.modify_geom(0).modify_vertex_data())
        unsel_tris_geom = Geom(vertex_data)
        sel_tris_geom = Geom(vertex_data)
        seam_geom = Geom(vertex_data)
        seam_geom.add_primitive(self.geom.get_child(0).node().get_geom(0).get_primitive(0))

        geom_node_copy = GeomNode(geom_node.name)
        geom_node_copy.add_geom(unsel_tris_geom, UVMgr.get("part_states")["unselected"])
        geom_node_copy.add_geom(sel_tris_geom)
        data_copy["geom"] = geom = NodePath(geom_node_copy)
        geom.set_state(UVMgr.get("part_states")["selected"])
        geom.set_effects(UVMgr.get("poly_selection_effects"))
        geom.set_bin("background", 10)
        geom.set_tag("uv_template", "poly")
        seam_node_copy = GeomNode("seams")
        seam_node_copy.add_geom(seam_geom)
        seams_copy = geom.attach_new_node(seam_node_copy)
        seams_copy.set_state(self.geom.get_child(0).get_state())
        seams_copy.set_tag("uv_template", "seam")
        prim = UVPrimitive(uv_set_id, None, None, data_copy)

        for part_index, part in enumerate(self._primitive.parts):

            part_copy = self.parts[part_index].copy(prim)
            parts.append(part_copy)

            if uv_set_id is not None:
                part.uv_parts[uv_set_id] = part_copy

        sel_uv_parts = []
        other = self._primitive if uv_set_id is None else self

        for uv_part, part in zip(parts, other.parts):
            if part.is_selected:
                sel_uv_parts.append(uv_part)

        prim.set_selected_parts(sel_uv_parts)

        return prim

    def __create_geometry(self, part_registry):

        uv_set_id = self.uv_set_id
        count = sum(len(p.uv_borders[uv_set_id]) for p in self._primitive.parts)
        vertex_format_picking = Mgr.get("vertex_format_picking")
        vertex_data = GeomVertexData("data", vertex_format_picking, Geom.UH_dynamic)
        vertex_data.reserve_num_rows(count)
        vertex_data.unclean_set_num_rows(count)
        self._vertex_data = vertex_data
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")
        ind_writer = GeomVertexWriter(vertex_data, "index")
        pickable_type_id = PickableTypes.get_id("primitive_part")
        vert_index = 0
        parts = self.parts
        unsel_tris_geom = Geom(vertex_data)
        sel_tris_geom = Geom(vertex_data)
        seam_geom = Geom(vertex_data)
        seam_prim = GeomLines(Geom.UH_static)
        seam_prim.reserve_num_vertices(count)
        seam_geom.add_primitive(seam_prim)

        for part_index, part in enumerate(self._primitive.parts):

            uv_border = part.uv_borders[uv_set_id]
            tri_vert_count = (len(uv_border) - 2) * 3
            unsel_tris_prim = GeomTriangles(Geom.UH_static)
            unsel_tris_prim.set_index_type(Geom.NT_uint32)
            unsel_tris_prim.reserve_num_vertices(tri_vert_count)
            picking_col_id = part.picking_color_id
            picking_color = get_color_vec(picking_col_id, pickable_type_id)
            start_index = vert_index
            seam_prim.add_vertices(start_index, start_index + 1)

            for i, (u, v) in enumerate(uv_border):

                pos = (u, 0., v)
                pos_writer.add_data3(pos)
                col_writer.add_data4(picking_color)
                ind_writer.add_data1i(part_index)

                if i > 1:
                    unsel_tris_prim.add_vertices(start_index, vert_index - 1, vert_index)
                    seam_prim.add_vertices(vert_index - 1, vert_index)

                vert_index += 1

            seam_prim.add_vertices(vert_index - 1, start_index)

            row_range = (start_index, vert_index)
            pos = sum([Point3(u, 0., v) for u, v in uv_border], Point3()) / len(uv_border)
            start_positions = array.array("f", [c for p in (Point3(u, 0., v)
                for u, v in uv_border) for c in p])
            uv_part = UVPrimitivePart(picking_col_id, self, row_range, start_positions,
                part.uv_defaults, unsel_tris_prim, pos)
            parts.append(uv_part)
            part.uv_parts[self.uv_set_id] = uv_part
            part_registry[picking_col_id] = uv_part
            unsel_tris_geom.add_primitive(unsel_tris_prim)

        name = f"{self._primitive.model.id}_uv_geom"
        geom_node = GeomNode(name)
        geom_node.add_geom(unsel_tris_geom, UVMgr.get("part_states")["unselected"])
        geom_node.add_geom(sel_tris_geom)
        geom = GD.uv_prim_geom_root.attach_new_node(geom_node)
        geom.set_state(UVMgr.get("part_states")["selected"])
        geom.set_effects(UVMgr.get("poly_selection_effects"))
        geom.set_bin("background", 10)
        geom.set_tag("uv_template", "poly")
        self.geom = geom
        geom_node = GeomNode("seams")
        geom_node.add_geom(seam_geom)
        seams_node = geom.attach_new_node(geom_node)
        seams_node.set_state(UVMgr.get("part_states")["unselected"])
        seams_node.set_color(0., 1., 0., 1.)
        seams_node.set_transparency(TransparencyAttrib.M_none)
        seams_node.set_render_mode_thickness(1, 2)
        seams_node.set_tag("uv_template", "seam")

    def get_selected_parts(self):

        return [p for p in self.parts if p.is_selected]

    def set_selected_parts(self, parts):

        geom = self.geom
        unsel_geom = geom.node().modify_geom(0)
        unsel_geom.clear_primitives()
        sel_geom = geom.node().modify_geom(1)
        sel_geom.clear_primitives()
        rows = self._rows_to_transf
        rows.clear()

        for part in self.parts:
            if part in parts:
                start_row, end_row = part.data_row_range
                rows.set_range(start_row, end_row - start_row)
                sel_geom.add_primitive(part.geom_prim)
                part.is_selected = True
            else:
                unsel_geom.add_primitive(part.geom_prim)
                part.is_selected = False

    def set_part_state(self, sel_state, state):

        if sel_state == "unselected":
            self.geom.node().set_geom_state(0, state)
        else:
            self.geom.set_state(state)

    def init_transform(self):

        pos_array = self.geom.node().modify_geom(0).modify_vertex_data().modify_array(0)
        self._pos_array_start = GeomVertexArrayData(pos_array)

    def __set_start_positions(self):

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        pos_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")

        for part in self.get_selected_parts():
            start_row, end_row = part.data_row_range
            pos_values = part.start_positions
            pos_view[start_row*3:end_row*3] = pos_values

    def set_transform_component(self, transf_type, axis, value):

        self.geom.node().clear_bounds()

        self.__set_start_positions()
        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        tmp_vertex_data = GeomVertexData(vertex_data)
        primitive = self._primitive

        for part in self.get_selected_parts():

            mat = part.mat
            transform = TransformState.make_mat(mat)

            if transf_type == "translate":

                pos = VBase3(transform.get_pos())

                if axis == "u":
                    pos.x = value
                else:
                    pos.z = value

                new_mat = transform.set_pos(pos).get_mat()

            elif transf_type == "rotate":

                hpr = VBase3(transform.get_hpr())
                hpr.z = value
                new_mat = transform.set_hpr(hpr).get_mat()

            elif transf_type == "scale":

                scale = VBase3(transform.get_scale())

                if axis == "u":
                    scale.x = max(.01, value)
                else:
                    scale.z = max(.01, value)

                new_mat = transform.set_scale(scale).get_mat()

            part.transform(new_mat, is_rel_value=False)
            offset_mat = Mat4.translate_mat(-part.default_pos)
            new_mat = offset_mat * new_mat
            start_row, end_row = part.data_row_range
            rows = SparseArray.range(start_row, end_row - start_row)
            tmp_vertex_data.transform_vertices(new_mat, rows)
            mat = (Mat4.rotate_mat_normaxis(90., Vec3.right()) * new_mat
                * Mat4.rotate_mat_normaxis(-90., Vec3.right()))
            primitive.transform_uvs(self.uv_set_id, [self.parts.index(part)],
                mat, is_rel_value=False)

        pos_array = GeomVertexArrayData(tmp_vertex_data.get_array(0))
        vertex_data.set_array(0, pos_array)
        vertex_data = self.geom.node().modify_geom(1).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = self.geom.get_child(0).node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)

        bounds = self.geom.node().get_bounds()

        if bounds.radius == 0.:
            bounds = BoundingSphere(bounds.center, .1)

        self.geom.node().set_bounds(bounds)
        self.geom.get_child(0).node().set_bounds(bounds)

    def reset_default_part_uvs(self):

        pos_views = []
        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        pos_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
        pos_views.append(pos_view)
        vertex_data = self.geom.node().modify_geom(1).modify_vertex_data()
        pos_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
        pos_views.append(pos_view)
        vertex_data = self.geom.get_child(0).node().modify_geom(0).modify_vertex_data()
        pos_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
        pos_views.append(pos_view)

        for part in self.get_selected_parts():

            start_row, end_row = part.data_row_range

            for pos_view in pos_views:
                pos_view[start_row*3:end_row*3] = part.default_positions

            part.set_default_transform()

        self._primitive.reset_default_part_uvs(self.uv_set_id)

    def transform_selection(self, mat):

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        tmp_vertex_data = GeomVertexData(vertex_data)
        tmp_vertex_data.set_array(0, GeomVertexArrayData(self._pos_array_start))
        tmp_vertex_data.transform_vertices(mat, self._rows_to_transf)
        pos_array = GeomVertexArrayData(tmp_vertex_data.get_array(0))
        vertex_data.set_array(0, pos_array)
        vertex_data = self.geom.node().modify_geom(1).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = self.geom.get_child(0).node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)

    def finalize_transform(self, mat, cancelled=False):

        self.geom.node().clear_bounds()

        if cancelled:

            vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, self._pos_array_start)
            vertex_data = self.geom.node().modify_geom(1).modify_vertex_data()
            vertex_data.set_array(0, self._pos_array_start)
            vertex_data = self.geom.get_child(0).node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, self._pos_array_start)

        else:

            primitive = self._primitive
            part_indices = []

            for i, part in enumerate(self.parts):
                if part.is_selected:
                    part.transform(mat)
                    part_indices.append(i)

            mat = (Mat4.rotate_mat_normaxis(90., Vec3.right()) * mat
                * Mat4.rotate_mat_normaxis(-90., Vec3.right()))
            primitive.transform_uvs(self.uv_set_id, part_indices, mat)

        bounds = self.geom.node().get_bounds()

        if bounds.radius == 0.:
            bounds = BoundingSphere(bounds.center, .1)

        self.geom.node().set_bounds(bounds)
        self.geom.get_child(0).node().set_bounds(bounds)
        self._pos_array_start = None

    def show(self):

        self.geom.reparent_to(GD.uv_prim_geom_root)

    def hide(self):

        self.geom.detach_node()
