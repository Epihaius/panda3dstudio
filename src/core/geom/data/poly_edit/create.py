from ....base import *


class CreationBase(BaseObject):

    def prepare_poly_creation(self):

        # Make the vertices pickable at polygon level instead of the polygons, to
        # assist with polygon creation

        picking_masks = Mgr.get("picking_masks")["all"]
        geoms = self._geoms
        geoms["vert"]["pickable"].show_through(picking_masks)
        geoms["poly"]["pickable"].show(picking_masks)

    def init_poly_creation(self):

        origin = self._origin
        geoms = self._geoms
        render_masks = Mgr.get("render_masks")

        # Create temporary geometry

        tmp_geoms = {}
        tmp_data = {"geoms": tmp_geoms}

        vertex_format_vert = GeomVertexFormat.get_v3()
        vertex_data_vert = GeomVertexData("vert_data", vertex_format_vert, Geom.UH_dynamic)
        vertex_format_line = GeomVertexFormat.get_v3cp()
        vertex_data_line = GeomVertexData("line_data", vertex_format_line, Geom.UH_dynamic)
        vertex_format_tri = GeomVertexFormat.get_v3n3()
        vertex_data_tri = GeomVertexData("tri_data", vertex_format_tri, Geom.UH_dynamic)

        # Create the first vertex of the first triangle

        vertex_data_tri.set_num_rows(1)
        pos_writer = GeomVertexWriter(vertex_data_tri, "vertex")
        pos_writer.add_data3f(0., 0., 0.)
        normal_writer = GeomVertexWriter(vertex_data_tri, "normal")
        normal_writer.add_data3f(0., 0., 0.)

        # Create a temporary geom for new vertices

        points_prim = GeomPoints(Geom.UH_static)
        point_geom = Geom(vertex_data_vert)
        point_geom.add_primitive(points_prim)
        geom_node = GeomNode("new_vertices_geom")
        geom_node.add_geom(point_geom)
        new_vert_geom = geoms["vert"]["pickable"].attach_new_node(geom_node)
        new_vert_geom.show_through(render_masks["all"])
        new_vert_geom.set_color(1., 1., 0., 1.)
        new_vert_geom.set_render_mode_thickness(7)
        new_vert_geom.set_light_off()
        new_vert_geom.set_texture_off()
        new_vert_geom.set_material_off()
        tmp_geoms["vert"] = new_vert_geom

        # Create a temporary geom for edges

        lines_prim = GeomLines(Geom.UH_static)
        lines_geom = Geom(vertex_data_line)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("edges_geom")
        geom_node.add_geom(lines_geom)
        edge_geom = origin.attach_new_node(geom_node)
        edge_geom.show_through(render_masks["all"])
        edge_geom.set_render_mode_thickness(3)
        edge_geom.set_color_off()
        edge_geom.set_light_off()
        edge_geom.set_texture_off()
        edge_geom.set_material_off()
        edge_geom.set_shader_off()
        tmp_geoms["edge"] = edge_geom
        edge_geom.set_attrib(DepthTestAttrib.make(RenderAttrib.M_less_equal))
        edge_geom.set_bin("background", 1)

        # Create a temporary geom for the new polygon

        tris_prim = GeomTriangles(Geom.UH_static)
        geom = Geom(vertex_data_tri)
        geom.add_primitive(tris_prim)
        geom_node = GeomNode("new_polygon_geom")
        geom_node.add_geom(geom)
        new_poly_geom = origin.attach_new_node(geom_node)
        new_poly_geom.set_texture_off()
        tmp_geoms["poly"] = new_poly_geom

        # store all temporary normals of the polygon
        tmp_data["normals"] = [Vec3()]

        # store the indices of the shared vertices for every new triangle
        tmp_data["shared_verts"] = []

        # store the already existing vertices of this GeomDataObject that the new
        # polygon will be merged with (these have to be MergedVertex objects)
        tmp_data["owned_verts"] = {}

        # store the positions of all vertices that the new polygon will contain
        tmp_data["vert_pos"] = []

        # store the vertex geom row indices
        tmp_data["vert_geom_rows"] = []

        # store the indices of all vertices that the new polygon will contain, in
        # the winding order needed to correctly define the normals and visibility of
        # the triangles
        tmp_data["vert_indices"] = [[0, 1, 2]]

        # store the index of the first vertex to be used to define the next triangle;
        # that vertex will be used together with the other shared vertex and the one
        # currently under the mouse
        tmp_data["start_index"] = 0
        tmp_data["start_index_prev"] = 0

        # keep track of whether or not the normal of the new polygon will be flipped,
        # relative to the automatically computed direction
        tmp_data["flip_normal"] = False

        self._tmp_data = tmp_data

    def add_new_poly_vertex(self, vertex=None, point=None):

        tmp_data = self._tmp_data

        last_index = len(tmp_data["vert_pos"])

        if vertex:

            vert_id = vertex.get_id()

            if vert_id in self._subobjs["vert"]:

                merged_vert = self._merged_verts[vert_id]

                if merged_vert.is_border_vertex():
                    tmp_data["owned_verts"][last_index] = merged_vert

                pos = vertex.get_pos()

            else:

                pos = vertex.get_pos(self._origin)

        else:

            grid_origin = Mgr.get(("grid", "origin"))
            pos = self._origin.get_relative_point(grid_origin, point)

            geom = tmp_data["geoms"]["vert"].node().modify_geom(0)
            vertex_data = geom.modify_vertex_data()
            row = vertex_data.get_num_rows()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(row)
            pos_writer.add_data3f(pos)
            point_prim = geom.modify_primitive(0)
            point_prim.add_vertex(row)
            tmp_data["vert_geom_rows"].append(last_index)

        tmp_data["vert_pos"].append(pos)

        geom = tmp_data["geoms"]["poly"].node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.set_row(last_index)
        pos_writer.set_data3f(pos)
        pos_writer.add_data3f(pos)
        normal_writer = GeomVertexWriter(vertex_data, "normal")
        normal_writer.set_row(last_index)
        normal_writer.set_data3f(0., 0., 0.)
        normal_writer.add_data3f(0., 0., 0.)

        if last_index == 1:

            if tmp_data["flip_normal"]:
                geom.reverse_in_place()

            tris_prim = geom.modify_primitive(0)
            tris_prim.add_next_vertices(3)

            if tmp_data["flip_normal"]:
                geom.reverse_in_place()

        elif last_index > 1:

            start_index = tmp_data["start_index"]
            index2 = last_index - 1 if start_index == last_index else last_index
            index3 = last_index + 1
            tmp_data["shared_verts"].append([start_index, tmp_data["start_index_prev"]])
            prev_indices = tmp_data["vert_indices"][-1]
            i1 = prev_indices.index(start_index)
            i2 = prev_indices.index(index2)

            # to obtain the correct normal and visibility of the new triangle (so it
            # appears to form a contiguous surface with the previous triangle), the
            # indices of the vertices that define the edge shared with the previously
            # created triangle need to be used in reverse order (because these vertices
            # are used with a new third vertex that lies on the other side of the
            # shared edge, compared to the third vertex of the previous
            # triangle)
            if abs(i2 - i1) == 1:
                indices = [prev_indices[max(i1, i2)], prev_indices[min(i1, i2)], index3]
            else:
                # the indices were not listed consecutively; since there are only 3
                # indices in the list, this means that, if the list were to be rotated,
                # they *would* follow each other directly, with their order reversed, so
                # they are already in the needed order
                indices = [prev_indices[min(i1, i2)], prev_indices[max(i1, i2)], index3]

            tmp_data["vert_indices"].append(indices)

            if tmp_data["flip_normal"]:
                geom.reverse_in_place()

            tris_prim = geom.modify_primitive(0)
            tris_prim.add_vertices(*indices)

            if tmp_data["flip_normal"]:
                geom.reverse_in_place()

            pos1, pos2, pos3 = [tmp_data["vert_pos"][i] for i in prev_indices]
            normal = V3D(pos2 - pos1) ** V3D(pos3 - pos2)
            normal += tmp_data["normals"][-1]

            tmp_data["normals"].append(Vec3(normal))
            normal.normalize()

            if tmp_data["flip_normal"]:
                normal *= -1.

            normal_writer.set_row(0)
            sign = -1. if self._owner.has_flipped_normals() else 1.

            for i in range(last_index):
                normal_writer.set_data3f(normal * sign)

        edge_geom = tmp_data["geoms"]["edge"].node().modify_geom(0)
        vertex_data = edge_geom.modify_vertex_data()
        count = vertex_data.get_num_rows()
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.set_row(count)
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(count)
        edge_prim = edge_geom.modify_primitive(0)

        if last_index:
            start_index = tmp_data["start_index"]
            index2 = last_index - 1 if start_index == last_index else last_index
            start_pos = tmp_data["vert_pos"][start_index]
            pos2 = tmp_data["vert_pos"][index2]
            pos_writer.add_data3f(start_pos)
            pos_writer.add_data3f(pos)
            pos_writer.add_data3f(pos2)
            pos_writer.add_data3f(pos)
            col_writer.add_data4f(.5, .5, .5, 1.)
            col_writer.add_data4f(.5, .5, .5, 1.)
            col_writer.add_data4f(1., 1., 0., 1.)
            col_writer.add_data4f(1., 1., 0., 1.)
            edge_prim.add_vertices(count, count + 1, count + 2, count + 3)
        else:
            pos_writer.add_data3f(pos)
            pos_writer.add_data3f(pos)
            col_writer.add_data4f(1., 1., 0., 1.)
            col_writer.add_data4f(1., 1., 0., 1.)
            edge_prim.add_vertices(count, count + 1)

    def remove_new_poly_vertex(self):

        tmp_data = self._tmp_data

        last_index = len(tmp_data["vert_pos"]) - 1

        if not last_index:
            return False

        if last_index > 1:
            del tmp_data["normals"][-1]

        del tmp_data["vert_pos"][-1]

        if last_index in tmp_data["vert_geom_rows"]:
            geom = tmp_data["geoms"]["vert"].node().modify_geom(0)
            vertex_data = geom.modify_vertex_data()
            row_count = vertex_data.get_num_rows() - 1
            vertex_data.set_num_rows(row_count)
            geom.modify_primitive(0).modify_vertices().set_num_rows(row_count)
            tmp_data["vert_geom_rows"].remove(last_index)

        if last_index in tmp_data["owned_verts"]:
            del tmp_data["owned_verts"][last_index]

        geom = tmp_data["geoms"]["poly"].node().modify_geom(0)

        if tmp_data["flip_normal"]:
            geom.reverse_in_place()

        geom.modify_vertex_data().set_num_rows(last_index + 1)
        tris_prim = geom.modify_primitive(0)

        if last_index > 1:
            del tmp_data["vert_indices"][-1]
            array = tris_prim.modify_vertices()
            array.set_num_rows(array.get_num_rows() - 3)
        else:
            tris_prim.modify_vertices().set_num_rows(0)

        if tmp_data["flip_normal"]:
            geom.reverse_in_place()

        if tmp_data["shared_verts"]:
            tmp_data["start_index"], tmp_data["start_index_prev"] = tmp_data["shared_verts"][-1]
            del tmp_data["shared_verts"][-1]

        edge_geom = tmp_data["geoms"]["edge"].node().modify_geom(0)
        vertex_data = edge_geom.modify_vertex_data()
        count = vertex_data.get_num_rows() - 4
        vertex_data.set_num_rows(count)
        edge_geom.modify_primitive(0).modify_vertices().set_num_rows(count)

        return True

    def switch_new_poly_start_vertex(self):

        # When <Shift> is pressed, switch between the two vertices shared by the
        # last created triangle and the temporary triangle to determine which one
        # will be used as the new starting vertex. This effectively allows the user
        # to control the triangulation (to some degree) of the new polygon while
        # creating it.

        tmp_data = self._tmp_data

        last_index = len(tmp_data["vert_pos"]) - 1

        if not last_index:
            return

        if tmp_data["start_index"] == last_index:
            tmp_data["start_index"], tmp_data["start_index_prev"] = \
                tmp_data["start_index_prev"], tmp_data["start_index"]
        else:
            tmp_data["start_index_prev"] = tmp_data["start_index"]
            tmp_data["start_index"] = last_index

        edge_geom = tmp_data["geoms"]["edge"].node().modify_geom(0)
        vertex_data = edge_geom.modify_vertex_data()
        count = vertex_data.get_num_rows()
        col_writer = GeomVertexRewriter(vertex_data, "color")
        col_writer.set_row(count - 4)

        if col_writer.get_data4f() == VBase4(1., 1., 0., 1.):
            col_writer.set_data4f(.5, .5, .5, 1.)
            col_writer.set_data4f(.5, .5, .5, 1.)
            col_writer.set_data4f(1., 1., 0., 1.)
            col_writer.set_data4f(1., 1., 0., 1.)
        else:
            col_writer.set_data4f(1., 1., 0., 1.)
            col_writer.set_data4f(1., 1., 0., 1.)
            col_writer.set_data4f(.5, .5, .5, 1.)
            col_writer.set_data4f(.5, .5, .5, 1.)

    def flip_new_poly_normal(self):

        # When <Ctrl> is pressed, flip the normal of the new polygon.

        tmp_data = self._tmp_data

        if len(tmp_data["vert_pos"]) < 2:
            return

        tmp_data["flip_normal"] = not tmp_data["flip_normal"]

        poly_geom = tmp_data["geoms"]["poly"].node().modify_geom(0)
        vertex_data = poly_geom.modify_vertex_data()
        vertex_data = vertex_data.reverse_normals()
        poly_geom.set_vertex_data(vertex_data)
        poly_geom.reverse_in_place()

    def update_new_polygon(self, point):

        tmp_data = self._tmp_data

        grid_origin = Mgr.get(("grid", "origin"))
        pos = self._origin.get_relative_point(grid_origin, point)

        last_index = len(tmp_data["vert_pos"]) - 1

        if last_index > 0:

            geom = tmp_data["geoms"]["poly"].node().modify_geom(0)
            vertex_data = geom.modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(last_index + 1)
            pos_writer.set_data3f(pos)

            if last_index == 1:

                indices = tmp_data["vert_indices"][-1]
                points = [tmp_data["vert_pos"][i] for i in indices[:2]]
                points.append(pos)
                plane = Plane(*points)
                normal = plane.get_normal()
                normal.normalize()

                if tmp_data["flip_normal"]:
                    normal *= -1.

                normal_writer = GeomVertexWriter(vertex_data, "normal")
                sign = -1. if self._owner.has_flipped_normals() else 1.

                for row_index in indices:
                    normal_writer.set_row(row_index)
                    normal_writer.set_data3f(normal * sign)

        geom = tmp_data["geoms"]["edge"].node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        count = vertex_data.get_num_rows()
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.set_row(count - 1)
        pos_writer.set_data3f(pos)

        if last_index > 0:
            pos_writer.set_row(count - 3)
            pos_writer.set_data3f(pos)

    def finalize_poly_creation(self, cancel=False):

        tmp_data = self._tmp_data

        positions = tmp_data["vert_pos"]

        if not cancel and len(positions) < 3:
            return False

        # Clean up the temporary geometry

        tmp_geoms = tmp_data["geoms"]

        for subobj_type in ("vert", "edge", "poly"):
            tmp_geoms[subobj_type].remove_node()

        del self._tmp_data

        if cancel:
            return True

        # Create the new polygon

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        ordered_polys = self._ordered_polys
        merged_verts = self._merged_verts
        merged_verts_by_pos = {}
        merged_edges = self._merged_edges
        merged_edges_tmp = {}
        sel_vert_ids = self._selected_subobj_ids["vert"]
        sel_edge_ids = self._selected_subobj_ids["edge"]
        self._selected_subobj_ids["edge"] = []
        subobjs_to_select = {"vert": [], "edge": []}
        subobj_change = self._subobj_change

        owned_verts = tmp_data["owned_verts"]
        indices = tmp_data["vert_indices"]
        del indices[-1]
        normal = tmp_data["normals"][-1]
        normal.normalize()

        if tmp_data["flip_normal"]:
            normal *= -1.

        row_index = 0
        verts_by_pos = {}
        tmp_edges = []
        poly_edges_by_vert_id = {}

        poly_verts = []
        poly_edges = []
        poly_tris = []

        normal_change = self._normal_change
        normal_lock_change = self._normal_lock_change
        shared_normals = self._shared_normals

        for tri_data in indices:

            if tmp_data["flip_normal"]:
                tri_data = reversed(tri_data)

            tri_vert_ids = []

            for pos_index in tri_data:

                if pos_index in verts_by_pos:

                    vertex = verts_by_pos[pos_index]
                    vert_id = vertex.get_id()

                else:

                    pos = positions[pos_index]
                    vertex = Mgr.do("create_vert", self, pos)
                    vertex.set_row_index(row_index)
                    row_index += 1
                    vertex.set_normal(normal)
                    vert_id = vertex.get_id()
                    verts[vert_id] = vertex
                    verts_by_pos[pos_index] = vertex

                    if pos_index in owned_verts:
                        merged_vert = owned_verts[pos_index]
                        if merged_vert.get_id() in sel_vert_ids:
                            subobjs_to_select["vert"].append(vert_id)
                    elif pos_index in merged_verts_by_pos:
                        merged_vert = merged_verts_by_pos[pos_index]
                    else:
                        merged_vert = Mgr.do("create_merged_vert", self)
                        merged_verts_by_pos[pos_index] = merged_vert

                    merged_vert.append(vert_id)
                    merged_verts[vert_id] = merged_vert
                    normal_change.add(vert_id)
                    normal_lock_change.add(vert_id)
                    shared_normals[vert_id] = Mgr.do("create_shared_normal", self, [vert_id])

                tri_vert_ids.append(vert_id)

            for i, j in ((0, 1), (1, 2), (2, 0)):

                edge_vert_ids = (tri_vert_ids[i], tri_vert_ids[j])
                reversed_vert_ids = edge_vert_ids[::-1]

                if reversed_vert_ids in tmp_edges:
                    # if the edge appears twice, it's actually a diagonal
                    tmp_edges.remove(reversed_vert_ids)
                else:
                    tmp_edges.append(edge_vert_ids)

            poly_tris.append(tuple(tri_vert_ids))

        owned_verts = owned_verts.values()

        for merged_vert in owned_verts:
            for vert_id in merged_vert:
                for edge_id in verts[vert_id].get_edge_ids():
                    mvs = [merged_verts[v_id] for v_id in edges[edge_id]]
                    if mvs[0] not in owned_verts or mvs[1] not in owned_verts:
                        continue
                    merged_edge_verts = tuple(sorted(mvs))
                    merged_edge = merged_edges[edge_id]
                    merged_edges_tmp[merged_edge_verts] = merged_edge

        for edge_vert_ids in tmp_edges:
            poly_edges_by_vert_id[edge_vert_ids[0]] = edge_vert_ids

        # Define verts and edges in winding order

        vert1_id, vert2_id = edge_vert_ids = poly_edges_by_vert_id[poly_tris[0][0]]
        vert1 = verts[vert1_id]
        vert2 = verts[vert2_id]
        poly_verts.append(vert1)
        edge = Mgr.do("create_edge", self, edge_vert_ids)
        edge1_id = edge.get_id()
        vert2.add_edge_id(edge1_id)
        edges[edge1_id] = edge
        poly_edges.append(edge)
        verts_to_unmerge = set()
        edges_to_unmerge = set()

        merged_edge_verts = tuple(sorted(merged_verts[v_id] for v_id in edge_vert_ids))

        if merged_edge_verts in merged_edges_tmp:

            merged_edge = merged_edges_tmp[merged_edge_verts]

            if len(merged_edge) == 2:
                # triple edge; needs fix
                verts_to_unmerge.update(edge_vert_ids)

            if merged_edge[0] in sel_edge_ids:
                subobjs_to_select["edge"].append(edge1_id)

        else:

            merged_edge = Mgr.do("create_merged_edge", self)

        merged_edge.append(edge1_id)
        merged_edges[edge1_id] = merged_edge

        while vert2_id != vert1_id:

            poly_verts.append(vert2)
            vert1 = vert2
            edge_vert_ids = poly_edges_by_vert_id[vert2_id]
            vert2_id = edge_vert_ids[1]
            vert2 = verts[vert2_id]
            edge = Mgr.do("create_edge", self, edge_vert_ids)
            edge_id = edge.get_id()
            vert1.add_edge_id(edge_id)
            vert2.add_edge_id(edge_id)
            edges[edge_id] = edge
            poly_edges.append(edge)

            merged_edge_verts = tuple(sorted(merged_verts[v_id] for v_id in edge_vert_ids))

            if merged_edge_verts in merged_edges_tmp:

                merged_edge = merged_edges_tmp[merged_edge_verts]

                if len(merged_edge) == 2:
                    # triple edge; needs fix
                    verts_to_unmerge.update(edge_vert_ids)

                if merged_edge[0] in sel_edge_ids:
                    subobjs_to_select["edge"].append(edge_id)

            else:

                merged_edge = Mgr.do("create_merged_edge", self)

            merged_edge.append(edge_id)
            merged_edges[edge_id] = merged_edge

        vert2.add_edge_id(edge1_id)

        polygon = Mgr.do("create_poly", self, poly_tris, poly_edges, poly_verts)
        Mgr.do("register_vert_objs", poly_verts, restore=False)
        Mgr.do("register_edge_objs", poly_edges, restore=False)
        Mgr.do("register_poly", polygon, restore=False)
        ordered_polys.append(polygon)
        poly_id = polygon.get_id()
        polys[poly_id] = polygon
        subobj_change["vert"]["created"] = poly_verts
        subobj_change["edge"]["created"] = poly_edges
        subobj_change["poly"]["created"] = [polygon]

        # Check surface normal discontinuity

        for edge in poly_edges:

            edge_id = edge.get_id()
            merged_edge = merged_edges[edge_id]

            if len(merged_edge) == 1:
                continue

            edge_ids = merged_edge[:]
            edge_ids.remove(edge_id)
            other_edge_id = edge_ids[0]
            other_edge = edges[other_edge_id]

            if merged_verts[edge[0]] is merged_verts[other_edge[0]]:
                # surface normal discontinuity; needs fix
                verts_to_unmerge.update(edge)

        # Undo edge and vertex merging where it leads to a surface normal discontinuity
        # or triple edges

        while verts_to_unmerge:

            vert_id = verts_to_unmerge.pop()
            merged_vert = merged_verts[vert_id]
            merged_vert.remove(vert_id)
            merged_verts[vert_id] = Mgr.do("create_merged_vert", self, vert_id)
            vert = verts[vert_id]

            if vert_id in subobjs_to_select["vert"]:
                subobjs_to_select["vert"].remove(vert_id)

            edges_to_unmerge.update(vert.get_edge_ids())

        while edges_to_unmerge:

            edge_id = edges_to_unmerge.pop()
            merged_edge = merged_edges[edge_id]
            merged_edge.remove(edge_id)
            merged_edges[edge_id] = Mgr.do("create_merged_edge", self, edge_id)

            if edge_id in subobjs_to_select["edge"]:
                subobjs_to_select["edge"].remove(edge_id)

        # also undo vertex merging where it leads to self-intersecting borders
        border_edges = (merged_edges[edge.get_id()] for edge in poly_edges)
        self.fix_borders(border_edges)

        # Update geometry structures

        vert_count = polygon.get_vertex_count()
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

        pickable_type_id = PickableTypes.get_id("poly")
        picking_col_id = polygon.get_picking_color_id()
        picking_color = get_color_vec(picking_col_id, pickable_type_id)

        verts_by_row = {}

        for vert in poly_verts:
            vert.offset_row_index(old_count)
            row = vert.get_row_index()
            verts_by_row[row] = vert

        for row in sorted(verts_by_row):
            vert = verts_by_row[row]
            pos = vert.get_pos()
            pos_writer.add_data3f(pos)
            col_writer.add_data4f(picking_color)
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
        pickable_type_id = PickableTypes.get_id("vert")

        for row in sorted(verts_by_row):
            vert = verts_by_row[row]
            picking_color = get_color_vec(vert.get_picking_color_id(), pickable_type_id)
            col_writer1.add_data4f(picking_color)
            col_writer2.add_data4f(color_vert)
            col_writer3.add_data4f(color_normal)

        col_array = GeomVertexArrayData(vertex_data_vert1.get_array(1))
        vertex_data_normal1.set_array(1, col_array)

        sel_data = self._poly_selection_data
        sel_data["unselected"].extend(polygon)

        picking_colors1 = {}
        picking_colors2 = {}
        pickable_type_id = PickableTypes.get_id("edge")

        for edge in poly_edges:
            row1, row2 = [verts[v_id].get_row_index() for v_id in edge]
            picking_color = get_color_vec(edge.get_picking_color_id(), pickable_type_id)
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

        data = vertex_data_tmp.get_array(1).get_handle().get_data()

        vertex_data_tmp = GeomVertexData(vertex_data_edge1)
        array = vertex_data_tmp.modify_array(1)
        stride = array.get_array_format().get_stride()
        array.modify_handle().set_subdata(0, old_count * stride, "")
        vertex_data_tmp.set_num_rows(count)
        col_writer1 = GeomVertexWriter(vertex_data_tmp, "color")
        col_writer1.set_row(old_count)
        col_writer2.set_row(count + old_count)

        for row_index in sorted(picking_colors2):
            picking_color = picking_colors2[row_index]
            col_writer1.add_data4f(picking_color)
            col_writer2.add_data4f(color)

        data += vertex_data_tmp.get_array(1).get_handle().get_data()

        vertex_data_edge1.set_num_rows(count * 2)
        vertex_data_edge1.modify_array(1).modify_handle().set_data(data)

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(count * 2)

        for poly in ordered_polys:
            for edge in poly.get_edges():
                row1, row2 = [verts[v_id].get_row_index() for v_id in edge]
                lines_prim.add_vertices(row1, row2 + count)

        self.clear_selection("edge", update_verts_to_transf=False)
        subobjs_to_select["edge"].extend(sel_edge_ids)

        geom_node = geoms["edge"]["pickable"].node()
        geom_node.modify_geom(0).set_primitive(0, lines_prim)
        geom_node = geoms["edge"]["sel_state"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomLines(lines_prim))

        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_num_rows(count)

        vertex_data_top = geom_node_top.get_geom(0).get_vertex_data()
        pos_array = vertex_data_top.get_array(0)
        pos_data = pos_array.get_handle().get_data()
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
        pos_array = GeomVertexArrayData(pos_array)
        pos_array.modify_handle().set_data(pos_data * 2)
        vertex_data_edge1.set_array(0, pos_array)
        vertex_data_edge2.set_array(0, pos_array)

        tris_prim = geom_node_top.modify_geom(0).modify_primitive(0)
        start = tris_prim.get_num_vertices()

        for vert_ids in poly_tris:
            tris_prim.add_vertices(*[verts[v_id].get_row_index() for v_id in vert_ids])

        array = tris_prim.get_vertices()
        stride = array.get_array_format().get_stride()
        start *= stride
        size = len(polygon) * stride
        data = array.get_handle().get_subdata(start, size)
        geom_node = geoms["poly"]["unselected"].node()
        prim = geom_node.modify_geom(0).modify_primitive(0)
        handle = prim.modify_vertices().modify_handle()
        handle.set_data(handle.get_data() + data)
        geom_node = geoms["poly"]["pickable"].node()
        prim = geom_node.modify_geom(0).modify_primitive(0)
        handle = prim.modify_vertices().modify_handle()
        handle.set_data(handle.get_data() + data)

        tmp_prim = GeomPoints(Geom.UH_static)
        tmp_prim.reserve_num_vertices(vert_count)
        tmp_prim.add_next_vertices(vert_count)
        tmp_prim.offset_vertices(old_count)
        array = tmp_prim.get_vertices()
        data = array.get_handle().get_data()
        geom_node = geoms["vert"]["pickable"].node()
        prim = geom_node.modify_geom(0).modify_primitive(0)
        handle = prim.modify_vertices().modify_handle()
        handle.set_data(handle.get_data() + data)
        geom_node = geoms["vert"]["sel_state"].node()
        prim = geom_node.modify_geom(0).modify_primitive(0)
        handle = prim.modify_vertices().modify_handle()
        handle.set_data(handle.get_data() + data)
        geom_node = geoms["normal"]["pickable"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomPoints(prim))
        geom_node = geoms["normal"]["sel_state"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomPoints(prim))

        # Miscellaneous updates

        polygon.update_center_pos()
        polygon.update_normal()

        merged_subobjs = {"vert": merged_verts, "edge": merged_edges}

        for subobj_type in ("vert", "edge"):
            if subobjs_to_select[subobj_type]:
                subobj_id = subobjs_to_select[subobj_type][0]
                merged_subobj = merged_subobjs[subobj_type][subobj_id]
                # since update_selection(...) processes *all* subobjects referenced by the
                # merged subobject, it is replaced by a temporary merged subobject that
                # only references newly created subobjects;
                # as an optimization, one temporary merged subobject references all newly
                # created subobjects, so self.update_selection() needs to be called only
                # once
                tmp_merged_subobj = Mgr.do("create_merged_%s" % subobj_type, self)
                for s_id in subobjs_to_select[subobj_type]:
                    tmp_merged_subobj.append(s_id)
                merged_subobjs[subobj_type][subobj_id] = tmp_merged_subobj
                subobj = subobjs[subobj_type][subobj_id]
                self.update_selection(subobj_type, [subobj], [], False)
                # the original merged subobject can now be restored
                merged_subobjs[subobj_type][subobj_id] = merged_subobj
                self._update_verts_to_transform(subobj_type)

        self._update_verts_to_transform("poly")
        self._origin.node().set_bounds(geom_node_top.get_bounds())
        model = self.get_toplevel_object()
        model.get_bbox().update(*self._origin.get_tight_bounds())

        self._normal_sharing_change = True

        if model.has_tangent_space():
            tangent_flip, bitangent_flip = model.get_tangent_space_flip()
            self.update_tangent_space(tangent_flip, bitangent_flip, [poly_id])
        else:
            self._is_tangent_space_initialized = False

        return True

    def end_poly_creation(self):

        # Make the polygons pickable again at polygon level instead of the
        # vertices

        picking_masks = Mgr.get("picking_masks")["all"]
        geoms = self._geoms
        geoms["vert"]["pickable"].show(picking_masks)
        geoms["poly"]["pickable"].show_through(picking_masks)


class CreationManager(BaseObject):

    def __init__(self):

        self._vert_positions = []
        self._pixel_under_mouse = None
        self._picked_verts = []
        self._geom_data_objs = []
        self._active_geom_data_obj = None
        self._interactive_creation_started = False
        self._interactive_creation_ended = False

        add_state = Mgr.add_state
        add_state("poly_creation_mode", -10,
                  self.__enter_creation_mode, self.__exit_creation_mode)
        add_state("poly_creation", -11)

        def cancel_creation():

            self.__finalize_poly_creation(cancel=True)

        bind = Mgr.bind_state
        bind("poly_creation_mode", "create poly -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("poly_creation_mode", "create poly -> select", "escape",
             lambda: Mgr.exit_state("poly_creation_mode"))
        bind("poly_creation_mode", "exit poly creation mode", "mouse3-up",
             lambda: Mgr.exit_state("poly_creation_mode"))
        bind("poly_creation_mode", "start poly creation",
             "mouse1", self.__init_poly_creation)
        bind("poly_creation", "add poly vertex",
             "mouse1", self.__add_poly_vertex)
        bind("poly_creation", "remove poly vertex",
             "backspace", self.__remove_poly_vertex)
        bind("poly_creation", "switch poly start vertex",
             "shift", self.__switch_start_vertex)
        bind("poly_creation", "flip poly normal",
             "control", self.__flip_poly_normal)
        bind("poly_creation", "quit poly creation", "escape", cancel_creation)
        bind("poly_creation", "cancel poly creation",
             "mouse3-up", cancel_creation)

        status_data = GlobalData["status_data"]
        mode_text = "Create polygon"
        info_text = "LMB to create first vertex; RMB to cancel"
        status_data["create_poly"] = {"mode": mode_text, "info": info_text}
        info_text = "LMB to add vertex; <Backspace> to undo; " \
                    "click a previously added vertex to finalize; " \
                    "<Ctrl> to flip normal; <Shift> to turn diagonal; RMB to cancel"
        status_data["start_poly_creation"] = {"mode": mode_text, "info": info_text}

    def __enter_creation_mode(self, prev_state_id, is_active):

        if self._interactive_creation_ended:

            self._interactive_creation_ended = False

        else:

            editable_geoms = Mgr.get("selection_top")
            geom_data_objs = [geom.get_geom_object().get_geom_data_object()
                              for geom in editable_geoms]

            for data_obj in geom_data_objs:
                data_obj.prepare_poly_creation()

            self._geom_data_objs = geom_data_objs

            GlobalData["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")
            Mgr.do("enable_view_gizmo", False)
            Mgr.do("enable_view_tiles", False)
            Mgr.set_cursor("create")
            Mgr.add_task(self.__check_vertex_under_mouse, "check_vertex_under_mouse", sort=3)

        Mgr.update_app("status", "create_poly")

    def __exit_creation_mode(self, next_state_id, is_active):

        if self._interactive_creation_started:

            self._interactive_creation_started = False

        else:

            Mgr.set_cursor("main")

            for data_obj in self._geom_data_objs:
                data_obj.end_poly_creation()

            self._geom_data_objs = []

            Mgr.remove_task("check_vertex_under_mouse")
            Mgr.do("enable_view_gizmo")
            Mgr.do("enable_view_tiles")

    def __check_vertex_under_mouse(self, task):

        # Check if there is an existing vertex at the mouse position and set the
        # mouse cursor accordingly.

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("create" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __get_point_on_grid(self):

        if not self.mouse_watcher.has_mouse():
            return

        mouse_pos = self.mouse_watcher.get_mouse()

        return Mgr.get(("grid", "point_at_screen_pos"), mouse_pos)

    def __get_vertex(self):

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b

        return Mgr.get("vert", color_id)

    def __init_poly_creation(self):

        if self._pixel_under_mouse == VBase4():

            point = self.__get_point_on_grid()

            if not point:
                return

            vertex = None
            geom_data_obj = self._geom_data_objs[0]

        else:

            vertex = self.__get_vertex()

            if not vertex:
                return

            vertex = vertex.get_merged_vertex()
            point = None
            geom_data_obj = vertex.get_geom_data_object()

        geom_data_obj.init_poly_creation()
        geom_data_obj.add_new_poly_vertex(vertex, point)

        self._picked_verts.append(vertex)
        self._active_geom_data_obj = geom_data_obj

        self._interactive_creation_started = True
        self._interactive_creation_ended = False

        Mgr.update_app("status", "start_poly_creation")
        Mgr.enter_state("poly_creation")
        Mgr.add_task(self.__update_polygon, "update_polygon", sort=4)

    def __update_polygon(self, task):

        if self._pixel_under_mouse == VBase4():

            point = self.__get_point_on_grid()

            if not point:
                return task.cont

        else:

            vertex = self.__get_vertex()

            if not vertex:
                return task.cont

            grid_origin = Mgr.get(("grid", "origin"))
            point = vertex.get_pos(grid_origin)

        self._active_geom_data_obj.update_new_polygon(point)

        return task.cont

    def __add_poly_vertex(self):

        if self._pixel_under_mouse == VBase4():

            point = self.__get_point_on_grid()

            if not point:
                return

            vertex = None

        else:

            vertex = self.__get_vertex()

            if not vertex:
                # one of the previously added new vertices is picked, so the polygon
                # will be finalized
                self.__finalize_poly_creation()
                return

            vertex = vertex.get_merged_vertex()

            if vertex in self._picked_verts:
                # one of the previously picked existing vertices is picked again, so the
                # polygon will be finalized
                self.__finalize_poly_creation()
                return

            point = None

        self._picked_verts.append(vertex)
        self._active_geom_data_obj.add_new_poly_vertex(vertex, point)

    def __remove_poly_vertex(self):

        del self._picked_verts[-1]

        if self._picked_verts:
            self._active_geom_data_obj.remove_new_poly_vertex()
        else:
            self.__finalize_poly_creation(cancel=True)

    def __switch_start_vertex(self):

        self._active_geom_data_obj.switch_new_poly_start_vertex()

    def __flip_poly_normal(self):

        self._active_geom_data_obj.flip_new_poly_normal()

    def __finalize_poly_creation(self, cancel=False):

        geom_data_obj = self._active_geom_data_obj

        if not geom_data_obj.finalize_poly_creation(cancel=cancel):
            return

        self._active_geom_data_obj = None
        self._picked_verts = []
        self._interactive_creation_started = False
        self._interactive_creation_ended = True

        Mgr.remove_task("update_polygon")
        Mgr.enter_state("poly_creation_mode")

        if cancel:
            return

        Mgr.do("update_history_time")
        obj_id = geom_data_obj.get_toplevel_object().get_id()
        obj_data = {obj_id: geom_data_obj.get_data_to_store("subobj_change")}
        event_descr = "Create polygon"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)
