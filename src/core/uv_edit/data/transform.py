from ..base import *


class UVDataTransformBase(BaseObject):

    def __init__(self, is_copy=False):

        self._verts_to_transf = {"vert": {}, "edge": {}, "poly": {}}
        self._rows_to_transf = {"vert": None, "edge": None, "poly": None}

        if is_copy:
            for subobj_lvl in ("vert", "edge", "poly"):
                self._update_verts_to_transform(subobj_lvl)

        self._transf_start_data = {"bbox": None, "pos_array": None}

    def _update_verts_to_transform(self, subobj_lvl):

        selected_subobj_ids = self._selected_subobj_ids[subobj_lvl]
        verts = self._subobjs["vert"]
        self._verts_to_transf[subobj_lvl] = verts_to_transf = {}
        self._rows_to_transf[
            subobj_lvl] = rows_to_transf = SparseArray.allOff()

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

        geom_node = self._geoms["hidden"].node()
        start_data = self._transf_start_data
        start_data["bbox"] = geom_node.get_bounds()
        start_data["pos_array"] = geom_node.get_geom(
            0).get_vertex_data().get_array(0)

    def transform_selection(self, subobj_lvl, transf_type, value):

        geom = self._geoms["hidden"]
        vertex_data_top = geom.node().modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")

        if transf_type == "translate":

            rows = self._rows_to_transf[subobj_lvl]
            start_data = self._transf_start_data
            vertex_data_top.set_array(0, start_data["pos_array"])
            mat = Mat4.translate_mat(value)
            vertex_data_top.transform_vertices(mat, rows)
##      start_data = self._transf_start_data
##      vertex_data.set_array(0, start_data["pos_array"])
##      mat = Mat4.translate_mat(value)
##      vertex_data.transform_vertices(mat, 20, 50)

# for vert, indices in self._verts_to_transf[subobj_lvl].iteritems():
##
##        pos = vert.get_pos() + value
##
# for index in indices:
# pos_writer.set_row(index)
# pos_writer.set_data3f(pos)

        elif transf_type == "rotate":

            tc_pos = UVMgr.get("selection_center")

            for vert, indices in self._verts_to_transf[subobj_lvl].iteritems():

                pos = value.xform(vert.get_pos() - tc_pos) + tc_pos

                for index in indices:
                    pos_writer.set_row(index)
                    pos_writer.set_data3f(pos)

        elif transf_type == "scale":

            tc_pos = UVMgr.get("selection_center")
            mat = Mat4.scale_mat(value)

            for vert, indices in self._verts_to_transf[subobj_lvl].iteritems():

                pos = mat.xform_vec(vert.get_pos() - tc_pos) + tc_pos

                for index in indices:
                    pos_writer.set_row(index)
                    pos_writer.set_data3f(pos)

        array = vertex_data_top.get_array(0)

        for subobj_type in ("vert", "poly"):
            vertex_data = self._vertex_data[subobj_type]
            vertex_data.set_array(0, array)

        array = GeomVertexArrayData(array)
        handle = array.modify_handle()
        handle.set_data(handle.get_data() * 2)
        self._vertex_data["edge"].set_array(0, array)

    def finalize_transform(self, cancelled=False):

        start_data = self._transf_start_data

        geom = self._geoms["hidden"]
        vertex_data = geom.node().modify_geom(0).modify_vertex_data()

        if cancelled:

            bounds = start_data["bbox"]

            pos_array = start_data["pos_array"]
            vertex_data.set_array(0, pos_array)

            for subobj_type in ("vert", "poly"):
                self._vertex_data[subobj_type].set_array(0, pos_array)

            pos_array = GeomVertexArrayData(pos_array)
            handle = pos_array.modify_handle()
            handle.set_data(handle.get_data() * 2)
            self._vertex_data["edge"].set_array(0, pos_array)

        else:

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
                vert_ids.extend(merged_vert[:])

                for vert_id in merged_vert:
                    geom_verts[vert_id].set_uvs((u, v), uv_set_id)

                for poly_id in merged_vert.get_polygon_ids():
                    poly_ids.add(poly_id)

            for poly_id in poly_ids:
                poly = polys[poly_id]
                poly.update_center_pos()

            geom_data_obj.apply_uv_edits(vert_ids, uv_set_id)

        self._origin.node().set_bounds(bounds)
        start_data.clear()
