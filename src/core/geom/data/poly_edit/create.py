from ....base import *


class CreationMixin:
    """ PolygonEditMixin class mix-in """

    def prepare_poly_creation(self):

        # Make the vertices pickable at polygon level instead of the polygons, to
        # assist with polygon creation

        picking_mask = Mgr.get("picking_mask")
        geoms = self._geoms
        geoms["vert"]["pickable"].show_through(picking_mask)
        geoms["poly"]["pickable"].show(picking_mask)

    def init_poly_creation(self):

        origin = self.origin
        geoms = self._geoms
        render_mask = Mgr.get("render_mask")

        # Create temporary geometry

        tmp_geoms = {}
        tmp_data = {"geoms": tmp_geoms}

        vertex_format_vert = GeomVertexFormat.get_v3()
        vertex_data_vert = GeomVertexData("vert_data", vertex_format_vert, Geom.UH_dynamic)
        vertex_format_line = GeomVertexFormat.get_v3c4()
        vertex_data_line = GeomVertexData("line_data", vertex_format_line, Geom.UH_dynamic)
        vertex_format_tri = GeomVertexFormat.get_v3n3()
        vertex_data_tri = GeomVertexData("tri_data", vertex_format_tri, Geom.UH_dynamic)

        # Create the first vertex of the first triangle

        vertex_data_tri.set_num_rows(1)
        pos_writer = GeomVertexWriter(vertex_data_tri, "vertex")
        pos_writer.add_data3(0., 0., 0.)
        normal_writer = GeomVertexWriter(vertex_data_tri, "normal")
        normal_writer.add_data3(0., 0., 0.)

        # Create a temporary geom for new vertices

        points_prim = GeomPoints(Geom.UH_static)
        point_geom = Geom(vertex_data_vert)
        point_geom.add_primitive(points_prim)
        geom_node = GeomNode("new_vertices_geom")
        geom_node.add_geom(point_geom)
        new_vert_geom = geoms["vert"]["pickable"].attach_new_node(geom_node)
        new_vert_geom.show_through(render_mask)
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
        edge_geom.show_through(render_mask)
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

            vert_id = vertex.id

            if vert_id in self._subobjs["vert"]:

                merged_vert = self.merged_verts[vert_id]

                if merged_vert.is_border_vertex():
                    tmp_data["owned_verts"][last_index] = merged_vert

                pos = vertex.get_pos()

            else:

                pos = vertex.get_pos(self.origin)

        else:

            grid_origin = Mgr.get("grid").origin
            pos = self.origin.get_relative_point(grid_origin, point)

            geom = tmp_data["geoms"]["vert"].node().modify_geom(0)
            vertex_data = geom.modify_vertex_data()
            row = vertex_data.get_num_rows()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(row)
            pos_writer.add_data3(pos)
            point_prim = geom.modify_primitive(0)
            point_prim.add_vertex(row)
            tmp_data["vert_geom_rows"].append(last_index)

        tmp_data["vert_pos"].append(pos)

        geom = tmp_data["geoms"]["poly"].node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.set_row(last_index)
        pos_writer.set_data3(pos)
        pos_writer.add_data3(pos)
        normal_writer = GeomVertexWriter(vertex_data, "normal")
        normal_writer.set_row(last_index)
        normal_writer.set_data3(0., 0., 0.)
        normal_writer.add_data3(0., 0., 0.)

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
            sign = -1. if self.owner.has_flipped_normals() else 1.

            for i in range(last_index):
                normal_writer.set_data3(normal * sign)

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
            pos_writer.add_data3(start_pos)
            pos_writer.add_data3(pos)
            pos_writer.add_data3(pos2)
            pos_writer.add_data3(pos)
            col_writer.add_data4(.5, .5, .5, 1.)
            col_writer.add_data4(.5, .5, .5, 1.)
            col_writer.add_data4(1., 1., 0., 1.)
            col_writer.add_data4(1., 1., 0., 1.)
            edge_prim.add_vertices(count, count + 1, count + 2, count + 3)
        else:
            pos_writer.add_data3(pos)
            pos_writer.add_data3(pos)
            col_writer.add_data4(1., 1., 0., 1.)
            col_writer.add_data4(1., 1., 0., 1.)
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
            tris_prim.modify_vertices().clear_rows()

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

        if col_writer.get_data4() == VBase4(1., 1., 0., 1.):
            col_writer.set_data4(.5, .5, .5, 1.)
            col_writer.set_data4(.5, .5, .5, 1.)
            col_writer.set_data4(1., 1., 0., 1.)
            col_writer.set_data4(1., 1., 0., 1.)
        else:
            col_writer.set_data4(1., 1., 0., 1.)
            col_writer.set_data4(1., 1., 0., 1.)
            col_writer.set_data4(.5, .5, .5, 1.)
            col_writer.set_data4(.5, .5, .5, 1.)

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

        grid_origin = Mgr.get("grid").origin
        pos = self.origin.get_relative_point(grid_origin, point)

        last_index = len(tmp_data["vert_pos"]) - 1

        if last_index > 0:

            geom = tmp_data["geoms"]["poly"].node().modify_geom(0)
            vertex_data = geom.modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(last_index + 1)
            pos_writer.set_data3(pos)

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
                sign = -1. if self.owner.has_flipped_normals() else 1.

                for row_index in indices:
                    normal_writer.set_row(row_index)
                    normal_writer.set_data3(normal * sign)

        geom = tmp_data["geoms"]["edge"].node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        count = vertex_data.get_num_rows()
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.set_row(count - 1)
        pos_writer.set_data3(pos)

        if last_index > 0:
            pos_writer.set_row(count - 3)
            pos_writer.set_data3(pos)

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
        merged_verts = self.merged_verts
        merged_verts_by_pos = {}
        merged_edges = self.merged_edges
        merged_edges_tmp = {}

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

        for tri_data in indices:

            if tmp_data["flip_normal"]:
                tri_data = reversed(tri_data)

            tri_vert_ids = []

            for pos_index in tri_data:

                if pos_index in verts_by_pos:

                    vertex = verts_by_pos[pos_index]
                    vert_id = vertex.id

                else:

                    pos = positions[pos_index]
                    vertex = Mgr.do("create_vert", self, pos)
                    vertex.row_index = row_index
                    row_index += 1
                    vertex.normal = normal
                    vert_id = vertex.id
                    verts[vert_id] = vertex
                    verts_by_pos[pos_index] = vertex

                    if pos_index in owned_verts:
                        merged_vert = owned_verts[pos_index]
                    elif pos_index in merged_verts_by_pos:
                        merged_vert = merged_verts_by_pos[pos_index]
                    else:
                        merged_vert = Mgr.do("create_merged_vert", self)
                        merged_verts_by_pos[pos_index] = merged_vert

                    merged_vert.append(vert_id)
                    merged_verts[vert_id] = merged_vert

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

        owned_verts = list(owned_verts.values())

        for merged_vert in owned_verts:
            for vert_id in merged_vert:
                for edge_id in verts[vert_id].edge_ids:
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
        edge1_id = edge.id
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
            edge_id = edge.id
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

            else:

                merged_edge = Mgr.do("create_merged_edge", self)

            merged_edge.append(edge_id)
            merged_edges[edge_id] = merged_edge

        vert2.add_edge_id(edge1_id)

        polygon = Mgr.do("create_poly", self, poly_tris, poly_edges, poly_verts)
        ordered_polys.append(polygon)
        poly_id = polygon.id
        polys[poly_id] = polygon

        # Check surface normal discontinuity

        for edge in poly_edges:

            edge_id = edge.id
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
            edges_to_unmerge.update(vert.edge_ids)

        while edges_to_unmerge:
            edge_id = edges_to_unmerge.pop()
            merged_edge = merged_edges[edge_id]
            merged_edge.remove(edge_id)
            merged_edges[edge_id] = Mgr.do("create_merged_edge", self, edge_id)

        # also undo vertex merging where it leads to self-intersecting borders
        border_edges = (merged_edges[edge.id] for edge in poly_edges)
        self.fix_borders(border_edges)

        polygon.update_center_pos()
        polygon.update_normal()

        self._create_new_geometry(poly_verts, poly_edges, [polygon])

        return True

    def end_poly_creation(self):

        # Make the polygons pickable again at polygon level instead of the
        # vertices

        picking_mask = Mgr.get("picking_mask")
        geoms = self._geoms
        geoms["vert"]["pickable"].show(picking_mask)
        geoms["poly"]["pickable"].show_through(picking_mask)


class CreationManager:
    """ PolygonEditManager class mix-in """

    def __init__(self):

        self._pixel_under_mouse = None
        self._picked_verts = []
        self._positions = []
        self._geom_data_objs = []
        self._active_geom_data_obj = None
        self._interactive_creation_started = False
        self._interactive_creation_ended = False

        add_state = Mgr.add_state
        add_state("poly_creation_mode", -10,
                  self.__enter_creation_mode, self.__exit_creation_mode)
        add_state("poly_creation", -11,
                  self.__enter_poly_creation, self.__exit_poly_creation)

        def cancel_creation():

            self.__finalize_poly_creation(cancel=True)

        bind = Mgr.bind_state
        bind("poly_creation_mode", "create poly -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("poly_creation_mode", "create poly -> select", "escape",
             lambda: Mgr.exit_state("poly_creation_mode"))
        bind("poly_creation_mode", "exit poly creation mode", "mouse3",
             lambda: Mgr.exit_state("poly_creation_mode"))
        bind("poly_creation_mode", "start poly creation",
             "mouse1", self.__init_poly_creation)
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("poly_creation_mode", "create poly ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))
        bind("poly_creation", "add poly vertex",
             "mouse1", self.__add_poly_vertex)
        bind("poly_creation", "remove poly vertex",
             "backspace", self.__remove_poly_vertex)
        bind("poly_creation", "switch poly start vertex",
             "shift", self.__switch_start_vertex)
        bind("poly_creation", "flip poly normal",
             "control", self.__flip_poly_normal)
        bind("poly_creation", "poly creation -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("poly_creation", "quit poly creation", "escape", cancel_creation)
        bind("poly_creation", "cancel poly creation", "mouse3", cancel_creation)
        bind("poly_creation", "abort poly creation", "focus_loss", cancel_creation)

        status_data = GD["status"]
        mode_text = "Create polygon"
        info_text = "LMB to create first vertex; RMB to cancel"
        status_data["create_poly"] = {"mode": mode_text, "info": info_text}
        info_text = "LMB to add vertex; <Backspace> to undo; " \
                    "click a previously added vertex to finalize; " \
                    "<Ctrl> to flip normal; <Shift> to turn diagonal; " \
                    "RMB to cancel; <Space> to navigate"
        status_data["start_poly_creation"] = {"mode": mode_text, "info": info_text}

    def __enter_creation_mode(self, prev_state_id, active):

        Mgr.do("enable_view_gizmo")

        if self._interactive_creation_ended:

            GD["interactive_creation"] = False
            self._interactive_creation_ended = False

        else:

            editable_geoms = Mgr.get("selection_top")
            geom_data_objs = [geom.geom_obj.geom_data_obj for geom in editable_geoms]

            for data_obj in geom_data_objs:
                data_obj.prepare_poly_creation()

            self._geom_data_objs = geom_data_objs

            GD["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")
            Mgr.set_cursor("create")
            Mgr.add_task(self.__check_vertex_under_mouse, "check_vertex_under_mouse", sort=3)

        Mgr.update_app("status", ["create_poly"])

    def __exit_creation_mode(self, next_state_id, active):

        if self._interactive_creation_started:

            GD["interactive_creation"] = True
            self._interactive_creation_started = False

        else:

            Mgr.set_cursor("main")

            for data_obj in self._geom_data_objs:
                data_obj.end_poly_creation()

            self._geom_data_objs = []

            Mgr.remove_task("check_vertex_under_mouse")
            Mgr.do("enable_view_gizmo")

    def __enter_poly_creation(self, prev_state_id, active):

        if active:
            Mgr.do("enable_view_gizmo", False)
            Mgr.do("set_view_gizmo_mouse_region_sort", 0)
            Mgr.update_remotely("interactive_creation", "resumed")

        Mgr.add_task(self.__update_polygon, "update_polygon", sort=4)
        Mgr.update_app("status", ["start_poly_creation"])

    def __exit_poly_creation(self, next_state_id, active):

        if active:
            Mgr.remove_task("update_polygon")
            pos = Mgr.get("grid").origin.get_relative_point(GD.world, self._positions[-1])
            self._active_geom_data_obj.update_new_polygon(pos)
            Mgr.do("enable_view_gizmo", True)
            Mgr.do("set_view_gizmo_mouse_region_sort", 210)

    def __check_vertex_under_mouse(self, task):

        # Check if there is an existing vertex at the mouse position and set the
        # mouse cursor accordingly.

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("create" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __get_point_on_grid(self):

        if not GD.mouse_watcher.has_mouse():
            return

        mouse_pos = GD.mouse_watcher.get_mouse()

        return Mgr.get("grid").get_point_at_screen_pos(mouse_pos)

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
            pos = GD.world.get_relative_point(Mgr.get("grid").origin, point)

        else:

            vertex = self.__get_vertex()

            if not vertex:
                return

            vertex = vertex.merged_vertex
            point = None
            geom_data_obj = vertex.geom_data_obj
            pos = vertex.get_pos(GD.world)

        geom_data_obj.init_poly_creation()
        geom_data_obj.add_new_poly_vertex(vertex, point)

        self._picked_verts.append(vertex)
        self._active_geom_data_obj = geom_data_obj

        self._interactive_creation_started = True
        self._interactive_creation_ended = False

        self._positions.append(pos)
        Mgr.enter_state("poly_creation")

    def __update_polygon(self, task):

        if self._pixel_under_mouse == VBase4():

            point = self.__get_point_on_grid()

            if not point:
                return task.cont

        else:

            vertex = self.__get_vertex()

            if not vertex:
                return task.cont

            point = vertex.get_pos(Mgr.get("grid").origin)

        self._active_geom_data_obj.update_new_polygon(point)

        return task.cont

    def __add_poly_vertex(self):

        if self._pixel_under_mouse == VBase4():

            point = self.__get_point_on_grid()

            if not point:
                return

            vertex = None
            pos = GD.world.get_relative_point(Mgr.get("grid").origin, point)

        else:

            vertex = self.__get_vertex()

            if not vertex:
                # one of the previously added new vertices is picked, so the polygon
                # will be finalized
                self.__finalize_poly_creation()
                return

            vertex = vertex.merged_vertex

            if vertex in self._picked_verts:
                # one of the previously picked existing vertices is picked again, so the
                # polygon will be finalized
                self.__finalize_poly_creation()
                return

            point = None
            pos = vertex.get_pos(GD.world)

        self._picked_verts.append(vertex)
        self._active_geom_data_obj.add_new_poly_vertex(vertex, point)
        self._positions.append(pos)

    def __remove_poly_vertex(self):

        del self._picked_verts[-1]
        del self._positions[-1]

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
        self._positions = []
        self._interactive_creation_started = False
        self._interactive_creation_ended = True

        Mgr.remove_task("update_polygon")
        Mgr.enter_state("poly_creation_mode")

        if cancel:
            return

        Mgr.do("update_history_time")
        obj_id = geom_data_obj.toplevel_obj.id
        obj_data = {obj_id: geom_data_obj.get_data_to_store("subobj_change")}
        event_descr = "Create polygon"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)
