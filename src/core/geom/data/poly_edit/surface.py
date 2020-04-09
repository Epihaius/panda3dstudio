from ....base import *


class SurfaceMixin:
    """ PolygonEditMixin class mix-in """

    def get_polygon_surface(self, poly_id):

        polys = self._subobjs["poly"]
        poly = polys[poly_id]
        poly_ids = set([poly_id])
        neighbor_ids = list(poly.neighbor_ids)

        while neighbor_ids:
            neighbor_id = neighbor_ids.pop()
            neighbor = polys[neighbor_id]
            neighbor_ids.extend(neighbor.neighbor_ids - poly_ids)
            poly_ids.add(neighbor_id)

        return [polys[p_id] for p_id in poly_ids]

    def invert_polygon_surfaces(self):

        # Inverting a surface of contiguous polygons comes down to flipping each polygon.
        # Flipping a polygon can be accomplished by swapping properties of every two
        # vertices equally far removed from a starting vertex (pair) at either side of
        # that vertex (pair).
        # If the triangulation is symmetric, first identifying a center of that symmetry
        # and choosing the starting vertex (pair) at that center can avoid the need for
        # retriangulation.

        selection_ids = self._selected_subobj_ids
        selected_vert_ids = selection_ids["vert"]
        selected_edge_ids = selection_ids["edge"]
        selected_poly_ids = selection_ids["poly"]
        selected_normal_ids = selection_ids["normal"]

        if not selected_poly_ids:
            return

        poly_ids = set(selected_poly_ids)
        polys_to_flip = set()

        # determine the contiguous surfaces that the selected polys belong to
        while poly_ids:
            poly_id = poly_ids.pop()
            surface = self.get_polygon_surface(poly_id)
            polys_to_flip.update(surface)
            poly_ids.difference_update([poly.id for poly in surface])

        verts = self._subobjs["vert"]
        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        shared_normals = self.shared_normals
        combined_subobjs = {"vert": merged_verts, "edge": merged_edges, "normal": shared_normals}
        tmp_combined_subobjs = {}
        xformed_verts = self._transformed_verts
        tri_change = self._tri_change
        lock_change = self._normal_lock_change
        uv_change = self._uv_change
        uv_set_ids = set()
        sel_change = False
        subobjs_to_select = {"vert": set(), "edge": set(), "normal": set()}
        subobjs_to_deselect = {"vert": set(), "edge": set(), "normal": set()}
        verts_to_swap = []

        for poly in polys_to_flip:

            poly.reverse_normal()
            poly_vert_ids = poly.vertex_ids
            l = len(poly_vert_ids)
            l_half = l // 2
            vert_ids1 = poly_vert_ids[::-1][:l_half]
            vert_ids2 = poly_vert_ids[:l_half]

            if len(poly_vert_ids) > 4:

                # Determine how many triangles each vertex belongs to and then check whether
                # the triangulation is symmetric. If it is symmetric, it need not be changed.

                vert_ids = []

                for tri_vert_ids in poly:
                    vert_ids.extend(tri_vert_ids)

                tri_membership = []

                for vert_id in poly_vert_ids:
                    # determine how many triangles each vertex belongs to
                    tri_membership.append(vert_ids.count(vert_id))

                tri_membership_str = " ".join(map(str, tri_membership * 2))
                tri_membership_rev_str = " ".join(map(str, tri_membership[::-1]))
                offset = tri_membership_str.find(tri_membership_rev_str)

                if offset != -1:

                    offset = len(tri_membership_str[:offset].split())

                    # if the stringified reversed list is in the stringified doubled list,
                    # then the list is circularly symmetrical;
                    # if a center point of symmetry is at index i in a list with length l,
                    # then it is at index (l-i-1) in the reversed list;
                    # the offset of the reversed list in the doubled list equals i - (l-i-1),
                    # or 2 * i - l + 1, so i equals (offset + l - 1) // 2
                    i = (offset + l - 1) // 2

                    poly_vert_ids2 = poly_vert_ids * 2
                    j = i + 1
                    vert_ids1 = poly_vert_ids2[j-l_half:j][::-1]
                    vert_ids2 = poly_vert_ids2[j:j+l_half]

                    if l % 2 == 1:

                        # If there is an uneven amount of vertices, the determined
                        # center point of symmetry could be in between two vertices
                        # (as is always the case with an even vertex count), but it
                        # could just as well be *at* a particular vertex.

                        tri_membership2 = tri_membership * 2

                        if tri_membership2[j-l_half:j][::-1] != tri_membership2[j:j+l_half]:
                            # the center point of symmetry is located at a particular vertex,
                            # which can therefore keep its properties (except its normal, which
                            # will still need to be reversed)
                            vert_ids1 = vert_ids2[::-1]
                            vert_ids2 = poly_vert_ids2[i-l_half:i]

                else:

                    # Since the triangulation is not symmetric, it needs to be changed.

                    src_triangles = {}
                    dest_triangles = {}

                    for tri_vert_ids in poly:

                        for vert_id in tri_vert_ids:
                            src_triangles.setdefault(vert_id, []).append(tri_vert_ids)

                        dest_triangles[tri_vert_ids] = []

                    for src_vert_id, dest_vert_id in zip(vert_ids1 + vert_ids2, vert_ids2 + vert_ids1):
                        for tri_vert_ids in src_triangles[src_vert_id]:
                            dest_triangles[tri_vert_ids].append(dest_vert_id)

                    if l % 2 == 1:

                        vert_id = poly_vert_ids[l_half]

                        for tri_vert_ids in src_triangles[vert_id]:
                            dest_triangles[tri_vert_ids].append(vert_id)

                    new_tri_data = []

                    for new_tri_vert_ids in dest_triangles.values():

                        ordered_vert_ids = {}

                        for vert_id in new_tri_vert_ids:
                            ordered_vert_ids[poly_vert_ids.index(vert_id)] = vert_id

                        vert_ids = []

                        for index in sorted(ordered_vert_ids):
                            vert_ids.append(ordered_vert_ids[index])

                        new_tri_data.append(tuple(vert_ids))

                    poly.set_triangle_data(new_tri_data)
                    tri_change.add(poly.id)

            # switch vertices by swapping their properties
            for vert1_id, vert2_id in zip(vert_ids1, vert_ids2):

                vert1 = verts[vert1_id]
                vert2 = verts[vert2_id]
                verts_to_swap.extend((vert1, vert2))
                merged_vert1 = merged_verts[vert1_id]
                merged_vert2 = merged_verts[vert2_id]
                pos1 = vert1.get_pos()
                pos2 = vert2.get_pos()
                col1 = vert1.color
                col2 = vert2.color
                uvs1 = vert1.get_uvs()
                uvs2 = vert2.get_uvs()
                vert1_selected = vert1_id in selected_vert_ids
                vert2_selected = vert2_id in selected_vert_ids
                normal1 = vert1.normal * -1.
                normal2 = vert2.normal * -1.
                shared_normal1 = shared_normals[vert1_id]
                shared_normal2 = shared_normals[vert2_id]
                normal1_selected = vert1_id in selected_normal_ids
                normal2_selected = vert2_id in selected_normal_ids
                locked_normal1 = vert1.has_locked_normal()
                locked_normal2 = vert2.has_locked_normal()
                merged_vert1.remove(vert1_id)
                merged_vert1.append(vert2_id)
                merged_vert2.remove(vert2_id)
                merged_vert2.append(vert1_id)
                merged_verts[vert1_id] = merged_vert2
                merged_verts[vert2_id] = merged_vert1
                xformed_verts.add(merged_vert1)
                xformed_verts.add(merged_vert2)
                vert1.set_pos(pos2)
                vert2.set_pos(pos1)
                vert1.color = col2
                vert2.color = col1
                vert1.set_uvs(uvs2)
                vert2.set_uvs(uvs1)

                if uvs1 != uvs2:
                    uv_change.update((vert1_id, vert2_id))
                    uv_set_ids.update(uvs1, uvs2)

                if vert1_selected != vert2_selected:

                    sel_change = True
                    subobjs_to_select["vert"].add(vert1_id if vert2_selected else vert2_id)
                    subobjs_to_deselect["vert"].add(vert1_id if vert1_selected else vert2_id)

                    if "vert" not in tmp_combined_subobjs:
                        tmp_sel_subobj = Mgr.do("create_merged_vert", self)
                        tmp_desel_subobj = Mgr.do("create_merged_vert", self)
                        tmp_combined_subobjs["vert"] = (tmp_sel_subobj, tmp_desel_subobj)

                vert1.normal = normal2
                vert2.normal = normal1
                shared_normal1.discard(vert1_id)
                shared_normal1.add(vert2_id)
                shared_normal2.discard(vert2_id)
                shared_normal2.add(vert1_id)
                shared_normals[vert1_id] = shared_normal2
                shared_normals[vert2_id] = shared_normal1

                if normal1_selected != normal2_selected:

                    sel_change = True
                    subobjs_to_select["normal"].add(vert1_id if normal2_selected else vert2_id)
                    subobjs_to_deselect["normal"].add(vert1_id if normal1_selected else vert2_id)

                    if "normal" not in tmp_combined_subobjs:
                        tmp_sel_subobj = Mgr.do("create_shared_normal", self)
                        tmp_desel_subobj = Mgr.do("create_shared_normal", self)
                        tmp_combined_subobjs["normal"] = (tmp_sel_subobj, tmp_desel_subobj)

                if vert1.lock_normal(locked_normal2):
                    lock_change.add(vert1_id)

                if vert2.lock_normal(locked_normal1):
                    lock_change.add(vert2_id)

                edge1_id = vert1.edge_ids[0]
                edge2_id = vert2.edge_ids[1]

                if edge1_id != edge2_id:

                    merged_edge1 = merged_edges[edge1_id]
                    merged_edge2 = merged_edges[edge2_id]
                    merged_edge1.remove(edge1_id)
                    merged_edge1.append(edge2_id)
                    merged_edge2.remove(edge2_id)
                    merged_edge2.append(edge1_id)
                    merged_edges[edge1_id] = merged_edge2
                    merged_edges[edge2_id] = merged_edge1

                    edge1_selected = edge1_id in selected_edge_ids
                    edge2_selected = edge2_id in selected_edge_ids

                    if edge1_selected != edge2_selected:

                        sel_change = True
                        subobjs_to_select["edge"].add(edge1_id if edge2_selected else edge2_id)
                        subobjs_to_deselect["edge"].add(edge1_id if edge1_selected else edge2_id)

                        if "edge" not in tmp_combined_subobjs:
                            tmp_sel_subobj = Mgr.do("create_merged_edge", self)
                            tmp_desel_subobj = Mgr.do("create_merged_edge", self)
                            tmp_combined_subobjs["edge"] = (tmp_sel_subobj, tmp_desel_subobj)

            for vert_id in set(poly_vert_ids).difference(vert_ids1 + vert_ids2):
                verts[vert_id].normal *= -1.

        toplvl_geom = self._toplvl_node.modify_geom(0)
        vertex_data_top = toplvl_geom.modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")
        uv_writers = {}

        for uv_set_id in uv_set_ids:
            column = "texcoord" if uv_set_id == 0 else f"texcoord.{uv_set_id}"
            uv_writers[uv_set_id] = GeomVertexWriter(vertex_data_top, column)

        for vert in verts_to_swap:
            row = vert.row_index
            pos = vert.get_pos()
            pos_writer.set_row(row)
            pos_writer.set_data3(pos)

        for vert_id in uv_change:

            vert = verts[vert_id]
            row = vert.row_index

            for uv_set_id, uv in vert.get_uvs().items():
                uv_writer = uv_writers[uv_set_id]
                uv_writer.set_row(row)
                uv_writer.set_data2(*uv)

        pos_array = GeomVertexArrayData(vertex_data_top.get_array(0))

        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_array(0, pos_array)
        vertex_data = self._vertex_data["poly_picking"]
        vertex_data.set_array(0, pos_array)

        for uv_set_id in uv_set_ids:
            uv_array = vertex_data_top.get_array(4 + uv_set_id)
            vertex_data_poly.set_array(4 + uv_set_id, GeomVertexArrayData(uv_array))

        geoms = self._geoms

        for geom_type in ("vert", "normal"):
            vertex_data = geoms[geom_type]["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array)
            vertex_data = geoms[geom_type]["sel_state"].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array)

        size = pos_array.data_size_bytes
        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        from_view = memoryview(pos_array).cast("B")
        to_view = memoryview(vertex_data.modify_array(0)).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view
        pos_array = vertex_data.get_array(0)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)

        if tri_change:

            self.create_selection_backup("poly")
            self.clear_selection("poly", False)
            self._poly_selection_data["unselected"] = data_unselected = []
            prim = GeomTriangles(Geom.UH_static)
            prim.set_index_type(Geom.NT_uint32)

            for poly in self.ordered_polys:
                for tri_vert_ids in poly:
                    data_unselected.append(tri_vert_ids)
                    indices = [verts[v_id].row_index for v_id in tri_vert_ids]
                    prim.add_vertices(*indices)

            poly_unselected_geom = geoms["poly"]["unselected"].node().modify_geom(0)
            poly_unselected_geom.set_primitive(0, prim)
            prim = GeomTriangles(prim)
            toplvl_geom.set_primitive(0, prim)
            poly_picking_geom = geoms["poly"]["pickable"].node().modify_geom(0)
            poly_picking_geom.set_primitive(0, prim)
            self.restore_selection_backup("poly")

        normal_writer = GeomVertexWriter(vertex_data_top, "normal")
        sign = -1. if self.owner.has_inverted_geometry() else 1.
        normal_change = self._normal_change

        for poly in polys_to_flip:

            vert_ids = poly.vertex_ids
            normal_change.update(vert_ids)

            for vert_id in vert_ids:
                vert = verts[vert_id]
                normal_writer.set_row(vert.row_index)
                normal_writer.set_data3(vert.normal * sign)

        normal_array = vertex_data_top.get_array(2)
        vertex_data_poly.set_array(2, GeomVertexArrayData(normal_array))

        for geom_type in ("pickable", "sel_state"):
            geom = self._geoms["normal"][geom_type].node().modify_geom(0)
            vertex_data = geom.modify_vertex_data()
            vertex_data.set_array(2, normal_array)

        if sel_change:
            for subobj_type in ("vert", "edge", "normal"):
                if subobj_type in tmp_combined_subobjs:
                    tmp_sel_subobj, tmp_desel_subobj = tmp_combined_subobjs[subobj_type]
                    tmp_sel_subobj.extend(subobjs_to_select[subobj_type])
                    tmp_desel_subobj.extend(subobjs_to_deselect[subobj_type])
                    sel_subobj_id = tmp_sel_subobj.id
                    desel_subobj_id = tmp_desel_subobj.id
                    orig_sel_subobj = combined_subobjs[subobj_type][sel_subobj_id]
                    orig_desel_subobj = combined_subobjs[subobj_type][desel_subobj_id]
                    combined_subobjs[subobj_type][sel_subobj_id] = tmp_sel_subobj
                    combined_subobjs[subobj_type][desel_subobj_id] = tmp_desel_subobj
                    self.update_selection(subobj_type, [tmp_sel_subobj], [tmp_desel_subobj])
                    combined_subobjs[subobj_type][sel_subobj_id] = orig_sel_subobj
                    combined_subobjs[subobj_type][desel_subobj_id] = orig_desel_subobj

        self._normal_sharing_change = True
        model = self.toplevel_obj

        if model.has_tangent_space():
            tangent_flip, bitangent_flip = model.get_tangent_space_flip()
            poly_ids = [p.id for p in polys_to_flip]
            self.update_tangent_space(tangent_flip, bitangent_flip, poly_ids)
        else:
            self.is_tangent_space_initialized = False

        self._update_verts_to_transform("poly")
        self.update_vertex_colors()

        return tri_change, uv_change, sel_change

    def doubleside_polygon_surfaces(self, all_surfaces=False):
        """
        Create inverted duplicates of the surfaces (either all of them if
        all_surfaces is True, or those that the selected polygons belong
        to) and merge their borders with the corresponding borders of the
        originals.

        """

        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        polys = self._subobjs["poly"]

        if all_surfaces:

            polys_to_doubleside = list(polys.values())

        else:

            selected_poly_ids = self._selected_subobj_ids["poly"]

            if not selected_poly_ids:
                return False

            poly_ids = set(selected_poly_ids)
            polys_to_doubleside = set()

            # determine the contiguous surfaces that the selected polys belong to
            while poly_ids:
                poly_id = poly_ids.pop()
                surface = self.get_polygon_surface(poly_id)
                polys_to_doubleside.update(surface)
                poly_ids.difference_update([poly.id for poly in surface])

        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        shared_normals = self.shared_normals
        locked_normal_ids = []
        uv_set_ids = set()
        new_vert_ids = {}
        new_edge_ids = {}
        new_merged_verts = {}
        new_merged_edges = {}
        new_shared_normals = {}
        new_polys = []

        border_merged_edges = [me for me in (merged_edges[e_id] for p in
            polys_to_doubleside for e_id in p.edge_ids) if len(me) == 1]
        border_merged_verts = [merged_verts[edges[me[0]][0]]
            for me in border_merged_edges]

        for poly in polys_to_doubleside:

            poly_verts = []
            poly_edges = []
            poly_tris = []
            new_poly_edges = []

            for vert in poly.vertices[::-1]:

                new_vert = Mgr.do("create_vert", self, vert.get_pos())
                uvs = vert.get_uvs()
                uv_set_ids.update(uvs)
                new_vert.set_uvs(uvs)
                new_vert.color = vert.color
                new_vert.normal = vert.normal * -1.

                if vert.has_locked_normal():
                    new_vert.lock_normal()
                    locked_normal_ids.append(new_vert.id)

                new_vert_ids[vert.id] = new_vert.id
                verts[new_vert.id] = new_vert
                poly_verts.append(new_vert)
                merged_vert = merged_verts[vert.id]
                shared_normal = shared_normals[vert.id]
                new_shared_normals[shared_normal] = Mgr.do("create_shared_normal", self)

                if merged_vert in border_merged_verts:
                    merged_vert.append(new_vert.id)
                    merged_verts[new_vert.id] = merged_vert
                else:
                    new_merged_verts[merged_vert] = Mgr.do("create_merged_vert", self)

            for edge in poly.edges[::-1]:

                v1_id, v2_id = edge
                new_v1_id = new_vert_ids[v1_id]
                new_v2_id = new_vert_ids[v2_id]
                new_edge = Mgr.do("create_edge", self, (new_v2_id, new_v1_id))
                edges[new_edge.id] = new_edge
                poly_edges.append(new_edge)
                new_poly_edges.append(new_edge)
                merged_edge = merged_edges[edge.id]

                if merged_edge in border_merged_edges:
                    merged_edge.append(new_edge.id)
                    merged_edges[new_edge.id] = merged_edge
                else:
                    new_edge_ids[edge.id] = new_edge.id
                    new_merged_edges[merged_edge] = Mgr.do("create_merged_edge", self)

            for i, edge in enumerate(new_poly_edges):
                vert = verts[edge[0]]
                vert.add_edge_id(new_poly_edges[i - 1].id)
                vert.add_edge_id(edge.id)

            for tri_vert_ids in poly:
                poly_tris.append(tuple(new_vert_ids[v_id] for v_id in tri_vert_ids[::-1]))

            new_poly = Mgr.do("create_poly", self, poly_tris, poly_edges, poly_verts)
            polys[new_poly.id] = new_poly
            new_polys.append(new_poly)
            self.ordered_polys.append(new_poly)

            new_poly.center_pos = Point3(poly.center_pos)
            new_poly.normal = poly.normal * -1.

        for merged_vert, new_merged_vert in new_merged_verts.items():
            new_merged_vert.extend(new_vert_ids[v_id] for v_id in merged_vert)
            for vert_id in new_merged_vert:
                merged_verts[vert_id] = new_merged_vert

        for merged_edge, new_merged_edge in new_merged_edges.items():
            new_merged_edge.extend(new_edge_ids[e_id] for e_id in merged_edge)
            for edge_id in new_merged_edge:
                merged_edges[edge_id] = new_merged_edge

        for shared_normal, new_shared_normal in new_shared_normals.items():
            new_shared_normal.extend(new_vert_ids[v_id] for v_id in shared_normal)
            for vert_id in new_shared_normal:
                shared_normals[vert_id] = new_shared_normal

        self.create_new_geometry(new_polys, create_normals=False)
        self.update_locked_normal_selection(None, None, locked_normal_ids, ())

        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        uv_writers = {}

        for uv_set_id in uv_set_ids:
            column = "texcoord" if uv_set_id == 0 else f"texcoord.{uv_set_id}"
            uv_writers[uv_set_id] = GeomVertexWriter(vertex_data_top, column)

        for vert_id in new_vert_ids.values():

            vert = verts[vert_id]
            row = vert.row_index

            for uv_set_id, uv in vert.get_uvs().items():
                uv_writer = uv_writers[uv_set_id]
                uv_writer.set_row(row)
                uv_writer.set_data2(*uv)

        vertex_data_poly = self._vertex_data["poly"]

        for uv_set_id in uv_set_ids:
            uv_array = vertex_data_top.get_array(4 + uv_set_id)
            vertex_data_poly.set_array(4 + uv_set_id, GeomVertexArrayData(uv_array))

        self.update_vertex_colors()

        return True

    def get_subdivision_data(self):

        class MergedUV:

            def __init__(self, merged_vert, u, v):

                self.merged_vert = merged_vert
                self.uv = [u, v]

        merged_verts = list(set(self.merged_verts.values()))
        verts = self._subobjs["vert"]
        positions = [list(mv.get_pos()) for mv in merged_verts]
        merged_uvs = {}

        for merged_vert in merged_verts:

            verts_by_uv = {}

            for vert_id in merged_vert:

                vert = verts[vert_id]
                uv = vert.get_uvs(0)

                if uv in verts_by_uv:
                    verts_by_uv[uv].append(vert_id)
                else:
                    verts_by_uv[uv] = [vert_id]

            for (u, v), vert_ids in verts_by_uv.items():
                merged_uv = MergedUV(merged_vert, u, v)
                merged_uvs.update({v_id: merged_uv for v_id in vert_ids})

        merged_uv_list = list(set(merged_uvs.values()))
        uvs = [(muv.uv, merged_verts.index(muv.merged_vert)) for muv in merged_uv_list]
        faces = []
        uv_faces = []
        sign = -1 if self.owner.has_inverted_geometry() else 1

        for poly in self.ordered_polys:
            poly_vert_ids = poly.vertex_ids[::sign]
            faces.append([merged_verts.index(self.merged_verts[v_id]) for v_id in poly_vert_ids])
            uv_faces.append([merged_uv_list.index(merged_uvs[v_id]) for v_id in poly_vert_ids])

        return positions, uvs, faces, uv_faces


class SurfaceManager:
    """ PolygonEditManager class mix-in """

    def __init__(self):

        self._id_generator = id_generator()
        self._src_obj_ids = []
        self._add_geometry_from_multiple_models = False
        Mgr.add_app_updater("poly_surface_inversion", self.__invert_poly_surfaces)
        Mgr.add_app_updater("poly_surface_doublesiding", self.__doubleside_poly_surfaces)
        Mgr.add_app_updater("poly_surface_to_model", self.__update_models_from_poly_surfaces)
        Mgr.add_app_updater("geometry_from_model", self.__update_geometry_from_model)

        add_state = Mgr.add_state
        add_state("model_picking_mode", -10, self.__enter_model_picking_mode,
                  self.__exit_model_picking_mode)

        bind = Mgr.bind_state
        bind("model_picking_mode", "pick model -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("model_picking_mode", "quit model picking", "escape",
             lambda: Mgr.exit_state("model_picking_mode"))
        bind("model_picking_mode", "cancel model picking", "mouse3",
             lambda: Mgr.exit_state("model_picking_mode"))
        bind("model_picking_mode", "pick model", "mouse1",
             self.__pick_src)
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("model_picking_mode", "pick model ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))

        status_data = GD["status"]
        mode_text = "Pick source model"
        info_text = "LMB to pick a model to add geometry from; RMB to cancel; <Space> to navigate"
        status_data["pick_geom_src"] = {"mode": mode_text, "info": info_text}

    def __invert_poly_surfaces(self):

        # exit any subobject modes
        Mgr.exit_states(min_persistence=-99)
        selection = Mgr.get("selection_top")
        changed_objs = {}
        changed_triangulations = []
        changed_selections = []
        changed_uvs = []

        for model in selection:

            geom_data_obj = model.geom_obj.geom_data_obj
            change = geom_data_obj.invert_polygon_surfaces()

            if change:

                changed_objs[model] = geom_data_obj
                tri_change, uv_change, sel_change = change

                if tri_change:
                    changed_triangulations.append(model)

                if uv_change:
                    changed_uvs.append(model)

                if sel_change:
                    changed_selections.append(model)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj, geom_data_obj in changed_objs.items():

            data = geom_data_obj.get_data_to_store("prop_change", "subobj_merge")
            data.update(geom_data_obj.get_data_to_store("prop_change", "subobj_transform", "check"))

            if obj in changed_triangulations:
                data.update(geom_data_obj.get_data_to_store("prop_change", "poly_tris"))

            if obj in changed_uvs:
                data.update(geom_data_obj.get_data_to_store("prop_change", "uvs"))

            if obj in changed_selections:
                data.update(geom_data_obj.get_property_to_store("subobj_selection"))

            obj_data[obj.id] = data

        if len(changed_objs) == 1:
            obj = list(changed_objs)[0]
            event_descr = f'Invert surfaces of "{obj.name}"'
        else:
            event_descr = 'Invert surfaces of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __doubleside_poly_surfaces(self):

        # exit any subobject modes
        Mgr.exit_states(min_persistence=-99)
        selection = Mgr.get("selection_top")
        changed_objs = {}

        for model in selection:

            geom_data_obj = model.geom_obj.geom_data_obj

            if geom_data_obj.doubleside_polygon_surfaces():
                changed_objs[model] = geom_data_obj

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj, geom_data_obj in changed_objs.items():
            obj_data[obj.id] = geom_data_obj.get_data_to_store("subobj_change")

        if len(changed_objs) == 1:
            obj = list(changed_objs)[0]
            event_descr = f'Doubleside surfaces of "{obj.name}"'
        else:
            event_descr = 'Doubleside surfaces of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __copy_polygons(self, src_polys, dest_data_obj):

        src_verts = []
        src_edges = []

        for poly, sign in src_polys:
            src_verts.extend((v, sign) for v in poly.vertices)
            src_edges.extend((e, sign) for e in poly.edges)

        src_merged_verts = set(v.merged_vertex for v, _ in src_verts)
        src_merged_edges = set(e.merged_edge for e, _ in src_edges)
        src_shared_normals = set(v.shared_normal for v, _ in src_verts)
        dest_verts = dest_data_obj.get_subobjects("vert")
        dest_edges = dest_data_obj.get_subobjects("edge")
        dest_polys = dest_data_obj.get_subobjects("poly")
        dest_ordered_polys = dest_data_obj.ordered_polys
        dest_merged_verts = dest_data_obj.merged_verts
        dest_merged_edges = dest_data_obj.merged_edges
        dest_shared_normals = dest_data_obj.shared_normals
        new_verts = {}
        new_edges = {}

        for vert, sign in src_verts:
            new_vert = Mgr.do("create_vert", dest_data_obj, vert.get_pos())
            new_vert.color = vert.color
            new_vert.set_uvs(vert.get_uvs())
            new_vert.normal = vert.normal
            new_vert.lock_normal(vert.has_locked_normal())
            new_vert.tangent_space = vert.tangent_space
            new_verts[vert.id] = (new_vert, sign)
            dest_verts[new_vert.id] = new_vert

        for shared_normal in src_shared_normals:

            new_vert_ids = [new_verts[v_id][0].id for v_id in shared_normal]
            new_shared_normal = Mgr.do("create_shared_normal", dest_data_obj, new_vert_ids)

            for new_vert_id in new_vert_ids:
                dest_shared_normals[new_vert_id] = new_shared_normal

        del src_shared_normals

        for merged_vert in src_merged_verts:

            new_vert_ids = [new_verts[v_id][0].id for v_id in merged_vert]
            new_merged_vert = Mgr.do("create_merged_vert", dest_data_obj)
            new_merged_vert.extend(new_vert_ids)

            for new_vert_id in new_vert_ids:
                dest_merged_verts[new_vert_id] = new_merged_vert

        del src_merged_verts

        for edge, sign in src_edges:
            new_vert_ids = tuple(new_verts[v_id][0].id for v_id in edge[::sign])
            new_edge = Mgr.do("create_edge", dest_data_obj, new_vert_ids)
            new_edges[edge.id] = new_edge
            dest_edges[new_edge.id] = new_edge

        del src_edges

        for merged_edge in src_merged_edges:

            new_edge_ids = [new_edges[e_id].id for e_id in merged_edge]
            new_merged_edge = Mgr.do("create_merged_edge", dest_data_obj)
            new_merged_edge.extend(new_edge_ids)

            for new_edge_id in new_edge_ids:
                dest_merged_edges[new_edge_id] = new_merged_edge

        del src_merged_edges
        verts = {v.id: v for v, _ in src_verts}
        del src_verts

        for vert_id, (new_vert, sign) in new_verts.items():
            new_vert.edge_ids = [new_edges[e_id].id for e_id in verts[vert_id].edge_ids][::sign]

        del verts
        new_polys = []

        for poly, sign in src_polys:
            poly_tris = [tuple(new_verts[v_id][0].id for v_id in tri_vert_ids[::sign])
                for tri_vert_ids in poly][::sign]
            poly_edges = [new_edges[e_id] for e_id in poly.edge_ids][::sign]
            poly_verts = [new_verts[v_id][0] for v_id in poly.vertex_ids][::sign]
            new_poly = Mgr.do("create_poly", dest_data_obj, poly_tris, poly_edges, poly_verts)
            dest_polys[new_poly.id] = new_poly
            dest_ordered_polys.append(new_poly)
            new_polys.append(new_poly)

        return new_polys

    def __update_models_from_poly_surfaces(self, update_type, *args):

        if update_type == "init":
            if Mgr.get("selection"):
                Mgr.update_remotely("poly_surface_to_model")
        elif update_type == "create":
            self.__create_models_from_poly_surfaces(*args)

    def __create_models_from_poly_surfaces(self, model_basename, creation_method, copy_surfaces):

        # exit any subobject modes
        Mgr.exit_states(min_persistence=-99)
        obj_names = GD["obj_names"]
        changed_objs = {}
        src_objs = []
        created_objs = []

        if creation_method == "single":

            selection = Mgr.get("selection_top")
            pos = sum((m.pivot.get_pos(GD.world) for m in selection), Point3()) / len(selection)
            new_model_id = ("unlocked_geom",) + next(self._id_generator)
            name = model_basename if model_basename else "model 0001"
            name = get_unique_name(name, obj_names)
            new_model = Mgr.do("create_model", new_model_id, name, pos)
            created_objs.append(new_model)
            color = tuple(random.random() * .4 + .5 for _ in range(3))
            color += (1.,)
            new_model.set_color(color, update_app=False)
            unlocked_geom = Mgr.do("create_unlocked_geom", new_model)
            new_geom_data_obj = unlocked_geom.geom_data_obj
            pivot = new_model.pivot
            pivot.set_hpr(0., 0., 0.)
            polys_to_copy = []
            pos_backup = {}
            normal_backup = {}
            surface_polys_by_model = {}

            for model in selection:

                geom_data_obj = model.geom_obj.geom_data_obj
                sign = -1 if geom_data_obj.has_inverted_geometry() else 1
                sel_polys = set(geom_data_obj.get_selection("poly"))
                surface_polys = []

                while sel_polys:

                    poly = sel_polys.pop()
                    surface = geom_data_obj.get_polygon_surface(poly.id)
                    polys_to_copy.extend((p, sign) for p in surface)
                    surface_polys.extend(surface)
                    sel_polys.difference_update(surface)

                    if copy_surfaces:
                        for poly in surface:
                            for vert in poly.vertices:
                                pos_backup[vert] = vert.get_pos()
                                normal_backup[vert] = vert.normal

                    for poly in surface:
                        for vert in poly.vertices:
                            vert.set_pos(vert.get_pos(pivot))
                            vert.normal = pivot.get_relative_vector(model.pivot,
                                vert.normal * sign).normalized()

                if surface_polys:
                    src_objs.append(model)

                if not copy_surfaces and surface_polys:
                    surface_polys_by_model[model] = surface_polys
                    geom_data_obj.set_subobjs_to_unregister(surface_polys)
                    geom_data_obj.unregister()
                    changed_objs[model] = geom_data_obj

            if not copy_surfaces:
                Mgr.do("update_picking_col_id_ranges", as_task=False)

            self.__copy_polygons(polys_to_copy, new_geom_data_obj)

            if copy_surfaces:
                for poly, _ in polys_to_copy:
                    for vert in poly.vertices:
                        vert.set_pos(pos_backup[vert])
                        vert.normal = normal_backup[vert]
            else:
                for model, geom_data_obj in changed_objs.items():
                    surface_polys = surface_polys_by_model[model]
                    geom_data_obj.delete_polygons(surface_polys, unregister_globally=False)

            del pos_backup
            del normal_backup

            for _ in new_geom_data_obj.create_geometry("unlocked_geom"): pass

            new_geom_data_obj.finalize_geometry()
            new_geom_data_obj.update_poly_centers()
            new_geom_data_obj.update_poly_normals()
            new_model.register(restore=False)
            new_model.bbox.update(new_geom_data_obj.origin.get_tight_bounds())

        else:

            for model in Mgr.get("selection_top"):

                geom_data_obj = model.geom_obj.geom_data_obj
                inverted_geom = geom_data_obj.has_inverted_geometry()
                polys_to_copy = set()
                surface_list = []
                sel_polys = set(geom_data_obj.get_selection("poly"))

                while sel_polys:

                    poly = sel_polys.pop()
                    surface = geom_data_obj.get_polygon_surface(poly.id)

                    if creation_method == "per_src":
                        polys_to_copy.update(surface)
                    else:  # creation_method == "per_surface"
                        surface_list.append(surface)

                    sel_polys.difference_update(surface)

                if creation_method == "per_src" and polys_to_copy:
                    surface_list.append(list(polys_to_copy))

                if surface_list:
                    src_objs.append(model)

                if not copy_surfaces and surface_list:
                    surface_polys = sum(surface_list, [])
                    geom_data_obj.set_subobjs_to_unregister(surface_polys)
                    geom_data_obj.unregister()
                    Mgr.do("update_picking_col_id_ranges", as_task=False)
                    changed_objs[model] = geom_data_obj

                for polys_to_copy in surface_list:

                    new_model_id = ("unlocked_geom",) + next(self._id_generator)
                    name = model_basename if model_basename else model.name
                    name = get_unique_name(name, obj_names)
                    new_model = Mgr.do("create_model", new_model_id, name, Point3())
                    created_objs.append(new_model)
                    new_model.pivot.set_transform(GD.world, model.pivot.get_transform(GD.world))
                    color = tuple(random.random() * .4 + .5 for _ in range(3))
                    color += (1.,)
                    new_model.set_color(color, update_app=False)
                    unlocked_geom = Mgr.do("create_unlocked_geom", new_model)
                    new_geom_data_obj = unlocked_geom.geom_data_obj
                    polys_to_copy = [(p, 1) for p in polys_to_copy]
                    self.__copy_polygons(polys_to_copy, new_geom_data_obj)

                    for _ in new_geom_data_obj.create_geometry("unlocked_geom"): pass

                    new_geom_data_obj.finalize_geometry()
                    new_geom_data_obj.update_poly_centers()
                    new_geom_data_obj.update_poly_normals()
                    new_model.register(restore=False)
                    new_model.bbox.update(new_geom_data_obj.origin.get_tight_bounds())

                    if inverted_geom:
                        new_geom_data_obj.invert_geometry(delay=False)

                if not copy_surfaces and surface_list:
                    geom_data_obj.delete_polygons(surface_polys, unregister_globally=False)

        for obj in created_objs:

            geom_data_obj = obj.geom_obj.geom_data_obj
            locked_normal_ids = []

            for vert in geom_data_obj.get_subobjects("vert").values():
                if vert.has_locked_normal():
                    locked_normal_ids.append(vert.id)

            geom_data_obj.update_locked_normal_selection(None, None, locked_normal_ids, ())
            for _ in geom_data_obj.update_smoothing(): pass

        if not copy_surfaces:
            Mgr.get("selection").clear(add_to_hist=False)
            Mgr.update_remotely("selection_set", "hide_name")

        Mgr.do("update_history_time")
        obj_data = {}

        for obj, geom_data_obj in changed_objs.items():
            obj_data[obj.id] = geom_data_obj.get_data_to_store("subobj_change")

        for obj in created_objs:
            obj_data[obj.id] = obj.get_data_to_store("creation")

        if len(created_objs) == 1:
            obj = created_objs[0]
            event_descr = f'Create model:\n\n    "{obj.name}"'
        else:
            event_descr = f'Create models:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in created_objs])

        if len(src_objs) == 1:
            obj = src_objs[0]
            event_descr += f'\n\nfrom polys of "{obj.name}"'
        else:
            event_descr += '\n\nfrom polys of:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in src_objs])

        event_data = {"objects": obj_data}
        event_data["object_ids"] = set(Mgr.get("object_ids"))
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __update_geometry_from_model(self, update_type, *args):

        def handler(obj_ids):

            if obj_ids:
                objs = [Mgr.get("object", obj_id) for obj_id in obj_ids]
                self.__pick_src(picked_src=objs)

        if update_type == "init":
            if self._add_geometry_from_multiple_models:
                Mgr.update_remotely("selection_by_name", "",
                                    "Choose models to add geometry from",
                                    ["model"], True, "OK", handler)
                Mgr.update_remotely("selection_by_name", "show")
                Mgr.update_remotely("selection_by_name", "default")
            else:
                Mgr.enter_state("model_picking_mode")
        elif update_type == "multiple":
            self._add_geometry_from_multiple_models = args[0]
        elif update_type == "add":
            self.__add_geometry_from_models(*args)

    def __enter_model_picking_mode(self, prev_state_id, active):

        Mgr.add_task(self._update_cursor, "update_model_picking_cursor")
        Mgr.update_app("status", ["pick_geom_src"])

        if not active:

            def handler(obj_ids):

                if obj_ids:
                    models = [Mgr.get("model", obj_id) for obj_id in obj_ids]
                    self.__pick_src(picked_src=models)

            Mgr.update_remotely("selection_by_name", "", "Pick model to add geometry from",
                                ["model"], False, "Pick", handler)
            Mgr.get("gizmo_picking_cam").node().active = False
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = False

    def __exit_model_picking_mode(self, next_state_id, active):

        if not active:
            Mgr.get("gizmo_picking_cam").node().active = True
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = True
            Mgr.update_remotely("selection_by_name", "default")

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self._update_cursor()
                                        # is called
        Mgr.remove_task("update_model_picking_cursor")
        Mgr.set_cursor("main")

    def __pick_src(self, picked_src=None):

        if not (picked_src or self._add_geometry_from_multiple_models):
            picked_src = [Mgr.get("object", pixel_color=self._pixel_under_mouse)]

        selection = set(Mgr.get("selection_top"))

        if not selection.difference(picked_src):
            Mgr.update_remotely("geometry_from_model", "invalid_src")
            return

        def is_valid_model(obj):

            valid_model = obj and obj.type == "model" and obj.geom_type == "unlocked_geom"

            return valid_model and obj.geom_obj.geom_data_obj.ordered_polys

        src_models = [obj for obj in picked_src if is_valid_model(obj)]

        if src_models:
            self._src_obj_ids = [obj.id for obj in src_models]
            name = src_models[0].name if len(src_models) == 1 else None
            Mgr.update_remotely("geometry_from_model", "options", name)
        else:
            Mgr.update_remotely("geometry_from_model", "invalid_src")

    def __add_geometry_from_models(self, delete_src_geometry, keep_src_models):

        # exit any subobject modes
        Mgr.exit_states(min_persistence=-99)
        selection = Mgr.get("selection_top")
        src_models = [Mgr.get("object", obj_id) for obj_id in self._src_obj_ids]
        self._src_obj_ids = []
        src_data_objs = {m: m.geom_obj.geom_data_obj for m in src_models}
        ordered_polys = {m: gdo.ordered_polys for m, gdo in src_data_objs.items()}
        src_polys = []
        changed_objs = {}
        pos_backup = {}
        normal_backup = {}

        if delete_src_geometry:

            for src_data_obj in src_data_objs.values():
                src_data_obj.set_subobjs_to_unregister(src_data_obj.ordered_polys)
                src_data_obj.unregister()

            Mgr.do("update_picking_col_id_ranges", as_task=False)

        for model in selection:

            if model in src_models:
                continue

            geom_data_obj = model.geom_obj.geom_data_obj
            changed_objs[model] = geom_data_obj
            pivot = model.pivot
            dest_flip = -1. if geom_data_obj.has_inverted_geometry() else 1.

            for src_model, polys in ordered_polys.items():
                src_pivot = src_model.pivot
                src_flip = -1. if src_model.geom_obj.geom_data_obj.has_inverted_geometry() else 1.
                sign = int(src_flip * dest_flip)
                for poly in polys:
                    src_polys.append((poly, sign))
                    for vert in poly.vertices:
                        pos_backup[vert] = vert.get_pos()
                        normal_backup[vert] = vert.normal
                        vert.set_pos(vert.get_pos(pivot))
                        vert.normal = pivot.get_relative_vector(src_pivot,
                            vert.normal * sign).normalized()

            new_polys = self.__copy_polygons(src_polys, geom_data_obj)
            geom_data_obj.create_new_geometry(new_polys, create_normals=False)

            locked_normal_ids = []

            for poly in new_polys:

                poly.update_center_pos()
                poly.update_normal()

                for vert in poly.vertices:
                    if vert.has_locked_normal():
                        locked_normal_ids.append(vert.id)

            geom_data_obj.update_locked_normal_selection(None, None, locked_normal_ids, ())
            for _ in geom_data_obj.update_smoothing(): pass

            for poly, _ in src_polys:
                for vert in poly.vertices:
                    vert.set_pos(pos_backup[vert])
                    vert.normal = normal_backup[vert]

        del pos_backup
        del normal_backup
        del src_polys

        Mgr.do("update_history_time")
        obj_data = {}
        src_names = [model.name for model in src_models]

        def reparent(model):

            new_parent = model.parent
            new_parent_id = new_parent.id if new_parent else None

            for child in model.children:
                child.parent = new_parent_id
                data = child.get_data_to_store("prop_change", "link")
                data.update(child.get_data_to_store("prop_change", "transform"))
                obj_data.setdefault(child.id, {}).update(data)

        if delete_src_geometry:

            if keep_src_models:

                for src_model, src_data_obj in src_data_objs.items():
                    src_data_obj.delete_polygons(src_data_obj.ordered_polys[:],
                        unregister_globally=False)
                    obj_data[src_model.id] = src_data_obj.get_data_to_store("subobj_change")

            else:

                groups = []

                for src_model in src_models:

                    reparent(src_model)
                    data = src_model.get_data_to_store("deletion")
                    obj_data.setdefault(src_model.id, {}).update(data)
                    group = src_model.group

                    if group:
                        groups.append(group)

                Mgr.do("create_registry_backups", ("vert", "edge", "poly"))
                Mgr.do("create_id_range_backups", ("vert", "edge", "poly"))
                Mgr.do("reset_registries", ("vert", "edge", "poly"))
                Mgr.do("reset_picking_col_id_ranges", ("vert", "edge", "poly"))

                for src_model, src_data_obj in src_data_objs.items():
                    src_data_obj.register()
                    src_model.destroy(add_to_hist=False)

                Mgr.do("update_picking_col_id_ranges", as_task=False)
                Mgr.do("restore_registry_backups", info='source models destroyed')
                Mgr.do("restore_id_range_backups", info='source models destroyed')
                Mgr.do("prune_empty_groups", groups, obj_data)

        for obj, geom_data_obj in changed_objs.items():
            data = geom_data_obj.get_data_to_store("subobj_change")
            obj_data.setdefault(obj.id, {}).update(data)

        if len(src_names) == 1:
            event_descr = f'Add geometry from "{src_names[0]}"'
        else:
            event_descr = 'Add geometry from source models:\n'
            event_descr += "".join([f'\n    "{name}"' for name in src_names])
            event_descr += "\n"

        if len(changed_objs) == 1:
            obj = list(changed_objs)[0]
            event_descr += f'\nto "{obj.name}"'
        else:
            event_descr += '\nto:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        event_data = {"objects": obj_data}

        if delete_src_geometry and not keep_src_models:
            event_data["object_ids"] = set(Mgr.get("object_ids"))

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)
