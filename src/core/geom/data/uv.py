from ...base import *


class UVEditBase(BaseObject):

    def __init__(self):

        self._has_poly_tex_proj = False
        self._uv_change = set()
        self._copied_uvs = {}
        self._copied_uv_array = None

    def init_uvs(self):

        vertex_data_poly = self._vertex_data["poly"]
        uv_writer = GeomVertexWriter(vertex_data_poly, "texcoord")

        for poly in self._ordered_polys:
            for vert in poly.get_vertices():
                row = vert.get_row_index()
                uv = vert.get_uvs(0)
                uv_writer.set_row(row)
                uv_writer.set_data2f(uv)

        array = vertex_data_poly.get_array(2)
        vertex_data_top = self._geoms["top"][
            "shaded"].node().modify_geom(0).modify_vertex_data()
        vertex_data_top.set_array(2, GeomVertexArrayData(array))

    def project_uvs(self, uv_set_ids=None, project=True, projector=None,
                    toplvl=True, show_poly_sel=True):

        material = self.get_toplevel_object().get_material()

        if not material:
            return

        self._has_poly_tex_proj = project and not toplvl
        render_mask = Mgr.get("render_mask")

        if toplvl:

            geom = self._geoms["top"]["shaded"]
            self._geom_roots["poly"].show(render_mask)
            self._geoms["poly"]["selected"].set_state(
                Mgr.get("poly_selection_state"))

        else:

            geom = self._geoms["poly"]["selected"]

            if project:
                state = "poly_selection_state" + \
                    ("" if show_poly_sel else "_off")
                geom.set_state(Mgr.get(state))
                self._geom_roots["poly"].show_through(render_mask)
            else:
                geom.set_state(Mgr.get("poly_selection_state"))
                self._geom_roots["poly"].show(render_mask)

        self.update_render_mode()

        if not uv_set_ids:
            return

        get_tex_stages = material.get_tex_stages
        tex_stages = [
            ts for uv_id in uv_set_ids for ts in get_tex_stages(uv_id)]

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
        vertex_data_poly = self._vertex_data["poly"]
        uv_readers = {}

        for uv_set_id in uv_set_ids:
            column = "texcoord" if uv_set_id == 0 else "texcoord.%d" % uv_set_id
            uv_readers[uv_set_id] = GeomVertexReader(vertex_data, column)

        if toplvl:

            array = vertex_data.get_array(2 + uv_set_id)
            self._uv_change = verts.iterkeys()

            for vert in verts.itervalues():

                row_index = vert.get_row_index()

                for uv_set_id in uv_set_ids:
                    uv_reader = uv_readers[uv_set_id]
                    uv_reader.set_row(row_index)
                    u, v = uv_reader.get_data2f()
                    vert.set_uvs((u, v), uv_set_id)

        else:

            polys = self._subobjs["poly"]
            vertex_data_tmp = GeomVertexData(vertex_data_poly)
            uv_writers = {}

            for uv_set_id in uv_set_ids:
                column = "texcoord" if uv_set_id == 0 else "texcoord.%d" % uv_set_id
                uv_writers[uv_set_id] = GeomVertexWriter(
                    vertex_data_tmp, column)

            for poly_id in self._selected_subobj_ids["poly"]:

                vert_ids = polys[poly_id].get_vertex_ids()
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

            array = vertex_data_tmp.get_array(2 + uv_set_id)

        vertex_data_top = self._geoms["top"][
            "shaded"].node().modify_geom(0).modify_vertex_data()
        vertex_data_top.set_array(2 + uv_set_id, GeomVertexArrayData(array))
        vertex_data_poly.set_array(2 + uv_set_id, array)

    def apply_uv_edits(self, vert_ids, uv_set_id):

        self._uv_change.update(vert_ids)
        verts = self._subobjs["vert"]
        vertex_data_top = self._geoms["top"][
            "shaded"].node().modify_geom(0).modify_vertex_data()
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_tmp = GeomVertexData(vertex_data_poly)

        column = "texcoord" if uv_set_id == 0 else "texcoord.%d" % uv_set_id
        uv_writer = GeomVertexWriter(vertex_data_tmp, column)

        for vert_id in vert_ids:
            vert = verts[vert_id]
            row_index = vert.get_row_index()
            u, v = vert.get_uvs(uv_set_id)
            uv_writer.set_row(row_index)
            uv_writer.set_data2f(u, v)

        array = vertex_data_tmp.get_array(2 + uv_set_id)
        vertex_data_top.set_array(2 + uv_set_id, GeomVertexArrayData(array))
        vertex_data_poly.set_array(2 + uv_set_id, array)

    def copy_uvs(self, uv_set_id):

        verts = self._subobjs["vert"]

        for vert_id, vert in verts.iteritems():
            self._copied_uvs[vert_id] = vert.get_uvs(uv_set_id)

        vertex_data = self._vertex_data["poly"]
        self._copied_uv_array = GeomVertexArrayData(
            vertex_data.get_array(2 + uv_set_id))

    def paste_uvs(self, uv_set_id):

        verts = self._subobjs["vert"]
        self._uv_change = set(verts.iterkeys())

        for vert_id, vert in verts.iteritems():
            vert.set_uvs(self._copied_uvs[vert_id], uv_set_id)

        array = self._copied_uv_array
        vertex_data_top = self._geoms["top"][
            "shaded"].node().modify_geom(0).modify_vertex_data()
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_top.set_array(2 + uv_set_id, GeomVertexArrayData(array))
        vertex_data_poly.set_array(2 + uv_set_id, array)

    def clear_copied_uvs(self):

        self._copied_uvs = {}
        self._copied_uv_array = None

    def get_uv_change(self):

        return self._uv_change

    def _restore_uvs(self, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = "uvs"

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

        data_id = "uv_data"

        time_ids_to_restore = {}
        time_ids = {}
        uv_data = {}

        # to undo UV-mapping, determine the time IDs of the UV-mappings that
        # need to be restored by checking the data that was stored when mappings
        # occurred, at times leading up to the time that is being replaced (the old
        # time)

        uv_set_ids = {}

        for time_id in prev_time_ids[::-1]:

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
                uv_set_ids.setdefault(vert_id, set()).update(
                    restored_uv_data.get(vert_id, {}).iterkeys())

        vert_ids = {}

        for vert_id, time_id in time_ids_to_restore.iteritems():
            if vert_id in verts:
                time_ids[vert_id] = time_id
                vert_ids.setdefault(time_id, []).append(vert_id)

        for time_id, ids in vert_ids.iteritems():

            if time_id:

                subobj_data = Mgr.do("load_from_history",
                                     obj_id, data_id, time_id)

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

            for vert_id, uvs in restored_uv_data.iteritems():
                if vert_id in uv_set_ids:
                    uv_set_ids[vert_id].update(uvs.iterkeys())

            uv_data.update(restored_uv_data)

            for vert_id in subobj_data.get("prev", {}):
                if vert_id in verts:
                    time_ids[vert_id] = time_id

        # restore the verts' previous UV-mapping time IDs
        for vert_id, time_id in time_ids.iteritems():
            verts[vert_id].set_previous_property_time("uvs", time_id)

        vertex_data_top = self._geoms["top"][
            "shaded"].node().modify_geom(0).modify_vertex_data()
        uv_writers = {0: GeomVertexWriter(vertex_data_top, "texcoord")}

        for uv_set_id in range(1, 8):
            uv_writers[uv_set_id] = GeomVertexWriter(
                vertex_data_top, "texcoord.%d" % uv_set_id)

        uv_sets_to_restore = set()

        for vert_id, uvs in uv_data.iteritems():

            if vert_id in verts:

                vert = verts[vert_id]
                row = vert.get_row_index()

                for uv_set_id, uv in uvs.iteritems():
                    uv_writer = uv_writers[uv_set_id]
                    uv_writer.set_row(row)
                    uv_writer.set_data2f(uv)
                    uv_sets_to_restore.add(uv_set_id)

                vert.set_uvs(uvs)

        for uv_set_id in uv_sets_to_restore:
            array = vertex_data_top.get_array(2 + uv_set_id)
            self._vertex_data["poly"].set_array(
                2 + uv_set_id, GeomVertexArrayData(array))
