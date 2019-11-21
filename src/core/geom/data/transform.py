from ...base import *


class GeomTransformMixin:
    """ GeomDataObject class mix-in """

    def __init__(self):

        self._verts_to_transf = {"vert": {}, "edge": {}, "poly": {}}
        self._rows_to_transf = {"vert": None, "edge": None, "poly": None, "normal": None}
        self._transf_start_data = {"bounds": None, "pos_array": None}
        self._pos_arrays = {"main": None, "edge": None}
        self._transformed_verts = set()
        self._picking_geom_xform_locked = False

    def _update_verts_to_transform(self, subobj_lvl):

        selected_subobj_ids = self._selected_subobj_ids[subobj_lvl]
        self._rows_to_transf[subobj_lvl] = rows_to_transf = SparseArray()

        if subobj_lvl != "normal":
            self._verts_to_transf[subobj_lvl] = verts_to_transf = {}

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

        elif subobj_lvl == "normal":

            verts = self._subobjs["vert"]

            for vert_id in selected_subobj_ids:
                vert = verts[vert_id]
                rows_to_transf.set_bit(vert.row_index)

            return

        for merged_vert in merged_verts_to_transf:

            rows = merged_vert.row_indices
            verts_to_transf[merged_vert] = rows

            for row in rows:
                rows_to_transf.set_bit(row)

    def _get_ref_node(self):

        if GD["coord_sys_type"] == "local":
            return self.toplevel_obj.pivot
        else:
            return Mgr.get("grid").origin

    def _get_transf_center_pos(self):

        cs_type = GD["coord_sys_type"]
        tc_type = GD["transf_center_type"]

        if tc_type == "pivot" or (cs_type == "local" and tc_type == "cs_origin"):
            return self.toplevel_obj.pivot.get_pos(GD.world)
        else:
            return Mgr.get("transf_center_pos")

    def update_vertex_positions(self, vertex_ids, update_bounds=True):

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]
        merged_verts = self.merged_verts
        polys_to_update = set()
        verts_to_resmooth = set()
        geom_node_top = self._toplvl_node
        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")

        for vert_id in vertex_ids:
            vert = verts[vert_id]
            poly = polys[vert.polygon_id]
            polys_to_update.add(poly)
            row = vert.row_index
            pos = vert.get_pos()
            pos_writer.set_row(row)
            pos_writer.set_data3(pos)

        pos_array = vertex_data_top.get_array(0)

        for geom_type in ("poly", "poly_picking"):
            vertex_data = self._vertex_data[geom_type]
            vertex_data.set_array(0, pos_array)

        geoms = self._geoms

        for geom_type in ("vert", "normal"):
            vertex_data = geoms[geom_type]["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array)
            vertex_data = geoms[geom_type]["sel_state"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array)

        size = pos_array.data_size_bytes
        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        pos_array_edge = vertex_data.modify_array(0)
        from_view = memoryview(pos_array).cast("B")
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view
        pos_array_edge = vertex_data.get_array(0)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array_edge)

        for poly in polys_to_update:
            poly.update_center_pos()
            poly.update_normal()
            verts_to_resmooth.update(merged_verts[v_id] for v_id in poly.vertex_ids)

        self.update_vertex_normals(verts_to_resmooth)

        if update_bounds:
            bounds = geom_node_top.get_bounds()
            self.origin.node().set_bounds(bounds)
            model = self.toplevel_obj
            model.bbox.update(*self.origin.get_tight_bounds())

    def reposition_vertices(self, computation):
        """ Change the positions of all vertices using the given computation """

        verts = self._subobjs["vert"]
        geoms = self._geoms
        geom_node_top = self._toplvl_node
        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")

        for vert in self._subobjs["vert"].values():
            row = vert.row_index
            old_pos = vert.get_initial_pos()
            new_pos = computation(Point3(*old_pos))
            pos_writer.set_row(row)
            pos_writer.set_data3(Point3(*new_pos))
            vert.set_pos(Point3(*new_pos))

        pos_array = vertex_data_top.get_array(0)

        for geom_type in ("poly", "poly_picking"):
            vertex_data = self._vertex_data[geom_type]
            vertex_data.set_array(0, pos_array)

        for geom_type in ("vert", "normal"):
            vertex_data = geoms[geom_type]["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array)
            vertex_data = geoms[geom_type]["sel_state"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array)

        size = pos_array.data_size_bytes
        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        pos_array_edge = vertex_data.modify_array(0)
        from_view = memoryview(pos_array).cast("B")
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view
        pos_array_edge = vertex_data.get_array(0)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array_edge)

        self.update_poly_centers()
        self.update_poly_normals()

        self.toplevel_obj.bbox.update(*self.origin.get_tight_bounds())

    def bake_transform(self):
        """ Bake the origin's transform into the vertices and reset it to identity """

        mat = self.origin.get_mat()
        geoms = self._geoms
        geom_node_top = self._toplvl_node
        geom_node_top.modify_geom(0).transform_vertices(mat)
        self.origin.clear_transform()
        vertex_data_top = geom_node_top.get_geom(0).get_vertex_data()
        pos_array = vertex_data_top.get_array(0)

        for geom_type in ("poly", "poly_picking"):
            vertex_data = self._vertex_data[geom_type]
            vertex_data.set_array(0, pos_array)

        for geom_type in ("vert", "normal"):
            vertex_data = geoms[geom_type]["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array)
            vertex_data = geoms[geom_type]["sel_state"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array)

        size = pos_array.data_size_bytes
        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        pos_array_edge = vertex_data.modify_array(0)
        from_view = memoryview(pos_array).cast("B")
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view
        pos_array_edge = vertex_data.get_array(0)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array_edge)

        pos_reader = GeomVertexReader(vertex_data_top, "vertex")

        for vert in self._subobjs["vert"].values():
            row = vert.row_index
            pos_reader.set_row(row)
            pos = pos_reader.get_data3()
            # NOTE: the LVecBase3f returned by the GeomVertexReader is a const
            vert.set_pos(Point3(*pos))

        self.update_poly_centers()
        self.update_poly_normals()

        self.toplevel_obj.bbox.update(*self.origin.get_tight_bounds())

    def set_picking_geom_xform_locked(self, locked=True):

        self._picking_geom_xform_locked = locked

    def get_vertex_position_data(self):

        data = {}
        geom_node_top = self._toplvl_node
        data["bounds"] = geom_node_top.get_bounds()
        pos_array_main = geom_node_top.modify_geom(0).modify_vertex_data().modify_array(0)
        data["pos_array"] = GeomVertexArrayData(pos_array_main)

        return data

    def prepare_transform(self, pos_data):

        start_data = self._transf_start_data
        start_data["bounds"] = pos_data["bounds"]
        pos_array_main = pos_data["pos_array"]
        start_data["pos_array"] = GeomVertexArrayData(pos_array_main)
        geom_node_top = self._toplvl_node
        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()
        vertex_data_top.set_array(0, pos_array_main)
        vertex_data = self._vertex_data["poly"]
        vertex_data.set_array(0, pos_array_main)

        geoms = self._geoms

        vertex_data = geoms["vert"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array_main)
        self._pos_arrays["main"] = pos_array_main

        size = pos_array_main.data_size_bytes
        pos_array_edge = GeomVertexArrayData(pos_array_main.array_format, pos_array_main.usage_hint)
        pos_array_edge.unclean_set_num_rows(pos_array_main.get_num_rows() * 2)

        from_view = memoryview(pos_array_main).cast("B")
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view

        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array_edge)
        self._pos_arrays["edge"] = pos_array_edge

        if not self._picking_geom_xform_locked:
            vertex_data = self._vertex_data["poly_picking"]
            vertex_data.set_array(0, pos_array_main)
            vertex_data = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array_main)
            vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array_edge)

    def init_transform(self):

        self.prepare_transform(self.get_vertex_position_data())

    def set_vert_sel_coordinate(self, axis, value):

        verts = self._verts_to_transf["vert"]

        if not verts:
            return

        origin = self.origin
        ref_node = self._get_ref_node()
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        tmp_vertex_data = GeomVertexData(vertex_data_top)
        index = "xyz".index(axis)
        pos_rewriter = GeomVertexRewriter(tmp_vertex_data, "vertex")

        for rows in verts.values():
            for row in rows:
                pos_rewriter.set_row(row)
                pos = pos_rewriter.get_data3()
                pos = ref_node.get_relative_point(origin, pos)
                pos[index] = value
                pos = origin.get_relative_point(ref_node, pos)
                pos_rewriter.set_data3(pos)

        pos_array_top = vertex_data_top.modify_array(0)
        pos_array_tmp = tmp_vertex_data.get_array(0)
        size = pos_array_tmp.data_size_bytes
        from_view = memoryview(pos_array_tmp).cast("B")
        to_view = memoryview(pos_array_top).cast("B")
        to_view[:] = from_view
        to_view = memoryview(self._pos_arrays["main"]).cast("B")
        to_view[:] = from_view
        to_view = memoryview(self._pos_arrays["edge"]).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view

    def transform_selection(self, subobj_lvl, transf_type, value):

        rows = self._rows_to_transf[subobj_lvl]

        if not rows:
            return

        ref_node = self._get_ref_node()
        transf_center_pos = self._get_transf_center_pos()
        origin = self.origin
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        tmp_vertex_data = GeomVertexData(vertex_data_top)
        tmp_vertex_data.set_array(0, GeomVertexArrayData(self._transf_start_data["pos_array"]))

        if transf_type == "custom":

            def get_custom_mat():

                final_mat = Mat4.ident_mat()
                mats = value["mats"]

                for mat, ref_type in mats:
                    if ref_type == "ref_node":
                        node = ref_node
                    elif ref_type == "pivot":
                        node = self.toplevel_obj.pivot
                    elif ref_type == "grid_origin":
                        node = Mgr.get("grid").origin
                    elif ref_type == "origin":
                        node = origin
                    elif ref_type == "world":
                        node = GD.world
                    elif ref_type == "custom":
                        node = value["ref_node"]
                    final_mat = final_mat * origin.get_mat(node) * mat * node.get_mat(origin)

                return final_mat

            mat = get_custom_mat()

        elif transf_type == "translate":

            vec = origin.get_relative_vector(ref_node, value)
            mat = Mat4.translate_mat(vec)

        elif transf_type == "rotate":

            tc_pos = origin.get_relative_point(GD.world, transf_center_pos)
            quat = origin.get_quat(ref_node) * value * ref_node.get_quat(origin)
            quat_mat = Mat4()
            quat.extract_to_matrix(quat_mat)
            offset_mat = Mat4.translate_mat(-tc_pos)
            mat = offset_mat * quat_mat
            offset_mat = Mat4.translate_mat(tc_pos)
            mat *= offset_mat

        elif transf_type == "scale":

            tc_pos = origin.get_relative_point(GD.world, transf_center_pos)
            scale_mat = Mat4.scale_mat(value)
            mat = origin.get_mat(ref_node) * scale_mat * ref_node.get_mat(origin)
            # remove translation component
            mat.set_row(3, VBase3())
            offset_mat = Mat4.translate_mat(-tc_pos)
            mat = offset_mat * mat
            offset_mat = Mat4.translate_mat(tc_pos)
            mat *= offset_mat

        tmp_vertex_data.transform_vertices(mat, rows)
        pos_array_tmp = GeomVertexArrayData(tmp_vertex_data.get_array(0))
        vertex_data_top.set_array(0, pos_array_tmp)

        size = pos_array_tmp.data_size_bytes
        pos_array_main = self._pos_arrays["main"]
        pos_array_edge = self._pos_arrays["edge"]
        pos_array_edge.unclean_set_num_rows(pos_array_tmp.get_num_rows() * 2)

        from_view = memoryview(pos_array_tmp).cast("B")
        to_view = memoryview(pos_array_main).cast("B")
        to_view[:] = from_view
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view

    def finalize_transform(self, cancelled=False):

        start_data = self._transf_start_data
        geom_node_top = self._toplvl_node
        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()

        if self._picking_geom_xform_locked:
            pos_array_main = self._pos_arrays["main"]
            pos_array_edge = self._pos_arrays["edge"]
            geoms = self._geoms
            vertex_data = self._vertex_data["poly_picking"]
            vertex_data.set_array(0, pos_array_main)
            vertex_data = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array_main)
            vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array_edge)
            self._picking_geom_xform_locked = False

        if cancelled:

            bounds = start_data["bounds"]

            pos_array_tmp = start_data["pos_array"]
            vertex_data_top.set_array(0, pos_array_tmp)

            for geom_type in ("poly", "poly_picking"):
                self._vertex_data[geom_type].set_array(0, pos_array_tmp)

            size = pos_array_tmp.data_size_bytes
            pos_array_main = self._pos_arrays["main"]
            pos_array_edge = self._pos_arrays["edge"]
            pos_array_edge.unclean_set_num_rows(pos_array_tmp.get_num_rows() * 2)

            from_view = memoryview(pos_array_tmp).cast("B")
            to_view = memoryview(pos_array_main).cast("B")
            to_view[:] = from_view
            to_view = memoryview(pos_array_edge).cast("B")
            to_view[:size] = from_view
            to_view[size:] = from_view

        else:

            bounds = geom_node_top.get_bounds()

            pos_reader = GeomVertexReader(vertex_data_top, "vertex")
            subobj_lvl = GD["active_obj_level"]
            polys = self._subobjs["poly"]
            poly_ids = set()

            for merged_vert, indices in self._verts_to_transf[subobj_lvl].items():
                pos_reader.set_row(indices[0])
                pos = Point3(pos_reader.get_data3())
                merged_vert.set_pos(pos)
                poly_ids.update(merged_vert.polygon_ids)

            vert_ids = []
            polys_to_update = [polys[poly_id] for poly_id in poly_ids]

            for poly in polys_to_update:
                poly.update_center_pos()
                poly.update_normal()
                vert_ids.extend(poly.vertex_ids)

            merged_verts = set(self.merged_verts[vert_id] for vert_id in vert_ids)
            self.update_vertex_normals(merged_verts)

            pos_array = geom_node_top.get_geom(0).get_vertex_data().get_array(0)
            from_view = memoryview(pos_array).cast("B")
            normal_geoms = self._geoms["normal"]
            vertex_data = normal_geoms["pickable"].node().modify_geom(0).modify_vertex_data()
            to_array = vertex_data.modify_array(0)
            to_array.unclean_set_num_rows(pos_array.get_num_rows())
            to_view = memoryview(to_array).cast("B")
            to_view[:] = from_view
            pos_array = vertex_data.get_array(0)
            vertex_data = normal_geoms["sel_state"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array)
            model = self.toplevel_obj
            model.bbox.update(*self.origin.get_tight_bounds())

        self.origin.node().set_bounds(bounds)
        start_data.clear()
        self._pos_arrays = {"main": None, "edge": None}

    def _restore_subobj_transforms(self, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id
        prop_id = self._unique_prop_ids["subobj_transform"]

        prev_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id, old_time_id)
        new_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)

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

            prev_time_ids = prev_time_ids[i:]
            new_time_ids = new_time_ids[i:]

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]

        data_id = self._unique_prop_ids["vert_pos__extra__"]

        time_ids_to_restore = {}
        prev_prop_times = {}
        positions = {}

        # to undo transformations, determine the time IDs of the transforms that
        # need to be restored by checking the data that was stored when transforms
        # occurred, at times leading up to the time that is being replaced (the old
        # time)

        for time_id in reversed(prev_time_ids):
            # time_id is a Time ID to update time_ids_to_restore with

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            # subobj_data.get("prev", {}) yields previous transform times
            time_ids_to_restore.update(subobj_data.get("prev", {}))

        data_for_loading = {}

        # time_ids_to_restore.keys() are the IDs of vertices that need a
        # transform update
        for vert_id, time_id in time_ids_to_restore.items():

            if vert_id in verts:
                prev_prop_times[vert_id] = time_id
                # since multiple vertex positions might have to be loaded from the same
                # datafile, make sure each datafile is loaded only once
                data_for_loading.setdefault(time_id, []).append(vert_id)

        for time_id, vert_ids in data_for_loading.items():

            pos_data = Mgr.do("load_from_history", obj_id, data_id, time_id)["pos"]

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
        for vert_id, time_id in prev_prop_times.items():
            verts[vert_id].set_previous_property_time("transform", time_id)

        polys_to_update = set()
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")

        for vert_id, pos in positions.items():
            if vert_id in verts:
                vert = verts[vert_id]
                poly = polys[vert.polygon_id]
                polys_to_update.add(poly)
                vert.set_pos(pos)
                row = vert.row_index
                pos_writer.set_row(row)
                pos_writer.set_data3(pos)

        pos_array_top = vertex_data_top.get_array(0)

        for geom_type in ("poly", "poly_picking"):
            vertex_data = self._vertex_data[geom_type]
            vertex_data.set_array(0, pos_array_top)

        geoms = self._geoms

        for geom_type in ("vert", "normal"):
            vertex_data = geoms[geom_type]["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array_top)
            vertex_data = geoms[geom_type]["sel_state"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array_top)

        size = pos_array_top.data_size_bytes
        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        pos_array_edge = vertex_data.modify_array(0)
        pos_array_edge.unclean_set_num_rows(pos_array_top.get_num_rows() * 2)

        from_view = memoryview(pos_array_top).cast("B")
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view

        pos_array_edge = vertex_data.get_array(0)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array_edge)

        for poly in polys_to_update:
            poly.update_center_pos()
            poly.update_normal()

        bounds = self.origin.get_tight_bounds()

        if bounds:
            self.toplevel_obj.bbox.update(*bounds)


class TransformMixin:
    """ Selection class mix-in """

    def __init__(self):

        self._obj_root = Mgr.get("object_root")
        self._center_pos = Point3()

    def update_center_pos(self):

        if not self._objs:
            self._center_pos = Point3()
        else:
            self._center_pos = sum([obj.get_center_pos(GD.world)
                                   for obj in self._objs], Point3()) / len(self._objs)

    def get_center_pos(self):

        return Point3(self._center_pos)

    def update_ui(self):

        tc_type = GD["transf_center_type"]

        if tc_type == "adaptive":
            adaptive_tc_type = Mgr.get("adaptive_transf_center_type")
        else:
            adaptive_tc_type = ""

        count = len(self._objs)

        if count:
            if tc_type == "sel_center" or adaptive_tc_type:
                Mgr.get("transf_gizmo").pos = self.get_center_pos()

        if count == 1:
            grid_origin = Mgr.get("grid").origin
            if self._obj_level == "normal":
                h, p, r = self._objs[0].get_hpr(grid_origin)
                transform_values = {"rotate": (p, r, h)}
            else:
                x, y, z = self._objs[0].get_center_pos(grid_origin)
                transform_values = {"translate": (x, y, z)}
        else:
            transform_values = None

        Mgr.update_remotely("transform_values", transform_values)

        prev_count = GD["selection_count"]

        if count != prev_count:
            transf_gizmo = Mgr.get("transf_gizmo")
            transf_gizmo.show() if count else transf_gizmo.hide()
            GD["selection_count"] = count

        Mgr.update_remotely("selection_count")
        Mgr.update_remotely("sel_color_count")

    def get_vertex_position_data(self):

        data = {}

        if self._obj_level == "normal":
            for geom_data_obj in self._groups:
                data[geom_data_obj] = geom_data_obj.get_normal_array()
        else:
            for geom_data_obj in self._groups:
                data[geom_data_obj] = geom_data_obj.get_vertex_position_data()

        return data

    def prepare_transform(self, pos_data):

        if self._obj_level == "normal":
            for geom_data_obj, data in pos_data.items():
                geom_data_obj.prepare_normal_transform(data)
        else:
            for geom_data_obj, data in pos_data.items():
                geom_data_obj.prepare_transform(data)

    def set_transform_component(self, transf_type, axis, value, is_rel_value, add_to_hist=True):

        obj_lvl = self._obj_level

        if obj_lvl == "normal":
            for geom_data_obj in self._groups:
                geom_data_obj.init_normal_transform()
        else:
            for geom_data_obj in self._groups:
                geom_data_obj.init_transform()

        if is_rel_value:

            if transf_type == "translate":
                transform = Vec3()
                transform["xyz".index(axis)] = value
            elif transf_type == "rotate":
                hpr = VBase3()
                hpr["zxy".index(axis)] = value
                transform = Quat()
                transform.set_hpr(hpr)
            elif transf_type == "scale":
                transform = Vec3(1., 1., 1.)
                value = max(10e-008, abs(value)) * (-1. if value < 0. else 1.)
                transform["xyz".index(axis)] = value

            if obj_lvl == "normal":
                for geom_data_obj in self._groups:
                    geom_data_obj.transform_normals(transf_type, transform)
                    geom_data_obj.finalize_normal_transform()
            else:
                for geom_data_obj in self._groups:
                    geom_data_obj.transform_selection(obj_lvl, transf_type, transform)
                    geom_data_obj.finalize_transform()

        elif obj_lvl == "normal":

            # Set absolute angle for selected normals

            for geom_data_obj in self._groups:
                geom_data_obj.set_normal_sel_angle(axis, value)
                geom_data_obj.finalize_normal_transform()

            if len(self._objs) == 1:
                h, p, r = self._objs[0].get_hpr(Mgr.get("grid").origin)
                transform_values = {"rotate": (p, r, h)}
                Mgr.update_remotely("transform_values", transform_values)

        else:

            # Set absolute coordinate for selected vertices

            for geom_data_obj in self._groups:
                geom_data_obj.set_vert_sel_coordinate(axis, value)
                geom_data_obj.finalize_transform()

            if len(self._objs) == 1:
                x, y, z = self._objs[0].get_pos(Mgr.get("grid").origin)
                transform_values = {"translate": (x, y, z)}
                Mgr.update_remotely("transform_values", transform_values)

        if obj_lvl != "normal":

            self.update_center_pos()

            if GD["transf_center_type"] in ("adaptive", "sel_center"):
                Mgr.get("transf_gizmo").pos = self.get_center_pos()

        if add_to_hist:
            self.add_history(transf_type)

    def aim_at_point(self, point, ref_node, toward=True, add_to_hist=True, objects=None, lock_normals=True):

        if self._obj_level == "normal":

            geom_data_objs = [o.geom_obj.geom_data_obj for o in objects] if objects else self._groups

            for geom_data_obj in geom_data_objs:
                geom_data_obj.aim_selected_normals(point, ref_node, toward)
                geom_data_obj.finalize_normal_transform(lock_normals=lock_normals)

            if len(self._objs) == 1:
                h, p, r = self._objs[0].get_hpr(Mgr.get("grid").origin)
                transform_values = {"rotate": (p, r, h)}
                Mgr.update_remotely("transform_values", transform_values)

            if add_to_hist:
                self.add_history("custom", "Aim {} at point")

    def update_transform_values(self):

        if len(self._objs) == 1:

            subobj = self._objs[0]

            if GD["coord_sys_type"] == "local":
                ref_node = subobj.toplevel_obj.pivot
            else:
                ref_node = Mgr.get("grid").origin

            if self._obj_level == "normal":
                h, p, r = subobj.get_hpr(ref_node)
                transform_values = {"rotate": (p, r, h)}
            else:
                x, y, z = subobj.get_center_pos(ref_node)
                transform_values = {"translate": (x, y, z)}

            Mgr.update_remotely("transform_values", transform_values)

    def init_transform(self, objects=None):

        geom_data_objs = [o.geom_obj.geom_data_obj for o in objects] if objects else self._groups

        if self._obj_level == "normal":
            for geom_data_obj in geom_data_objs:
                geom_data_obj.init_normal_transform()
        else:
            for geom_data_obj in geom_data_objs:
                geom_data_obj.init_transform()

    def init_translation(self):

        self.init_transform()

    def translate(self, translation_vec):

        obj_lvl = self._obj_level

        if obj_lvl == "normal":
            for geom_data_obj in self._groups:
                geom_data_obj.transform_normals("translate", translation_vec)
        else:
            for geom_data_obj in self._groups:
                geom_data_obj.transform_selection(obj_lvl, "translate", translation_vec)

    def init_rotation(self):

        self.init_transform()

    def rotate(self, rotation):

        obj_lvl = self._obj_level

        if obj_lvl == "normal":
            for geom_data_obj in self._groups:
                geom_data_obj.transform_normals("rotate", rotation)
        else:
            for geom_data_obj in self._groups:
                geom_data_obj.transform_selection(obj_lvl, "rotate", rotation)

    def init_scaling(self):

        self.init_transform()

    def scale(self, scaling):

        obj_lvl = self._obj_level

        if obj_lvl == "normal":
            for geom_data_obj in self._groups:
                geom_data_obj.transform_normals("scale", scaling)
        else:
            for geom_data_obj in self._groups:
                geom_data_obj.transform_selection(obj_lvl, "scale", scaling)

    def custom_transform(self, data, add_to_hist=True, objects=None, lock_normals=True):

        self.init_transform(objects)

        geom_data_objs = [o.geom_obj.geom_data_obj for o in objects] if objects else self._groups

        obj_lvl = self._obj_level

        if obj_lvl == "normal":
            for geom_data_obj in geom_data_objs:
                geom_data_obj.transform_normals("custom", data)
        else:
            for geom_data_obj in geom_data_objs:
                geom_data_obj.transform_selection(obj_lvl, "custom", data)

        self.finalize_transform(add_to_hist=add_to_hist, data=data,
                                objects=objects, lock_normals=lock_normals)

    def finalize_transform(self, cancelled=False, add_to_hist=True, data=None,
                           objects=None, lock_normals=True):

        geom_data_objs = [o.geom_obj.geom_data_obj for o in objects] if objects else self._groups

        if self._obj_level == "normal":

            for geom_data_obj in geom_data_objs:
                geom_data_obj.finalize_normal_transform(cancelled, lock_normals)

            if not cancelled:
                self.update_transform_values()
                if add_to_hist:
                    xform_type = "custom" if data else GD["active_transform_type"]
                    self.add_history(xform_type, data["descr"] if data else "")

        else:

            for geom_data_obj in geom_data_objs:
                geom_data_obj.finalize_transform(cancelled)

            if not cancelled:

                self.update_center_pos()

                if GD["transf_center_type"] in ("adaptive", "sel_center"):
                    Mgr.get("transf_gizmo").pos = self.get_center_pos()
                else:
                    Mgr.get("transf_gizmo").pos = Mgr.get("transf_center_pos")

                self.update_transform_values()

                if add_to_hist:
                    xform_type = "custom" if data else GD["active_transform_type"]
                    self.add_history(xform_type, data["descr"] if data else "")

    def add_history(self, transf_type, descr=""):

        obj_data = {}
        event_data = {"objects": obj_data}
        Mgr.do("update_history_time")

        if self._obj_level == "vert":
            subobj_descr = "vertices"
        elif self._obj_level == "edge":
            subobj_descr = "edges"
        elif self._obj_level == "poly":
            subobj_descr = "polygons"
        elif self._obj_level == "normal":
            subobj_descr = "normals"

        if descr:
            event_descr = descr.format(subobj_descr)
        else:
            event_descr = f'{transf_type.title()} {subobj_descr}'

        if self._obj_level == "normal":
            for geom_data_obj in self._groups:
                obj_id = geom_data_obj.toplevel_obj.id
                obj_data[obj_id] = geom_data_obj.get_data_to_store("prop_change", "normals")
        else:
            for geom_data_obj in self._groups:
                obj_id = geom_data_obj.toplevel_obj.id
                obj_data[obj_id] = geom_data_obj.get_data_to_store("prop_change", "subobj_transform")

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def cancel_transform(self):

        self.finalize_transform(cancelled=True)
