from ....base import *


class TriangleSide:

    def __init__(self, geom_data_obj, poly_id, vert_ids):

        self.id = 0
        self.geom_data_obj = geom_data_obj
        self.polygon_id = poly_id
        self._vert_ids = set(vert_ids)  # a set of 2 vertex IDs
        self.start_row_index = 0

    def __hash__(self):

        return hash(tuple(sorted(self._vert_ids)))

    def __eq__(self, other):

        return self._vert_ids == other.vertex_ids

    def __ne__(self, other):

        return self._vert_ids != other.vertex_ids

    @property
    def vertex_ids(self):

        return self._vert_ids

    @vertex_ids.setter
    def vertex_ids(self, vert_ids):

        self._vert_ids = set(vert_ids)  # a set of 2 vertex IDs


class TriangulationMixin:
    """ PolygonEditMixin class mix-in """

    def __init__(self):

        # a dict of (TriangleSide:[apex1_id, apex2_id]) pairs
        self._tmp_tris = {}
        self._tmp_geom = None
        self._tri_change = set()

    def create_triangulation_data(self):

        selected_poly_ids = self._selected_subobj_ids["poly"]

        if not selected_poly_ids:
            return False

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]
        tris = self._tmp_tris

        for poly_id in selected_poly_ids:

            tris[poly_id] = poly_tris = {}
            poly = polys[poly_id]

            for tri_vert_ids in poly:
                for i in range(3):
                    side_vert_ids = (tri_vert_ids[i], tri_vert_ids[i - 2])
                    tri_side = TriangleSide(self, poly_id, side_vert_ids)
                    poly_tris.setdefault(tri_side, []).append(tri_vert_ids[i - 1])

        diagonals = []

        for poly_tris in tris.values():
            for tri_side, apex_ids in poly_tris.items():
                if len(apex_ids) == 2:
                    diagonals.append(tri_side)
                    Mgr.do("add_diagonal", tri_side)

        if not diagonals:
            return False

        # Create a temporary geom for diagonals

        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        geoms = self._geoms
        geoms["poly"]["pickable"].show(picking_mask)

        count = self._data_row_count
        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data_line = GeomVertexData("line_data", vertex_format, Geom.UH_dynamic)
        vertex_data_line.reserve_num_rows(len(diagonals) * 2)
        geom_node_top = self._toplvl_node
        vertex_data_top = geom_node_top.get_geom(0).get_vertex_data()

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(len(diagonals) * 2)
        pos_reader = GeomVertexReader(vertex_data_top, "vertex")
        pos_writer = GeomVertexWriter(vertex_data_line, "vertex")
        col_writer = GeomVertexWriter(vertex_data_line, "color")

        for i, diagonal in enumerate(diagonals):

            diagonal.start_row_index = i * 2
            rows = [verts[vert_id].row_index for vert_id in diagonal.vertex_ids]
            picking_color = get_color_vec(diagonal.id, 254)

            for row in rows:
                pos_reader.set_row(row)
                pos = pos_reader.get_data3()
                pos_writer.add_data3(pos)
                col_writer.add_data4(picking_color)

            lines_prim.add_next_vertices(2)

        lines_geom = Geom(vertex_data_line)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("diagonals_geom")
        geom_node.add_geom(lines_geom)
        diagonals_geom = self.origin.attach_new_node(geom_node)
        diagonals_geom.show_through(render_mask | picking_mask)
        diagonals_geom.set_render_mode_thickness(3)
        diagonals_geom.set_color(.5, .5, .5)
        diagonals_geom.set_light_off()
        diagonals_geom.set_texture_off()
        diagonals_geom.set_material_off()
        diagonals_geom.set_shader_off()
        diagonals_geom.set_attrib(DepthTestAttrib.make(RenderAttrib.M_less_equal))
        diagonals_geom.set_bin("background", 1)
        self._tmp_geom = diagonals_geom

        return True

    def clear_triangulation_data(self):

        picking_mask = Mgr.get("picking_mask")
        self._geoms["poly"]["pickable"].show_through(picking_mask)

        self._tmp_tris = {}

        if self._tmp_geom:
            self._tmp_geom.remove_node()
            self._tmp_geom = None

    def turn_diagonal(self, diagonal):

        # Each diagonal of a polygon connects 2 triangles of that polygon.
        # "Turning" a diagonal means replacing it with a new diagonal whose endpoints
        # are the apexes of those triangles. This results in 2 new triangles that
        # are connected by the new diagonal and whose apexes are the endpoints of
        # the old diagonal.

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]
        poly_id = diagonal.polygon_id
        poly = polys[poly_id]
        sel_data = self._poly_selection_data["selected"]
        poly_start = sel_data.index(poly[0]) * 3
        tris = self._tmp_tris[poly_id]
        old_vert_ids = list(diagonal.vertex_ids)
        new_vert_ids = tris[diagonal]
        del tris[diagonal]
        diagonal.vertex_ids = new_vert_ids
        tris[diagonal] = old_vert_ids

        # for each remaining side of each of the 2 old triangles, replace the
        # corresponding apex with a new one to correctly define the 2 new
        # triangles
        for old_vert_id in old_vert_ids:
            for new_vert_id in new_vert_ids:
                tri_side = TriangleSide(self, poly_id, [old_vert_id, new_vert_id])
                apex_ids = tris[tri_side]
                apex_ids.remove(old_vert_ids[1 - old_vert_ids.index(old_vert_id)])
                apex_ids.append(new_vert_ids[1 - new_vert_ids.index(new_vert_id)])

        quad_to_retriangulate = []
        tris_to_replace = []
        new_tri_data = poly[:]

        for apex_id in new_vert_ids:

            old_tri_vert_ids = set(old_vert_ids + [apex_id])

            for tri_vert_ids in poly:
                if set(tri_vert_ids) == old_tri_vert_ids:
                    tris_to_replace.append(tri_vert_ids)
                    quad_to_retriangulate.append(list(tri_vert_ids))
                    break

        quad_ordered = quad_to_retriangulate[0]
        index1 = quad_ordered.index(old_vert_ids[0])
        index2 = quad_ordered.index(old_vert_ids[1])

        # if both diagonal vertex indices are successive in quad_ordered, the fourth
        # vertex index has to be inserted inbetween them to have all 4 vertices in
        # the correct winding order, otherwise the 4th index can just be appended or
        # prepended
        index = (index1 if index1 > index2 else index2) if abs(index2 - index1) == 1 else 0
        new_vert_id = new_vert_ids[1]
        quad_ordered.insert(index, new_vert_id)
        new_tris_vert_ids = []
        vert_ids = (quad_ordered[index - 2], quad_ordered[index - 1], new_vert_id)
        new_tris_vert_ids.append(vert_ids)
        new_vert_id = new_vert_ids[0]
        vert_ids = (quad_ordered[index - 4], quad_ordered[index - 3], new_vert_id)
        new_tris_vert_ids.append(vert_ids)

        # Update the geoms

        diagonals_geom = self._tmp_geom
        geom_poly_selected = self._geoms["poly"]["selected"]
        geom_node_top = self._toplvl_node
        start_row = diagonal.start_row_index

        # Update the temporary diagonals geom

        vertex_data_line = diagonals_geom.node().modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_line, "vertex")
        pos_writer.set_row(start_row)

        for vert_id in new_vert_ids:
            pos_writer.set_data3(verts[vert_id].get_pos())

        # Update the selected polys geom and top-level geom

        prim_poly_sel = geom_poly_selected.node().modify_geom(0).modify_primitive(0)
        stride = prim_poly_sel.get_index_stride()
        mem_view = memoryview(prim_poly_sel.modify_vertices()).cast("B")
        prim_top = geom_node_top.modify_geom(0).modify_primitive(0)
        array_top = prim_top.modify_vertices()
        view_top = memoryview(array_top).cast("B")

        for vert_ids_to_replace, new_tri_vert_ids in zip(tris_to_replace, new_tris_vert_ids):
            tris_prim = GeomTriangles(Geom.UH_static)
            rows = [verts[vert_id].row_index for vert_id in new_tri_vert_ids]
            tris_prim.reserve_num_vertices(3)
            tris_prim.add_vertices(*rows)
            tris_prim.make_indexed()
            view_tmp = memoryview(tris_prim.get_vertices()).cast("B")
            index = new_tri_data.index(vert_ids_to_replace)
            start_row = index * 3 + poly_start
            start = start_row * stride
            size = 3 * stride
            mem_view[start:start+size] = view_tmp
            new_tri_data[index] = new_tri_vert_ids
            sel_data[start_row // 3] = new_tri_vert_ids

        vert_id = new_tri_data[0][0]
        row_index = verts[vert_id].row_index
        from_size = prim_poly_sel.get_vertex_list().index(row_index) * stride
        vert_id = poly[0][0]
        row_index = verts[vert_id].row_index
        to_size = prim_top.get_vertex_list().index(row_index) * stride
        size = len(poly) * stride
        view_top[to_size:to_size+size] = mem_view[from_size:from_size+size]

        poly.set_triangle_data(new_tri_data)
        self._tri_change = set(self._selected_subobj_ids["poly"])

        prim = self._toplvl_node.get_geom(0).get_primitive(0)
        poly_picking_geom = self._geoms["poly"]["pickable"].node().modify_geom(0)
        poly_picking_geom.set_primitive(0, GeomTriangles(prim))

    def _restore_poly_triangle_data(self, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id
        prop_id = self._unique_prop_ids["poly_tris"]

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

        data_id = self._unique_prop_ids["tri__extra__"]

        time_ids_to_restore = {}
        time_ids = {}
        tris = {}

        # to undo triangulations, determine the time IDs of the triangulatians that
        # need to be restored by checking the data that was stored when triangulatians
        # occurred, at times leading up to the time that is being replaced (the old
        # time)

        for time_id in reversed(prev_time_ids):
            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            time_ids_to_restore.update(subobj_data.get("prev", {}))

        poly_ids = {}

        for poly_id, time_id in time_ids_to_restore.items():

            if poly_id in polys:
                time_ids[poly_id] = time_id
                poly_ids.setdefault(time_id, []).append(poly_id)

        for time_id, ids in poly_ids.items():

            if time_id:

                tri_data = Mgr.do("load_from_history", obj_id, data_id, time_id)["tri_data"]

                for poly_id in ids:
                    tris[poly_id] = tri_data[poly_id]

        # to redo triangulations, retrieve the triangulations that need to be restored
        # from the data that was stored when triangulations occurred, at times leading
        # up to the time that is being restored (the new time)

        for time_id in new_time_ids:

            tri_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            tris.update(tri_data.get("tri_data", {}))

            for poly_id in tri_data.get("prev", {}):
                if poly_id in polys:
                    time_ids[poly_id] = time_id

        # restore the polys' previous triangulation time IDs
        for poly_id, time_id in time_ids.items():
            poly = polys[poly_id]
            poly.set_previous_property_time("tri_data", time_id)

        polys_to_update = {}

        for poly_id, tri_data in tris.items():
            if poly_id in polys:
                poly = polys[poly_id]
                polys_to_update[poly] = tri_data

        # Update geometry structures

        geoms = self._geoms
        geom_poly_selected = geoms["poly"]["selected"].node().modify_geom(0)
        array_selected = geom_poly_selected.modify_primitive(0).modify_vertices()
        stride = array_selected.array_format.stride
        view_selected = memoryview(array_selected).cast("B")
        geom_poly_unselected = geoms["poly"]["unselected"].node().modify_geom(0)
        array_unselected = geom_poly_unselected.modify_primitive(0).modify_vertices()
        view_unselected = memoryview(array_unselected).cast("B")
        geom_node_top = self._toplvl_node.modify_geom(0)
        array_top = geom_node_top.modify_primitive(0).modify_vertices()
        view_top = memoryview(array_top).cast("B")

        poly_sel_data = self._poly_selection_data
        data_selected = poly_sel_data["selected"]
        data_unselected = poly_sel_data["unselected"]

        ordered_polys = self._ordered_polys
        selected_poly_ids = self._selected_subobj_ids["poly"]

        row_offset = 0

        for poly in ordered_polys:

            if poly in polys_to_update:

                tri_data = polys_to_update[poly]

                if not tri_data or tri_data == poly[:]:
                    row_offset += len(poly)
                    continue

                prim = GeomTriangles(Geom.UH_static)
                prim.reserve_num_vertices(len(tri_data) * 3)

                for tri_verts in tri_data:
                    prim.add_vertices(*[verts[vert_id].row_index for vert_id in tri_verts])

                offset = row_offset * stride
                size = len(poly) * stride
                prim.make_indexed()
                from_view = memoryview(prim.get_vertices()).cast("B")
                view_top[offset:offset+size] = from_view

                if poly.id in selected_poly_ids:
                    sel_data = data_selected
                    mem_view = view_selected
                else:
                    sel_data = data_unselected
                    mem_view = view_unselected

                start = sel_data.index(poly[0])

                for i, tri_verts in enumerate(tri_data):
                    sel_data[start + i] = tri_verts

                offset = start * 3 * stride
                mem_view[offset:offset+size] = from_view
                poly.set_triangle_data(tri_data)

            row_offset += len(poly)

        prim = self._toplvl_node.get_geom(0).get_primitive(0)
        poly_picking_geom = geoms["poly"]["pickable"].node().modify_geom(0)
        poly_picking_geom.set_primitive(0, GeomTriangles(prim))


class TriangulationManager:
    """ PolygonEditManager class mix-in """

    def __init__(self):

        self._geom_data_objs = []
        self._excluded_geom_data_objs = []
        self._diagonals = []

        Mgr.accept("add_diagonal", self.__add_diagonal)
        Mgr.add_app_updater("diagonal_turn", self.__init_diagonal_turning_mode)

        add_state = Mgr.add_state
        add_state("diagonal_turning_mode", -10, self.__enter_diagonal_turning_mode,
                  self.__exit_diagonal_turning_mode)

        bind = Mgr.bind_state
        bind("diagonal_turning_mode", "turn diagonal -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("diagonal_turning_mode", "quit diagonal turning", "escape",
             lambda: Mgr.exit_state("diagonal_turning_mode"))
        bind("diagonal_turning_mode", "cancel diagonal turning", "mouse3",
             lambda: Mgr.exit_state("diagonal_turning_mode"))
        bind("diagonal_turning_mode", "turn diagonal", "mouse1",
             self.__turn_diagonal)
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("diagonal_turning_mode", "turn diagonal ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))

        status_data = GD["status"]
        mode_text = "Turn polygon diagonal"
        info_text = "LMB to pick a polygon diagonal to turn; RMB to cancel"
        status_data["turn_diagonal"] = {"mode": mode_text, "info": info_text}

    def __add_diagonal(self, diagonal):

        self._diagonals.append(diagonal)
        diagonal.id = len(self._diagonals)

    def __init_diagonal_turning_mode(self):

        Mgr.exit_states(min_persistence=-99)
        selection = Mgr.get("selection_top")
        geom_data_objs = [obj.geom_obj.geom_data_obj for obj in selection]

        for data_obj in geom_data_objs:
            if data_obj.create_triangulation_data():
                self._geom_data_objs.append(data_obj)
            else:
                self._excluded_geom_data_objs.append(data_obj)

        if self._geom_data_objs:

            for data_obj in self._excluded_geom_data_objs:
                data_obj.set_pickable(False)

            Mgr.enter_state("diagonal_turning_mode")

        else:

            self._excluded_geom_data_objs = []

    def __enter_diagonal_turning_mode(self, prev_state_id, active):

        GD["active_transform_type"] = ""
        Mgr.update_app("active_transform_type", "")
        Mgr.add_task(self._update_cursor, "update_diagonal_turning_cursor")
        Mgr.update_app("status", ["turn_diagonal"])

    def __exit_diagonal_turning_mode(self, next_state_id, active):

        if not active:

            for data_obj in self._geom_data_objs:
                data_obj.clear_triangulation_data()

            for data_obj in self._excluded_geom_data_objs:
                data_obj.set_pickable()

            self._geom_data_objs = []
            self._excluded_geom_data_objs = []
            self._diagonals = []

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self._update_cursor()
                                        # is called
        Mgr.remove_task("update_diagonal_turning_cursor")
        Mgr.set_cursor("main")

    def __turn_diagonal(self):

        if not self._pixel_under_mouse:
            return

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b

        if color_id == 0:
            return

        diagonal = self._diagonals[color_id - 1]
        geom_data_obj = diagonal.geom_data_obj
        geom_data_obj.turn_diagonal(diagonal)
        obj = geom_data_obj.toplevel_obj

        Mgr.do("update_history_time")
        obj_data = {obj.id: geom_data_obj.get_data_to_store("prop_change", "poly_tris")}
        event_descr = f'Turn polygon diagonal of object:\n\n    "{obj.name}"'
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)
