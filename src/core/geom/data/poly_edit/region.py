from ....base import *


class RegionBase(BaseObject):

    def get_polygon_region(self, poly_id):

        polys = self._subobjs["poly"]
        poly = polys[poly_id]
        poly_ids = set([poly_id])
        neighbor_ids = list(poly.get_neighbor_ids())

        while neighbor_ids:
            neighbor_id = neighbor_ids.pop()
            neighbor = polys[neighbor_id]
            neighbor_ids.extend(neighbor.get_neighbor_ids() - poly_ids)
            poly_ids.add(neighbor_id)

        return [polys[p_id] for p_id in poly_ids]

    def flip_polygon_regions(self):

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
            return False

        poly_ids = set(selected_poly_ids)
        polys_to_flip = set()

        # determine the regions that the selected polys belong to
        while poly_ids:
            poly_id = poly_ids.pop()
            region = self.get_polygon_region(poly_id)
            polys_to_flip.update(region)
            poly_ids.difference_update([poly.get_id() for poly in region])

        verts = self._subobjs["vert"]
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        shared_normals = self._shared_normals
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
            poly_vert_ids = poly.get_vertex_ids()
            l = len(poly_vert_ids)
            l_half = l / 2
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
                    # or 2 * i - l + 1, so i equals (offset + l - 1) / 2
                    i = (offset + l - 1) / 2

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

                    for new_tri_vert_ids in dest_triangles.itervalues():

                        ordered_vert_ids = {}

                        for vert_id in new_tri_vert_ids:
                            ordered_vert_ids[poly_vert_ids.index(vert_id)] = vert_id

                        vert_ids = []

                        for index in sorted(ordered_vert_ids):
                            vert_ids.append(ordered_vert_ids[index])

                        new_tri_data.append(tuple(vert_ids))

                    poly.set_triangle_data(new_tri_data)
                    tri_change.add(poly.get_id())

            # switch vertices by swapping their properties
            for vert1_id, vert2_id in zip(vert_ids1, vert_ids2):

                # TODO: swap vertex colors

                vert1 = verts[vert1_id]
                vert2 = verts[vert2_id]
                verts_to_swap.extend((vert1, vert2))
                merged_vert1 = merged_verts[vert1_id]
                merged_vert2 = merged_verts[vert2_id]
                pos1 = vert1.get_pos()
                pos2 = vert2.get_pos()
                uvs1 = vert1.get_uvs()
                uvs2 = vert2.get_uvs()
                vert1_selected = vert1_id in selected_vert_ids
                vert2_selected = vert2_id in selected_vert_ids
                normal1 = vert1.get_normal() * -1.
                normal2 = vert2.get_normal() * -1.
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

                vert1.set_normal(normal2)
                vert2.set_normal(normal1)
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

                edge1_id = vert1.get_edge_ids()[0]
                edge2_id = vert2.get_edge_ids()[1]

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
                vert = verts[vert_id]
                normal = vert.get_normal() * -1.
                vert.set_normal(normal)

        toplvl_geom = self._toplvl_node.modify_geom(0)
        vertex_data_top = toplvl_geom.modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")
        uv_writers = {}

        for uv_set_id in uv_set_ids:
            column = "texcoord" if uv_set_id == 0 else "texcoord.%d" % uv_set_id
            uv_writers[uv_set_id] = GeomVertexWriter(vertex_data_top, column)

        for vert in verts_to_swap:
            row = vert.get_row_index()
            pos = vert.get_pos()
            pos_writer.set_row(row)
            pos_writer.set_data3f(pos)

        for vert_id in uv_change:

            vert = verts[vert_id]
            row = vert.get_row_index()

            for uv_set_id, uv in vert.get_uvs().iteritems():
                uv_writer = uv_writers[uv_set_id]
                uv_writer.set_row(row)
                uv_writer.set_data2f(*uv)

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

        pos_array = GeomVertexArrayData(pos_array)
        handle = pos_array.modify_handle()
        handle.set_data(handle.get_data() * 2)
        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, pos_array)

        if tri_change:

            self.create_selection_backup("poly")
            self.clear_selection("poly", False)
            self._poly_selection_data["unselected"] = data_unselected = []
            prim = GeomTriangles(Geom.UH_static)

            for poly in self._ordered_polys:
                for tri_vert_ids in poly:
                    data_unselected.append(tri_vert_ids)
                    indices = [verts[v_id].get_row_index() for v_id in tri_vert_ids]
                    prim.add_vertices(*indices)

            poly_unselected_geom = geoms["poly"]["unselected"].node().modify_geom(0)
            poly_unselected_geom.set_primitive(0, prim)
            prim = GeomTriangles(prim)
            toplvl_geom.set_primitive(0, prim)
            poly_picking_geom = geoms["poly"]["pickable"].node().modify_geom(0)
            poly_picking_geom.set_primitive(0, prim)
            self.restore_selection_backup("poly")

        normal_writer = GeomVertexWriter(vertex_data_top, "normal")
        sign = -1. if self._owner.has_flipped_normals() else 1.
        normal_change = self._normal_change

        for poly in polys_to_flip:

            vert_ids = poly.get_vertex_ids()
            normal_change.update(vert_ids)

            for vert_id in vert_ids:
                vert = verts[vert_id]
                normal_writer.set_row(vert.get_row_index())
                normal_writer.set_data3f(vert.get_normal() * sign)

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
                    sel_subobj_id = tmp_sel_subobj.get_id()
                    desel_subobj_id = tmp_desel_subobj.get_id()
                    orig_sel_subobj = combined_subobjs[subobj_type][sel_subobj_id]
                    orig_desel_subobj = combined_subobjs[subobj_type][desel_subobj_id]
                    combined_subobjs[subobj_type][sel_subobj_id] = tmp_sel_subobj
                    combined_subobjs[subobj_type][desel_subobj_id] = tmp_desel_subobj
                    self.update_selection(subobj_type, [tmp_sel_subobj], [tmp_desel_subobj])
                    combined_subobjs[subobj_type][sel_subobj_id] = orig_sel_subobj
                    combined_subobjs[subobj_type][desel_subobj_id] = orig_desel_subobj

        self._normal_sharing_change = True
        model = self.get_toplevel_object()

        if model.has_tangent_space():
            tangent_flip, bitangent_flip = model.get_tangent_space_flip()
            poly_ids = [p.get_id() for p in polys_to_flip]
            self.update_tangent_space(tangent_flip, bitangent_flip, poly_ids)
        else:
            self._is_tangent_space_initialized = False

        return True, tri_change, uv_change, sel_change


class RegionManager(BaseObject):

    def __init__(self):

        Mgr.add_app_updater("poly_region_flip", self.__flip_poly_regions)

    def __flip_poly_regions(self):

        selection = Mgr.get("selection", "top")
        changed_objs = {}
        changed_triangulations = []
        changed_selections = []
        changed_uvs = []

        for model in selection:

            model_id = model.get_id()
            geom_data_obj = model.get_geom_object().get_geom_data_object()
            change, tri_change, uv_change, sel_change = geom_data_obj.flip_polygon_regions()

            if change:

                changed_objs[model_id] = geom_data_obj

                if tri_change:
                    changed_triangulations.append(model_id)

                if uv_change:
                    changed_uvs.append(model_id)

                if sel_change:
                    changed_selections.append(model_id)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.iteritems():

            data = geom_data_obj.get_data_to_store("prop_change", "subobj_merge")
            data.update(geom_data_obj.get_data_to_store("prop_change", "subobj_transform", "check"))

            if obj_id in changed_triangulations:
                data.update(geom_data_obj.get_data_to_store("prop_change", "poly_tris"))

            if obj_id in changed_uvs:
                data.update(geom_data_obj.get_data_to_store("prop_change", "uvs"))

            if obj_id in changed_selections:
                data.update(geom_data_obj.get_property_to_store("subobj_selection"))

            obj_data[obj_id] = data

        event_descr = "Flip polygon regions"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)
