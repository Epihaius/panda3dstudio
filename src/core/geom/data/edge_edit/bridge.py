from ....base import *


class EdgeBridgeBase(BaseObject):

    def __create_bridge_polygon(self, ordered_verts):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        ordered_polys = self._ordered_polys
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges

        poly_verts = []
        poly_edges = []
        poly_tris = []

        merged_vert1, merged_vert2, merged_vert3, merged_vert4 = ordered_verts
        row_index = 0

        # Create the vertices

        def get_new_vertex(merged_vert):

            if len(merged_vert) == 1:

                vert_id = merged_vert.get_id()
                vert = verts[vert_id]

                if not vert.get_edge_ids():
                    # this vertex was newly created to allow segmentation of bridge
                    # polygons; it can become part of the new bridge polygon
                    return vert, vert_id

            return None, None

        pos1 = merged_vert1.get_pos()
        vert1, vert1_id = get_new_vertex(merged_vert1)

        if not vert1:
            vert1 = Mgr.do("create_vert", self, pos1)
            vert1_id = vert1.get_id()
            verts[vert1_id] = vert1
            merged_vert1.append(vert1_id)
            merged_verts[vert1_id] = merged_vert1

        vert1.set_row_index(row_index)
        row_index += 1
        poly_verts.append(vert1)

        if merged_vert2 is merged_vert1:

            pos2 = pos1
            vert2 = None

        else:

            pos2 = merged_vert2.get_pos()
            vert2, vert2_id = get_new_vertex(merged_vert2)

            if not vert2:
                vert2 = Mgr.do("create_vert", self, pos2)
                vert2_id = vert2.get_id()
                verts[vert2_id] = vert2
                merged_vert2.append(vert2_id)
                merged_verts[vert2_id] = merged_vert2

            vert2.set_row_index(row_index)
            row_index += 1
            poly_verts.append(vert2)

        pos3 = merged_vert3.get_pos()
        vert3, vert3_id = get_new_vertex(merged_vert3)

        if not vert3:
            vert3 = Mgr.do("create_vert", self, pos3)
            vert3_id = vert3.get_id()
            verts[vert3_id] = vert3
            merged_vert3.append(vert3_id)
            merged_verts[vert3_id] = merged_vert3

        vert3.set_row_index(row_index)
        row_index += 1
        poly_verts.append(vert3)

        if merged_vert4 is merged_vert3:

            pos4 = pos3
            vert4 = None

        else:

            pos4 = merged_vert4.get_pos()
            vert4, vert4_id = get_new_vertex(merged_vert4)

            if not vert4:
                vert4 = Mgr.do("create_vert", self, pos4)
                vert4_id = vert4.get_id()
                verts[vert4_id] = vert4
                merged_vert4.append(vert4_id)
                merged_verts[vert4_id] = merged_vert4

            vert4.set_row_index(row_index)
            poly_verts.append(vert4)

        # Define triangulation

        poly_tris.append(tuple(vert.get_id() for vert in poly_verts[:3]))

        if len(poly_verts) == 4:
            tri_verts = poly_verts[:]
            del tri_verts[1]
            poly_tris.append(tuple(vert.get_id() for vert in tri_verts))

        # Create the edges

        if vert2:
            edge1 = Mgr.do("create_edge", self, (vert1_id, vert2_id))
            edge1_id = edge1.get_id()
            vert2.add_edge_id(edge1_id)
            edges[edge1_id] = edge1
            poly_edges.append(edge1)

        edge2 = Mgr.do("create_edge", self, (vert2_id if vert2 else vert1_id, vert3_id))
        edge2_id = edge2.get_id()

        if vert2:
            vert2.add_edge_id(edge2_id)

        vert3.add_edge_id(edge2_id)
        edges[edge2_id] = edge2
        poly_edges.append(edge2)

        if vert4:
            edge3 = Mgr.do("create_edge", self, (vert3_id, vert4_id))
            edge3_id = edge3.get_id()
            vert3.add_edge_id(edge3_id)
            vert4.add_edge_id(edge3_id)
            edges[edge3_id] = edge3
            poly_edges.append(edge3)

        edge4 = Mgr.do("create_edge", self, (vert4_id if vert4 else vert3_id, vert1_id))
        edge4_id = edge4.get_id()

        if vert4:
            vert4.add_edge_id(edge4_id)
        else:
            vert3.add_edge_id(edge4_id)

        vert1.add_edge_id(edge4_id)

        if vert2:
            vert1.add_edge_id(edge1_id)
        else:
            vert1.add_edge_id(edge2_id)

        edges[edge4_id] = edge4
        poly_edges.append(edge4)

        def merge_edge(edge):

            border_edge_id = edge.get_id()
            merged_vert1, merged_vert2 = [merged_verts[v_id] for v_id in edge]

            for vert_id in merged_vert1:

                vert = verts[vert_id]

                for edge_id in vert.get_edge_ids():

                    if edge_id not in merged_edges:
                        continue

                    merged_edge = merged_edges[edge_id]

                    if len(merged_edge) > 1:
                        continue

                    vert1_id, vert2_id = edges[edge_id]
                    other_vert_id = vert1_id if merged_verts[vert2_id] is merged_vert1 else vert2_id

                    if merged_verts[other_vert_id] is merged_vert2:
                        merged_edge.append(border_edge_id)
                        merged_edges[border_edge_id] = merged_edge
                        break

                else:

                    continue

                break

            else:

                merged_edge = Mgr.do("create_merged_edge", self, border_edge_id)
                merged_edges[border_edge_id] = merged_edge

        for edge in poly_edges:
            merge_edge(edge)

        poly = Mgr.do("create_poly", self, poly_tris, poly_edges, poly_verts)
        ordered_polys.append(poly)
        polys[poly.get_id()] = poly
        poly.update_center_pos()
        poly.update_normal()
        normal = poly.get_normal().normalized()

        for vert in poly_verts:
            vert.set_normal(normal)

        return poly, poly_edges, poly_verts

    def bridge_edges(self, src_border_edge, dest_border_edge):

        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        selection_ids = self._selected_subobj_ids
        selected_vert_ids = selection_ids["vert"]
        selected_edge_ids = selection_ids["edge"]

        # when edges are selected via polygon, the IDs of selected polys are
        # currently backed up
        if "poly" in self._sel_subobj_ids_backup:

            selected_poly_ids = self._sel_subobj_ids_backup["poly"][:]

            # the current selection (the picked helper poly) may not be made empty,
            # or the call to self.clear_selection() will have no effect and leave
            # the helper poly visible
            if selected_poly_ids:
                self._selected_subobj_ids["poly"] = selected_poly_ids

        else:

            selected_poly_ids = selection_ids["poly"]

        border_segments = ([], [])
        segment_is_border = None

        def get_next_border_edge(edge_id, index):

            vert_id = edges[edge_id][index]
            merged_vert = merged_verts[vert_id]

            for vert_id in merged_vert:

                vert = verts[vert_id]
                merged_edge = merged_edges[vert.get_edge_ids()[index]]

                if len(merged_edge) == 1:
                    return merged_edge

        edge_id = src_border_edge.get_id()

        if edge_id in selected_edge_ids:

            for index in (0, 1):

                src_edge = src_border_edge
                border_segment = border_segments[index]

                while True:

                    edge_id = src_edge[0]
                    src_edge = get_next_border_edge(edge_id, index)

                    if src_edge is src_border_edge:
                        segment_is_border = index

                    if (src_edge is src_border_edge
                            or src_edge.get_id() not in selected_edge_ids):
                        break

                    if src_edge is dest_border_edge:
                        return False

                    border_segment.append(src_edge)

        verts_to_merge = {}
        edges_to_merge = {src_border_edge: dest_border_edge}
        src_end_edges = [src_border_edge, src_border_edge]
        dest_end_edges = [dest_border_edge, dest_border_edge]

        for index in (0, 1):

            dest_edge = dest_border_edge
            border_segment = border_segments[1 - index]

            while border_segment:

                src_edge = border_segment.pop(0)
                edge_id = dest_edge[0]
                dest_edge = get_next_border_edge(edge_id, index)

                if dest_edge is dest_border_edge:
                    border_segments = ([], [])
                    src_end_edges = [src_border_edge, src_border_edge]
                    dest_end_edges = [dest_border_edge, dest_border_edge]
                    break

                if not (dest_edge is src_edge or dest_edge in edges_to_merge):

                    edges_to_merge[src_edge] = dest_edge

                    if segment_is_border is None:
                        src_end_edges[index] = src_edge
                        dest_end_edges[index] = dest_edge

        new_verts = []
        new_edges = []
        new_polys = []

        update_polys_to_transf = False

        bridge_segments = GlobalData["subobj_edit_options"]["edge_bridge_segments"]

        if bridge_segments > 1:

            seg_verts = {}

            def add_segment_vertices(src_vert, dest_vert):

                if src_vert is dest_vert:

                    seg_verts[src_vert] = [src_vert] * (bridge_segments + 1)

                else:

                    seg_verts[src_vert] = new_seg_verts = [src_vert]
                    src_pos = src_vert.get_pos()
                    seg_vec = (dest_vert.get_pos() - src_pos) / bridge_segments

                    for i in range(bridge_segments - 1):
                        pos = src_pos + seg_vec * (i + 1)
                        new_vert = Mgr.do("create_vert", self, pos)
                        vert_id = new_vert.get_id()
                        verts[vert_id] = new_vert
                        new_merged_vert = Mgr.do("create_merged_vert", self, vert_id)
                        merged_verts[vert_id] = new_merged_vert
                        new_seg_verts.append(new_merged_vert)

                    new_seg_verts.append(dest_vert)

        def add_new_subobjects(vert1, vert2, vert3, vert4):

            # define the merged vertices of the bridging polygon(s) in winding order,
            # starting and ending with 2 vertices along the length of the bridge
            ordered_verts = (vert1, vert2, vert3, vert4)
            poly, poly_edges, poly_verts = self.__create_bridge_polygon(ordered_verts)
            new_verts.extend(poly_verts)
            new_edges.extend(poly_edges)
            new_polys.append(poly)

        for src_edge, dest_edge in edges_to_merge.items():

            src_vert1_id, src_vert2_id = edges[src_edge[0]]
            src_vert1 = merged_verts[src_vert1_id]
            src_vert2 = merged_verts[src_vert2_id]
            dest_vert2_id, dest_vert1_id = edges[dest_edge[0]]
            dest_vert1 = merged_verts[dest_vert1_id]
            dest_vert2 = merged_verts[dest_vert2_id]

            for merged_vert in set([src_vert1, src_vert2, dest_vert1, dest_vert2]):
                for vert_id in merged_vert:
                    if verts[vert_id].get_polygon_id() in selected_poly_ids:
                        update_polys_to_transf = True

            if bridge_segments > 1:

                if src_vert1 not in seg_verts:
                    add_segment_vertices(src_vert1, dest_vert1)

                if src_vert2 not in seg_verts:
                    add_segment_vertices(src_vert2, dest_vert2)

                for i in range(bridge_segments):
                    vert1 = seg_verts[src_vert1][i]
                    vert2 = seg_verts[src_vert1][i + 1]
                    vert3 = seg_verts[src_vert2][i + 1]
                    vert4 = seg_verts[src_vert2][i]
                    add_new_subobjects(vert1, vert2, vert3, vert4)

            else:

                add_new_subobjects(src_vert1, dest_vert1, dest_vert2, src_vert2)

        if bridge_segments > 1:
            seg_verts.clear()

        Mgr.do("register_vert_objs", new_verts, restore=False)
        Mgr.do("register_edge_objs", new_edges, restore=False)
        Mgr.do("register_poly_objs", new_polys, restore=False)

        subobj_change = self._subobj_change
        subobj_change["vert"]["created"] = new_verts
        subobj_change["edge"]["created"] = new_edges
        subobj_change["poly"]["created"] = new_polys

        normal_change = self._normal_change
        normal_lock_change = self._normal_lock_change
        shared_normals = self._shared_normals

        tmp_merged_vert = Mgr.do("create_merged_vert", self)
        tmp_merged_edge = Mgr.do("create_merged_edge", self)
        tmp_merged_edge.extend(selected_edge_ids)

        for vert_id in (vert.get_id() for vert in new_verts):

            normal_change.add(vert_id)
            normal_lock_change.add(vert_id)
            shared_normals[vert_id] = Mgr.do("create_shared_normal", self, [vert_id])
            id_set = set(merged_verts[vert_id])

            if not (id_set.isdisjoint(selected_vert_ids) or id_set.issubset(selected_vert_ids)):
                tmp_merged_vert.extend(id_set.difference(selected_vert_ids))

        for edge_id in (edge.get_id() for edge in new_edges):

            id_set = set(merged_edges[edge_id])

            if not (id_set.isdisjoint(selected_edge_ids) or id_set.issubset(selected_edge_ids)):
                tmp_merged_edge.extend(id_set.difference(selected_edge_ids))

        self.clear_selection("edge", update_verts_to_transf=False)

        # Update geometry structures

        vert_count = sum([poly.get_vertex_count() for poly in new_polys])
        old_count = self._data_row_count
        count = old_count + vert_count
        self._data_row_count = count

        geoms = self._geoms
        geom_node_top = self._toplvl_node
        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()
        vertex_data_top.reserve_num_rows(count)
        vertex_data_poly_picking = self._vertex_data["poly_picking"]
        vertex_data_poly_picking.reserve_num_rows(count)
        vertex_data_poly_picking.set_num_rows(count)

        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")
        pos_writer.set_row(old_count)
        col_writer = GeomVertexWriter(vertex_data_poly_picking, "color")
        col_writer.set_row(old_count)
        normal_writer = GeomVertexWriter(vertex_data_top, "normal")
        normal_writer.set_row(old_count)
        sign = -1. if self._owner.has_flipped_normals() else 1.

        poly_type_id = PickableTypes.get_id("poly")

        prev_count = old_count
        verts_by_row = {}
        poly_picking_colors = {}
        sel_data = self._poly_selection_data["unselected"]

        for poly in new_polys:

            for vert in poly.get_vertices():
                vert.offset_row_index(prev_count)
                row = vert.get_row_index()
                verts_by_row[row] = vert

            prev_count += poly.get_vertex_count()

            picking_col_id = poly.get_picking_color_id()
            picking_color = get_color_vec(picking_col_id, poly_type_id)
            poly_picking_colors[poly.get_id()] = picking_color
            sel_data.extend(poly)

        for row in sorted(verts_by_row):
            vert = verts_by_row[row]
            pos = vert.get_pos()
            pos_writer.add_data3f(pos)
            picking_color = poly_picking_colors[vert.get_polygon_id()]
            col_writer.add_data4f(picking_color)
            normal = vert.get_normal()
            normal_writer.add_data3f(normal * sign)

        vertex_data_vert1 = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_vert1.set_num_rows(count)
        vertex_data_vert2 = geoms["vert"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data_vert2.set_num_rows(count)
        vertex_data_normal1 = geoms["normal"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_normal1.set_num_rows(count)
        vertex_data_normal2 = geoms["normal"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data_normal2.set_num_rows(count)
        col_writer1 = GeomVertexWriter(vertex_data_vert1, "color")
        col_writer1.set_row(old_count)
        col_writer2 = GeomVertexWriter(vertex_data_vert2, "color")
        col_writer2.set_row(old_count)
        col_writer3 = GeomVertexWriter(vertex_data_normal2, "color")
        col_writer3.set_row(old_count)

        sel_colors = Mgr.get("subobj_selection_colors")
        color_vert = sel_colors["vert"]["unselected"]
        color_normal = sel_colors["normal"]["unselected"]
        vert_type_id = PickableTypes.get_id("vert")

        for row in sorted(verts_by_row):
            vert = verts_by_row[row]
            picking_color = get_color_vec(vert.get_picking_color_id(), vert_type_id)
            col_writer1.add_data4f(picking_color)
            col_writer2.add_data4f(color_vert)
            col_writer3.add_data4f(color_normal)

        col_array = GeomVertexArrayData(vertex_data_vert1.get_array(1))
        vertex_data_normal1.set_array(1, col_array)

        picking_colors1 = {}
        picking_colors2 = {}
        edge_type_id = PickableTypes.get_id("edge")

        for edge in new_edges:
            row1, row2 = [verts[v_id].get_row_index() for v_id in edge]
            picking_color = get_color_vec(edge.get_picking_color_id(), edge_type_id)
            picking_colors1[row1] = picking_color
            picking_colors2[row2 + count] = picking_color

        vertex_data_edge1 = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_edge2 = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data_edge2.set_num_rows(count * 2)
        vertex_data_tmp = GeomVertexData(vertex_data_edge1)
        vertex_data_tmp.set_num_rows(count)
        col_writer1 = GeomVertexWriter(vertex_data_tmp, "color")
        col_writer1.set_row(old_count)
        col_writer2 = GeomVertexWriter(vertex_data_edge2, "color")
        col_writer2.set_row(old_count)
        color = sel_colors["edge"]["unselected"]

        for row_index in sorted(picking_colors1):
            picking_color = picking_colors1[row_index]
            col_writer1.add_data4f(picking_color)
            col_writer2.add_data4f(color)

        from_array = vertex_data_tmp.get_array(1)
        size = from_array.data_size_bytes
        from_handle = from_array.get_handle()

        vertex_data_tmp = GeomVertexData(vertex_data_edge1)
        array = vertex_data_tmp.modify_array(1)
        stride = array.array_format.get_stride()
        array.modify_handle().set_subdata(0, old_count * stride, bytes())
        vertex_data_tmp.set_num_rows(count)
        col_writer1 = GeomVertexWriter(vertex_data_tmp, "color")
        col_writer1.set_row(old_count)
        col_writer2.set_row(count + old_count)

        for row_index in sorted(picking_colors2):
            picking_color = picking_colors2[row_index]
            col_writer1.add_data4f(picking_color)
            col_writer2.add_data4f(color)

        vertex_data_edge1.set_num_rows(count * 2)
        to_array = vertex_data_edge1.modify_array(1)
        to_handle = to_array.modify_handle()
        to_handle.copy_subdata_from(0, size, from_handle, 0, size)

        from_array = vertex_data_tmp.get_array(1)
        from_handle = from_array.get_handle()
        to_handle.copy_subdata_from(size, size, from_handle, 0, size)

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(count * 2)

        for poly in self._ordered_polys:
            for edge in poly.get_edges():
                row1, row2 = [verts[v_id].get_row_index() for v_id in edge]
                lines_prim.add_vertices(row1, row2 + count)

        geom_node = geoms["edge"]["pickable"].node()
        geom_node.modify_geom(0).set_primitive(0, lines_prim)
        geom_node = geoms["edge"]["sel_state"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomLines(lines_prim))

        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_num_rows(count)

        vertex_data_top = geom_node_top.get_geom(0).get_vertex_data()
        pos_array = vertex_data_top.get_array(0)
        size = pos_array.data_size_bytes
        from_handle = pos_array.get_handle()
        normal_array = vertex_data_top.get_array(2)
        tan_array = vertex_data_top.get_array(3)
        vertex_data_poly_picking.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_vert1.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_vert2.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_normal1.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_normal2.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_normal1.set_array(2, GeomVertexArrayData(normal_array))
        vertex_data_normal2.set_array(2, GeomVertexArrayData(normal_array))
        vertex_data_poly.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_poly.set_array(2, GeomVertexArrayData(normal_array))
        vertex_data_poly.set_array(3, GeomVertexArrayData(tan_array))
        pos_array_edge = GeomVertexArrayData(pos_array.array_format, pos_array.usage_hint)
        pos_array_edge.unclean_set_num_rows(pos_array.get_num_rows() * 2)
        to_handle = pos_array_edge.modify_handle()
        to_handle.copy_subdata_from(0, size, from_handle, 0, size)
        to_handle.copy_subdata_from(size, size, from_handle, 0, size)
        vertex_data_edge1.set_array(0, pos_array_edge)
        vertex_data_edge2.set_array(0, pos_array_edge)

        tris_prim = geom_node_top.modify_geom(0).modify_primitive(0)
        from_start = tris_prim.get_num_vertices()

        for poly in new_polys:
            for vert_ids in poly:
                tris_prim.add_vertices(*[verts[v_id].get_row_index() for v_id in vert_ids])

        from_array = tris_prim.get_vertices()
        stride = from_array.array_format.get_stride()
        from_start *= stride
        size = sum([len(poly) for poly in new_polys]) * stride
        from_handle = from_array.get_handle()
        geom_node = geoms["poly"]["unselected"].node()
        prim = geom_node.modify_geom(0).modify_primitive(0)
        to_array = prim.modify_vertices()
        to_start = to_array.data_size_bytes
        to_handle = to_array.modify_handle()
        to_handle.copy_subdata_from(to_start, size, from_handle, from_start, size)
        geom_node = geoms["poly"]["pickable"].node()
        prim = geom_node.modify_geom(0).modify_primitive(0)
        to_array = prim.modify_vertices()
        to_start = to_array.data_size_bytes
        to_handle = to_array.modify_handle()
        to_handle.copy_subdata_from(to_start, size, from_handle, from_start, size)

        tmp_prim = GeomPoints(Geom.UH_static)
        tmp_prim.reserve_num_vertices(vert_count)
        tmp_prim.add_next_vertices(vert_count)
        tmp_prim.offset_vertices(old_count)
        from_array = tmp_prim.get_vertices()
        size = from_array.data_size_bytes
        from_handle = from_array.get_handle()
        geom_node = geoms["vert"]["pickable"].node()
        prim = geom_node.modify_geom(0).modify_primitive(0)
        to_array = prim.modify_vertices()
        to_start = to_array.data_size_bytes
        to_handle = to_array.modify_handle()
        to_handle.copy_subdata_from(to_start, size, from_handle, 0, size)
        geom_node = geoms["vert"]["sel_state"].node()
        prim = geom_node.modify_geom(0).modify_primitive(0)
        to_array = prim.modify_vertices()
        to_start = to_array.data_size_bytes
        to_handle = to_array.modify_handle()
        to_handle.copy_subdata_from(to_start, size, from_handle, 0, size)
        geom_node = geoms["normal"]["pickable"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomPoints(prim))
        geom_node = geoms["normal"]["sel_state"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomPoints(prim))

        if tmp_merged_vert[:]:
            vert_id = tmp_merged_vert.get_id()
            orig_merged_vert = merged_verts[vert_id]
            merged_verts[vert_id] = tmp_merged_vert
            self.update_selection("vert", [tmp_merged_vert], [], False)
            merged_verts[vert_id] = orig_merged_vert
            self._update_verts_to_transform("vert")

        if tmp_merged_edge[:]:
            edge_id = tmp_merged_edge.get_id()
            orig_merged_edge = merged_edges[edge_id]
            merged_edges[edge_id] = tmp_merged_edge
            self.update_selection("edge", [tmp_merged_edge], [], False)
            merged_edges[edge_id] = orig_merged_edge
            self._update_verts_to_transform("edge")

        if update_polys_to_transf:
            self._update_verts_to_transform("poly")

        self._normal_sharing_change = True
        model = self.get_toplevel_object()

        if model.has_tangent_space():
            tangent_flip, bitangent_flip = model.get_tangent_space_flip()
            self.update_tangent_space(tangent_flip, bitangent_flip, [poly_id])
        else:
            self._is_tangent_space_initialized = False

        return True


class EdgeBridgeManager(BaseObject):

    def __init__(self):

        add_state = Mgr.add_state
        add_state("edge_bridge_mode", -10, self.__enter_bridge_mode,
                  self.__exit_bridge_mode)
        add_state("edge_bridge", -11)

        cancel_bridge = lambda: self._finalize_bridge(cancel=True)
        exit_mode = lambda: Mgr.exit_state("edge_bridge_mode")

        bind = Mgr.bind_state
        bind("edge_bridge_mode", "bridge edges -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("edge_bridge_mode", "bridge edges -> select", "escape", exit_mode)
        bind("edge_bridge_mode", "exit edge bridge mode", "mouse3-up", exit_mode)
        bind("edge_bridge_mode", "bridge edges", "mouse1", self._init_bridge)
        bind("edge_bridge", "quit edge bridge", "escape", cancel_bridge)
        bind("edge_bridge", "cancel edge bridge", "mouse3-up", cancel_bridge)
        bind("edge_bridge", "abort edge bridge", "focus_loss", cancel_bridge)
        bind("edge_bridge", "finalize edge bridge", "mouse1-up", self._finalize_bridge)
        bind("edge_bridge", "bridge edges -> pick edge via poly",
             "mouse1", self._start_dest_edge_picking_via_poly)

        status_data = GlobalData["status_data"]
        mode_text = "Bridge edges"
        info_text = "LMB-drag over a border edge and release LMB over" \
                    " other border edge to create bridge; RMB or <Escape> to end"
        status_data["edge_bridge_mode"] = {"mode": mode_text, "info": info_text}

    def __enter_bridge_mode(self, prev_state_id, is_active):

        if prev_state_id == "edge_bridge":
            return

        if GlobalData["active_transform_type"]:
            GlobalData["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")

        self._mode_id = "bridge"
        Mgr.add_task(self._update_cursor, "update_mode_cursor")
        Mgr.update_app("status", ["edge_bridge_mode"])

    def __exit_bridge_mode(self, next_state_id, is_active):

        if next_state_id == "edge_bridge":
            return

        Mgr.remove_task("update_mode_cursor")
        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self._update_cursor()
                                        # is called
        Mgr.set_cursor("main")

        if next_state_id != "edge_picking_via_poly":
            self._mode_id = ""

    def _init_bridge(self, picked_edge=None):

        if picked_edge:

            edge = picked_edge

        else:

            if not self._pixel_under_mouse:
                return

            r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
            color_id = r << 16 | g << 8 | b
            pickable_type = PickableTypes.get(a)

            if pickable_type == "poly":

                self._picked_poly = Mgr.get("poly", color_id)
                merged_edges = self._picked_poly.get_geom_data_object().get_merged_edges()

                for edge_id in self._picked_poly.get_edge_ids():
                    if len(merged_edges[edge_id]) == 1:
                        break
                else:
                    return

                Mgr.enter_state("edge_picking_via_poly")

                return

            picked_obj = Mgr.get("edge", color_id)
            edge = picked_obj.get_merged_edge() if picked_obj else None

        if not edge or len(edge) > 1:
            return

        model = edge.get_toplevel_object()

        for obj in Mgr.get("selection_top"):
            if obj is not model:
                obj.get_geom_object().get_geom_data_object().set_pickable(False)

        self._src_border_edge = edge
        self._picking_dest_edge = True
        pos = edge.get_center_pos(self.world)
        Mgr.do("start_drawing_rubber_band", pos)
        Mgr.do("enable_view_gizmo", False)
        Mgr.enter_state("edge_bridge")
        Mgr.set_cursor("main")

    def _finalize_bridge(self, cancel=False, picked_edge=None):

        if not cancel:
            self.__bridge_edges(picked_edge)

        src_border_edge = self._src_border_edge

        if src_border_edge:

            model = src_border_edge.get_toplevel_object()

            for obj in Mgr.get("selection_top"):
                if obj is not model:
                    obj.get_geom_object().get_geom_data_object().set_pickable()

        Mgr.do("end_drawing_rubber_band")
        self._picking_dest_edge = False
        Mgr.enter_state("edge_bridge_mode")
        Mgr.set_cursor("main" if self._pixel_under_mouse == VBase4() else "select")
        Mgr.do("enable_view_gizmo")

        self._src_border_edge = None

    def __bridge_edges(self, picked_edge=None):

        src_border_edge = self._src_border_edge

        if not src_border_edge:
            return

        model = src_border_edge.get_toplevel_object()

        if picked_edge:
            dest_border_edge = picked_edge
        else:
            r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
            color_id = r << 16 | g << 8 | b
            picked_obj = Mgr.get("edge", color_id)
            dest_border_edge = picked_obj.get_merged_edge() if picked_obj else None

        if not dest_border_edge or dest_border_edge is src_border_edge or len(dest_border_edge) > 1:
            return

        geom_data_obj = model.get_geom_object().get_geom_data_object()

        if not geom_data_obj.bridge_edges(src_border_edge, dest_border_edge):
            return

        Mgr.do("update_active_selection")
        Mgr.do("update_history_time")

        obj_data = {model.get_id(): geom_data_obj.get_data_to_store("subobj_change")}
        event_descr = "Bridge edges"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)
