from ..base import *


class UVDataTransformBase(BaseObject):

    def __init__(self, is_copy=False):

        self._verts_to_transf = {"vert": {}, "edge": {}, "poly": {}}
        self._rows_to_transf = {"vert": None, "edge": None, "poly": None}

        if is_copy:
            for subobj_lvl in ("vert", "edge", "poly"):
                self._update_verts_to_transform(subobj_lvl)

        self._transf_start_data = {"bounds": None, "pos_array": None}
        self._pos_arrays = {"main": None, "edge": None}

    def update_vertex_positions(self, vertex_ids):

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]
        merged_verts = self._merged_verts
        geoms = self._geoms
        uv_set_id = UVMgr.get("active_uv_set")
        geom_data_obj = self._geom_data_obj
        geom_verts = geom_data_obj.get_subobjects("vert")
        polys_to_update = set()
        vertex_data = self._vertex_data_poly
        tmp_vertex_data = GeomVertexData(vertex_data)
        pos_writer = GeomVertexWriter(tmp_vertex_data, "vertex")

        for vert_id in vertex_ids:
            vert = verts[vert_id]
            poly = polys[vert.get_polygon_id()]
            polys_to_update.add(poly)
            row = vert.get_row_index()
            pos = vert.get_pos()
            pos_writer.set_row(row)
            pos_writer.set_data3f(pos)
            u, v = pos[0], pos[2]
            geom_verts[vert_id].set_uvs((u, v), uv_set_id)

        pos_array = GeomVertexArrayData(tmp_vertex_data.get_array(0))
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["vert"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)

        pos_array = GeomVertexArrayData(pos_array)
        handle = pos_array.modify_handle()
        handle.set_data(handle.get_data() * 2)
        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["seam"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)

        for poly in polys_to_update:
            poly.update_center_pos()

        geom = geoms["vert"]["sel_state"]
        geom.node().modify_geom(0).modify_vertex_data() # updates bounds
        bounds = geom.node().get_bounds()

        if bounds.get_radius() == 0.:
            center = bounds.get_center()
            bounds = BoundingSphere(center, .1)

        self._origin.node().set_bounds(bounds)

        geom_data_obj.apply_uv_edits(vertex_ids, uv_set_id)

    def _update_verts_to_transform(self, subobj_lvl):

        selected_subobj_ids = self._selected_subobj_ids[subobj_lvl]
        verts = self._subobjs["vert"]
        self._verts_to_transf[subobj_lvl] = verts_to_transf = {}
        self._rows_to_transf[subobj_lvl] = rows_to_transf = SparseArray.allOff()

        merged_verts = self._merged_verts
        merged_verts_to_transf = set()

        if subobj_lvl == "vert":

            for vert_id in selected_subobj_ids:
                merged_verts_to_transf.add(merged_verts[vert_id])

        elif subobj_lvl == "edge":

            edges = self._subobjs["edge"]

            for edge_id in selected_subobj_ids:

                edge = edges[edge_id]

                for vert_id in edge:
                    merged_verts_to_transf.add(merged_verts[vert_id])

        elif subobj_lvl == "poly":

            polys = self._subobjs["poly"]

            for poly_id in selected_subobj_ids:

                poly = polys[poly_id]

                for vert_ids in poly:
                    for vert_id in vert_ids:
                        merged_verts_to_transf.add(merged_verts[vert_id])

        for merged_vert in merged_verts_to_transf:

            rows = merged_vert.get_row_indices()
            verts_to_transf[merged_vert] = rows

            for row in rows:
                rows_to_transf.set_bit(row)

    def init_transform(self):

        geom_node = self._geoms["vert"]["sel_state"].node()
        start_data = self._transf_start_data
        start_data["bounds"] = geom_node.get_bounds()
        pos_array = self._vertex_data_poly.modify_array(0)
        start_data["pos_array"] = GeomVertexArrayData(pos_array)

        geoms = self._geoms

        vertex_data = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["vert"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        self._pos_arrays["main"] = pos_array

        pos_array = GeomVertexArrayData(pos_array)
        handle = pos_array.modify_handle()
        handle.set_data(handle.get_data() * 2)
        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["seam"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        self._pos_arrays["edge"] = pos_array

    def set_vert_sel_coordinate(self, axis, value):

        verts = self._verts_to_transf["vert"]

        if not verts:
            return

        vertex_data = self._vertex_data_poly
        tmp_vertex_data = GeomVertexData(vertex_data)
        tmp_vertex_data.set_array(0, GeomVertexArrayData(self._transf_start_data["pos_array"]))
        index = "u_v".index(axis)
        pos_rewriter = GeomVertexRewriter(tmp_vertex_data, "vertex")

        for rows in verts.itervalues():
            for row in rows:
                pos_rewriter.set_row(row)
                pos = Point3(pos_rewriter.get_data3f())
                pos[index] = value
                pos_rewriter.set_data3f(pos)

        pos_array = GeomVertexArrayData(tmp_vertex_data.get_array(0))
        vertex_data.set_array(0, pos_array)

        handle = self._pos_arrays["main"].modify_handle()
        data = pos_array.get_handle().get_data()
        handle.set_data(data)

        handle = self._pos_arrays["edge"].modify_handle()
        handle.set_data(data * 2)

    def transform_selection(self, subobj_lvl, transf_type, value):

        rows = self._rows_to_transf[subobj_lvl]

        if not rows:
            return

        vertex_data = self._vertex_data_poly
        tmp_vertex_data = GeomVertexData(vertex_data)
        tmp_vertex_data.set_array(0, GeomVertexArrayData(self._transf_start_data["pos_array"]))

        if transf_type == "translate":

            mat = Mat4.translate_mat(value)

        elif transf_type == "rotate":

            tc_pos = UVMgr.get("selection_center")
            quat_mat = Mat4()
            value.extract_to_matrix(quat_mat)
            offset_mat = Mat4.translate_mat(-tc_pos)
            mat = offset_mat * quat_mat
            offset_mat = Mat4.translate_mat(tc_pos)
            mat *= offset_mat

        elif transf_type == "scale":

            tc_pos = UVMgr.get("selection_center")
            mat = Mat4.scale_mat(value)
            offset_mat = Mat4.translate_mat(-tc_pos)
            mat = offset_mat * mat
            offset_mat = Mat4.translate_mat(tc_pos)
            mat *= offset_mat

        tmp_vertex_data.transform_vertices(mat, rows)
        pos_array = GeomVertexArrayData(tmp_vertex_data.get_array(0))
        vertex_data.set_array(0, pos_array)

        handle = self._pos_arrays["main"].modify_handle()
        data = pos_array.get_handle().get_data()
        handle.set_data(data)

        handle = self._pos_arrays["edge"].modify_handle()
        handle.set_data(data * 2)

    def finalize_transform(self, cancelled=False):

        start_data = self._transf_start_data
        vertex_data = self._vertex_data_poly

        if cancelled:

            bounds = start_data["bounds"]

            pos_array = start_data["pos_array"]
            vertex_data.set_array(0, pos_array)

            handle = self._pos_arrays["main"].modify_handle()
            data = pos_array.get_handle().get_data()
            handle.set_data(data)

            handle = self._pos_arrays["edge"].modify_handle()
            handle.set_data(data * 2)

        else:

            geom = self._geoms["vert"]["sel_state"]
            geom.node().modify_geom(0).modify_vertex_data() # updates bounds
            bounds = geom.node().get_bounds()

            geom_data_obj = self._geom_data_obj
            geom_verts = geom_data_obj.get_subobjects("vert")

            pos_reader = GeomVertexReader(vertex_data, "vertex")
            subobj_lvl = UVMgr.get("active_obj_level")
            uv_set_id = UVMgr.get("active_uv_set")
            vert_ids = []
            polys = self._subobjs["poly"]
            poly_ids = set()

            for merged_vert, indices in self._verts_to_transf[subobj_lvl].iteritems():

                pos_reader.set_row(indices[0])
                pos = Point3(pos_reader.get_data3f())
                merged_vert.set_pos(pos)
                u, v = pos[0], pos[2]
                vert_ids.extend(merged_vert)

                for vert_id in merged_vert:
                    geom_verts[vert_id].set_uvs((u, v), uv_set_id)

                for poly_id in merged_vert.get_polygon_ids():
                    poly_ids.add(poly_id)

            for poly_id in poly_ids:
                poly = polys[poly_id]
                poly.update_center_pos()

            geom_data_obj.apply_uv_edits(vert_ids, uv_set_id)

        if bounds.get_radius() == 0.:
            center = bounds.get_center()
            bounds = BoundingSphere(center, .1)

        self._origin.node().set_bounds(bounds)
        start_data.clear()
        self._pos_arrays = {"main": None, "edge": None}
