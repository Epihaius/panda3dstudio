from ...base import *


class UVEditMixin:
    """ GeomDataObject class mix-in """

    def __init__(self):

        self._uv_set_names = ["", "1", "2", "3", "4", "5", "6", "7"]
        self._has_poly_tex_proj = False
        self._uv_change = set()
        self._copied_uvs = {}
        self._copied_uv_array = None
        self._tex_seam_edge_ids = {}
        self._tex_seam_geom = None
        self._tex_seam_prims = {}
        self._edge_prims = {}

    def init_uvs(self):

        vertex_data_poly = self._vertex_data["poly"]
        uv_writers = [GeomVertexWriter(vertex_data_poly, "texcoord")]

        for i in range(1, 8):
            uv_writers.append(GeomVertexWriter(vertex_data_poly, f"texcoord.{i}"))

        for poly in self.ordered_polys:

            for vert in poly.vertices:

                row = vert.row_index
                uvs = vert.get_uvs()

                for uv_set_id, uv in uvs.items():
                    uv_writer = uv_writers[uv_set_id]
                    uv_writer.set_row(row)
                    uv_writer.set_data2(uv)

        arrays = []

        for i in range(8):
            array = vertex_data_poly.get_array(4 + i)
            arrays.append(array)

        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()

        for i, array in enumerate(arrays):
            vertex_data_top.set_array(4 + i, GeomVertexArrayData(array))

    def set_uv_set_names(self, uv_set_names):

        if self._uv_set_names == uv_set_names:
            return False

        self._uv_set_names = uv_set_names

        return True

    def get_uv_set_names(self):

        return self._uv_set_names

    def _restore_uv_set_names(self, time_id):

        obj_id = self.toplevel_obj.id
        prop_id = self._unique_prop_ids["uv_set_names"]
        data = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)
        self._uv_set_names = data

    def create_tex_seams(self, uv_set_id, seam_edge_ids, color):

        self._tex_seam_edge_ids[uv_set_id] = seam_edge_ids
        edge_geom = self._geoms["edge"]["sel_state"]
        edge_prims = self._edge_prims
        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        all_masks = render_mask | picking_mask

        if self._tex_seam_geom:
            seam_geom = self._tex_seam_geom
            edge_prim = edge_prims["main"]
        else:
            seam_geom = edge_geom.copy_to(edge_geom)
            seam_geom.set_color(color)
            seam_geom.show(all_masks)
            self._tex_seam_geom = seam_geom
            seam_geom.show_through(render_mask)
            edge_prim = GeomLines(edge_geom.node().get_geom(0).get_primitive(0))
            edge_prims["main"] = edge_prim

        edge_prim = GeomLines(edge_prim)
        seam_prim = GeomLines(edge_prim)

        tmp_merged_edge = Mgr.do("create_merged_edge", self)

        for edge_id in seam_edge_ids:
            tmp_merged_edge.append(edge_id)

        row_indices = tmp_merged_edge.start_row_indices
        edge_array = edge_prim.modify_vertices()
        stride = edge_array.array_format.stride
        edge_view = memoryview(edge_array).cast("B")
        seam_array = seam_prim.modify_vertices()
        seam_array.unclean_set_num_rows(len(row_indices) * 2)
        seam_view = memoryview(seam_array).cast("B")
        rows = edge_prim.get_vertex_list()[::2]
        row_ranges_to_keep = SparseArray()
        row_ranges_to_keep.set_range(0, edge_array.get_num_rows())
        row_ranges_to_move = SparseArray()

        for i in row_indices:
            start = rows.index(i) * 2
            row_ranges_to_keep.clear_range(start, 2)
            row_ranges_to_move.set_range(start, 2)

        f = lambda values, stride: (v * stride for v in values)
        row_count = 0

        for i in range(row_ranges_to_move.get_num_subranges()):
            start = row_ranges_to_move.get_subrange_begin(i)
            size = row_ranges_to_move.get_subrange_end(i) - start
            offset, start_, size_ = f((row_count, start, size), stride)
            seam_view[offset:offset+size_] = edge_view[start_:start_+size_]
            row_count += size

        row_count = 0

        for i in range(row_ranges_to_keep.get_num_subranges()):
            start = row_ranges_to_keep.get_subrange_begin(i)
            size = row_ranges_to_keep.get_subrange_end(i) - start
            offset, start_, size_ = f((row_count, start, size), stride)
            edge_view[offset:offset+size_] = edge_view[start_:start_+size_]
            row_count += size

        edge_array.set_num_rows(row_count)
        edge_geom.node().modify_geom(0).set_primitive(0, edge_prim)
        seam_geom.node().modify_geom(0).set_primitive(0, seam_prim)
        edge_prims[uv_set_id] = edge_prim
        self._tex_seam_prims[uv_set_id] = seam_prim

        self.clear_tex_seam_selection(uv_set_id, color)

    def add_tex_seam_edges(self, uv_set_id, edge_ids):

        self._tex_seam_edge_ids[uv_set_id].extend(edge_ids)
        edge_prim = self._edge_prims[uv_set_id]
        seam_prim = self._tex_seam_prims[uv_set_id]

        tmp_merged_edge = Mgr.do("create_merged_edge", self)

        for edge_id in edge_ids:
            tmp_merged_edge.append(edge_id)

        row_indices = tmp_merged_edge.start_row_indices
        edge_array = edge_prim.modify_vertices()
        stride = edge_array.array_format.stride
        edge_view = memoryview(edge_array).cast("B")
        seam_array = seam_prim.modify_vertices()
        row_count = seam_array.get_num_rows()
        seam_array.set_num_rows(row_count + len(row_indices) * 2)
        seam_view = memoryview(seam_array).cast("B")
        rows = edge_prim.get_vertex_list()[::2]
        row_ranges_to_keep = SparseArray()
        row_ranges_to_keep.set_range(0, edge_array.get_num_rows())
        row_ranges_to_move = SparseArray()

        for i in row_indices:
            start = rows.index(i) * 2
            row_ranges_to_keep.clear_range(start, 2)
            row_ranges_to_move.set_range(start, 2)

        f = lambda values, stride: (v * stride for v in values)

        for i in range(row_ranges_to_move.get_num_subranges()):
            start = row_ranges_to_move.get_subrange_begin(i)
            size = row_ranges_to_move.get_subrange_end(i) - start
            offset, start_, size_ = f((row_count, start, size), stride)
            seam_view[offset:offset+size_] = edge_view[start_:start_+size_]
            row_count += size

        row_count = 0

        for i in range(row_ranges_to_keep.get_num_subranges()):
            start = row_ranges_to_keep.get_subrange_begin(i)
            size = row_ranges_to_keep.get_subrange_end(i) - start
            offset, start_, size_ = f((row_count, start, size), stride)
            edge_view[offset:offset+size_] = edge_view[start_:start_+size_]
            row_count += size

        edge_array.set_num_rows(row_count)

    def remove_tex_seam_edges(self, uv_set_id, edge_ids):

        seam_edge_ids = self._tex_seam_edge_ids[uv_set_id]
        selected_edge_ids = self._selected_subobj_ids["edge"]
        merged_edges = self.merged_edges
        tmp_merged_edge1 = Mgr.do("create_merged_edge", self)
        tmp_merged_edge2 = Mgr.do("create_merged_edge", self)

        for edge_id in edge_ids:

            seam_edge_ids.remove(edge_id)

            if edge_id in selected_edge_ids:
                selected_edge_ids.remove(edge_id)
                tmp_merged_edge1.append(edge_id)
            else:
                selected_edge_ids.append(edge_id)
                tmp_merged_edge2.append(edge_id)

        if tmp_merged_edge1[:]:
            edge_id = tmp_merged_edge1.id
            orig_merged_edge = merged_edges[edge_id]
            merged_edges[edge_id] = tmp_merged_edge1
            self.update_selection("edge", [tmp_merged_edge1], [], False)
            merged_edges[edge_id] = orig_merged_edge

        if tmp_merged_edge2[:]:
            edge_id = tmp_merged_edge2.id
            orig_merged_edge = merged_edges[edge_id]
            merged_edges[edge_id] = tmp_merged_edge2
            self.update_selection("edge", [], [tmp_merged_edge2], False)
            merged_edges[edge_id] = orig_merged_edge

        edge_prim = self._edge_prims[uv_set_id]
        seam_prim = self._tex_seam_prims[uv_set_id]

        tmp_merged_edge = Mgr.do("create_merged_edge", self)

        for edge_id in edge_ids:
            tmp_merged_edge.append(edge_id)

        row_indices = tmp_merged_edge.start_row_indices
        seam_array = seam_prim.modify_vertices()
        stride = seam_array.array_format.stride
        seam_view = memoryview(seam_array).cast("B")
        edge_array = edge_prim.modify_vertices()
        row_count = edge_array.get_num_rows()
        edge_array.set_num_rows(row_count + len(row_indices) * 2)
        edge_view = memoryview(edge_array).cast("B")
        rows = seam_prim.get_vertex_list()[::2]
        row_ranges_to_keep = SparseArray()
        row_ranges_to_keep.set_range(0, seam_array.get_num_rows())
        row_ranges_to_move = SparseArray()

        for i in row_indices:
            start = rows.index(i) * 2
            row_ranges_to_keep.clear_range(start, 2)
            row_ranges_to_move.set_range(start, 2)

        f = lambda values, stride: (v * stride for v in values)

        for i in range(row_ranges_to_move.get_num_subranges()):
            start = row_ranges_to_move.get_subrange_begin(i)
            size = row_ranges_to_move.get_subrange_end(i) - start
            offset, start_, size_ = f((row_count, start, size), stride)
            edge_view[offset:offset+size_] = seam_view[start_:start_+size_]
            row_count += size

        row_count = 0

        for i in range(row_ranges_to_keep.get_num_subranges()):
            start = row_ranges_to_keep.get_subrange_begin(i)
            size = row_ranges_to_keep.get_subrange_end(i) - start
            offset, start_, size_ = f((row_count, start, size), stride)
            seam_view[offset:offset+size_] = seam_view[start_:start_+size_]
            row_count += size

        seam_array.set_num_rows(row_count)

    def set_selected_tex_seam_edge(self, uv_set_id, colors, edge, is_selected=True):

        if not uv_set_id in self._tex_seam_edge_ids:
            return

        if edge.id in self._tex_seam_edge_ids[uv_set_id]:
            sel_colors = colors
            geom = self._tex_seam_geom
        else:
            sel_colors = None
            geom = None

        if is_selected:
            self.update_selection("edge", [edge], [], False, sel_colors, geom)
        else:
            self.update_selection("edge", [], [edge], False, sel_colors, geom)

    def clear_tex_seam_selection(self, uv_set_id, color):

        self.clear_selection("edge", False, True)

        if not uv_set_id in self._tex_seam_edge_ids:
            return

        edge_ids = self._tex_seam_edge_ids[uv_set_id]

        if not edge_ids:
            return

        tmp_merged_edge = Mgr.do("create_merged_edge", self)

        for edge_id in edge_ids:
            tmp_merged_edge.append(edge_id)

        vertex_data = self._tex_seam_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")

        for row_index in tmp_merged_edge.row_indices:
            col_writer.set_row(row_index)
            col_writer.set_data4(color)

    def update_tex_seam_selection(self, edge_ids, color):

        tmp_merged_edge = Mgr.do("create_merged_edge", self)

        for edge_id in edge_ids:
            tmp_merged_edge.append(edge_id)

        vertex_data = self._tex_seam_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")

        for row_index in tmp_merged_edge.row_indices:
            col_writer.set_row(row_index)
            col_writer.set_data4(color)

    def set_tex_seams(self, uv_set_id):

        seam_geom = self._tex_seam_geom

        if not seam_geom:
            return

        seam_geom.node().modify_geom(0).set_primitive(0, self._tex_seam_prims[uv_set_id])
        edge_geom = self._geoms["edge"]["sel_state"]
        edge_geom.node().modify_geom(0).set_primitive(0, self._edge_prims[uv_set_id])

    def show_tex_seams(self, obj_level, color):

        seam_geom = self._tex_seam_geom

        if not seam_geom:
            return

        if obj_level == "edge":
            seam_geom.set_color_off()
        else:
            seam_geom.set_color(color)

    def destroy_tex_seams(self, uv_set_id):

        if self._tex_seam_geom:
            self._tex_seam_geom.detach_node()
            self._tex_seam_geom = None
            edge_prim = self._edge_prims["main"]
            edge_geom = self._geoms["edge"]["sel_state"]
            edge_geom.node().modify_geom(0).set_primitive(0, edge_prim)
            del self._edge_prims["main"]

        del self._edge_prims[uv_set_id]
        del self._tex_seam_prims[uv_set_id]
        del self._tex_seam_edge_ids[uv_set_id]

    def project_uvs(self, uv_set_ids=None, project=True, projector=None,
                    toplvl=True, show_poly_sel=True):

        material = self.toplevel_obj.get_material()

        if not material:
            return

        self._has_poly_tex_proj = project and not toplvl
        render_mask = Mgr.get("render_mask")

        if toplvl:

            geom = self.toplevel_geom
            self._geoms["poly"]["unselected"].hide(render_mask)
            self._geoms["poly"]["selected"].hide(render_mask)
            self._geoms["poly"]["selected"].set_state(Mgr.get("poly_selection_state"))

        else:

            geom = self._geoms["poly"]["selected"]

            if project:
                state = "poly_selection_state" + ("" if show_poly_sel else "_off")
                geom.set_state(Mgr.get(state))
                geom.show(render_mask)
                self._geoms["poly"]["unselected"].show(render_mask)
            else:
                geom.set_state(Mgr.get("poly_selection_state"))
                geom.hide(render_mask)
                self._geoms["poly"]["unselected"].hide(render_mask)

        self.update_render_mode(self.toplevel_obj.is_selected())

        if not uv_set_ids:
            return

        get_tex_stages = material.get_tex_stages
        tex_stages = [ts for uv_id in uv_set_ids for ts in get_tex_stages(uv_id)]

        if project:
            for tex_stage in tex_stages:
                geom.set_tex_gen(tex_stage, TexGenAttrib.M_world_position)
                geom.set_tex_projector(tex_stage, GD.world, projector)
        else:
            for tex_stage in tex_stages:
                geom.clear_tex_gen(tex_stage)
                geom.clear_tex_projector(tex_stage)

    def apply_uv_projection(self, vertex_data, uv_set_ids, toplvl=True):

        verts = self._subobjs["vert"]
        model = self.toplevel_obj
        tangent_space_needs_update = 0 in uv_set_ids and model.has_tangent_space()
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        uv_readers = {}

        for uv_set_id in uv_set_ids:
            column = "texcoord" if uv_set_id == 0 else f"texcoord.{uv_set_id}"
            uv_readers[uv_set_id] = GeomVertexReader(vertex_data, column)

        if toplvl:

            if tangent_space_needs_update:
                polys_to_update = None

            self._uv_change = set(verts)
            arrays = []

            for uv_set_id in uv_set_ids:
                array = vertex_data.get_array(4 + uv_set_id)
                arrays.append(array)
                vertex_data_top.set_array(4 + uv_set_id, GeomVertexArrayData(array))

            for vert in verts.values():

                row_index = vert.row_index

                for uv_set_id in uv_set_ids:
                    uv_reader = uv_readers[uv_set_id]
                    uv_reader.set_row(row_index)
                    u, v = uv_reader.get_data2()
                    vert.set_uvs((u, v), uv_set_id)

        else:

            polys = self._subobjs["poly"]
            uv_writers = {}

            for uv_set_id in uv_set_ids:
                column = "texcoord" if uv_set_id == 0 else f"texcoord.{uv_set_id}"
                uv_writers[uv_set_id] = GeomVertexWriter(vertex_data_top, column)

            if tangent_space_needs_update:
                polys_to_update = self._selected_subobj_ids["poly"][:]

            for poly_id in self._selected_subobj_ids["poly"]:

                poly = polys[poly_id]
                vert_ids = poly.vertex_ids
                self._uv_change.update(vert_ids)

                for vert_id in vert_ids:

                    vert = verts[vert_id]
                    row_index = vert.row_index

                    for uv_set_id in uv_set_ids:
                        uv_reader = uv_readers[uv_set_id]
                        uv_writer = uv_writers[uv_set_id]
                        uv_reader.set_row(row_index)
                        u, v = uv_reader.get_data2()
                        vert.set_uvs((u, v), uv_set_id)
                        uv_writer.set_row(row_index)
                        uv_writer.set_data2(u, v)

            arrays = []

            for uv_set_id in uv_set_ids:
                arrays.append(vertex_data_top.get_array(4 + uv_set_id))

        vertex_data_poly = self._vertex_data["poly"]

        for array in arrays:
            vertex_data_poly.set_array(4 + uv_set_id, GeomVertexArrayData(array))

        if tangent_space_needs_update:
            tangent_flip, bitangent_flip = model.get_tangent_space_flip()
            self.update_tangent_space(tangent_flip, bitangent_flip, polys_to_update)
        else:
            self.is_tangent_space_initialized = False

        if 0 in uv_set_ids:
            self.update_vertex_colors()

    def apply_uv_edits(self, vert_ids, uv_set_id):

        self._uv_change.update(vert_ids)
        verts = self._subobjs["vert"]
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data_poly = self._vertex_data["poly"]

        column = "texcoord" if uv_set_id == 0 else f"texcoord.{uv_set_id}"
        uv_writer = GeomVertexWriter(vertex_data_top, column)

        for vert_id in vert_ids:
            vert = verts[vert_id]
            row_index = vert.row_index
            u, v = vert.get_uvs(uv_set_id)
            uv_writer.set_row(row_index)
            uv_writer.set_data2(u, v)

        array = vertex_data_top.get_array(4 + uv_set_id)
        vertex_data_poly.set_array(4 + uv_set_id, GeomVertexArrayData(array))

        if uv_set_id == 0:

            model = self.toplevel_obj

            if model.has_tangent_space():
                polys_to_update = set(verts[vert_id].polygon_id for vert_id in vert_ids)
                tangent_flip, bitangent_flip = model.get_tangent_space_flip()
                self.update_tangent_space(tangent_flip, bitangent_flip, polys_to_update)
            else:
                self.is_tangent_space_initialized = False

            self.update_vertex_colors()

    def copy_uvs(self, uv_set_id):

        verts = self._subobjs["vert"]

        for vert_id, vert in verts.items():
            self._copied_uvs[vert_id] = vert.get_uvs(uv_set_id)

        vertex_data = self._vertex_data["poly"]
        self._copied_uv_array = GeomVertexArrayData(vertex_data.get_array(4 + uv_set_id))

    def paste_uvs(self, uv_set_id):

        verts = self._subobjs["vert"]
        self._uv_change = set(verts)

        for vert_id, vert in verts.items():
            vert.set_uvs(self._copied_uvs[vert_id], uv_set_id)

        array = self._copied_uv_array
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_top.set_array(4 + uv_set_id, GeomVertexArrayData(array))
        vertex_data_poly.set_array(4 + uv_set_id, array)

        if uv_set_id == 0:

            model = self.toplevel_obj

            if model.has_tangent_space():
                model.update_tangent_space()
            else:
                self.is_tangent_space_initialized = False

            self.update_vertex_colors()

    def clear_copied_uvs(self):

        self._copied_uvs = {}
        self._copied_uv_array = None

    def get_uv_change(self):

        return self._uv_change

    def _restore_uvs(self, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id
        prop_id = self._unique_prop_ids["uvs"]

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

            common_time_ids = prev_time_ids[:i]
            prev_time_ids = prev_time_ids[i:]
            new_time_ids = new_time_ids[i:]

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]

        data_id = self._unique_prop_ids["uv__extra__"]

        time_ids_to_restore = {}
        time_ids = {}
        uv_data = {}

        # to undo UV-mapping, determine the time IDs of the UV-mappings that
        # need to be restored by checking the data that was stored when mappings
        # occurred, at times leading up to the time that is being replaced (the old
        # time)

        uv_set_ids = {}

        for time_id in reversed(prev_time_ids):

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            prev_data = subobj_data.get("prev", {})
            time_ids_to_restore.update(prev_data)
            restored_uv_data = subobj_data.get("uvs", {})

            for vert_id in prev_data:
                # the restored data is a dict containing (vert_id, subdict) pairs, with
                # each subdict containing (uv_set_id, uv) pairs;
                # this data is used to build up a uv_set_ids dict that associates a
                # vertex with all of the UV sets whose UVs have been stored for
                # that vertex
                uv_set_ids.setdefault(vert_id, set()).update(restored_uv_data.get(vert_id, {}))

        vert_ids = {}

        for vert_id, time_id in time_ids_to_restore.items():
            if vert_id in verts:
                time_ids[vert_id] = time_id
                vert_ids.setdefault(time_id, []).append(vert_id)

        for time_id, ids in vert_ids.items():

            if time_id:

                subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)

                for vert_id in ids:
                    uv_data[vert_id] = subobj_data["uvs"][vert_id]

            else:

                for vert_id in ids:
                    uv_data[vert_id] = {}

        # to redo UV-mappings, retrieve the mappings that need to be restored
        # from the data that was stored when mappings occurred, at times leading
        # up to the time that is being restored (the new time)

        for time_id in new_time_ids:

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            restored_uv_data = subobj_data.get("uvs", {})

            for vert_id, uvs in restored_uv_data.items():
                if vert_id in uv_set_ids:
                    uv_set_ids[vert_id].update(uvs)

            uv_data.update(restored_uv_data)

            for vert_id in subobj_data.get("prev", {}):
                if vert_id in verts:
                    time_ids[vert_id] = time_id

        # restore the verts' previous UV-mapping time IDs
        for vert_id, time_id in time_ids.items():
            verts[vert_id].set_previous_property_time("uvs", time_id)

        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        uv_writers = {0: GeomVertexWriter(vertex_data_top, "texcoord")}

        for uv_set_id in range(1, 8):
            uv_writers[uv_set_id] = GeomVertexWriter(vertex_data_top, f"texcoord.{uv_set_id}")

        uv_sets_to_restore = set()

        for vert_id, uvs in uv_data.items():

            if vert_id in verts:

                if vert_id in uv_set_ids:

                    # when storing UV-mapping data, only the UVs that were specifically changed for a
                    # particular UV set are stored, instead of also storing the initial (0., 0.) UVs
                    # of the remaining UV sets (since there are 8 UV sets in total, this would result
                    # in a lot of redundant data in most cases);
                    # when creating a new vertex with initial (0., 0.) UV values, those values are
                    # not stored so any changed values would not be reset to zero when undoing those
                    # changes; to remedy this, those UVs must now be explicitly set to (0., 0.)
                    missing_uv_sets = uv_set_ids[vert_id].difference(uvs)

                    for uv_set_id in missing_uv_sets:
                        uvs[uv_set_id] = (0., 0.)

                vert = verts[vert_id]
                row = vert.row_index

                for uv_set_id, uv in uvs.items():
                    uv_writer = uv_writers[uv_set_id]
                    uv_writer.set_row(row)
                    uv_writer.set_data2(uv)
                    uv_sets_to_restore.add(uv_set_id)

                vert.set_uvs(uvs)

        for uv_set_id in uv_sets_to_restore:
            array = vertex_data_top.get_array(4 + uv_set_id)
            self._vertex_data["poly"].set_array(4 + uv_set_id, GeomVertexArrayData(array))

        if 0 in uv_sets_to_restore:
            self.update_vertex_colors()
