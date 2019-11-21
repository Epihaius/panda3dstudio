from ....base import *
from math import sin, cos, acos


class ExtrusionInsetMixin:
    """ PolygonEditMixin class mix-in """

    def __compute_extr_inset_data(self, extrusion, inset):
        """
        Compute the data for previewing or creating extrusions and insets.
        This data includes direction vectors for each of these operations, needed
        to offset the vertices of the newly created polygons.

        """

        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        polys = self._subobjs["poly"]
        selected_poly_ids = set(self._selected_subobj_ids["poly"])
        selected_polys = set(polys[p_id] for p_id in selected_poly_ids)

        # a polygon region is a collection of polygons, each of which shares at
        # least one edge with at least one other polygon in that collection
        regions = []
        borders = []
        avg_normals = {}
        extr1_vecs = {}  # per-vertex averaged polygon normal
        extr2_vecs = {}  # individual polygon normal
        extr3_vecs = {}  # per-region averaged polygon normal
        inset1_vecs = {}
        inset2_vecs = {}
        sides = {}
        data = {
            "regions": regions,
            "borders": borders,
            "avg_normals": avg_normals,
            "extr1_vecs": extr1_vecs,
            "extr2_vecs": extr2_vecs,
            "extr3_vecs": extr3_vecs,
            "inset1_vecs": inset1_vecs,
            "inset2_vecs": inset2_vecs,
            "sides": sides
        }
        edge_vert_ids1 = []
        computed_extr1_vecs = []
        computed_extr3_vecs = []
        sign = -1 if self.owner.has_flipped_normals() else 1

        def get_poly_neighbor_ids(poly):
            """
            Return the IDs of the polygons that share an edge with the given poly.

            """

            neighbor_ids = set()

            for edge in poly.edges:
                neighbor_ids.update(edge.merged_edge.polygon_ids)

            neighbor_ids.remove(poly.id)

            return neighbor_ids

        def get_polygon_region(poly_id):
            """
            Return the region of contiguously connected polygons, including the
            one with the given poly_id.

            """

            poly = polys[poly_id]
            poly_ids = set([poly_id])
            neighbor_ids = list(get_poly_neighbor_ids(poly) & selected_poly_ids)

            while neighbor_ids:
                neighbor_id = neighbor_ids.pop()
                neighbor = polys[neighbor_id]
                neighbor_ids.extend(get_poly_neighbor_ids(neighbor) & selected_poly_ids - poly_ids)
                poly_ids.add(neighbor_id)

            return set(polys[p_id] for p_id in poly_ids)

        def get_border_edge_verts(region):
            """
            Return a list of edges that make up the border(s) of the given
            polygon region, with each edge represented by a (end_merged_vert1,
            end_merged_vert2) tuple.

            """

            edge_mvs = []

            for p in region:

                ids = (edge[:] for edge in p.edges)
                mvs = ((merged_verts[vi1], merged_verts[vi2]) for vi1, vi2 in ids)

                for mv_tuple in mvs:
                    if mv_tuple[::-1] in edge_mvs:
                        edge_mvs.remove(mv_tuple[::-1])
                    else:
                        edge_mvs.append(mv_tuple)

            return edge_mvs

        def compute_inset_vectors(region, border_data):
            """
            For each vertex, compute the vector used to inset all selected polys
            connected at that vertex.

            """

            border_edge_loop, intersection_data = border_data
            border_merged_verts = [merged_verts[e[1]] for e in border_edge_loop]
            old_merged_verts = {}

            for index, split_merged_vert in intersection_data:
                old_merged_vert = border_merged_verts[index]
                for v_id in split_merged_vert:
                    old_merged_verts[v_id] = old_merged_vert
                    merged_verts[v_id] = split_merged_vert
                border_merged_verts[index] = split_merged_vert

            border_merged_verts.append(border_merged_verts[0])

            for i in range(len(border_merged_verts) - 1):

                v0 = border_merged_verts[i - (2 if i == 0 else 1)]
                v1 = border_merged_verts[i]
                v2 = border_merged_verts[i + 1]
                vec1 = (v0.get_pos() - v1.get_pos()).normalized()
                vec2 = (v2.get_pos() - v1.get_pos()).normalized()

                connected_edges = (e for e in v1.connected_edges
                                   if polys[e.polygon_id] in region)
                shared_edges = [e.merged_edge for e in connected_edges]
                shared_edges = set(me for me in shared_edges
                                   if shared_edges.count(me) > 1)

                if shared_edges:
                    inset1_vec = sum((me.get_direction_vector(v1.id)
                        for me in shared_edges), Vec3()).normalized()
                    angle1 = acos(vec1.dot(inset1_vec))
                    angle2 = acos(inset1_vec.dot(vec2))
                    cosine = cos(angle1 + angle2)
                else:
                    inset1_vec = (vec1 + vec2).normalized()
                    cosine = vec1.dot(vec2)
                    normal = sum((p.normal for p in v1.connected_polys
                        & region), Vec3()).normalized()

                if cosine < -.999:
                    inset_scale = 1.
                    if not shared_edges:
                        inset1_vec = vec1.cross(normal).normalized()
                else:
                    sine = sin(acos(min(1., cosine)) * .5)
                    inset_scale = 1. / sine if sine > .0001 else 0.
                    if not shared_edges:
                        cross_vec = vec2.cross(vec1).normalized()
                        # reverse inset vector when inner corner angle > 180 degrees
                        # (i.e. where the polygon is concave)
                        inset1_vec *= -1. if cross_vec.dot(normal) < 0. else 1.

                inset1_vec = Vec4(*inset1_vec, inset_scale)

                for vert_id in v1:
                    if polys[verts[vert_id].polygon_id] in region:
                        inset1_vecs[vert_id] = inset1_vec

            merged_verts.update(old_merged_verts)

        def compute_per_vertex_extrusion_vector(merged_vert, region):
            """
            Compute the vector used to extrude polys connected at the given vertex;
            it is computed in a way that depends on the number of connected
            polygons (as an optimization, polygons with (almost) duplicate
            normals are discarded):

            *) two polygons:
                the extrusion vector points to the closest point on the intersection
                line of the polygon planes;
            *) three polygons:
                the extrusion vector points to the intersection point of the polygon
                planes;
            *) four or more polygons:
                the extrusion vector is the normalized sum of the normals of
                all polygons connected at this vertex, scaled by the length of
                another vector;
                polygon normals are sorted by their dot product with the average
                polygon normal, smallest to largest; only the first four normals
                will be considered (otherwise the computation might become too
                slow, even though this restriction can lead to suboptimal results);
                the corresponding planes should be the four most significant ones
                as they make the sharpest angles;
                with P1 the intersection point of the first three planes and P2
                the intersection point of the first two planes with the fourth, the
                scale vector points to the median of P1 and P2.

            """

            polys_at_vert = merged_vert.connected_polys & region
            normals_at_vert = [p.normal.normalized() for p in polys_at_vert]
            avg_poly_normal = sum(normals_at_vert, Vec3()).normalized()
            normals = []

            for n in normals_at_vert:
                for other_n in normals:
                    if abs(n.dot(other_n)) > .999:
                        break
                else:
                    normals.append(n)

            normals_by_dot = {(avg_poly_normal.dot(n), i): n for i, n in enumerate(normals)}
            normals = [normals_by_dot[d] for d in sorted(normals_by_dot)][:4]
            planes = [Plane(n, Point3() + n) for n in normals]
            point_on_line = Point3()
            line_vec = Vec3()
            intersection_point = Point3()

            if len(planes) == 1:
                # there's only one poly at the vertex; the extrusion vector
                # is the normal to that poly
                extrusion_vec = normals[0]
            else:
                if planes[0].intersects_plane(point_on_line, line_vec, planes[1]):
                    if len(planes) == 2:
                        # there are two polys at the vertex; the extrusion
                        # vector is perpendicular to the intersection line of
                        # both polygon planes
                        extrusion_vec = Vec3(point_on_line)
                        extrusion_vec -= extrusion_vec.project(line_vec)
                elif len(planes) == 2:
                    extrusion_vec = normals[0]

            if len(planes) < 3:
                return extrusion_vec * sign

            scale_vec = None

            while len(planes) > 2:

                if planes.pop(2).intersects_line(intersection_point, point_on_line,
                        point_on_line + line_vec):
                    tmp_vec = Vec3(intersection_point)

                if scale_vec:
                    scale_vec = (scale_vec + tmp_vec) * .5
                else:
                    scale_vec = tmp_vec

            return avg_poly_normal * scale_vec.length() * sign

        # Process all selected polygons; compute the extrusion and inset vectors for
        # all of their vertices.

        for poly_id in selected_poly_ids:

            poly = polys[poly_id]

            for i, region in enumerate(regions):

                if poly in region:
                    edge_mvs = edge_vert_ids1[i]
                    tmp_extr_vecs = computed_extr1_vecs[i]
                    extr3_vec = computed_extr3_vecs[i]
                    break

            else:

                region = get_polygon_region(poly_id)
                regions.append(region)
                edge_mvs = get_border_edge_verts(region)
                edge_vert_ids1.append(edge_mvs)
                border_edges = self.get_region_border_edges(region)

                if border_edges:
                    borders.append(border_edges)

                tmp_extr_vecs = {}
                computed_extr1_vecs.append(tmp_extr_vecs)
                # compute the vector used to extrude the polygon region at every
                # vertex; it is the per-region averaged polygon normal
                extr3_vec = sum((p.normal.normalized() for p in region),
                                Vec3()).normalized()
                computed_extr3_vecs.append(extr3_vec)

                for border_data in border_edges:
                    compute_inset_vectors(region, border_data)

            poly_verts = poly.vertices

            for vert in poly_verts:

                merged_vert = vert.merged_vertex

                if merged_vert in tmp_extr_vecs:

                    extr1_vec, avg_normal = tmp_extr_vecs[merged_vert]

                else:

                    extr1_vec = compute_per_vertex_extrusion_vector(merged_vert, region)

                    # As an alternative, compute the averaged vertex normal

                    verts_in_sel = (v for v in merged_vert.connected_verts
                                    if polys[v.polygon_id] in region)
                    avg_normal = sum((v.normal for v in verts_in_sel),
                                     Vec3()).normalized() * sign

                    tmp_extr_vecs[merged_vert] = (extr1_vec, avg_normal)

                extr1_vecs[vert.id] = extr1_vec
                avg_normals[vert.id] = avg_normal

            # the vector used to extrude an individual poly is just its normalized normal
            extr2_vec = poly.normal.normalized()
            extr2_vecs[poly_id] = extr2_vec
            # store the per-region averaged polygon normal
            extr3_vecs[poly_id] = extr3_vec

            # Compute the vectors used to inset individual polys

            poly_verts.append(poly_verts[0])

            for i in range(len(poly_verts) - 1):

                v0 = poly_verts[i - (2 if i == 0 else 1)]
                v1 = poly_verts[i]
                v2 = poly_verts[i + 1]
                vec1 = (v0.get_pos() - v1.get_pos()).normalized()
                vec2 = (v2.get_pos() - v1.get_pos()).normalized()
                cosine = vec1.dot(vec2)

                if cosine < -.999:
                    inset_scale = 1.
                    inset2_vec = vec1.cross(extr2_vec).normalized()
                else:
                    sine = sin(acos(min(1., cosine)) * .5)
                    inset_scale = 1. / sine if sine > .0001 else 0.
                    inset2_vec = (vec1 + vec2).normalized()
                    cross_vec = vec2.cross(vec1).normalized()
                    # reverse inset vector when inner corner angle > 180 degrees
                    # (i.e. where the polygon is concave)
                    inset2_vec *= -1. if cross_vec.dot(extr2_vec) < 0. else 1.

                inset2_vecs[v1.id] = Vec4(*inset2_vec, inset_scale)

            # Determine which sides of each triangle should be extruded/inset

            sides[poly_id] = poly_sides = []
            edge_vert_ids2 = [edge[::sign] for edge in poly.edges]

            for tri_vert_ids in poly:

                vi1, vi2, vi3 = tri_vert_ids[::sign]
                mvs = (merged_verts[vi1], merged_verts[vi2])
                s1 = 1 if mvs in edge_mvs or mvs[::-1] in edge_mvs else 0
                mvs = (merged_verts[vi2], merged_verts[vi3])
                s2 = 1 if mvs in edge_mvs or mvs[::-1] in edge_mvs else 0
                mvs = (merged_verts[vi3], merged_verts[vi1])
                s3 = 1 if mvs in edge_mvs or mvs[::-1] in edge_mvs else 0
                sides1 = s1 << 2 | s2 << 1 | s3

                s1 = 1 if (vi1, vi2) in edge_vert_ids2 else 0
                s2 = 1 if (vi2, vi3) in edge_vert_ids2 else 0
                s3 = 1 if (vi3, vi1) in edge_vert_ids2 else 0
                sides2 = s1 << 2 | s2 << 1 | s3

                poly_sides.append((sides1, sides2))

        return data

    def initialize_extr_inset_preview(self, extrusion, inset, extr_inset_type):
        """
        Create a temporary geom for previewing extrusions and insets.

        """

        selected_poly_ids = set(self._selected_subobj_ids["poly"])

        if not selected_poly_ids:
            return False

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]
        selected_polys = set(polys[p_id] for p_id in selected_poly_ids)

        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        geoms = self._geoms
        geoms["poly"]["pickable"].show(picking_mask)
        geoms["poly"]["selected"].hide()

        # Define a GeomVertexFormat that accommodates custom "averaged_normal",
        # "sides", "extrusion*_vec" and "inset*_vec" attributes. There are multiple
        # versions of each of the latter two; one or two for contiguous polygon regions
        # and one for individual polys.

        array_format = GeomVertexArrayFormat()
        array_format.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)
        array_format.add_column(InternalName.make("normal"), 3, Geom.NT_float32, Geom.C_normal)
        array_format.add_column(InternalName.make("averaged_normal"), 3, Geom.NT_float32, Geom.C_vector)
        array_format.add_column(InternalName.make("sides"), 2, Geom.NT_int32, Geom.C_other)
        array_format.add_column(InternalName.make("extrusion1_vec"), 3, Geom.NT_float32, Geom.C_vector)
        array_format.add_column(InternalName.make("extrusion2_vec"), 3, Geom.NT_float32, Geom.C_vector)
        array_format.add_column(InternalName.make("extrusion3_vec"), 3, Geom.NT_float32, Geom.C_vector)
        array_format.add_column(InternalName.make("inset1_vec"), 4, Geom.NT_float32, Geom.C_vector)
        array_format.add_column(InternalName.make("inset2_vec"), 4, Geom.NT_float32, Geom.C_vector)

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(array_format)
        vertex_format = GeomVertexFormat.register_format(vertex_format)

        vertex_data = GeomVertexData("poly_data", vertex_format, Geom.UH_dynamic)
        vertex_data.reserve_num_rows(sum(p.vertex_count for p in selected_polys))

        prim = GeomTriangles(Geom.UH_static)
        prim.reserve_num_vertices(sum(len(p) for p in selected_polys))
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        normal_writer = GeomVertexWriter(vertex_data, "normal")
        avg_normal_writer = GeomVertexWriter(vertex_data, "averaged_normal")
        sides_writer = GeomVertexWriter(vertex_data, "sides")
        extr1_writer = GeomVertexWriter(vertex_data, "extrusion1_vec")
        extr2_writer = GeomVertexWriter(vertex_data, "extrusion2_vec")
        extr3_writer = GeomVertexWriter(vertex_data, "extrusion3_vec")
        inset1_writer = GeomVertexWriter(vertex_data, "inset1_vec")
        inset2_writer = GeomVertexWriter(vertex_data, "inset2_vec")

        count = 0
        sign = -1 if self.owner.has_flipped_normals() else 1
        data = self.__compute_extr_inset_data(extrusion, inset)

        for poly_id in selected_poly_ids:

            avg_normals = data["avg_normals"]
            extr1_vecs = data["extr1_vecs"]
            extr2_vec = data["extr2_vecs"][poly_id]
            extr3_vec = data["extr3_vecs"][poly_id]
            inset1_vecs = data["inset1_vecs"]
            inset2_vecs = data["inset2_vecs"]

            for tri_vert_ids, sides in zip(polys[poly_id], data["sides"][poly_id]):

                for vi in tri_vert_ids[::sign]:
                    vert = verts[vi]
                    pos_writer.add_data3(vert.get_pos())
                    normal_writer.add_data3(vert.normal * sign)
                    avg_normal_writer.add_data3(avg_normals[vi])
                    extr1_writer.add_data3(extr1_vecs[vi])
                    extr2_writer.add_data3(extr2_vec * sign)
                    extr3_writer.add_data3(extr3_vec * sign)
                    inset1_writer.add_data4(inset1_vecs.get(vi, Vec4()))
                    inset2_writer.add_data4(inset2_vecs[vi])

                i1 = count
                i2 = count + 1
                i3 = count + 2
                prim.add_vertices(i1, i2, i3)

                for i in (i1, i2, i3):
                    sides_writer.set_row(i)
                    # write the visible outer edges to the "sides" vertex data column;
                    # this will prevent the geometry shader from generating unwanted
                    # internal polygons (extruded from inner diagonals or shared edges)
                    sides_writer.add_data2i(sides)

                count += 3

        geom = Geom(vertex_data)
        geom.add_primitive(prim)
        geom_node = GeomNode("inset_geom")
        geom_node.add_geom(geom)
        inset_geom = self.origin.attach_new_node(geom_node)
        inset_geom.show_through(render_mask)
        sh = shaders.extrusion_inset
        vs = sh.VERT_SHADER
        fs = sh.FRAG_SHADER
        gs = sh.GEOM_SHADER
        shader = Shader.make(Shader.SL_GLSL, vs, fs, gs)
        inset_geom.set_shader(shader)
        inset_geom.set_shader_input("extrusion", extrusion)
        inset_geom.set_shader_input("inset", inset)
        inset_geom.set_shader_input("extr_inset_type", extr_inset_type)
        self._tmp_geom = inset_geom

        if self.owner.has_flipped_normals():
            state = inset_geom.get_state()
            cull_attr = CullFaceAttrib.make(CullFaceAttrib.M_cull_counter_clockwise)
            state = state.add_attrib(cull_attr)
            inset_geom.set_state(state)

        return True

    def clear_extr_inset_preview(self):

        picking_mask = Mgr.get("picking_mask")
        self._geoms["poly"]["pickable"].show_through(picking_mask)
        self._geoms["poly"]["selected"].show()

        if self._tmp_geom:
            self._tmp_geom.clear_shader()
            self._tmp_geom.remove_node()
            self._tmp_geom = None

    def set_extrusion(self, extrusion):

        if self._tmp_geom:
            self._tmp_geom.set_shader_input("extrusion", extrusion)

    def set_inset(self, inset):

        if self._tmp_geom:
            self._tmp_geom.set_shader_input("inset", inset)

    def set_extrusion_inset_type(self, extr_inset_type):

        if self._tmp_geom:
            self._tmp_geom.set_shader_input("extr_inset_type", extr_inset_type)

    def __detach_polys_to_extr_inset(self, regions, merged_verts_to_resmooth):
        """
        Split merged edges (and merged vertices connecting them) that form the
        borders of the given polygon regions.

        """

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        selected_poly_ids = self._selected_subobj_ids["poly"]

        for poly_id in selected_poly_ids:

            poly = polys[poly_id]

            for i, region in enumerate(regions):
                if poly in region:
                    break

            for edge in poly.edges:

                merged_edge = edge.merged_edge

                if len(merged_edge) > 1:

                    e1_id, e2_id = merged_edge
                    other_edge_id = e1_id if edge.id == e2_id else e2_id
                    other_edge = edges[other_edge_id]

                    if polys[other_edge.polygon_id] not in region:

                        merged_edge.remove(edge.id)
                        new_merged_edge = Mgr.do("create_merged_edge", self, edge.id)
                        merged_edges[edge.id] = new_merged_edge

                        for vert_id in edge:

                            merged_vert = merged_verts[vert_id]
                            new_merged_vert = Mgr.do("create_merged_vert", self)

                            for v_id in merged_vert[:]:
                                if polys[verts[v_id].polygon_id] in region:
                                    merged_vert.remove(v_id)
                                    new_merged_vert.append(v_id)
                                    merged_verts[v_id] = new_merged_vert
                                    merged_verts_to_resmooth.add(merged_vert)
                                    merged_verts_to_resmooth.add(new_merged_vert)

    def __create_extr_inset_polygon(self, ordered_verts, ordered_pos):
        """
        Create a single extruded/inset polygon between the given merged ordered_verts
        (ordered counter-clockwise). Newly created vertices will be added to these
        merged vertices and given the corresponding position from ordered_pos.

        """

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        ordered_polys = self._ordered_polys
        merged_verts = self.merged_verts
        merged_edges = self.merged_edges

        poly_verts = []
        poly_edges = []
        poly_tris = []

        # Create the vertices

        for i in range(4):
            pos = ordered_pos[i]
            vert = Mgr.do("create_vert", self, pos)
            vert_id = vert.id
            verts[vert_id] = vert
            merged_vert = ordered_verts[i]
            merged_vert.append(vert_id)
            merged_verts[vert_id] = merged_vert
            vert.row_index = i
            poly_verts.append(vert)

        poly_verts_ = poly_verts[1:] + [poly_verts[0]]

        # Define triangulation

        vi1, vi2, vi3, vi4 = vert_ids = [vert.id for vert in poly_verts]
        vert_ids_ = [vi2, vi3, vi4, vi1]
        poly_tris.append((vi1, vi2, vi4))
        poly_tris.append((vi2, vi3, vi4))

        # Create the edges

        for i in range(4):
            edge = Mgr.do("create_edge", self, (vert_ids_[i - 1], vert_ids_[i]))
            edge_id = edge.id
            poly_verts_[i].add_edge_id(edge_id)
            edges[edge_id] = edge
            poly_edges.append(edge)

        for i in range(4):
            poly_verts[i].add_edge_id(poly_edges[i].id)

        def merge_edge(edge):

            border_edge_id = edge.id
            merged_vert1, merged_vert2 = [merged_verts[v_id] for v_id in edge]

            for vert_id in merged_vert1:

                vert = verts[vert_id]

                for edge_id in vert.edge_ids:

                    if edge_id not in merged_edges:
                        continue

                    merged_edge = merged_edges[edge_id]

                    if len(merged_edge) > 1:
                        continue

                    vert1_id, vert2_id = edges[edge_id]
                    other_vert_id = vert1_id if merged_verts[vert2_id] is merged_vert1 else vert2_id

                    if merged_verts[other_vert_id] is merged_vert2:
                        # add the given edge to an existing merged edge
                        merged_edge.append(border_edge_id)
                        merged_edges[border_edge_id] = merged_edge
                        break

                else:

                    continue

                break

            else:

                # add the given edge to a newly created merged edge
                merged_edge = Mgr.do("create_merged_edge", self, border_edge_id)
                merged_edges[border_edge_id] = merged_edge

        for edge in poly_edges:
            merge_edge(edge)

        poly = Mgr.do("create_poly", self, poly_tris, poly_edges, poly_verts)
        ordered_polys.append(poly)
        polys[poly.id] = poly
        poly.update_center_pos()
        poly.update_normal()
        normal = poly.normal.normalized()

        for vert in poly_verts:
            vert.normal = normal

        return poly, poly_edges, poly_verts

    def extrude_inset_polygons(self, extrusion, inset, extr_inset_type):
        """
        Extrude and/or inset the selected polygons.
        The selected polygons are detached and new polygons are created to connect
        their borders with those of the polygons they were detached from.

        """

        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        selected_poly_ids = set(self._selected_subobj_ids["poly"])
        selected_polys = set(polys[p_id] for p_id in selected_poly_ids)

        if not selected_poly_ids:
            return False

        sign = -1 if self.owner.has_flipped_normals() else 1
        data = self.__compute_extr_inset_data(extrusion, inset)
        regions = data["regions"]

        borders = []

        if extr_inset_type % 2 == 0:  # poly region

            vertex_data_lists = []
            old_merged_verts = {}

            for border_edges in data["borders"]:

                if not border_edges:
                    continue

                lists = {}
                vertex_data_lists.append(lists)
                border_data = []
                borders.append(border_data)

                for border_edge_loop, intersection_data in border_edges:

                    border_merged_verts = [merged_verts[e[1]] for e in border_edge_loop]
                    tmp_merged_verts = {}

                    for index, split_merged_vert in intersection_data:

                        old_merged_vert = border_merged_verts[index]

                        for v_id in split_merged_vert:
                            old_merged_verts[v_id] = old_merged_vert
                            merged_verts[v_id] = split_merged_vert

                        tmp_merged_verts[split_merged_vert] = old_merged_vert
                        border_merged_verts[index] = split_merged_vert

                    data_lists = []
                    border_data.append(data_lists)

                    for merged_vert in border_merged_verts:

                        if merged_vert in tmp_merged_verts:
                            vert_id_set = set(tmp_merged_verts[merged_vert])
                        else:
                            vert_id_set = set(merged_vert)

                        # store the following vertex data in a list:
                        #     1) a single vertex ID to retrieve the merged vertex
                        #        associated with it after extrusion/inset (will be
                        #        inserted into the list later);
                        #     2) set of IDs of all vertices that were merged
                        #        before extrusion/inset;
                        #     3) position of the vertices before extrusion/inset;
                        #     4) position of the vertices after extrusion/inset
                        #        (will be appended to the list later);
                        l = [vert_id_set, merged_vert.get_pos()]
                        lists[merged_vert] = l
                        data_lists.append(l)

                    del tmp_merged_verts

        extr_vert_ids = []
        border_vert_ids = set()
        merged_verts_to_resmooth = set()

        for poly_id in selected_poly_ids:

            poly = polys[poly_id]
            extr_vert_ids.extend(poly.vertex_ids)
            avg_normals = data["avg_normals"]
            extr1_vecs = data["extr1_vecs"]
            extr2_vec = data["extr2_vecs"][poly_id] * sign
            extr3_vec = data["extr3_vecs"][poly_id] * sign
            inset1_vecs = data["inset1_vecs"]
            inset2_vecs = data["inset2_vecs"]

            if extr_inset_type % 2 == 0:  # poly region
                if vertex_data_lists:
                    for i, region in enumerate(regions):
                        if poly in region:
                            lists = vertex_data_lists[i]
                            break
                else:
                    lists = {}
            else:
                data_lists = []
                border_data = [data_lists]
                borders.append(border_data)

            for vert in poly.vertices:

                old_pos = vert.get_pos()
                merged_vert = vert.merged_vertex
                avg_normal = avg_normals[vert.id]
                extr1_vec = extr1_vecs[vert.id]
                extr_vec = (extr1_vec, extr2_vec, extr3_vec, extr2_vec,
                            avg_normal, vert.normal * sign)[extr_inset_type]
                x, y, z, s = inset1_vecs.get(vert.id, Vec4())
                inset1_vec = Vec3(x, y, z) * s
                x, y, z, s = inset2_vecs[vert.id]
                inset2_vec = Vec3(x, y, z) * s
                inset_vec = (inset1_vec, inset2_vec)[extr_inset_type % 2]
                pos = old_pos + extr_vec * extrusion + inset_vec * inset
                vert.set_pos(pos)

                if extr_inset_type % 2 == 0:  # poly region

                    if merged_vert in lists:

                        border_vert_ids.add(vert.id)
                        l = lists[merged_vert]

                        if len(l) == 2:
                            l.insert(0, vert.id)
                            l.append(pos)

                else:  # individual polys

                    border_vert_ids.add(vert.id)
                    data_lists.append([vert.id, set(merged_vert), old_pos, pos])

                    if len(merged_vert) > 1:
                        merged_vert.remove(vert.id)
                        new_merged_vert = Mgr.do("create_merged_vert", self, vert.id)
                        merged_verts[vert.id] = new_merged_vert
                        merged_verts_to_resmooth.add(merged_vert)
                        merged_verts_to_resmooth.add(new_merged_vert)

        # restore the original merged verts
        if extr_inset_type % 2 == 0:  # poly region
            merged_verts.update(old_merged_verts)

        # Detach the selected polygons

        if extr_inset_type % 2 == 0:  # poly region

            # before detaching, split the merged vertices where the border(s)
            # self-intersect
            for border_edges in data["borders"]:
                for border_edge_loop, intersection_data in border_edges:
                    border_merged_verts = [merged_verts[e[1]] for e in border_edge_loop]
                    for index, split_merged_vert in intersection_data:
                        old_merged_vert = border_merged_verts[index]
                        for v_id in split_merged_vert:
                            merged_verts[v_id] = split_merged_vert
                            old_merged_vert.remove(v_id)

            self.__detach_polys_to_extr_inset(regions, merged_verts_to_resmooth)

        else:  # individual polys

            for poly in selected_polys:

                # completely detach every polygon in the selection
                for edge_id in poly.edge_ids:

                    merged_edge = merged_edges[edge_id]

                    if len(merged_edge) > 1:
                        merged_edge.remove(edge_id)
                        merged_edge = Mgr.do("create_merged_edge", self, edge_id)
                        merged_edges[edge_id] = merged_edge

        self.update_normal_sharing(merged_verts_to_resmooth)

        if GD["subobj_edit_options"]["normal_preserve"]:

            vert_ids = set()

            for merged_vert in merged_verts_to_resmooth:
                vert_ids.update(merged_vert)

            self.lock_normals(True, vert_ids)

        update_bounds = False if borders else True
        self.update_vertex_positions(extr_vert_ids, update_bounds=update_bounds)
        self.update_vertex_normals(merged_verts_to_resmooth)

        # Create polygons between original and extruded edge positions

        new_verts = []
        new_edges = []
        new_polys = []
        start_verts = {}  # maps extruded (border) vertex IDs to start merged vertices
        xformed_verts = self._transformed_verts
        xformed_verts.update(self._verts_to_transf["poly"])

        for border_data in borders:

            for data_lists in border_data:

                data_lists.append(data_lists[0])

                for i in range(len(data_lists) - 1):

                    vi1, s1, old_pos1, new_pos1 = data_lists[i]
                    # the merged vertex currently associated with the extruded vi1 vertex
                    # is the last of the 4 counter-clockwise ordered merged vertices that
                    # will be used to create the polygon between an extruded edge and its
                    # original edge
                    extr_mv1 = merged_verts[vi1]
                    # the difference of the set of vertex IDs, contained in the merged
                    # vertex that existed before the extrusion/inset, with the IDs of the
                    # vertices that lie on the selection borders; the resulting set contains
                    # the IDs of the vertices left behind when detaching the extruded/inset
                    # polygon
                    diff = s1 - border_vert_ids

                    # find an existing merged vertex to add a new "start" vertex to (a
                    # vertex to be created at the position of the vi1 vertex before it was
                    # extruded/inset), or create a new one;
                    # it is the first of the 4 counter-clockwise ordered merged vertices that
                    # will be used to create the polygon between an extruded edge and its
                    # original edge
                    if diff:
                        # use the merged vertex currently associated with the vert(s) left
                        # behind after extrusion/inset
                        start_mv1 = merged_verts[diff.pop()] 
                    elif extr_mv1.id in start_verts:
                        # use the merged vertex previously created for a different start
                        # vertex at the same position
                        start_mv1 = start_verts[extr_mv1.id]
                    else:
                        # use a new merged vertex
                        start_mv1 = Mgr.do("create_merged_vert", self)

                    vi2, s2, old_pos2, new_pos2 = data_lists[i + 1]
                    # the third of the 4 counter-clockwise ordered merged vertices
                    extr_mv2 = merged_verts[vi2]
                    diff = s2 - border_vert_ids

                    # the second of the 4 counter-clockwise ordered merged vertices
                    if diff:
                        start_mv2 = merged_verts[diff.pop()] 
                    elif extr_mv2.id in start_verts:
                        start_mv2 = start_verts[extr_mv2.id]
                    else:
                        start_mv2 = Mgr.do("create_merged_vert", self)

                    ordered_verts = (start_mv1, start_mv2, extr_mv2, extr_mv1)
                    xformed_verts.update(ordered_verts)
                    ordered_pos = (old_pos1, old_pos2, new_pos2, new_pos1)
                    poly, poly_edges, poly_verts = self.__create_extr_inset_polygon(
                        ordered_verts, ordered_pos
                    )

                    # update start_verts dict
                    for vi in s1:
                        start_verts[vi] = merged_verts[poly_verts[0].id]
                    for vi in s2:
                        start_verts[vi] = merged_verts[poly_verts[1].id]

                    new_verts.extend(poly_verts)
                    new_edges.extend(poly_edges)
                    new_polys.append(poly)

        if new_polys:
            self._create_new_geometry(new_verts, new_edges, new_polys)

        Mgr.get("selection").update()

        return True


class ExtrusionInsetManager:
    """ PolygonEditManager class mix-in """

    def __init__(self):

        self._indiv_poly_extr_inset = False
        self._poly_extr_vec_type = 0
        self._poly_extrusion = 0.
        self._poly_inset = 0.
        self._geom_data_objs = []
        self._excluded_geom_data_objs = []

        Mgr.add_app_updater("poly_extr_inset", self.__update_extrusion_inset)

        add_state = Mgr.add_state
        add_state("poly_extr_inset_preview_mode", -10,
                  self.__enter_poly_extr_inset_preview_mode,
                  self.__exit_poly_extr_inset_preview_mode)

        bind = Mgr.bind_state
        bind("poly_extr_inset_preview_mode", "extr/inset preview -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("poly_extr_inset_preview_mode", "quit extr/inset preview", "escape",
             lambda: Mgr.exit_state("poly_extr_inset_preview_mode"))
        bind("poly_extr_inset_preview_mode", "cancel extr/inset preview", "mouse3",
             lambda: Mgr.exit_state("poly_extr_inset_preview_mode"))
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("poly_extr_inset_preview_mode", "extr/inset preview ctrl-right-click",
             f"{mod_ctrl}|mouse3", lambda: Mgr.update_remotely("main_context"))

        status_data = GD["status"]
        mode_text = "Extrude/inset polygons"
        info_text = "Use control panel to extrude/inset selected polygons; RMB to cancel;"
        info_text += " <Space> to navigate"
        status_data["extr_inset_polys"] = {"mode": mode_text, "info": info_text}

    def __init_poly_extr_inset_preview_mode(self):

        Mgr.exit_states(min_persistence=-99)
        selection = Mgr.get("selection_top")
        geom_data_objs = [obj.geom_obj.geom_data_obj for obj in selection]
        extr_inset_type = self._poly_extr_vec_type << 1 | self._indiv_poly_extr_inset

        for data_obj in geom_data_objs:
            if data_obj.initialize_extr_inset_preview(self._poly_extrusion,
                    self._poly_inset, extr_inset_type):
                self._geom_data_objs.append(data_obj)
            else:
                self._excluded_geom_data_objs.append(data_obj)

        if self._geom_data_objs:

            for data_obj in self._excluded_geom_data_objs:
                data_obj.set_pickable(False)

            Mgr.enter_state("poly_extr_inset_preview_mode")

        else:

            self._excluded_geom_data_objs = []

    def __enter_poly_extr_inset_preview_mode(self, prev_state_id, active):

        GD["active_transform_type"] = ""
        Mgr.update_app("active_transform_type", "")
        Mgr.update_app("status", ["extr_inset_polys"])

    def __exit_poly_extr_inset_preview_mode(self, next_state_id, active):

        if not active:

            for data_obj in self._geom_data_objs:
                data_obj.clear_extr_inset_preview()

            for data_obj in self._excluded_geom_data_objs:
                data_obj.set_pickable()

            self._geom_data_objs = []
            self._excluded_geom_data_objs = []

    def __update_extrusion_inset(self, update_type, *args):

        if update_type == "preview":
            self.__init_poly_extr_inset_preview_mode()
        elif update_type == "individual":
            self._indiv_poly_extr_inset = args[0]
            extr_inset_type = self._poly_extr_vec_type << 1 | args[0]
            for data_obj in self._geom_data_objs:
                data_obj.set_extrusion_inset_type(extr_inset_type)
        elif update_type == "extr_vec_type":
            self._poly_extr_vec_type = args[0]
            extr_inset_type = args[0] << 1 | self._indiv_poly_extr_inset
            for data_obj in self._geom_data_objs:
                data_obj.set_extrusion_inset_type(extr_inset_type)
        elif update_type == "extrusion":
            self._poly_extrusion = args[0]
            for data_obj in self._geom_data_objs:
                data_obj.set_extrusion(args[0])
        elif update_type == "inset":
            self._poly_inset = args[0]
            for data_obj in self._geom_data_objs:
                data_obj.set_inset(args[0])
        elif update_type == "apply":
            self.__extrude_inset_polygons()

    def __extrude_inset_polygons(self):

        preview_mode = Mgr.is_state_active("poly_extr_inset_preview_mode")

        if preview_mode:
            for data_obj in self._geom_data_objs:
                data_obj.clear_extr_inset_preview()
        else:
            Mgr.exit_states(min_persistence=-99)

        selection = Mgr.get("selection_top")
        changed_objs = []
        # pack the extrusion vector type and extrude/inset type (per-region or per-poly)
        # options into a single integer, which can then be used to index into a list of
        # available extrusion and inset vectors
        extr_inset_type = self._poly_extr_vec_type << 1 | self._indiv_poly_extr_inset

        for obj in selection:
            if obj.geom_obj.geom_data_obj.extrude_inset_polygons(self._poly_extrusion,
                    self._poly_inset, extr_inset_type):
                changed_objs.append(obj)

        if preview_mode:
            for data_obj in self._geom_data_objs:
                data_obj.initialize_extr_inset_preview(self._poly_extrusion,
                    self._poly_inset, extr_inset_type)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in changed_objs:
            geom_data_obj = obj.geom_obj.geom_data_obj
            obj_data[obj.id] = geom_data_obj.get_data_to_store("subobj_change")
            data = geom_data_obj.get_data_to_store("prop_change", "subobj_transform", "check")
            obj_data[obj.id].update(data)

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'Extrude/inset polys of "{obj.name}"'
        else:
            event_descr = 'Extrude/inset polys of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)
