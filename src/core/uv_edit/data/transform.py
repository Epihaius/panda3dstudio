from ..base import *


class TransformMixin:
    """ UVDataObject class mix-in """

    def __init__(self, is_copy=False):

        self._verts_to_transf = {"vert": {}, "edge": {}, "poly": {}}
        self._rows_to_transf = {"vert": None, "edge": None, "poly": None}

        if is_copy:
            for subobj_lvl in ("vert", "edge", "poly"):
                self._update_verts_to_transform(subobj_lvl)

        self._pos_arrays = {"start": None, "main": None, "edge": None}

    def update_vertex_positions(self, vertex_ids):

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]
        merged_verts = self.merged_verts
        geoms = self._geoms
        uv_set_id = UVMgr.get("active_uv_set")
        geom_data_obj = self.geom_data_obj
        geom_verts = geom_data_obj.get_subobjects("vert")
        polys_to_update = set()
        vertex_data = self._vertex_data_poly
        tmp_vertex_data = GeomVertexData(vertex_data)
        pos_writer = GeomVertexWriter(tmp_vertex_data, "vertex")

        for vert_id in vertex_ids:
            vert = verts[vert_id]
            poly = polys[vert.polygon_id]
            polys_to_update.add(poly)
            row = vert.row_index
            pos = vert.get_pos()
            pos_writer.set_row(row)
            pos_writer.set_data3(pos)
            u, v = pos[0], pos[2]
            geom_verts[vert_id].set_uvs((u, v), uv_set_id)

        pos_array = GeomVertexArrayData(tmp_vertex_data.get_array(0))
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["vert"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)

        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        pos_array_edge = vertex_data.modify_array(0)
        size = pos_array.data_size_bytes
        from_view = memoryview(pos_array).cast("B")
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view
        pos_array_edge = vertex_data.get_array(0)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array_edge)
        vertex_data = geoms["seam"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array_edge)

        for poly in polys_to_update:
            poly.update_center_pos()

        geom = geoms["vert"]["sel_state"]
        geom.node().modify_geom(0).modify_vertex_data()  # updates bounds
        bounds = geom.node().get_bounds()

        if bounds.radius == 0.:
            bounds = BoundingSphere(bounds.center, .1)

        self.origin.node().set_bounds(bounds)

        geom_data_obj.apply_uv_edits(vertex_ids, uv_set_id)

    def _update_verts_to_transform(self, subobj_lvl):

        selected_subobj_ids = self._selected_subobj_ids[subobj_lvl]
        verts = self._subobjs["vert"]
        self._verts_to_transf[subobj_lvl] = verts_to_transf = {}
        self._rows_to_transf[subobj_lvl] = rows_to_transf = SparseArray()

        merged_verts = self.merged_verts
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

            rows = merged_vert.row_indices
            verts_to_transf[merged_vert] = rows

            for row in rows:
                rows_to_transf.set_bit(row)

    def init_transform(self):

        geom_node = self._geoms["vert"]["sel_state"].node()
        pos_array = self._vertex_data_poly.modify_array(0)
        self._pos_arrays["start"] = GeomVertexArrayData(pos_array)

        geoms = self._geoms

        vertex_data = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["vert"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        self._pos_arrays["main"] = pos_array

        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        pos_array_edge = vertex_data.modify_array(0)
        size = pos_array.data_size_bytes
        from_view = memoryview(pos_array).cast("B")
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view
        self._pos_arrays["edge"] = pos_array_edge
        pos_array_edge = vertex_data.get_array(0)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array_edge)
        vertex_data = geoms["seam"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array_edge)

    def set_vert_sel_coordinate(self, axis, value):

        verts = self._verts_to_transf["vert"]

        if not verts:
            return

        vertex_data = self._vertex_data_poly
        tmp_vertex_data = GeomVertexData(vertex_data)
        tmp_vertex_data.set_array(0, GeomVertexArrayData(self._pos_arrays["start"]))
        index = "u_v".index(axis)
        pos_rewriter = GeomVertexRewriter(tmp_vertex_data, "vertex")

        for rows in verts.values():
            for row in rows:
                pos_rewriter.set_row(row)
                pos = Point3(pos_rewriter.get_data3())
                pos[index] = value
                pos_rewriter.set_data3(pos)

        pos_array = GeomVertexArrayData(tmp_vertex_data.get_array(0))
        vertex_data.set_array(0, pos_array)
        from_view = memoryview(pos_array).cast("B")

        to_view = memoryview(self._pos_arrays["main"]).cast("B")
        to_view[:] = from_view

        size = pos_array.data_size_bytes
        to_view = memoryview(self._pos_arrays["edge"]).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view

    def transform_selection(self, subobj_lvl, mat):

        rows = self._rows_to_transf[subobj_lvl]

        if not rows:
            return

        vertex_data = self._vertex_data_poly
        tmp_vertex_data = GeomVertexData(vertex_data)
        tmp_vertex_data.set_array(0, GeomVertexArrayData(self._pos_arrays["start"]))
        tmp_vertex_data.transform_vertices(mat, rows)
        pos_array = GeomVertexArrayData(tmp_vertex_data.get_array(0))
        vertex_data.set_array(0, pos_array)
        from_view = memoryview(pos_array).cast("B")

        to_view = memoryview(self._pos_arrays["main"]).cast("B")
        to_view[:] = from_view

        size = pos_array.data_size_bytes
        to_view = memoryview(self._pos_arrays["edge"]).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view

    def finalize_transform(self, cancelled=False):

        vertex_data = self._vertex_data_poly
        node = self._geoms["vert"]["sel_state"].node()
        node.modify_geom(0).modify_vertex_data()  # updates bounds

        if cancelled:

            pos_array_start = self._pos_arrays["start"]
            vertex_data.set_array(0, pos_array_start)
            from_view = memoryview(pos_array_start).cast("B")

            to_view = memoryview(self._pos_arrays["main"]).cast("B")
            to_view[:] = from_view

            size = pos_array_start.data_size_bytes
            to_view = memoryview(self._pos_arrays["edge"]).cast("B")
            to_view[:size] = from_view
            to_view[size:] = from_view

        else:

            geom_data_obj = self.geom_data_obj
            geom_verts = geom_data_obj.get_subobjects("vert")

            pos_reader = GeomVertexReader(vertex_data, "vertex")
            subobj_lvl = UVMgr.get("active_obj_level")
            uv_set_id = UVMgr.get("active_uv_set")
            vert_ids = []
            polys = self._subobjs["poly"]
            poly_ids = set()

            for merged_vert, indices in self._verts_to_transf[subobj_lvl].items():

                pos_reader.set_row(indices[0])
                pos = Point3(pos_reader.get_data3())
                merged_vert.set_pos(pos)
                u, v = pos[0], pos[2]
                vert_ids.extend(merged_vert)

                for vert_id in merged_vert:
                    geom_verts[vert_id].set_uvs((u, v), uv_set_id)

                poly_ids.update(merged_vert.polygon_ids)

            for poly_id in poly_ids:
                poly = polys[poly_id]
                poly.update_center_pos()

            geom_data_obj.apply_uv_edits(vert_ids, uv_set_id)

        bounds = node.get_bounds()

        if bounds.radius == 0.:
            bounds = BoundingSphere(bounds.center, .1)

        self.origin.node().set_bounds(bounds)
        self._pos_arrays = {"start": None, "main": None, "edge": None}
