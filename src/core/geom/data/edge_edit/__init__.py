from ....base import *
from .merge import EdgeMergeMixin, EdgeMergeManager
from .bridge import EdgeBridgeMixin, EdgeBridgeManager
import copy


class EdgeEditMixin(EdgeMergeMixin, EdgeBridgeMixin):
    """ GeomDataObject class mix-in """

    def get_region_border_edges(self, poly_region):
        """
        Return the edges that form the borders (including the borders of holes,
        if any) of the given poly_region, in counter-clockwise order, as well
        as data that can help in dealing with self-intersecting borders.

        The format of the data returned is as follows:

            [
                (border_edge_loop_0, intersection_data_0),
                ...,
                (border_edge_loop_n, intersection_data_n)
            ];

            border_edge_loop:

                [edge_0, edge_1, ..., edge_n];

            intersection_data:

                [
                    (index_0, split_merged_vert_0),
                    ...,
                    (index_n, split_merged_vert_n)
                ];

                this data needs to be applied to a list of merged vertices generated
                as follows:
                border_merged_verts = [merged_verts[e[1]] for e in border_edge_loop]

                index:
                    the index of a merged vertex in border_merged_verts at which a
                    self-intersection occurs;
                split_merged_vert:
                    a new merged vertex that refers to only the vertices that belong
                    to polygons sharing an edge in between two border edges sharing
                    the original merged vertex at which a self-intersection occurs.

        """

        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        border_edge_ids = []
        border_merged_edges = []

        for poly in poly_region:

            for edge in poly.edges:

                merged_edge = edge.merged_edge

                if merged_edge in border_merged_edges:
                    index = border_merged_edges.index(merged_edge)
                    border_merged_edges.remove(merged_edge)
                    del border_edge_ids[index]
                else:
                    border_merged_edges.append(merged_edge)
                    border_edge_ids.append(edge.id)

        del border_merged_edges

        def get_adjacent_edge(edge):

            edge1_id, edge2_id = edge.merged_edge
            edge_id = edge1_id if edge2_id == edge.id else edge2_id

            return edges[edge_id]

        def get_next_border_edge(edge):

            # collect the IDs of all vertices at the corner of both edges;
            # they are needed to split a merged vertex at which the border
            # self-intersects
            vert_ids = []

            while True:

                vert_id = edge[1]
                vert_ids.append(vert_id)
                vert = verts[vert_id]
                edge_id = vert.edge_ids[1]
                edge = edges[edge_id]

                if edge_id in border_edge_ids:
                    border_edge_ids.remove(edge_id)
                    return edge, vert_ids
                else:
                    edge = get_adjacent_edge(edge)

        border_edges = []
        merged_verts = self.merged_verts

        while border_edge_ids:

            start_edge = edges[border_edge_ids[0]]
            next_edge, vert_ids = get_next_border_edge(start_edge)
            border_edge_loop = [start_edge]
            border_vert_ids = [vert_ids]
            border_merged_verts = [merged_verts[next_edge[0]]]
            merged_vert_indices = {}
            intersection_data = []

            while next_edge is not start_edge:

                border_edge_loop.append(next_edge)
                next_edge, vert_ids = get_next_border_edge(next_edge)
                border_vert_ids.append(vert_ids)
                merged_vert = merged_verts[next_edge[0]]

                if merged_vert in border_merged_verts:
                    # if the same merged vertex is encountered more than once, the
                    # border self-intersects at that vertex; the indices at which it
                    # appears in the border vertex list must be stored, so it can be
                    # replaced later with split merged vertices
                    index = border_merged_verts.index(merged_vert)
                    merged_vert_indices.setdefault(merged_vert, []).append(index)
                    border_merged_verts[index] = None

                border_merged_verts.append(merged_vert)

            for old_merged_vert, index_list in merged_vert_indices.items():

                # complete the index list with the index at which the merged vertex
                # appears one last time
                index_list.append(border_merged_verts.index(old_merged_vert))

                for index in index_list:
                    split_merged_vert = Mgr.do("create_merged_vert", self)
                    split_merged_vert.extend(border_vert_ids[index])
                    intersection_data.append((index, split_merged_vert))

            border_edges.append((border_edge_loop, intersection_data))

        return border_edges

    def get_containing_surface_border(self, start_merged_edge):
        """
        Return the surface border containing the given start_merged_edge
        as a list of merged edges.

        """

        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        border_edges = [start_merged_edge]
        border_edge = start_merged_edge

        while True:

            edge = edges[border_edge[0]]
            vert_id = edge[0]
            merged_vert = merged_verts[vert_id]

            for vert_id in merged_vert:

                vert = verts[vert_id]
                merged_edge = merged_edges[vert.edge_ids[0]]

                if len(merged_edge) == 1:
                    border_edge = merged_edge
                    break

            if border_edge is start_merged_edge:
                break
            else:
                border_edges.append(border_edge)

        return border_edges

    def fix_borders(self, border_edges):
        """
        Fix self-intersecting borders.
        Return the vertices that were separated.

        """

        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        new_merged_verts = []
        border_verts = set()

        for merged_edge in border_edges:

            edge = edges[merged_edge[0]]

            for vert_id in edge:
                border_verts.add(merged_verts[vert_id])

        for merged_vert in border_verts:

            vert_ids_by_merged_edge = {}
            vert_ids = {}

            for vert_id in merged_vert:

                vert = verts[vert_id]

                for edge_id in vert.edge_ids:

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

                    new_merged_vert = Mgr.do("create_merged_vert", self)
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
        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        selected_edges = set(merged_edges[i] for i in selected_edge_ids)
        verts_to_update = {}

        change = False
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
                    next_edge_ids = next_vert.edge_ids

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

                            if vert_ids not in verts_to_update.setdefault(merged_vert, []):
                                verts_to_update[merged_vert].append(vert_ids)

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
                    new_merged_edge = Mgr.do("create_merged_edge", self, edge1_id)
                    merged_edge.remove(edge1_id)
                    merged_edges[edge1_id] = new_merged_edge

                change = True

        if not change:
            return False

        merged_verts_to_resmooth = set(verts_to_update)

        for merged_vert in verts_to_update:

            for vert_ids_to_separate in verts_to_update[merged_vert]:

                new_merged_vert = Mgr.do("create_merged_vert", self)
                merged_verts_to_resmooth.add(new_merged_vert)

                for id_to_separate in vert_ids_to_separate:

                    merged_vert.remove(id_to_separate)
                    new_merged_vert.append(id_to_separate)
                    merged_verts[id_to_separate] = new_merged_vert

                    if id_to_separate in selected_vert_ids:
                        update_verts_to_transf = True

                    if merged_vert in poly_verts_to_transf:
                        update_polys_to_transf = True

        self.update_normal_sharing(merged_verts_to_resmooth)

        if GD["subobj_edit_options"]["normal_preserve"]:

            vert_ids = set()

            for merged_vert in merged_verts_to_resmooth:
                vert_ids.update(merged_vert)

            self.lock_normals(True, vert_ids)

        else:

            self.update_vertex_normals(merged_verts_to_resmooth)

        if update_verts_to_transf:
            self._update_verts_to_transform("vert")

        if update_edges_to_transf:
            self._update_verts_to_transform("edge")

        if update_polys_to_transf:
            self._update_verts_to_transform("poly")

        return True

    def smooth_edges(self, smooth=True):

        selected_edge_ids = self._selected_subobj_ids["edge"]

        if not selected_edge_ids:
            return False, False

        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        normal_sharing = self._shared_normals
        tmp_normal_sharing = copy.deepcopy(normal_sharing)
        selected_edges = set(merged_edges[i] for i in selected_edge_ids)
        normals_to_sel = False

        if smooth:

            verts_to_update = []
            selected_normal_ids = set(self._selected_subobj_ids["normal"])

            for merged_edge in selected_edges:

                if len(merged_edge) == 1:
                    continue

                edge1, edge2 = [edges[e_id] for e_id in merged_edge]

                for vert1_id in edge1:

                    merged_vert = merged_verts[vert1_id]
                    verts_to_update.append(merged_vert)
                    vert2_id = edge2[0] if merged_verts[edge2[0]] is merged_vert else edge2[1]
                    shared_normal1 = tmp_normal_sharing[vert1_id]
                    shared_normal2 = tmp_normal_sharing[vert2_id]
                    shared_normal1.update(shared_normal2)

                    for vert_id in shared_normal2:
                        tmp_normal_sharing[vert_id] = shared_normal1

                    # Make sure that all shared normals in the same merged vertex become
                    # selected if at least one of them is already selected.

                    ids = shared_normal1
                    sel_ids = selected_normal_ids.intersection(ids)

                    if not sel_ids or len(sel_ids) == len(ids):
                        continue

                    tmp_normal = Mgr.do("create_shared_normal", self, ids.difference(sel_ids))
                    tmp_id = tmp_normal.id
                    orig_normal = normal_sharing[tmp_id]
                    normal_sharing[tmp_id] = tmp_normal
                    self.update_selection("normal", [tmp_normal], [])
                    normal_sharing[tmp_id] = orig_normal
                    normals_to_sel = True

        else:

            verts_to_update = {}

            def is_sharp_edge(merged_edge):

                if len(merged_edge) == 1:
                    return True

                edge1, edge2 = [edges[e_id] for e_id in merged_edge]

                for vert1_id in edge1:

                    merged_vert = merged_verts[vert1_id]
                    vert2_id = edge2[0] if merged_verts[edge2[0]] is merged_vert else edge2[1]

                    if vert2_id not in normal_sharing[vert1_id]:
                        return True

                return False

            # for each selected edge vertex, check the connected edges (in ordered fashion,
            # starting at the selected edge) until either the starting selected edge is
            # encountered (in this case, the vertex cannot be sharpened), or a different
            # selected edge or sharp edge is encountered (if so, the vertex can be sharpened);
            # if at least one of the vertices of an edge can be sharpened, the edge itself
            # can be sharpened (unless it is already a sharp edge)
            for merged_edge in selected_edges:

                if is_sharp_edge(merged_edge):
                    edge1_id = merged_edge[0]
                    edge2_id = None
                else:
                    edge1_id, edge2_id = merged_edge

                edge1 = edges[edge1_id]

                for vert_id in edge1:

                    merged_vert = merged_verts[vert_id]
                    vert_ids_to_separate = []
                    next_vert_id = vert_id
                    edge_id = edge1_id

                    while True:

                        next_vert = verts[next_vert_id]
                        vert_ids_to_separate.append(next_vert_id)
                        edge_ids = next_vert.edge_ids

                        if edge_ids[0] == edge_id:
                            next_edge_id = edge_ids[1]
                        else:
                            next_edge_id = edge_ids[0]

                        if next_edge_id == edge2_id:
                            break

                        next_merged_edge = merged_edges[next_edge_id]

                        if next_merged_edge in selected_edges or is_sharp_edge(next_merged_edge):

                            if len(merged_vert) > len(vert_ids_to_separate):

                                vert_ids = set(vert_ids_to_separate)

                                if vert_ids not in verts_to_update.setdefault(merged_vert, []):
                                    verts_to_update[merged_vert].append(vert_ids)

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

            for merged_vert in verts_to_update:

                old_shared_normals = []
                new_shared_normals = []

                for vert_id in merged_vert:

                    shared_normal = tmp_normal_sharing[vert_id]

                    if shared_normal not in old_shared_normals:
                        old_shared_normals.append(shared_normal)

                tmp_id_sets = verts_to_update[merged_vert]

                for old_shared_normal in old_shared_normals:

                    for tmp_id_set in tmp_id_sets:

                        if tmp_id_set == old_shared_normal:
                            continue

                        intersection = old_shared_normal.intersection(tmp_id_set)

                        if intersection:
                            new_shared_normals.append(intersection)
                            old_shared_normal.difference_update(intersection)

                for shared_normal in new_shared_normals:
                    for vert_id in shared_normal:
                        tmp_normal_sharing[vert_id] = shared_normal

        # check if anything has changed
        for merged_vert in verts_to_update:
            for vert_id in merged_vert:
                if tmp_normal_sharing[vert_id] != normal_sharing[vert_id]:
                    break
            else:
                continue
            break
        else:
            return False, False

        self._shared_normals = tmp_normal_sharing
        self._normal_sharing_change = True
        merged_verts_to_resmooth = set(verts_to_update)
        self.update_vertex_normals(merged_verts_to_resmooth)

        return True, normals_to_sel

    def init_edge_picking_via_poly(self, poly, category="", extra_data=None):

        # Allow picking the edges of the poly picked in the previous step
        # (see prepare_subobj_picking_via_poly) instead of other edges;
        # as soon as the mouse is released over an edge, it gets picked and
        # polys become pickable again.

        origin = self.origin
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]

        if category == "border":

            merged_edges = self.merged_edges
            edge_ids = []

            for edge_id in poly.edge_ids:
                if len(merged_edges[edge_id]) == 1:
                    edge_ids.append(edge_id)

        elif category == "uv_seam":

            merged_edges = extra_data
            edge_ids = []

            for edge_id in poly.edge_ids:
                if len(merged_edges[edge_id]) == 1:
                    edge_ids.append(edge_id)

        else:

            edge_ids = poly.edge_ids

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
        by_aiming = GD["subobj_edit_options"]["pick_by_aiming"]

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
            aux_picking_cam = Mgr.get("aux_picking_cam")
            cam = GD.cam()
            cam_pos = cam.get_pos(GD.world)
            normal = GD.world.get_relative_vector(cam, Vec3.forward()).normalized()
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
            rel_pt = lambda point: GD.world.get_relative_point(origin, point)
            lens_is_ortho = GD.cam.lens_type == "ortho"

        for i, edge_id in enumerate(edge_ids):

            edge = edges[edge_id]
            vert1_id, vert2_id = edge
            vertex = verts[vert1_id]
            pos1 = vertex.get_pos()
            pos_writer.add_data3(pos1)
            vertex = verts[vert2_id]
            pos2 = vertex.get_pos()
            pos_writer.add_data3(pos2)
            color_id = edge.picking_color_id
            picking_color = get_color_vec(color_id, pickable_id)
            col_writer.add_data4(picking_color)
            col_writer.add_data4(picking_color)
            rows[color_id] = i * 2

            if by_aiming:

                p1 = Point3()
                point1 = rel_pt(pos1)
                point2 = point1 + normal if lens_is_ortho else cam_pos
                plane.intersects_line(p1, point1, point2)
                p2 = Point3()
                point1 = rel_pt(pos2)
                point2 = point1 + normal if lens_is_ortho else cam_pos
                plane.intersects_line(p2, point1, point2)
                pos_writer_poly.add_data3(p1 - normal)
                pos_writer_poly.add_data3(p1 + normal)
                pos_writer_poly.add_data3(p2 - normal)
                pos_writer_poly.add_data3(p2 + normal)

                for _ in range(4):
                    col_writer_poly.add_data4(picking_color)

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
        geom_sel_state.name = "tmp_geom_sel_state"
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
        vert_ids = poly.vertex_ids

        for vert_id in vert_ids:
            vertex = verts[vert_id]
            pos = vertex.get_pos()
            pos_writer_poly.add_data3(pos)

        for tri_vert_ids in poly:
            for vert_id in tri_vert_ids:
                tmp_poly_prim.add_vertex(vert_ids.index(vert_id))

        geom_poly = Geom(vertex_data_poly)
        geom_poly.add_primitive(tmp_poly_prim)
        node = GeomNode("tmp_geom_poly_pickable")
        node.add_geom(geom_poly)
        geom_poly_pickable = geom_pickable.attach_new_node(node)
        geom_poly_pickable.set_bin("fixed", 50)

        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        geom_pickable.hide(render_mask)
        geom_pickable.show_through(picking_mask)

        if by_aiming:
            aux_picking_cam.active = True
            Mgr.do("start_drawing_aux_picking_viz")

        geoms = self._geoms
        geoms["poly"]["pickable"].show(picking_mask)


class EdgeEditManager(EdgeMergeManager, EdgeBridgeManager):

    def __init__(self):

        EdgeMergeManager.__init__(self)
        EdgeBridgeManager.__init__(self)

        self._mode_id = ""
        self._picking_dest_edge = False
        self._src_border_edge = None
        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

        Mgr.add_app_updater("edge_split", self.__split_edges)
        Mgr.add_app_updater("edge_smoothing", self.__smooth_edges)

        add_state = Mgr.add_state
        add_state("edge_picking_via_poly", -11, self.__start_edge_picking_via_poly)

        bind = Mgr.bind_state
        bind("edge_picking_via_poly", "pick hilited edge",
             "mouse1-up", self.__pick_hilited_edge)
        bind("edge_picking_via_poly", "cancel edge picking",
             "mouse3", self.__cancel_edge_picking_via_poly)
        bind("edge_picking_via_poly", "abort edge picking",
             "focus_loss", self.__cancel_edge_picking_via_poly)

        status_data = GD["status"]
        info = "LMB-drag over edge to pick it; RMB to cancel"
        status_data["edge_picking_via_poly"] = {"mode": "Pick edge", "info": info}

    def _update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            self._pixel_under_mouse = pixel_under_mouse
            cursor_id = "main"

            if pixel_under_mouse != VBase4():

                r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                color_id = r << 16 | g << 8 | b

                if GD["subobj_edit_options"]["pick_via_poly"]:

                    poly = Mgr.get("poly", color_id)

                    if poly:

                        merged_edges = poly.geom_data_obj.merged_edges

                        for edge_id in poly.edge_ids:
                            if len(merged_edges[edge_id]) == 1:
                                cursor_id = "select"
                                break

                else:

                    edge = Mgr.get("edge", color_id)
                    target_edge = edge.merged_edge if edge else None

                    if target_edge and len(target_edge) == 1:
                        cursor_id = "select"

            Mgr.set_cursor(cursor_id)

        return task.cont

    def _start_dest_edge_picking_via_poly(self):

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b
        pickable_type = PickableTypes.get(a)

        if pickable_type == "poly":

            self._picked_poly = Mgr.get("poly", color_id)
            merged_edges = self._picked_poly.geom_data_obj.merged_edges

            for edge_id in self._picked_poly.edge_ids:
                if len(merged_edges[edge_id]) == 1:
                    break
            else:
                return

            Mgr.enter_state("edge_picking_via_poly")

    def __start_edge_picking_via_poly(self, prev_state_id, active):

        Mgr.remove_task("update_mode_cursor")

        geom_data_obj = self._picked_poly.geom_data_obj
        geom_data_obj.init_subobj_picking_via_poly("edge", self._picked_poly, category="border")
        # temporarily select picked poly
        geom_data_obj.update_selection("poly", [self._picked_poly], [], False)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.geom_obj.geom_data_obj

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable(False)

        Mgr.add_task(self.__hilite_edge, "hilite_edge")
        Mgr.update_app("status", ["edge_picking_via_poly"])

        cs_type = GD["coord_sys_type"]
        tc_type = GD["transf_center_type"]
        toplvl_obj = self._picked_poly.toplevel_obj

        if cs_type == "local":
            Mgr.update_locally("coord_sys", cs_type, toplvl_obj)

        if tc_type == "pivot":
            Mgr.update_locally("transf_center", tc_type, toplvl_obj)

    def __hilite_edge(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            if pixel_under_mouse != VBase4():

                r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                color_id = r << 16 | g << 8 | b
                geom_data_obj = self._picked_poly.geom_data_obj

                # highlight temporary edge
                if geom_data_obj.hilite_temp_subobject("edge", color_id):
                    self._tmp_color_id = color_id

            self._pixel_under_mouse = pixel_under_mouse

        not_hilited = pixel_under_mouse in (VBase4(), VBase4(1., 1., 1., 1.))
        cursor_id = "main" if not_hilited else "select"

        if GD["subobj_edit_options"]["pick_by_aiming"]:

            aux_pixel_under_mouse = Mgr.get("aux_pixel_under_mouse")

            if not_hilited or self._aux_pixel_under_mouse != aux_pixel_under_mouse:

                if not_hilited and aux_pixel_under_mouse != VBase4():

                    r, g, b, a = [int(round(c * 255.)) for c in aux_pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    geom_data_obj = self._picked_poly.geom_data_obj

                    # highlight temporary edge
                    if geom_data_obj.hilite_temp_subobject("edge", color_id):
                        self._tmp_color_id = color_id
                        cursor_id = "select"

                self._aux_pixel_under_mouse = aux_pixel_under_mouse

        if self._cursor_id != cursor_id:
            Mgr.set_cursor(cursor_id)
            self._cursor_id = cursor_id

        return task.cont

    def __pick_hilited_edge(self):

        Mgr.remove_task("hilite_edge")
        geom_data_obj = self._picked_poly.geom_data_obj

        if self._tmp_color_id is None:
            picked_edge = None
        else:
            edge_id = Mgr.get("edge", self._tmp_color_id).id
            picked_edge = geom_data_obj.get_merged_edge(edge_id)

        if self._picking_dest_edge:

            if self._mode_id == "merge":
                self._finalize_merge(picked_edge=picked_edge)
            elif self._mode_id == "bridge":
                self._finalize_bridge(picked_edge=picked_edge)

        elif picked_edge and len(picked_edge) == 1:

            if self._mode_id == "merge":
                self._init_merge(picked_edge)
            elif self._mode_id == "bridge":
                self._init_bridge(picked_edge)

            Mgr.add_task(self._update_cursor, "update_mode_cursor")
            Mgr.update_app("status", [f"edge_{self._mode_id}_mode"])

        else:

            for model in Mgr.get("selection_top"):

                other_geom_data_obj = model.geom_obj.geom_data_obj

                if other_geom_data_obj is not geom_data_obj:
                    other_geom_data_obj.set_pickable()

            Mgr.enter_state(f"edge_{self._mode_id}_mode")

        geom_data_obj.prepare_subobj_picking_via_poly("edge")

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

    def __cancel_edge_picking_via_poly(self):

        Mgr.remove_task("hilite_edge")
        Mgr.exit_state("edge_picking_via_poly")
        geom_data_obj = self._picked_poly.geom_data_obj
        geom_data_obj.prepare_subobj_picking_via_poly("edge")

        if self._picking_dest_edge:

            if self._mode_id == "merge":
                self._finalize_merge(cancel=True)
            elif self._mode_id == "bridge":
                self._finalize_bridge(cancel=True)

        else:

            for model in Mgr.get("selection_top"):

                other_geom_data_obj = model.geom_obj.geom_data_obj

                if other_geom_data_obj is not geom_data_obj:
                    other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

    def __split_edges(self):

        selection = Mgr.get("selection_top")
        changed_objs = {}

        for model in selection:

            geom_data_obj = model.geom_obj.geom_data_obj

            if geom_data_obj.split_edges():
                changed_objs[model.id] = geom_data_obj

        if not changed_objs:
            return

        Mgr.do("update_active_selection")
        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.items():
            obj_data[obj_id] = geom_data_obj.get_data_to_store("prop_change", "subobj_merge")

        event_descr = "Split edge selection"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __smooth_edges(self, smooth):

        selection = Mgr.get("selection_top")
        changed_objs = {}
        changed_selections = []

        for model in selection:

            geom_data_obj = model.geom_obj.geom_data_obj
            change, normals_to_sel = geom_data_obj.smooth_edges(smooth)

            if change:

                changed_objs[model.id] = geom_data_obj

                if normals_to_sel:
                    changed_selections.append(model.id)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.items():

            obj_data[obj_id] = geom_data_obj.get_data_to_store()

            if obj_id in changed_selections:
                obj_data[obj_id].update(geom_data_obj.get_property_to_store("subobj_selection"))

        event_descr = f'{"Smooth" if smooth else "Sharpen"} edge selection'
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(EdgeEditManager)
