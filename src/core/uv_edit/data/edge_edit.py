from ..base import *
from .vert import MergedVertex
from .edge import MergedEdge


class EdgeEditBase(BaseObject):

    def get_seam_edges(self, start_edge):

        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        seam_edges = [start_edge]
        seam_edge = start_edge

        while True:

            edge = edges[seam_edge[0]]
            vert_id = edge[0]
            merged_vert = merged_verts[vert_id]

            for vert_id in merged_vert:

                vert = verts[vert_id]
                merged_edge = merged_edges[vert.get_edge_ids()[0]]

                if len(merged_edge) == 1:
                    seam_edge = merged_edge
                    break

            if seam_edge is start_edge:
                break
            else:
                seam_edges.append(seam_edge)

        return seam_edges

    def fix_seams(self, seam_edges):
        """
        Fix self-intersecting seams.
        Return the vertices that were separated.

        """

        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        new_merged_verts = []
        seam_verts = set()

        for merged_edge in seam_edges:

            edge = edges[merged_edge[0]]

            for vert_id in edge:
                seam_verts.add(merged_verts[vert_id])

        for merged_vert in seam_verts:

            vert_ids_by_merged_edge = {}
            vert_ids = {}

            for vert_id in merged_vert:

                vert = verts[vert_id]

                for edge_id in vert.get_edge_ids():

                    merged_edge = merged_edges[edge_id]

                    if merged_edge in vert_ids_by_merged_edge:

                        vert_id_set = vert_ids[vert_ids_by_merged_edge[merged_edge]]

                        if vert_id in vert_ids:

                            old_vert_id_set = vert_ids[vert_id]
                            vert_id_set.update(old_vert_id_set)

                            for other_vert_id in old_vert_id_set:
                                vert_ids[other_vert_id] = vert_id_set

                        else:

                            vert_id_set.add(vert_id)
                            vert_ids[vert_id] = vert_id_set

                        del vert_ids_by_merged_edge[merged_edge]

                    else:

                        vert_ids_by_merged_edge[merged_edge] = vert_id

                        if vert_id not in vert_ids:
                            vert_ids[vert_id] = set([vert_id])

            vert_ids = set(tuple(id_set) for id_set in vert_ids.values())

            if len(vert_ids) > 1:

                for ids in vert_ids:

                    new_merged_vert = MergedVertex(self)
                    new_merged_vert.extend(ids)
                    new_merged_verts.append(new_merged_vert)

                    for vert_id in ids:
                        merged_verts[vert_id] = new_merged_vert

        return new_merged_verts

    def split_edges(self, edge_ids=None):

        selection_ids = self._selected_subobj_ids
        selected_edge_ids = selection_ids["edge"] if edge_ids is None else edge_ids

        if not selected_edge_ids:
            return False

        selected_vert_ids = selection_ids["vert"]
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        selected_edges = set(merged_edges[i] for i in selected_edge_ids)
        verts_to_split = {}

        change = False
        seam_edge_ids = []
        update_verts_to_transf = False
        update_edges_to_transf = not set(selection_ids["edge"]).isdisjoint(edge_ids) if edge_ids else True
        update_polys_to_transf = False
        poly_verts_to_transf = self._verts_to_transf["poly"]

        # for each selected edge vertex, check the connected edges (in ordered fashion,
        # starting at the selected edge) until either the starting selected edge is
        # encountered (in this case, the vertex cannot be split), or a different
        # selected edge or border edge is encountered (if so, the vertex can be split);
        # if at least one of the vertices of an edge can be split, the edge itself
        # can be split (unless it is a border edge)
        for merged_edge in selected_edges:

            if len(merged_edge) == 1:
                edge1_id = merged_edge[0]
                edge2_id = None
            else:
                edge1_id, edge2_id = merged_edge

            edge1 = edges[edge1_id]
            vert_split = False

            for vert_id in edge1:

                merged_vert = merged_verts[vert_id]
                vert_ids_to_separate = []
                next_vert_id = vert_id
                edge_id = edge1_id

                while True:

                    next_vert = verts[next_vert_id]
                    vert_ids_to_separate.append(next_vert_id)
                    next_edge_ids = next_vert.get_edge_ids()

                    if next_edge_ids[0] == edge_id:
                        next_edge_id = next_edge_ids[1]
                    else:
                        next_edge_id = next_edge_ids[0]

                    if next_edge_id == edge2_id:
                        break

                    next_merged_edge = merged_edges[next_edge_id]

                    if next_merged_edge in selected_edges or len(next_merged_edge) == 1:

                        if len(merged_vert) > len(vert_ids_to_separate):

                            vert_ids = set(vert_ids_to_separate)

                            if vert_ids not in verts_to_split.setdefault(merged_vert, []):
                                verts_to_split[merged_vert].append(vert_ids)

                            vert_split = True

                        break

                    if next_merged_edge[0] == next_edge_id:
                        edge_id = next_merged_edge[1]
                    else:
                        edge_id = next_merged_edge[0]

                    edge = edges[edge_id]

                    if merged_verts[edge[0]] == merged_vert:
                        next_vert_id = edge[0]
                    else:
                        next_vert_id = edge[1]

            if vert_split:

                # it is possible that only vertices are split, without splitting any edges,
                # e.g. when trying to split two border edges that meet at a vertex that is
                # shared with other border edges
                if len(merged_edge) > 1:
                    seam_edge_ids.extend([edge1_id, edge2_id])
                    new_merged_edge = MergedEdge(self)
                    new_merged_edge.append(edge1_id)
                    merged_edge.remove(edge1_id)
                    merged_edges[edge1_id] = new_merged_edge

                change = True

        if change:

            for merged_vert in verts_to_split:

                for vert_ids_to_separate in verts_to_split[merged_vert]:

                    new_merged_vert = MergedVertex(self)

                    for id_to_separate in vert_ids_to_separate:

                        merged_vert.remove(id_to_separate)
                        new_merged_vert.append(id_to_separate)
                        merged_verts[id_to_separate] = new_merged_vert

                        if id_to_separate in selected_vert_ids:
                            update_verts_to_transf = True

                        if merged_vert in poly_verts_to_transf:
                            update_polys_to_transf = True

            UVMgr.do("update_active_selection")

            if update_verts_to_transf:
                self._update_verts_to_transform("vert")

            if update_edges_to_transf:
                self._update_verts_to_transform("edge")

            if update_polys_to_transf:
                self._update_verts_to_transform("poly")

            if seam_edge_ids:

                self.add_seam_edges(seam_edge_ids)

                seam_edges_to_select = set(seam_edge_ids) & set(selection_ids["edge"])
                seam_edges_to_unselect = set(seam_edge_ids) - set(selection_ids["edge"])

                if seam_edges_to_select:
                    color = UVMgr.get("uv_selection_colors")["seam"]["selected"]
                    self.update_seam_selection(seam_edges_to_select, color)
                    self._geom_data_obj.update_tex_seam_selection(seam_edges_to_select, color)

                if seam_edges_to_unselect:
                    color = UVMgr.get("uv_selection_colors")["seam"]["unselected"]
                    self.update_seam_selection(seam_edges_to_unselect, color)
                    self._geom_data_obj.update_tex_seam_selection(seam_edges_to_unselect, color)

        return change

    def stitch_edges(self, edge_ids=None):

        selection_ids = self._selected_subobj_ids
        selected_edge_ids = selection_ids["edge"]
        seam_edge_ids = set(selected_edge_ids if edge_ids is None else edge_ids)

        if not seam_edge_ids:
            return False, False

        selected_vert_ids = selection_ids["vert"]
        selected_poly_ids = selection_ids["poly"]
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        geom_data_obj = self._geom_data_obj
        merged_geom_verts = geom_data_obj.get_merged_vertices()

        seam_edges_to_remove = set()
        uv_by_geom_vert = {}
        tmp_merged_vert = MergedVertex(self)
        tmp_merged_edge = MergedEdge(self)

        for edge1_id in seam_edge_ids:

            if len(merged_edges[edge1_id]) > 1:
                continue

            merged_geom_edge = geom_data_obj.get_merged_edge(edge1_id)

            if len(merged_geom_edge) == 1:
                continue

            seam_edges_to_remove.update(merged_geom_edge)
            edge_id1, edge_id2 = merged_geom_edge
            edge2_id = edge_id1 if edge_id2 == edge1_id else edge_id2
            vert_ids = edges[edge1_id]
            src_verts = [merged_verts[vert_id] for vert_id in vert_ids]

            for vert_id in vert_ids:
                d = uv_by_geom_vert.setdefault(merged_geom_verts[vert_id],
                                               {"src": set(), "dest": set()})
                merged_vert = merged_verts[vert_id]
                d["src"].add(merged_vert)

            vert_ids = edges[edge2_id]

            for vert_id in vert_ids:

                d = uv_by_geom_vert.setdefault(merged_geom_verts[vert_id],
                                               {"src": set(), "dest": set()})
                merged_vert = merged_verts[vert_id]

                if merged_vert in src_verts:
                    d["src"].remove(merged_vert)
                else:
                    d["dest"].add(merged_vert)

        if not seam_edges_to_remove:
            return False, False

        verts_to_move = set()
        new_merged_verts = []

        for merged_geom_vert, d in uv_by_geom_vert.items():

            src_verts = d["src"]
            dest_verts = d["dest"]
            dest_vert_count = len(dest_verts)
            pos = sum([v.get_pos() for v in dest_verts], Point3()) / dest_vert_count

            id_set = set()

            for merged_vert in src_verts:
                id_set.update(merged_vert)
                merged_vert.set_pos(pos)

            for merged_vert in dest_verts:
                id_set.update(merged_vert)
                merged_vert.set_pos(pos)

            verts_to_move.update(id_set)

            new_merged_vert = MergedVertex(self)
            new_merged_vert.extend(id_set)
            new_merged_verts.append(new_merged_vert)

            for vert_id in id_set:
                merged_verts[vert_id] = new_merged_vert

            if not (id_set.isdisjoint(selected_vert_ids) or id_set.issubset(selected_vert_ids)):
                tmp_merged_vert.extend(id_set.difference(selected_vert_ids))

        update_polys_to_transf = False

        for merged_vert in new_merged_verts:

            edges_by_merged_vert = {}

            for vert_id in merged_vert:

                vert = verts[vert_id]

                if vert.get_polygon_id() in selected_poly_ids:
                    update_polys_to_transf = True

                for edge1_id in vert.get_edge_ids():

                    merged_edge = merged_edges[edge1_id]

                    if len(merged_edge) > 1:
                        continue

                    vert1_id, vert2_id = edges[edge1_id]
                    other_vert_id = vert1_id if merged_verts[vert2_id] is merged_vert else vert2_id
                    other_merged_vert = merged_verts[other_vert_id]

                    if other_merged_vert in edges_by_merged_vert:

                        edge2_id = edges_by_merged_vert.pop(other_merged_vert)
                        merged_edge.append(edge2_id)
                        merged_edges[edge2_id] = merged_edge
                        seam_edges_to_remove.update(merged_edge)
                        edge1_selected = edge1_id in selected_edge_ids
                        edge2_selected = edge2_id in selected_edge_ids

                        if edge1_selected != edge2_selected:
                            tmp_merged_edge.append(edge1_id if edge2_selected else edge2_id)

                    else:

                        edges_by_merged_vert[other_merged_vert] = edge1_id

        self.remove_seam_edges(seam_edges_to_remove)
        selection_change = False

        if tmp_merged_vert[:]:
            vert_id = tmp_merged_vert.get_id()
            orig_merged_vert = merged_verts[vert_id]
            merged_verts[vert_id] = tmp_merged_vert
            self.update_selection("vert", [tmp_merged_vert], [], False)
            merged_verts[vert_id] = orig_merged_vert
            self._update_verts_to_transform("vert")
            selection_change = True

        if tmp_merged_edge[:]:
            edge_id = tmp_merged_edge.get_id()
            orig_merged_edge = merged_edges[edge_id]
            merged_edges[edge_id] = tmp_merged_edge
            self.update_selection("edge", [tmp_merged_edge], [], False)
            merged_edges[edge_id] = orig_merged_edge
            self._update_verts_to_transform("edge")
            selection_change = True

        self.update_vertex_positions(verts_to_move)
        UVMgr.do("update_active_selection")

        if update_polys_to_transf:
            self._update_verts_to_transform("poly")

        return True, selection_change

    def init_edge_picking_via_poly(self, poly, category=""):

        # Allow picking the edges of the poly picked in the previous step
        # (see prepare_subobj_picking_via_poly) instead of other edges;
        # as soon as the mouse is released over an edge, it gets picked and
        # polys become pickable again.

        origin = self._origin
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]

        if category == "seam":

            merged_edges = self._merged_edges
            edge_ids = []

            for edge_id in poly.get_edge_ids():
                if len(merged_edges[edge_id]) == 1:
                    edge_ids.append(edge_id)

        else:

            edge_ids = poly.get_edge_ids()

        count = len(edge_ids)

        # create pickable geometry, specifically for the edges of the
        # given polygon and belonging to the given category, if any
        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("edge_data", vertex_format, Geom.UH_static)
        vertex_data.reserve_num_rows(count * 2)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")
        pickable_id = PickableTypes.get_id("edge")
        rows = self._tmp_row_indices
        by_aiming = GlobalData["uv_edit_options"]["pick_by_aiming"]

        if by_aiming:

            # To further assist with edge picking, create a quad for each
            # edge, with the picking color of that edge and perpendicular to
            # the view plane;
            # the border of each quad will pass through the vertices of the
            # corresponding edge;
            # an auxiliary picking camera will be placed at the clicked point under
            # the mouse and follow the mouse cursor, rendering the picking color
            # of the quad it is pointed at.

            aux_picking_root = Mgr.get("aux_picking_root")
            aux_picking_cam = UVMgr.get("aux_picking_cam")
            cam = self.cam
            cam_pos = cam.get_pos(self.uv_space)
            normal = Vec3.forward()
            plane = Plane(normal, cam_pos + normal * 10.)
            aux_picking_cam.set_plane(plane)
            aux_picking_cam.update_pos()
            normal *= 5.
            vertex_data_poly = GeomVertexData("vert_data_poly", vertex_format, Geom.UH_static)
            vertex_data_poly.reserve_num_rows(count * 4)
            pos_writer_poly = GeomVertexWriter(vertex_data_poly, "vertex")
            col_writer_poly = GeomVertexWriter(vertex_data_poly, "color")
            tmp_poly_prim = GeomTriangles(Geom.UH_static)
            tmp_poly_prim.reserve_num_vertices(count * 6)
            rel_pt = lambda point: self.uv_space.get_relative_point(origin, point)

        for i, edge_id in enumerate(edge_ids):

            edge = edges[edge_id]
            vert1_id, vert2_id = edge
            vertex = verts[vert1_id]
            pos1 = vertex.get_pos()
            pos_writer.add_data3f(pos1)
            vertex = verts[vert2_id]
            pos2 = vertex.get_pos()
            pos_writer.add_data3f(pos2)
            color_id = edge.get_picking_color_id()
            picking_color = get_color_vec(color_id, pickable_id)
            col_writer.add_data4f(picking_color)
            col_writer.add_data4f(picking_color)
            rows[color_id] = i * 2

            if by_aiming:

                p1 = Point3()
                point1 = rel_pt(pos1)
                point2 = point1 + normal
                plane.intersects_line(p1, point1, point2)
                p2 = Point3()
                point1 = rel_pt(pos2)
                point2 = point1 + normal
                plane.intersects_line(p2, point1, point2)
                pos_writer_poly.add_data3f(p1 - normal)
                pos_writer_poly.add_data3f(p1 + normal)
                pos_writer_poly.add_data3f(p2 - normal)
                pos_writer_poly.add_data3f(p2 + normal)

                for _ in range(4):
                    col_writer_poly.add_data4f(picking_color)

                j = i * 4
                tmp_poly_prim.add_vertices(j, j + 1, j + 2)
                tmp_poly_prim.add_vertices(j + 1, j + 3, j + 2)

        tmp_prim = GeomLines(Geom.UH_static)
        tmp_prim.reserve_num_vertices(count * 2)
        tmp_prim.add_next_vertices(count * 2)
        geom = Geom(vertex_data)
        geom.add_primitive(tmp_prim)
        node = GeomNode("tmp_geom_pickable")
        node.add_geom(geom)
        geom_pickable = origin.attach_new_node(node)
        geom_pickable.set_bin("fixed", 51)
        geom_pickable.set_depth_test(False)
        geom_pickable.set_depth_write(False)
        geom_sel_state = geom_pickable.copy_to(origin)
        geom_sel_state.set_name("tmp_geom_sel_state")
        geom_sel_state.set_light_off()
        geom_sel_state.set_color_off()
        geom_sel_state.set_texture_off()
        geom_sel_state.set_material_off()
        geom_sel_state.set_transparency(TransparencyAttrib.M_alpha)
        geom_sel_state.set_render_mode_thickness(3)
        geom = geom_sel_state.node().modify_geom(0)
        vertex_data = geom.get_vertex_data().set_color((.3, .3, .3, .5))
        geom.set_vertex_data(vertex_data)
        self._tmp_geom_pickable = geom_pickable
        self._tmp_geom_sel_state = geom_sel_state

        if by_aiming:
            geom_poly = Geom(vertex_data_poly)
            geom_poly.add_primitive(tmp_poly_prim)
            node = GeomNode("tmp_geom_pickable")
            node.add_geom(geom_poly)
            geom_poly_pickable = aux_picking_root.attach_new_node(node)
            geom_poly_pickable.set_two_sided(True)

        # to determine whether the mouse is over the polygon or not, create a
        # duplicate with a white color to distinguish it from the black background
        # color (so it gets detected by the picking camera) and any other pickable
        # objects (so no attempt will be made to pick it)
        vertex_data_poly = GeomVertexData("vert_data_poly", vertex_format, Geom.UH_static)
        vertex_data_poly.reserve_num_rows(count)
        pos_writer_poly = GeomVertexWriter(vertex_data_poly, "vertex")
        tmp_poly_prim = GeomTriangles(Geom.UH_static)
        tmp_poly_prim.reserve_num_vertices(len(poly))
        vert_ids = poly.get_vertex_ids()

        for vert_id in vert_ids:
            vertex = verts[vert_id]
            pos = vertex.get_pos()
            pos_writer_poly.add_data3f(pos)

        for tri_vert_ids in poly:
            for vert_id in tri_vert_ids:
                tmp_poly_prim.add_vertex(vert_ids.index(vert_id))

        geom_poly = Geom(vertex_data_poly)
        geom_poly.add_primitive(tmp_poly_prim)
        node = GeomNode("tmp_geom_poly_pickable")
        node.add_geom(geom_poly)
        geom_poly_pickable = geom_pickable.attach_new_node(node)
        geom_poly_pickable.set_bin("fixed", 50)

        render_mask = UVMgr.get("render_mask")
        picking_mask = UVMgr.get("picking_mask")
        geom_pickable.hide(render_mask)
        geom_pickable.show(picking_mask)
        geom_sel_state.hide(picking_mask)

        if by_aiming:
            aux_picking_cam.set_active()
            UVMgr.do("start_drawing_aux_picking_viz")

        geoms = self._geoms
        geoms["poly"]["sel_state"].hide(picking_mask)


class EdgeEditManager(BaseObject):

    def setup(self):

        Mgr.add_app_updater("edge_split", self.__split_edges, interface_id="uv")
        Mgr.add_app_updater("edge_stitch", self.__stitch_edges, interface_id="uv")

    def __split_edges(self):

        selection = self._selections[self._uv_set_id]["edge"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.split_edges()

    def __stitch_edges(self):

        selection = self._selections[self._uv_set_id]["edge"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.stitch_edges()
