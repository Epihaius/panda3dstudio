from ...base import *


class GeomTransformBase(BaseObject):

    def __init__(self):

        self._verts_to_transf = {"vert": {}, "edge": {}, "poly": {}}
        self._rows_to_transf = {"vert": None, "edge": None, "poly": None}
        self._transf_start_data = {"bbox": None, "pos_array": None}

    def _update_verts_to_transform(self, subobj_lvl):

        selected_subobj_ids = self._selected_subobj_ids[subobj_lvl]
        verts = self._subobjs["vert"]
        self._verts_to_transf[subobj_lvl] = verts_to_transf = {}
        self._rows_to_transf[
            subobj_lvl] = rows_to_transf = SparseArray.allOff()
##    rows_to_transf = self._rows_to_transf[subobj_lvl]
# rows_to_transf.clear()

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

        geom_node_top = self._geoms["top"]["shaded"].node()
        start_data = self._transf_start_data
        start_data["bbox"] = geom_node_top.get_bounds()
        start_data["pos_array"] = geom_node_top.get_geom(
            0).get_vertex_data().get_array(0)

    def transform_selection(self, subobj_lvl, transf_type, value):

        geom_node_top = self._geoms["top"]["shaded"].node()
        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")

        if transf_type == "translate":

            grid_origin = Mgr.get(("grid", "origin"))
            vec = self._origin.get_relative_vector(grid_origin, value)
            rows = self._rows_to_transf[subobj_lvl]
            start_data = self._transf_start_data
            vertex_data_top.set_array(0, start_data["pos_array"])
            mat = Mat4.translate_mat(vec)
            vertex_data_top.transform_vertices(mat, rows)

        elif transf_type == "rotate":

            grid_origin = Mgr.get(("grid", "origin"))
            tc_pos = self._origin.get_relative_point(
                self.world, Mgr.get("transf_center_pos"))
            quat = self._origin.get_quat(
                grid_origin) * value * grid_origin.get_quat(self._origin)

            for vert, indices in self._verts_to_transf[subobj_lvl].iteritems():

                pos = quat.xform(vert.get_pos() - tc_pos) + tc_pos

                for index in indices:
                    pos_writer.set_row(index)
                    pos_writer.set_data3f(pos)

        elif transf_type == "scale":

            grid_origin = Mgr.get(("grid", "origin"))
            tc_pos = self._origin.get_relative_point(
                self.world, Mgr.get("transf_center_pos"))
            scale_mat = Mat4.scale_mat(value)
            mat = self._origin.get_mat(
                grid_origin) * scale_mat * grid_origin.get_mat(self._origin)

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

        geom_node_top = self._geoms["top"]["shaded"].node()
        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()

        if cancelled:

            bounds = start_data["bbox"]

            pos_array = start_data["pos_array"]
            vertex_data_top.set_array(0, pos_array)

            for subobj_type in ("vert", "poly"):
                self._vertex_data[subobj_type].set_array(0, pos_array)

            pos_array = GeomVertexArrayData(pos_array)
            handle = pos_array.modify_handle()
            handle.set_data(handle.get_data() * 2)
            self._vertex_data["edge"].set_array(0, pos_array)

        else:

            bounds = geom_node_top.get_bounds()

            pos_reader = GeomVertexReader(vertex_data_top, "vertex")
            subobj_lvl = Mgr.get_global("active_obj_level")
            polys = self._subobjs["poly"]
            poly_ids = set()

            for merged_vert, indices in self._verts_to_transf[subobj_lvl].iteritems():

                pos_reader.set_row(indices[0])
                pos = Point3(pos_reader.get_data3f())
                merged_vert.set_pos(pos)
                poly_ids.update(merged_vert.get_polygon_ids())

            vert_ids = []

            for poly_id in poly_ids:
                poly = polys[poly_id]
                poly.update_center_pos()
                poly.update_normal()
                vert_ids.extend(poly.get_vertex_ids())

            merged_verts = set(self._merged_verts[
                               vert_id] for vert_id in vert_ids)
            self._update_vertex_normals(merged_verts)

        self._origin.node().set_bounds(bounds)
        self.get_toplevel_object().get_bbox().update(*self._origin.get_tight_bounds())
        start_data.clear()

    def _restore_subobj_transforms(self, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = "subobj_transform"

        prev_time_ids = Mgr.do("load_last_from_history",
                               obj_id, prop_id, old_time_id)
        new_time_ids = Mgr.do("load_last_from_history",
                              obj_id, prop_id, new_time_id)

        if prev_time_ids is None:
            prev_time_ids = ()

        if new_time_ids is None:
            new_time_ids = ()

        if not (prev_time_ids or new_time_ids):
            return

        if prev_time_ids and new_time_ids:

            i = 0

            for time_id in new_time_ids:

                if time_id not in prev_time_ids:
                    break

                i += 1

            common_time_ids = prev_time_ids[:i]
            prev_time_ids = prev_time_ids[i:]
            new_time_ids = new_time_ids[i:]

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]

        data_id = "vert_pos_data"

        time_ids_to_restore = {}
        prev_prop_times = {}
        positions = {}

        # to undo transformations, determine the time IDs of the transforms that
        # need to be restored by checking the data that was stored when transforms
        # occurred, at times leading up to the time that is being replaced (the old
        # time)

        for time_id in prev_time_ids[::-1]:
            # time_id is a Time ID to update time_ids_to_restore with

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            # subobj_data.get("prev", {}) yields previous transform times
            time_ids_to_restore.update(subobj_data.get("prev", {}))

        data_for_loading = {}

        # time_ids_to_restore.keys() are the IDs of vertices that need a
        # transform update
        for vert_id, time_id in time_ids_to_restore.iteritems():

            if vert_id in verts:
                prev_prop_times[vert_id] = time_id
                # since multiple vertex positions might have to be loaded from the same
                # datafile, make sure each datafile is loaded only once
                data_for_loading.setdefault(time_id, []).append(vert_id)

        for time_id, vert_ids in data_for_loading.iteritems():

            pos_data = Mgr.do("load_from_history", obj_id,
                              data_id, time_id)["pos"]

            for vert_id in vert_ids:
                if vert_id in pos_data:
                    positions[vert_id] = pos_data[vert_id]

        # to redo transformations, retrieve the transforms that need to be restored
        # from the data that was stored when transforms occurred, at times leading
        # up to the time that is being restored (the new time)

        for time_id in new_time_ids:

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            positions.update(subobj_data.get("pos", {}))

            for vert_id in subobj_data.get("prev", {}):
                if vert_id in verts:
                    prev_prop_times[vert_id] = time_id

        # restore the verts' previous transform time IDs
        for vert_id, time_id in prev_prop_times.iteritems():
            verts[vert_id].set_previous_property_time("transform", time_id)

        polys_to_update = set()
        vertex_data_top = self._geoms["top"][
            "shaded"].node().modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")

        for vert_id, pos in positions.iteritems():
            if vert_id in verts:
                vert = verts[vert_id]
                poly = polys[vert.get_polygon_id()]
                polys_to_update.add(poly)
                vert.set_pos(pos)
                row = vert.get_row_index()
                pos_writer.set_row(row)
                pos_writer.set_data3f(pos)

        pos_array = vertex_data_top.get_array(0)
        self._vertex_data["vert"].set_array(0, pos_array)
        self._vertex_data["poly"].set_array(0, pos_array)

        pos_array = GeomVertexArrayData(pos_array)
        handle = pos_array.modify_handle()
        handle.set_data(handle.get_data() * 2)
        self._vertex_data["edge"].set_array(0, pos_array)

        vert_ids = []

        for poly in polys_to_update:
            poly.update_center_pos()
            poly.update_normal()
            vert_ids.extend(poly.get_vertex_ids())

        self._vert_normal_change.update(vert_ids)
        self.get_toplevel_object().get_bbox().update(*self._origin.get_tight_bounds())
