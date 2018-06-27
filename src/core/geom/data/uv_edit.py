from ...base import *


class UVEditBase(BaseObject):

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
            uv_writer = GeomVertexWriter(vertex_data_poly, "texcoord.{:d}".format(i))
            uv_writers.append(uv_writer)

        for poly in self._ordered_polys:

            for vert in poly.get_vertices():

                row = vert.get_row_index()
                uvs = vert.get_uvs()

                for uv_set_id, uv in uvs.items():
                    uv_writer = uv_writers[uv_set_id]
                    uv_writer.set_row(row)
                    uv_writer.set_data2f(uv)

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

        obj_id = self.get_toplevel_object().get_id()
        prop_id = self._unique_prop_ids["uv_set_names"]
        data = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)
        self._uv_set_names = data

    def create_tex_seams(self, uv_set_id, seam_edge_ids, color):

        self._tex_seam_edge_ids[uv_set_id] = seam_edge_ids
        edge_geom = self._geoms["edge"]["pickable"]
        edge_prims = self._edge_prims
        render_masks = Mgr.get("render_masks")["all"]
        picking_masks = Mgr.get("picking_masks")["all"]
        all_masks = render_masks | picking_masks

        if self._tex_seam_geom:
            seam_geom = self._tex_seam_geom
            edge_prim = edge_prims["main"]
        else:
            seam_geom = edge_geom.copy_to(edge_geom)
            seam_geom.set_color(color)
            seam_geom.show(all_masks)
            self._tex_seam_geom = seam_geom
            edge_prim = GeomLines(edge_geom.node().get_geom(0).get_primitive(0))
            edge_prims["main"] = edge_prim

        edge_prim = GeomLines(edge_prim)
        seam_prim = GeomLines(edge_prim)

        tmp_merged_edge = Mgr.do("create_merged_edge", self)

        for edge_id in seam_edge_ids:
            tmp_merged_edge.append(edge_id)

        row_indices = tmp_merged_edge.get_start_row_indices()
        array = edge_prim.modify_vertices()
        stride = array.get_array_format().get_stride()
        edge_handle = array.modify_handle()
        rows = edge_prim.get_vertex_list()[::2]
        data_rows = sorted((rows.index(i) * 2 for i in row_indices), reverse=True)
        data = ""

        for start in data_rows:
            data += edge_handle.get_subdata(start * stride, stride * 2)
            edge_handle.set_subdata(start * stride, stride * 2, "")

        seam_prim.modify_vertices().modify_handle().set_data(data)
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

        row_indices = tmp_merged_edge.get_start_row_indices()
        array = edge_prim.modify_vertices()
        stride = array.get_array_format().get_stride()
        edge_handle = array.modify_handle()
        rows = edge_prim.get_vertex_list()[::2]
        data_rows = sorted((rows.index(i) * 2 for i in row_indices), reverse=True)
        data = ""

        for start in data_rows:
            data += edge_handle.get_subdata(start * stride, stride * 2)
            edge_handle.set_subdata(start * stride, stride * 2, "")

        seam_handle = seam_prim.modify_vertices().modify_handle()
        seam_handle.set_data(seam_handle.get_data() + data)

    def remove_tex_seam_edges(self, uv_set_id, edge_ids):

        seam_edge_ids = self._tex_seam_edge_ids[uv_set_id]
        selected_edge_ids = self._selected_subobj_ids["edge"]
        merged_edges = self._merged_edges
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
            edge_id = tmp_merged_edge1.get_id()
            orig_merged_edge = merged_edges[edge_id]
            merged_edges[edge_id] = tmp_merged_edge1
            self.update_selection("edge", [tmp_merged_edge1], [], False)
            merged_edges[edge_id] = orig_merged_edge

        if tmp_merged_edge2[:]:
            edge_id = tmp_merged_edge2.get_id()
            orig_merged_edge = merged_edges[edge_id]
            merged_edges[edge_id] = tmp_merged_edge2
            self.update_selection("edge", [], [tmp_merged_edge2], False)
            merged_edges[edge_id] = orig_merged_edge

        edge_prim = self._edge_prims[uv_set_id]
        seam_prim = self._tex_seam_prims[uv_set_id]

        tmp_merged_edge = Mgr.do("create_merged_edge", self)

        for edge_id in edge_ids:
            tmp_merged_edge.append(edge_id)

        row_indices = tmp_merged_edge.get_start_row_indices()
        array = seam_prim.modify_vertices()
        stride = array.get_array_format().get_stride()
        seam_handle = array.modify_handle()
        rows = seam_prim.get_vertex_list()[::2]
        data_rows = sorted((rows.index(i) * 2 for i in row_indices), reverse=True)
        data = ""

        for start in data_rows:
            data += seam_handle.get_subdata(start * stride, stride * 2)
            seam_handle.set_subdata(start * stride, stride * 2, "")

        edge_handle = edge_prim.modify_vertices().modify_handle()
        edge_handle.set_data(edge_handle.get_data() + data)

    def set_selected_tex_seam_edge(self, uv_set_id, colors, edge, is_selected=True):

        if not uv_set_id in self._tex_seam_edge_ids:
            return

        if edge.get_id() in self._tex_seam_edge_ids[uv_set_id]:
            sel_colors = colors
        else:
            sel_colors = None

        if is_selected:
            self.update_selection("edge", [edge], [], False, sel_colors)
        else:
            self.update_selection("edge", [], [edge], False, sel_colors)

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

        sel_state_geom = self._geoms["edge"]["sel_state"]
        vertex_data = sel_state_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")

        for row_index in tmp_merged_edge.get_row_indices():
            col_writer.set_row(row_index)
            col_writer.set_data4f(color)

    def update_tex_seam_selection(self, edge_ids, color):

        tmp_merged_edge = Mgr.do("create_merged_edge", self)

        for edge_id in edge_ids:
            tmp_merged_edge.append(edge_id)

        sel_state_geom = self._geoms["edge"]["sel_state"]
        vertex_data = sel_state_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")

        for row_index in tmp_merged_edge.get_row_indices():
            col_writer.set_row(row_index)
            col_writer.set_data4f(color)

    def set_tex_seams(self, uv_set_id):

        seam_geom = self._tex_seam_geom

        if not seam_geom:
            return

        seam_geom.node().modify_geom(0).set_primitive(0, self._tex_seam_prims[uv_set_id])
        edge_geom = self._geoms["edge"]["pickable"]
        edge_geom.node().modify_geom(0).set_primitive(0, self._edge_prims[uv_set_id])

    def show_tex_seams(self, obj_level):

        seam_geom = self._tex_seam_geom

        if not seam_geom:
            return

        render_masks = Mgr.get("render_masks")["all"]

        if obj_level == "edge":
            seam_geom.show(render_masks)
        else:
            seam_geom.show_through(render_masks)

    def destroy_tex_seams(self, uv_set_id):

        if self._tex_seam_geom:
            self._tex_seam_geom.remove_node()
            self._tex_seam_geom = None
            edge_prim = self._edge_prims["main"]
            edge_geom = self._geoms["edge"]["pickable"]
            edge_geom.node().modify_geom(0).set_primitive(0, edge_prim)
            del self._edge_prims["main"]

        del self._edge_prims[uv_set_id]
        del self._tex_seam_prims[uv_set_id]
        del self._tex_seam_edge_ids[uv_set_id]

    def project_uvs(self, uv_set_ids=None, project=True, projector=None,
                    toplvl=True, show_poly_sel=True):

        material = self.get_toplevel_object().get_material()

        if not material:
            return

        self._has_poly_tex_proj = project and not toplvl
        render_masks = Mgr.get("render_masks")["all"]

        if toplvl:

            geom = self._toplvl_geom
            self._geoms["poly"]["unselected"].hide(render_masks)
            self._geoms["poly"]["selected"].hide(render_masks)
            self._geoms["poly"]["selected"].set_state(Mgr.get("poly_selection_state"))

        else:

            geom = self._geoms["poly"]["selected"]

            if project:
                state = "poly_selection_state" + ("" if show_poly_sel else "_off")
                geom.set_state(Mgr.get(state))
                geom.show(render_masks)
                self._geoms["poly"]["unselected"].show(render_masks)
            else:
                geom.set_state(Mgr.get("poly_selection_state"))
                geom.hide(render_masks)
                self._geoms["poly"]["unselected"].hide(render_masks)

        self.update_render_mode(self.get_toplevel_object().is_selected())

        if not uv_set_ids:
            return

        get_tex_stages = material.get_tex_stages
        tex_stages = [ts for uv_id in uv_set_ids for ts in get_tex_stages(uv_id)]

        if project:
            for tex_stage in tex_stages:
                geom.set_tex_gen(tex_stage, TexGenAttrib.M_world_position)
                geom.set_tex_projector(tex_stage, self.world, projector)
        else:
            for tex_stage in tex_stages:
                geom.clear_tex_gen(tex_stage)
                geom.clear_tex_projector(tex_stage)

    def apply_uv_projection(self, vertex_data, uv_set_ids, toplvl=True):

        verts = self._subobjs["vert"]
        model = self.get_toplevel_object()
        tangent_space_needs_update = 0 in uv_set_ids and model.has_tangent_space()
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        uv_readers = {}

        for uv_set_id in uv_set_ids:
            column = "texcoord" if uv_set_id == 0 else "texcoord.{:d}".format(uv_set_id)
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

                row_index = vert.get_row_index()

                for uv_set_id in uv_set_ids:
                    uv_reader = uv_readers[uv_set_id]
                    uv_reader.set_row(row_index)
                    u, v = uv_reader.get_data2f()
                    vert.set_uvs((u, v), uv_set_id)

        else:

            polys = self._subobjs["poly"]
            uv_writers = {}

            for uv_set_id in uv_set_ids:
                column = "texcoord" if uv_set_id == 0 else "texcoord.{:d}".format(uv_set_id)
                uv_writers[uv_set_id] = GeomVertexWriter(vertex_data_top, column)

            if tangent_space_needs_update:
                polys_to_update = self._selected_subobj_ids["poly"][:]

            for poly_id in self._selected_subobj_ids["poly"]:

                poly = polys[poly_id]
                vert_ids = poly.get_vertex_ids()
                self._uv_change.update(vert_ids)

                for vert_id in vert_ids:

                    vert = verts[vert_id]
                    row_index = vert.get_row_index()

                    for uv_set_id in uv_set_ids:
                        uv_reader = uv_readers[uv_set_id]
                        uv_writer = uv_writers[uv_set_id]
                        uv_reader.set_row(row_index)
                        u, v = uv_reader.get_data2f()
                        vert.set_uvs((u, v), uv_set_id)
                        uv_writer.set_row(row_index)
                        uv_writer.set_data2f(u, v)

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
            self._is_tangent_space_initialized = False

        if 0 in uv_set_ids:

            material = model.get_material()

            if material:

                vert_color_map = material.get_tex_map("vertex color")
                texture = vert_color_map.get_texture()

                if vert_color_map.is_active() and texture:
                    self.bake_texture(texture)

    def apply_uv_edits(self, vert_ids, uv_set_id):

        self._uv_change.update(vert_ids)
        verts = self._subobjs["vert"]
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data_poly = self._vertex_data["poly"]

        column = "texcoord" if uv_set_id == 0 else "texcoord.{:d}".format(uv_set_id)
        uv_writer = GeomVertexWriter(vertex_data_top, column)

        for vert_id in vert_ids:
            vert = verts[vert_id]
            row_index = vert.get_row_index()
            u, v = vert.get_uvs(uv_set_id)
            uv_writer.set_row(row_index)
            uv_writer.set_data2f(u, v)

        array = vertex_data_top.get_array(4 + uv_set_id)
        vertex_data_poly.set_array(4 + uv_set_id, GeomVertexArrayData(array))

        if uv_set_id == 0:

            model = self.get_toplevel_object()

            if model.has_tangent_space():
                polys_to_update = set(verts[vert_id].get_polygon_id() for vert_id in vert_ids)
                tangent_flip, bitangent_flip = model.get_tangent_space_flip()
                self.update_tangent_space(tangent_flip, bitangent_flip, polys_to_update)
            else:
                self._is_tangent_space_initialized = False

            material = model.get_material()

            if material:

                vert_color_map = material.get_tex_map("vertex color")
                texture = vert_color_map.get_texture()

                if vert_color_map.is_active() and texture:
                    self.bake_texture(texture)

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

            model = self.get_toplevel_object()

            if model.has_tangent_space():
                model.update_tangent_space()
            else:
                self._is_tangent_space_initialized = False

            material = model.get_material()

            if material:

                vert_color_map = material.get_tex_map("vertex color")
                texture = vert_color_map.get_texture()

                if vert_color_map.is_active() and texture:
                    self.bake_texture(texture)

    def clear_copied_uvs(self):

        self._copied_uvs = {}
        self._copied_uv_array = None

    def get_uv_change(self):

        return self._uv_change

    def _restore_uvs(self, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()
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
            uv_writers[uv_set_id] = GeomVertexWriter(vertex_data_top, "texcoord.{:d}".format(uv_set_id))

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
                row = vert.get_row_index()

                for uv_set_id, uv in uvs.items():
                    uv_writer = uv_writers[uv_set_id]
                    uv_writer.set_row(row)
                    uv_writer.set_data2f(uv)
                    uv_sets_to_restore.add(uv_set_id)

                vert.set_uvs(uvs)

        for uv_set_id in uv_sets_to_restore:
            array = vertex_data_top.get_array(4 + uv_set_id)
            self._vertex_data["poly"].set_array(4 + uv_set_id, GeomVertexArrayData(array))

        if 0 in uv_sets_to_restore:

            material = self.get_toplevel_object().get_material()

            if material:

                vert_color_map = material.get_tex_map("vertex color")
                texture = vert_color_map.get_texture()

                if vert_color_map.is_active() and texture:
                    self.bake_texture(texture)
