from ...base import *
from .transform import SelectionTransformBase


class GeomSelectionBase(BaseObject):

    def __editstate__(self, state):

        del state["_poly_selection_data"]
        del state["_selected_subobj_ids"]

    def __setstate__(self, state):

        self._poly_selection_data = {"selected": [], "unselected": []}
        self._selected_subobj_ids = {"vert": [], "edge": [], "poly": [], "normal": []}

    def __init__(self):

        self._poly_selection_data = {"selected": [], "unselected": []}
        self._selected_subobj_ids = {"vert": [], "edge": [], "poly": [], "normal": []}
        self._sel_subobj_ids_backup = {}
        self._selection_backup = {}

    def update_selection(self, subobj_type, subobjs_to_select, subobjs_to_deselect,
                         update_verts_to_transf=True, selection_colors=None, geom=None):

        selected_subobj_ids = self._selected_subobj_ids[subobj_type]
        geoms = self._geoms[subobj_type]
        selected_subobjs = [subobj for subobj in subobjs_to_select
                            if subobj.get_id() not in selected_subobj_ids]
        deselected_subobjs = [subobj for subobj in subobjs_to_deselect
                              if subobj.get_id() in selected_subobj_ids]

        if not (selected_subobjs or deselected_subobjs):
            return False

        if subobj_type == "poly":

            geom_selected = geoms["selected"]
            geom_unselected = geoms["unselected"]
            sel_data = self._poly_selection_data
            data_selected = sel_data["selected"]
            data_unselected = sel_data["unselected"]
            prim = geom_selected.node().modify_geom(0).modify_primitive(0)
            array_sel = prim.modify_vertices()
            stride = array_sel.array_format.stride
            size_sel = array_sel.get_num_rows()
            row_count = sum([len(poly) for poly in selected_subobjs], size_sel)
            array_sel.set_num_rows(row_count)
            view_sel = memoryview(array_sel).cast("B")
            prim = geom_unselected.node().modify_geom(0).modify_primitive(0)
            array_unsel = prim.modify_vertices()
            size_unsel = array_unsel.get_num_rows()
            row_count = sum([len(poly) for poly in deselected_subobjs], size_unsel)
            array_unsel.set_num_rows(row_count)
            view_unsel = memoryview(array_unsel).cast("B")
            polys_sel = []
            polys_unsel = []
            row_ranges_sel_to_keep = SparseArray()
            row_ranges_sel_to_keep.set_range(0, array_sel.get_num_rows())
            row_ranges_unsel_to_keep = SparseArray()
            row_ranges_unsel_to_keep.set_range(0, size_unsel)
            row_ranges_sel_to_move = SparseArray()
            row_ranges_unsel_to_move = SparseArray()

            for poly in selected_subobjs:
                selected_subobj_ids.append(poly.get_id())
                start = data_unselected.index(poly[0]) * 3
                polys_sel.append((start, poly))
                row_ranges_unsel_to_keep.clear_range(start, len(poly))
                row_ranges_unsel_to_move.set_range(start, len(poly))

            for poly in deselected_subobjs:
                selected_subobj_ids.remove(poly.get_id())
                start = data_selected.index(poly[0]) * 3
                polys_unsel.append((start, poly))
                row_ranges_sel_to_keep.clear_range(start, len(poly))
                row_ranges_sel_to_move.set_range(start, len(poly))

            polys_sel.sort()
            polys_unsel.sort()

            for _, poly in polys_sel:
                data_selected.extend(poly)
                for vert_ids in poly:
                    data_unselected.remove(vert_ids)

            for _, poly in polys_unsel:
                data_unselected.extend(poly)
                for vert_ids in poly:
                    data_selected.remove(vert_ids)

            f = lambda values, stride: (v * stride for v in values)

            for i in range(row_ranges_unsel_to_move.get_num_subranges()):
                start = row_ranges_unsel_to_move.get_subrange_begin(i)
                size = row_ranges_unsel_to_move.get_subrange_end(i) - start
                offset_, start_, size_ = f((size_sel, start, size), stride)
                view_sel[offset_:offset_+size_] = view_unsel[start_:start_+size_]
                size_sel += size
                size_unsel -= size

            offset = 0

            for i in range(row_ranges_unsel_to_keep.get_num_subranges()):
                start = row_ranges_unsel_to_keep.get_subrange_begin(i)
                size = row_ranges_unsel_to_keep.get_subrange_end(i) - start
                offset_, start_, size_ = f((offset, start, size), stride)
                view_unsel[offset_:offset_+size_] = view_unsel[start_:start_+size_]
                offset += size

            for i in range(row_ranges_sel_to_move.get_num_subranges()):
                start = row_ranges_sel_to_move.get_subrange_begin(i)
                size = row_ranges_sel_to_move.get_subrange_end(i) - start
                offset_, start_, size_ = f((size_unsel, start, size), stride)
                view_unsel[offset_:offset_+size_] = view_sel[start_:start_+size_]
                size_unsel += size
                size_sel -= size

            offset = 0

            for i in range(row_ranges_sel_to_keep.get_num_subranges()):
                start = row_ranges_sel_to_keep.get_subrange_begin(i)
                size = row_ranges_sel_to_keep.get_subrange_end(i) - start
                offset_, start_, size_ = f((offset, start, size), stride)
                view_sel[offset_:offset_+size_] = view_sel[start_:start_+size_]
                offset += size

            array_sel.set_num_rows(size_sel)
            array_unsel.set_num_rows(size_unsel)

        else:

            if subobj_type == "vert":
                combined_subobjs = self._merged_verts
            elif subobj_type == "edge":
                combined_subobjs = self._merged_edges
            elif subobj_type == "normal":
                combined_subobjs = self._shared_normals

            selected_subobjs = set(combined_subobjs[subobj.get_id()] for subobj in selected_subobjs)
            deselected_subobjs = set(combined_subobjs[subobj.get_id()] for subobj in deselected_subobjs)

            sel_state_geom = geom if geom else geoms["sel_state"]
            vertex_data = sel_state_geom.node().modify_geom(0).modify_vertex_data()
            col_writer = GeomVertexWriter(vertex_data, "color")

            if selection_colors:
                sel_colors = selection_colors
            else:
                sel_colors = Mgr.get("subobj_selection_colors")[subobj_type]

            color_sel = sel_colors["selected"]
            color_unsel = sel_colors["unselected"]

            for combined_subobj in selected_subobjs:

                selected_subobj_ids.extend(combined_subobj)

                for row_index in combined_subobj.get_row_indices():
                    col_writer.set_row(row_index)
                    col_writer.set_data4(color_sel)

            for combined_subobj in deselected_subobjs:

                for subobj_id in combined_subobj:
                    selected_subobj_ids.remove(subobj_id)

                for row_index in combined_subobj.get_row_indices():
                    col_writer.set_row(row_index)
                    col_writer.set_data4(color_unsel)

            if subobj_type == "normal":

                selected_normal_ids = []
                deselected_normal_ids = []

                for combined_subobj in selected_subobjs:
                    selected_normal_ids.extend(combined_subobj)

                for combined_subobj in deselected_subobjs:
                    deselected_normal_ids.extend(combined_subobj)

                self.update_locked_normal_selection(selected_normal_ids, deselected_normal_ids)

        if update_verts_to_transf:
            self._update_verts_to_transform(subobj_type)

        return True

    def is_selected(self, subobj):

        return subobj.get_id() in self._selected_subobj_ids[subobj.get_type()]

    def get_selection(self, subobj_lvl):

        selected_subobj_ids = self._selected_subobj_ids[subobj_lvl]

        if subobj_lvl == "poly":
            polys = self._subobjs["poly"]
            return [polys[poly_id] for poly_id in selected_subobj_ids]

        if subobj_lvl == "vert":
            combined_subobjs = self._merged_verts
        elif subobj_lvl == "edge":
            combined_subobjs = self._merged_edges
        elif subobj_lvl == "normal":
            combined_subobjs = self._shared_normals

        return list(set(combined_subobjs[subobj_id] for subobj_id in selected_subobj_ids))

    def create_selection_backup(self, subobj_lvl):

        if subobj_lvl in self._selection_backup:
            return

        self._sel_subobj_ids_backup[subobj_lvl] = self._selected_subobj_ids[subobj_lvl][:]
        self._selection_backup[subobj_lvl] = self.get_selection(subobj_lvl)

    def restore_selection_backup(self, subobj_lvl):

        sel_backup = self._selection_backup

        if subobj_lvl not in sel_backup:
            return

        self.clear_selection(subobj_lvl, False)
        self.update_selection(subobj_lvl, sel_backup[subobj_lvl], [], False)
        del sel_backup[subobj_lvl]
        del self._sel_subobj_ids_backup[subobj_lvl]

    def remove_selection_backup(self, subobj_lvl):

        sel_backup = self._selection_backup

        if subobj_lvl in sel_backup:
            del sel_backup[subobj_lvl]
            del self._sel_subobj_ids_backup[subobj_lvl]

    def clear_selection(self, subobj_lvl, update_verts_to_transf=True, force=False):

        if not (force or self._selected_subobj_ids[subobj_lvl]):
            return

        geoms = self._geoms[subobj_lvl]

        if subobj_lvl == "poly":

            geom_selected = geoms["selected"]
            geom_unselected = geoms["unselected"]
            sel_data = self._poly_selection_data
            sel_data["unselected"].extend(sel_data["selected"])
            sel_data["selected"] = []

            from_array = geom_selected.node().modify_geom(0).modify_primitive(0).modify_vertices()
            from_size = from_array.data_size_bytes
            from_view = memoryview(from_array).cast("B")
            to_array = geom_unselected.node().modify_geom(0).modify_primitive(0).modify_vertices()
            to_size = to_array.data_size_bytes
            to_array.set_num_rows(to_array.get_num_rows() + from_array.get_num_rows())
            to_view = memoryview(to_array).cast("B")
            to_view[to_size:to_size+from_size] = from_view
            from_array.clear_rows()

        elif subobj_lvl == "normal":

            color = Mgr.get("subobj_selection_colors")["normal"]["unselected"]
            color_locked = Mgr.get("subobj_selection_colors")["normal"]["locked_unsel"]
            vertex_data = geoms["sel_state"].node().modify_geom(0).modify_vertex_data()
            col_writer = GeomVertexWriter(vertex_data, "color")
            verts = self._subobjs["vert"]

            for vert_id in self._selected_subobj_ids["normal"]:
                vert = verts[vert_id]
                row = vert.get_row_index()
                col = color_locked if vert.has_locked_normal() else color
                col_writer.set_row(row)
                col_writer.set_data4(col)

        else:

            vertex_data = geoms["sel_state"].node().modify_geom(0).modify_vertex_data()
            color = Mgr.get("subobj_selection_colors")[subobj_lvl]["unselected"]
            new_data = vertex_data.set_color(color)
            vertex_data.set_array(1, new_data.get_array(1))

        self._selected_subobj_ids[subobj_lvl] = []

        if update_verts_to_transf:
            self._verts_to_transf[subobj_lvl] = {}

    def delete_selection(self, subobj_lvl):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        ordered_polys = self._ordered_polys

        selected_subobj_ids = self._selected_subobj_ids
        selected_vert_ids = selected_subobj_ids["vert"]
        selected_edge_ids = selected_subobj_ids["edge"]
        selected_poly_ids = selected_subobj_ids["poly"]
        selected_normal_ids = selected_subobj_ids["normal"]
        self._verts_to_transf["vert"] = {}
        self._verts_to_transf["edge"] = {}
        self._verts_to_transf["poly"] = {}
        verts_to_delete = []
        edges_to_delete = []
        border_edges = []

        if subobj_lvl == "vert":

            polys_to_delete = set()

            for vert in (verts[v_id] for v_id in selected_vert_ids):
                polys_to_delete.add(polys[vert.get_polygon_id()])

        elif subobj_lvl == "edge":

            polys_to_delete = set()

            for edge in (edges[e_id] for e_id in selected_edge_ids):
                polys_to_delete.add(polys[edge.get_polygon_id()])

        elif subobj_lvl == "poly":

            polys_to_delete = [polys[poly_id] for poly_id in selected_poly_ids]

        poly_index = min(ordered_polys.index(poly) for poly in polys_to_delete)
        polys_to_offset = ordered_polys[poly_index:]

        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        shared_normals = self._shared_normals
        row_ranges_to_keep = SparseArray()
        row_ranges_to_keep.set_range(0, self._data_row_count)

        subobjs_to_unreg = self._subobjs_to_unreg = {"vert": {}, "edge": {}, "poly": {}}

        subobj_change = self._subobj_change
        subobj_change["vert"]["deleted"] = vert_change = {}
        subobj_change["edge"]["deleted"] = edge_change = {}
        subobj_change["poly"]["deleted"] = poly_change = {}

        for poly in polys_to_delete:

            poly_verts = poly.get_vertices()
            vert = poly_verts[0]
            row = vert.get_row_index()
            row_ranges_to_keep.clear_range(row, len(poly_verts))

            verts_to_delete.extend(poly_verts)
            edges_to_delete.extend(poly.get_edges())

            for edge_id in poly.get_edge_ids():

                merged_edge = merged_edges[edge_id]

                if merged_edge in border_edges:
                    border_edges.remove(merged_edge)
                else:
                    border_edges.append(merged_edge)

            ordered_polys.remove(poly)
            poly_id = poly.get_id()
            subobjs_to_unreg["poly"][poly_id] = poly
            poly_change[poly] = poly.get_creation_time()

            if poly_id in selected_poly_ids:
                selected_poly_ids.remove(poly_id)

        merged_verts_to_resmooth = set()

        for vert in verts_to_delete:

            vert_id = vert.get_id()
            subobjs_to_unreg["vert"][vert_id] = vert
            vert_change[vert] = vert.get_creation_time()

            if vert_id in selected_vert_ids:
                selected_vert_ids.remove(vert_id)

            if vert_id in selected_normal_ids:
                selected_normal_ids.remove(vert_id)

            if vert_id in merged_verts:
                merged_vert = merged_verts[vert_id]
                merged_vert.remove(vert_id)
                del merged_verts[vert_id]
                merged_verts_to_resmooth.add(merged_vert)

            if vert_id in shared_normals:
                shared_normal = shared_normals[vert_id]
                shared_normal.discard(vert_id)
                del shared_normals[vert_id]

        sel_data = self._poly_selection_data
        geoms = self._geoms

        for state in ("selected", "unselected"):
            sel_data[state] = []
            prim = geoms["poly"][state].node().modify_geom(0).modify_primitive(0)
            prim.modify_vertices().clear_rows()

        for edge in edges_to_delete:

            edge_id = edge.get_id()
            subobjs_to_unreg["edge"][edge_id] = edge
            edge_change[edge] = edge.get_creation_time()

            if edge_id in selected_edge_ids:
                selected_edge_ids.remove(edge_id)

            if edge_id in merged_edges:

                merged_edge = merged_edges[edge_id]
                merged_edge.remove(edge_id)
                del merged_edges[edge_id]

                if not merged_edge[:] and merged_edge in border_edges:
                    border_edges.remove(merged_edge)

        if border_edges:

            new_merged_verts = self.fix_borders(border_edges)

            if new_merged_verts:
                self.update_normal_sharing(new_merged_verts)
                merged_verts_to_resmooth.update(new_merged_verts)

        self.unregister(locally=True)

        row_index_offset = 0

        for poly in polys_to_offset:

            if poly in polys_to_delete:
                row_index_offset -= poly.get_vertex_count()
                continue

            poly_verts = poly.get_vertices()

            for vert in poly_verts:
                vert.offset_row_index(row_index_offset)

        vert_geom = geoms["vert"]["pickable"].node().modify_geom(0)
        edge_geom = geoms["edge"]["pickable"].node().modify_geom(0)
        normal_geom = geoms["normal"]["pickable"].node().modify_geom(0)
        vertex_data_vert = vert_geom.modify_vertex_data()
        vertex_data_edge = edge_geom.modify_vertex_data()
        vertex_data_normal = normal_geom.modify_vertex_data()
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly_picking = self._vertex_data["poly_picking"]

        vert_array = vertex_data_vert.modify_array(1)
        vert_view = memoryview(vert_array).cast("B")
        vert_stride = vert_array.array_format.stride
        edge_array = vertex_data_edge.modify_array(1)
        edge_view = memoryview(edge_array).cast("B")
        edge_stride = edge_array.array_format.stride
        picking_array = vertex_data_poly_picking.modify_array(1)
        picking_view = memoryview(picking_array).cast("B")
        picking_stride = picking_array.array_format.stride

        poly_arrays = []
        poly_views = []
        poly_strides = []

        for i in range(vertex_data_poly.get_num_arrays()):
            poly_array = vertex_data_poly.modify_array(i)
            poly_arrays.append(poly_array)
            poly_views.append(memoryview(poly_array).cast("B"))
            poly_strides.append(poly_array.array_format.stride)

        pos_array = poly_arrays[0]
        f = lambda values, stride: (v * stride for v in values)
        offset = 0

        for i in range(row_ranges_to_keep.get_num_subranges()):

            start = row_ranges_to_keep.get_subrange_begin(i)
            size = row_ranges_to_keep.get_subrange_end(i) - start
            offset_, start_, size_ = f((offset, start, size), vert_stride)
            vert_view[offset_:offset_+size_] = vert_view[start_:start_+size_]
            offset_, start_, size_ = f((offset, start, size), edge_stride)
            edge_view[offset_:offset_+size_] = edge_view[start_:start_+size_]
            offset_, start_, size_ = f((offset, start, size), picking_stride)
            picking_view[offset_:offset_+size_] = picking_view[start_:start_+size_]

            for poly_view, poly_stride in zip(poly_views, poly_strides):
                offset_, start_, size_ = f((offset, start, size), poly_stride)
                poly_view[offset_:offset_+size_] = poly_view[start_:start_+size_]

            offset += size

        old_count = self._data_row_count
        count = len(verts)
        offset = count

        for i in range(row_ranges_to_keep.get_num_subranges()):
            start = row_ranges_to_keep.get_subrange_begin(i)
            size = row_ranges_to_keep.get_subrange_end(i) - start
            offset_, start_, size_ = f((offset, start + old_count, size), edge_stride)
            edge_view[offset_:offset_+size_] = edge_view[start_:start_+size_]
            offset += size

        self._data_row_count = count
        sel_colors = Mgr.get("subobj_selection_colors")

        vertex_data_poly.set_num_rows(count)
        vertex_data_vert.set_num_rows(count)
        vertex_data_vert.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_normal.set_num_rows(count)
        vertex_data_poly_picking.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_normal.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_normal.set_array(1, GeomVertexArrayData(vert_array))
        vertex_data_normal.set_array(2, GeomVertexArrayData(poly_arrays[2]))

        vertex_data_vert = geoms["vert"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data_vert.set_num_rows(count)
        vertex_data_vert.set_array(0, GeomVertexArrayData(pos_array))
        new_data = vertex_data_vert.set_color(sel_colors["vert"]["unselected"])
        vertex_data_vert.set_array(1, new_data.get_array(1))

        vertex_data_normal = geoms["normal"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data_normal.set_num_rows(count)
        vertex_data_normal.set_array(0, GeomVertexArrayData(pos_array))
        new_data = vertex_data_normal.set_color(sel_colors["normal"]["unselected"])
        vertex_data_normal.set_array(1, new_data.get_array(1))
        vertex_data_normal.set_array(2, GeomVertexArrayData(poly_arrays[2]))

        size = pos_array.data_size_bytes
        from_view = memoryview(pos_array).cast("B")

        vertex_data_edge.set_num_rows(count * 2)
        pos_array_edge = vertex_data_edge.modify_array(0)
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view

        vertex_data_edge = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data_edge.set_num_rows(count * 2)
        pos_array_edge = vertex_data_edge.modify_array(0)
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view
        new_data = vertex_data_edge.set_color(sel_colors["edge"]["unselected"])
        vertex_data_edge.set_array(1, new_data.get_array(1))

        data_unselected = sel_data["unselected"]

        for poly in ordered_polys:
            data_unselected.extend(poly)

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.reserve_num_vertices(count)
        points_prim.add_next_vertices(count)
        vert_geom.set_primitive(0, points_prim)
        normal_geom.set_primitive(0, GeomPoints(points_prim))
        geom_node = geoms["vert"]["sel_state"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomPoints(points_prim))
        geom_node = geoms["normal"]["sel_state"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomPoints(points_prim))

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(count * 2)

        tris_prim = GeomTriangles(Geom.UH_static)

        for poly in ordered_polys:

            for edge in poly.get_edges():
                row1, row2 = edge.get_row_indices()
                lines_prim.add_vertices(row1, row2)

            for vert_ids in poly:
                tris_prim.add_vertices(*[verts[v_id].get_row_index() for v_id in vert_ids])

        edge_geom.set_primitive(0, lines_prim)
        geom_node = geoms["edge"]["sel_state"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomLines(lines_prim))

        geom_node_top = self._toplvl_node
        geom_node_top.modify_geom(0).set_primitive(0, tris_prim)

        geom_node = geoms["poly"]["unselected"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomTriangles(tris_prim))

        geom_node = geoms["poly"]["pickable"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomTriangles(tris_prim))

        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()

        for i, poly_array in enumerate(poly_arrays):
            vertex_data_top.set_array(i, poly_array)

        geom_node.modify_geom(0).set_primitive(0, GeomTriangles(tris_prim))

        for subobj_type in ("vert", "edge", "poly", "normal"):
            selected_subobj_ids[subobj_type] = []

        if selected_vert_ids:
            selected_verts = (verts[vert_id] for vert_id in selected_vert_ids)
            self.update_selection("vert", selected_verts, [])

        if selected_edge_ids:
            selected_edges = (edges[edge_id] for edge_id in selected_edge_ids)
            self.update_selection("edge", selected_edges, [])

        if selected_poly_ids:
            selected_polys = (polys[poly_id] for poly_id in selected_poly_ids)
            self.update_selection("poly", selected_polys, [])

        if selected_normal_ids:
            selected_normals = (shared_normals[normal_id] for normal_id in selected_normal_ids)
            self.update_selection("normal", selected_normals, [])

        self.update_subobject_indices()

        poly_ids = [poly.get_id() for poly in polys_to_delete]
        self.smooth_polygons(poly_ids, smooth=False, update_normals=False)
        self._normal_sharing_change = True
        self.update_vertex_normals(merged_verts_to_resmooth)
        self.get_toplevel_object().get_bbox().update(*self._origin.get_tight_bounds())

    def _restore_subobj_selection(self, time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = self._unique_prop_ids["subobj_selection"]
        data = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)

        verts = self._subobjs["vert"]
        normal_ids = data["normal"]
        old_sel_normal_ids = set(self._selected_subobj_ids["normal"])
        new_sel_normal_ids = set(normal_ids)
        sel_normal_ids = new_sel_normal_ids - old_sel_normal_ids
        unsel_normal_ids = old_sel_normal_ids - new_sel_normal_ids
        unsel_normal_ids.intersection_update(verts)
        shared_normals = self._shared_normals
        original_shared_normals = {}

        if unsel_normal_ids:
            tmp_shared_normal = Mgr.do("create_shared_normal", self, unsel_normal_ids)
            unsel_id = tmp_shared_normal.get_id()
            original_shared_normals[unsel_id] = shared_normals[unsel_id]
            shared_normals[unsel_id] = tmp_shared_normal
            unsel_normals = [tmp_shared_normal]
        else:
            unsel_normals = []

        if sel_normal_ids:
            tmp_shared_normal = Mgr.do("create_shared_normal", self, sel_normal_ids)
            sel_id = tmp_shared_normal.get_id()
            original_shared_normals[sel_id] = shared_normals[sel_id]
            shared_normals[sel_id] = tmp_shared_normal
            sel_normals = [tmp_shared_normal]
        else:
            sel_normals = []

        self.update_selection("normal", sel_normals, unsel_normals, False)

        if unsel_normals:
            shared_normals[unsel_id] = original_shared_normals[unsel_id]
        if sel_normals:
            shared_normals[sel_id] = original_shared_normals[sel_id]

        self._update_verts_to_transform("normal")

        for subobj_type in ("vert", "edge", "poly"):

            subobjs = self._subobjs[subobj_type]

            subobj_ids = data[subobj_type]
            old_sel_subobj_ids = set(self._selected_subobj_ids[subobj_type])
            new_sel_subobj_ids = set(subobj_ids)
            sel_subobj_ids = new_sel_subobj_ids - old_sel_subobj_ids
            unsel_subobj_ids = old_sel_subobj_ids - new_sel_subobj_ids
            unsel_subobj_ids.intersection_update(subobjs)

            unsel_subobjs = [subobjs[i] for i in unsel_subobj_ids]
            sel_subobjs = [subobjs[i] for i in sel_subobj_ids]

            if subobj_type in ("vert", "edge"):

                merged_subobjs = self._merged_verts if subobj_type == "vert" else self._merged_edges
                original_merged_subobjs = {}

                if unsel_subobjs:

                    tmp_merged_subobj = Mgr.do("create_merged_{}".format(subobj_type), self)

                    for subobj_id in unsel_subobj_ids:
                        tmp_merged_subobj.append(subobj_id)

                    unsel_id = tmp_merged_subobj.get_id()
                    original_merged_subobjs[unsel_id] = merged_subobjs[unsel_id]
                    merged_subobjs[unsel_id] = tmp_merged_subobj
                    unsel_subobjs = [subobjs[unsel_id]]

                if sel_subobjs:

                    tmp_merged_subobj = Mgr.do("create_merged_{}".format(subobj_type), self)

                    for subobj_id in sel_subobj_ids:
                        tmp_merged_subobj.append(subobj_id)

                    sel_id = tmp_merged_subobj.get_id()
                    original_merged_subobjs[sel_id] = merged_subobjs[sel_id]
                    merged_subobjs[sel_id] = tmp_merged_subobj
                    sel_subobjs = [subobjs[sel_id]]

            self.update_selection(subobj_type, sel_subobjs, unsel_subobjs, False)

            if subobj_type in ("vert", "edge"):
                if unsel_subobjs:
                    merged_subobjs[unsel_id] = original_merged_subobjs[unsel_id]
                if sel_subobjs:
                    merged_subobjs[sel_id] = original_merged_subobjs[sel_id]

            self._update_verts_to_transform(subobj_type)


class Selection(SelectionTransformBase):

    def __init__(self, obj_level, subobjs):

        SelectionTransformBase.__init__(self)

        self._objs = subobjs
        self._obj_level = obj_level

        self._groups = {}

        for obj in subobjs:
            self._groups.setdefault(obj.get_geom_data_object(), []).append(obj)

    def __getitem__(self, index):

        try:
            return self._objs[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __len__(self):

        return len(self._objs)

    def get_toplevel_objects(self, get_group=False):

        return [geom_data_obj.get_toplevel_object(get_group) for geom_data_obj in self._groups]

    def get_toplevel_object(self, get_group=False):
        """ Return a random top-level object """

        if self._groups:
            return list(self._groups.keys())[0].get_toplevel_object(get_group)

    def get_subobjects(self, geom_data_obj):

        return self._groups.get(geom_data_obj, [])

    def update(self, hide_sets=False):

        self.update_center_pos()
        self.update_ui()

        if hide_sets:
            Mgr.update_remotely("selection_set", "hide_name")

    def add(self, subobjs, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_add = set(subobjs)
        common = old_sel & sel_to_add

        if common:
            sel_to_add -= common

        if not sel_to_add:
            return False

        geom_data_objs = {}
        groups = self._groups

        for obj in sel_to_add:
            geom_data_obj = obj.get_geom_data_object()
            geom_data_objs.setdefault(geom_data_obj, []).append(obj)
            groups.setdefault(geom_data_obj, []).append(obj)

        for geom_data_obj, objs in geom_data_objs.items():
            geom_data_obj.update_selection(self._obj_level, objs, [])

        sel.extend(sel_to_add)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon", "normal": "normal"}
            event_descr = 'Add to {} selection'.format(subobj_descr[self._obj_level])
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def remove(self, subobjs, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_remove = set(subobjs)
        common = old_sel & sel_to_remove

        if not common:
            return False

        geom_data_objs = {}
        groups = self._groups

        for obj in common:

            sel.remove(obj)
            geom_data_obj = obj.get_geom_data_object()
            geom_data_objs.setdefault(geom_data_obj, []).append(obj)

            groups[geom_data_obj].remove(obj)

            if not groups[geom_data_obj]:
                del groups[geom_data_obj]

        for geom_data_obj, objs in geom_data_objs.items():
            geom_data_obj.update_selection(self._obj_level, [], objs)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon", "normal": "normal"}
            event_descr = 'Remove from {} selection'.format(subobj_descr[self._obj_level])
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def replace(self, subobjs, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        new_sel = set(subobjs)
        common = old_sel & new_sel

        if common:
            old_sel -= common
            new_sel -= common

        if not (old_sel or new_sel):
            return False

        geom_data_objs = {}

        for old_obj in old_sel:
            sel.remove(old_obj)
            geom_data_obj = old_obj.get_geom_data_object()
            geom_data_objs.setdefault(geom_data_obj, {"sel": [], "desel": []})["desel"].append(old_obj)

        for new_obj in new_sel:
            geom_data_obj = new_obj.get_geom_data_object()
            geom_data_objs.setdefault(geom_data_obj, {"sel": [], "desel": []})["sel"].append(new_obj)

        for geom_data_obj, objs in geom_data_objs.items():
            geom_data_obj.update_selection(self._obj_level, objs["sel"], objs["desel"])

        sel.extend(new_sel)

        self._groups = groups = {}

        for obj in common | new_sel:
            groups.setdefault(obj.get_geom_data_object(), []).append(obj)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist and geom_data_objs:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon", "normal": "normal"}
            event_descr = 'Replace {} selection'.format(subobj_descr[self._obj_level])
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def clear(self, add_to_hist=True):

        if not self._objs:
            return False

        obj_lvl = self._obj_level
        geom_data_objs = []

        for geom_data_obj in self._groups:
            geom_data_obj.clear_selection(obj_lvl)
            geom_data_objs.append(geom_data_obj)

        self._groups = {}
        self._objs = []

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon", "normal": "normal"}
            event_descr = 'Clear {} selection'.format(subobj_descr[obj_lvl])
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def delete(self, add_to_hist=True):

        obj_lvl = self._obj_level

        if obj_lvl == "normal":
            return False

        if not self._objs:
            return False

        geom_data_objs = list(self._groups.keys())

        self._groups = {}
        self._objs = []

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        for geom_data_obj in geom_data_objs:
            geom_data_obj.delete_selection(obj_lvl)

        if add_to_hist:

            Mgr.do("update_history_time")

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon", "normal": "normal"}
            event_descr = 'Delete {} selection'.format(subobj_descr[obj_lvl])
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("subobj_change")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        return True


# subobject selection manager
class SelectionManager(BaseObject):

    def __init__(self):

        self._color_id = None
        self._selections = {}
        self._prev_obj_lvl = None
        self._selection_op = "replace"

        # the following variables are used to pick a subobject using its polygon
        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

        np = NodePath("poly_sel_state")
        poly_sel_state_off = np.get_state()
        tex_stage = TextureStage("poly_selection")
        tex_stage.set_sort(100)
        tex_stage.set_priority(-1)
        tex_stage.set_mode(TextureStage.M_add)
        np.set_transparency(TransparencyAttrib.M_none)
        projector = self.cam.get_projector()
        np.set_tex_gen(tex_stage, RenderAttrib.M_world_position)
        np.set_tex_projector(tex_stage, self.world, projector)
        tex = Texture()
        tex.read(Filename(GFX_PATH + "sel_tex.png"))
        np.set_texture(tex_stage, tex)
        red = VBase4(1., 0., 0., 1.)
        material = Material("poly_selection")
        material.set_diffuse(red)
        material.set_emission(red * .3)
        np.set_material(material)
        poly_sel_state = np.get_state()
        poly_sel_effects = np.get_effects()
        color = VBase4(0., .7, .5, 1.)
        material = Material("temp_poly_selection")
        material.set_diffuse(color)
        material.set_emission(color * .3)
        np.set_material(material)
        tmp_poly_sel_state = np.get_state()
        Mgr.expose("poly_selection_state_off", lambda: poly_sel_state_off)
        Mgr.expose("poly_selection_state", lambda: poly_sel_state)
        Mgr.expose("poly_selection_effects", lambda: poly_sel_effects)
        Mgr.expose("temp_poly_selection_state", lambda: tmp_poly_sel_state)

        vert_colors = {"selected": (1., 0., 0., 1.), "unselected": (.5, .5, 1., 1.)}
        edge_colors = {"selected": (1., 0., 0., 1.), "unselected": (1., 1., 1., 1.)}
        normal_colors = {"selected": (1., 0.3, 0.3, 1.), "unselected": (.75, .75, 0., 1.),
                         "locked_sel": (0.75, 0.3, 1., 1.), "locked_unsel": (0.3, 0.5, 1., 1.)}
        subobj_sel_colors = {"vert": vert_colors, "edge": edge_colors, "normal": normal_colors}

        Mgr.expose("subobj_selection_colors", lambda: subobj_sel_colors)

        Mgr.expose("selection_vert", lambda: self._selections["vert"])
        Mgr.expose("selection_edge", lambda: self._selections["edge"])
        Mgr.expose("selection_poly", lambda: self._selections["poly"])
        Mgr.expose("selection_normal", lambda: self._selections["normal"])
        Mgr.expose("subobj_selection_set", self.__get_selection_set)
        Mgr.accept("update_selection_vert", lambda: self.__update_selection("vert"))
        Mgr.accept("update_selection_edge", lambda: self.__update_selection("edge"))
        Mgr.accept("update_selection_poly", lambda: self.__update_selection("poly"))
        Mgr.accept("update_selection_normal", lambda: self.__update_selection("normal"))
        Mgr.accept("select_vert", lambda *args: self.__init_select("vert", *args))
        Mgr.accept("select_edge", lambda *args: self.__init_select("edge", *args))
        Mgr.accept("select_poly", lambda *args: self.__init_select("poly", *args))
        Mgr.accept("select_normal", lambda *args: self.__init_select("normal", *args))
        Mgr.accept("select_single_vert", lambda: self.__select_single("vert"))
        Mgr.accept("select_single_edge", lambda: self.__select_single("edge"))
        Mgr.accept("select_single_poly", lambda: self.__select_single("poly"))
        Mgr.accept("select_single_normal", lambda: self.__select_single("normal"))
        Mgr.accept("inverse_select_subobjs", self.__inverse_select)
        Mgr.accept("select_all_subobjs", self.__select_all)
        Mgr.accept("clear_subobj_selection", self.__select_none)
        Mgr.accept("apply_subobj_selection_set", self.__apply_selection_set)
        Mgr.accept("region_select_subobjs", self.__region_select)
        Mgr.accept("init_selection_via_poly", self.__init_selection_via_poly)
        Mgr.add_app_updater("active_obj_level", lambda: self.__clear_prev_selection(True))
        Mgr.add_app_updater("picking_via_poly", self.__set_subobj_picking_via_poly)
        Mgr.add_app_updater("viewport", self.__handle_viewport_resize)

        add_state = Mgr.add_state
        add_state("picking_via_poly", -1, self.__init_subobj_picking_via_poly)

        bind = Mgr.bind_state
        bind("picking_via_poly", "select subobj via poly",
             "mouse1-up", self.__select_subobj_via_poly)
        bind("picking_via_poly", "cancel subobj select via poly",
             "mouse3", self.__cancel_select_via_poly)

        status_data = GlobalData["status_data"]
        info = "LMB-drag over subobject to pick it; RMB to cancel"
        status_data["picking_via_poly"] = {"mode": "Pick subobject", "info": info}

    def __handle_viewport_resize(self):

        # Maintain the size and aspect ratio of the polygon selection texture.

        w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "main" else "size"]
        lenses = self.cam.get_projector_lenses()
        lens_persp = lenses["persp"]
        lens_persp.set_fov(2. * math.degrees(math.atan(2.5 / max(w, h))))
        lens_ortho = lenses["ortho"]
        lens_ortho.set_film_size(2000. / max(w, h))

    def __clear_prev_selection(self, check_top=False):

        obj_lvl = GlobalData["active_obj_level"]

        if check_top and obj_lvl != "top":
            return

        if self._prev_obj_lvl:
            self._selections[self._prev_obj_lvl] = None
            self._prev_obj_lvl = None

        selection = Mgr.get("selection_top")
        sel_count = len(selection)
        obj = selection[0]
        geom_data_obj = obj.get_geom_object().get_geom_data_object()

        for prop_id in geom_data_obj.get_type_property_ids(obj_lvl):
            value = geom_data_obj.get_property(prop_id, for_remote_update=True, obj_lvl=obj_lvl)
            value = (value, sel_count)
            Mgr.update_remotely("selected_obj_prop", "editable_geom", prop_id, value)

    def __update_selection(self, obj_lvl):

        self.__clear_prev_selection()
        subobjs = []

        for obj in Mgr.get("selection_top"):
            subobjs.extend(obj.get_subobj_selection(obj_lvl))

        self._selections[obj_lvl] = sel = Selection(obj_lvl, subobjs)
        sel.update()
        self._prev_obj_lvl = obj_lvl
        Mgr.update_remotely("selection_set", "hide_name")

    def __get_all_combined_subobjs(self, obj_lvl):

        subobjs = []
        geom_data_objs = [obj.get_geom_object().get_geom_data_object()
                          for obj in Mgr.get("selection_top")]

        if obj_lvl == "vert":
            for geom_data_obj in geom_data_objs:
                subobjs.extend(geom_data_obj.get_merged_vertices().values())
        elif obj_lvl == "edge":
            for geom_data_obj in geom_data_objs:
                subobjs.extend(geom_data_obj.get_merged_edges().values())
        elif obj_lvl == "normal":
            for geom_data_obj in geom_data_objs:
                subobjs.extend(geom_data_obj.get_shared_normals().values())
        elif obj_lvl == "poly":
            for geom_data_obj in geom_data_objs:
                subobjs.extend(geom_data_obj.get_subobjects("poly").values())

        return subobjs

    def __inverse_select(self):

        obj_lvl = GlobalData["active_obj_level"]
        selection = self._selections[obj_lvl]
        old_sel = set(selection)
        new_sel = set(self.__get_all_combined_subobjs(obj_lvl))
        selection.replace(new_sel - old_sel)
        Mgr.update_remotely("selection_set", "hide_name")

    def __select_all(self):

        obj_lvl = GlobalData["active_obj_level"]
        selection = self._selections[obj_lvl]
        selection.replace(self.__get_all_combined_subobjs(obj_lvl))
        Mgr.update_remotely("selection_set", "hide_name")

    def __select_none(self):

        obj_lvl = GlobalData["active_obj_level"]
        selection = self._selections[obj_lvl]
        selection.clear()
        Mgr.update_remotely("selection_set", "hide_name")

    def __get_selection_set(self):

        obj_lvl = GlobalData["active_obj_level"]
        selection = self._selections[obj_lvl]

        if obj_lvl == "poly":
            return set(obj.get_id() for obj in selection)
        else:
            return set(obj_id for obj in selection for obj_id in obj)

    def __apply_selection_set(self, sel_set):

        obj_lvl = GlobalData["active_obj_level"]
        selection = self._selections[obj_lvl]
        geom_data_objs = [model.get_geom_object().get_geom_data_object()
                          for model in Mgr.get("selection_top")]
        combined_subobjs = {}

        if obj_lvl == "vert":
            for geom_data_obj in geom_data_objs:
                combined_subobjs.update(geom_data_obj.get_merged_vertices())
        elif obj_lvl == "edge":
            for geom_data_obj in geom_data_objs:
                combined_subobjs.update(geom_data_obj.get_merged_edges())
        elif obj_lvl == "normal":
            for geom_data_obj in geom_data_objs:
                combined_subobjs.update(geom_data_obj.get_shared_normals())
        elif obj_lvl == "poly":
            for geom_data_obj in geom_data_objs:
                combined_subobjs.update(geom_data_obj.get_subobjects("poly"))

        new_sel = set(combined_subobjs.get(obj_id) for obj_id in sel_set)
        new_sel.discard(None)
        selection.replace(new_sel)

    def __init_select(self, obj_lvl, picked_obj, op):

        self._selection_op = op

        if obj_lvl == "vert":

            if GlobalData["subobj_edit_options"]["pick_via_poly"]:
                obj = picked_obj if picked_obj and picked_obj.get_type() == "poly" else None
                self._picked_poly = obj
            else:
                obj = picked_obj.get_merged_vertex() if picked_obj else None

        elif obj_lvl == "edge":

            if GlobalData["subobj_edit_options"]["pick_via_poly"]:

                obj = picked_obj if picked_obj and picked_obj.get_type() == "poly" else None

                if obj and GlobalData["subobj_edit_options"]["sel_edges_by_border"]:

                    merged_edges = obj.get_geom_data_object().get_merged_edges()

                    for edge_id in obj.get_edge_ids():
                        if len(merged_edges[edge_id]) == 1:
                            break
                    else:
                        obj = None

                self._picked_poly = obj

            else:

                obj = picked_obj.get_merged_edge() if picked_obj else None

                if obj and GlobalData["subobj_edit_options"]["sel_edges_by_border"] and len(obj) > 1:
                    obj = None

        elif obj_lvl == "normal":

            if GlobalData["subobj_edit_options"]["pick_via_poly"]:
                obj = picked_obj if picked_obj and picked_obj.get_type() == "poly" else None
                self._picked_poly = obj
            else:
                obj = picked_obj.get_shared_normal() if picked_obj else None

        elif obj_lvl == "poly":

            obj = picked_obj

        if self._picked_poly:
            Mgr.enter_state("picking_via_poly")
            return False, False

        self._color_id = obj.get_picking_color_id() if obj else None
        r = self.__select(obj_lvl)
        selection = self._selections[obj_lvl]

        if not (obj and obj in selection):
            obj = selection[0] if selection else None

        if obj:

            cs_type = GlobalData["coord_sys_type"]
            tc_type = GlobalData["transf_center_type"]
            toplvl_obj = obj.get_toplevel_object()

            if cs_type == "local":
                Mgr.update_locally("coord_sys", cs_type, toplvl_obj)

            if tc_type == "pivot":
                Mgr.update_locally("transf_center", tc_type, toplvl_obj)

        return r

    def __select(self, obj_lvl, ignore_transform=False):

        if obj_lvl == "normal":
            obj = Mgr.get("vert", self._color_id)
        else:
            obj = Mgr.get(obj_lvl, self._color_id)

        if obj_lvl == "vert":
            obj = obj.get_merged_vertex() if obj else None
        elif obj_lvl == "edge":
            obj = obj.get_merged_edge() if obj else None
        elif obj_lvl == "normal":
            obj = obj.get_shared_normal() if obj else None

        selection = self._selections[obj_lvl]
        can_select_single = False
        start_mouse_checking = False
        op = self._selection_op

        if obj:

            if op == "replace":

                if GlobalData["active_transform_type"] and not ignore_transform:

                    if obj in selection and len(selection) > 1:

                        # When the user clicks one of multiple selected objects, updating the
                        # selection must be delayed until it is clear whether he wants to
                        # transform the entire selection or simply have only this object
                        # selected (this is determined by checking if the mouse has moved at
                        # least a certain number of pixels by the time the left mouse button
                        # is released).

                        can_select_single = True

                    else:

                        selection.replace(obj.get_special_selection())

                    start_mouse_checking = True

                else:

                    selection.replace(obj.get_special_selection())

            elif op == "add":

                selection.add(obj.get_special_selection())
                transform_allowed = GlobalData["active_transform_type"]

                if transform_allowed:
                    start_mouse_checking = True

            elif op == "remove":

                selection.remove(obj.get_special_selection())

            elif op == "toggle":

                old_sel = set(selection)
                new_sel = set(obj.get_special_selection())
                selection.remove(old_sel & new_sel)
                selection.add(new_sel - old_sel)

                if obj in selection:
                    transform_allowed = GlobalData["active_transform_type"]
                else:
                    transform_allowed = False

                if transform_allowed:
                    start_mouse_checking = True

        elif op == "replace":

            selection.clear()

        Mgr.update_remotely("selection_set", "hide_name")

        return can_select_single, start_mouse_checking

    def __select_single(self, obj_lvl):

        # If multiple objects were selected and no transformation occurred, a single
        # object has been selected out of that previous selection.

        if obj_lvl == "normal":
            obj = Mgr.get("vert", self._color_id)
        else:
            obj = Mgr.get(obj_lvl, self._color_id)

        if obj_lvl == "vert":
            obj = obj.get_merged_vertex() if obj else None
        elif obj_lvl == "edge":
            obj = obj.get_merged_edge() if obj else None
        elif obj_lvl == "normal":
            obj = obj.get_shared_normal() if obj else None

        self._selections[obj_lvl].replace(obj.get_special_selection())

    def __region_select(self, cam, lens_exp, tex_buffer, ellipse_data, mask_tex, op):

        obj_lvl = GlobalData["active_obj_level"]

        subobjs = {}
        index_offset = 0

        for obj in Mgr.get("selection_top"):

            geom_data_obj = obj.get_geom_object().get_geom_data_object()
            obj_type = "vert" if obj_lvl == "normal" else obj_lvl
            indexed_subobjs = geom_data_obj.get_indexed_subobjects(obj_type)

            for index, subobj in indexed_subobjs.items():
                subobjs[index + index_offset] = subobj

            geom_data_obj.get_origin().set_shader_input("index_offset", index_offset)
            index_offset += len(indexed_subobjs)

        base = Mgr.get("base")
        ge = base.graphics_engine
        obj_count = len(subobjs)
        region_type = GlobalData["region_select"]["type"]
        subobj_edit_options = GlobalData["subobj_edit_options"]
        pick_via_poly = subobj_edit_options["pick_via_poly"]

        if pick_via_poly:
            Mgr.update_locally("picking_via_poly", False)

        def region_select_objects(sel, enclose=False):

            tex = Texture()
            tex.setup_1d_texture(obj_count, Texture.T_int, Texture.F_r32i)
            tex.set_clear_color(0)
            sh = shaders.region_sel

            if "rect" in region_type or "square" in region_type:
                fs = sh.FRAG_SHADER_INV if enclose else sh.FRAG_SHADER
            elif "ellipse" in region_type or "circle" in region_type:
                fs = sh.FRAG_SHADER_ELLIPSE_INV if enclose else sh.FRAG_SHADER_ELLIPSE
            else:
                fs = sh.FRAG_SHADER_FREE_INV if enclose else sh.FRAG_SHADER_FREE

            if obj_lvl == "normal":
                sh = shaders.region_sel_normal
                vs = sh.VERT_SHADER
                gs = sh.GEOM_SHADER
                shader = Shader.make(Shader.SL_GLSL, vs, fs, gs)
            else:
                vs = shaders.region_sel_subobj.VERT_SHADER
                shader = Shader.make(Shader.SL_GLSL, vs, fs)

            state_np = NodePath("state_np")
            state_np.set_shader(shader, 1)
            state_np.set_shader_input("selections", tex, read=False, write=True)

            if "ellipse" in region_type or "circle" in region_type:
                state_np.set_shader_input("ellipse_data", Vec4(*ellipse_data))
            elif region_type in ("fence", "lasso", "paint"):
                if enclose:
                    img = PNMImage()
                    mask_tex.store(img)
                    img.expand_border(2, 2, 2, 2, (0., 0., 0., 0.))
                    mask_tex.load(img)
                state_np.set_shader_input("mask_tex", mask_tex)
            elif enclose:
                w_b, h_b = tex_buffer.get_size()
                state_np.set_shader_input("buffer_size", Vec2(w_b + 2, h_b + 2))

            state = state_np.get_state()
            cam.node().set_initial_state(state)

            ge.render_frame()

            if ge.extract_texture_data(tex, base.win.get_gsg()):

                texels = memoryview(tex.get_ram_image()).cast("I")

                if obj_lvl == "edge":

                    sel_edges_by_border = subobj_edit_options["sel_edges_by_border"]

                    for i, mask in enumerate(texels):
                        for j in range(32):
                            if mask & (1 << j):
                                index = 32 * i + j
                                subobj = subobjs[index].get_merged_object()
                                if not sel_edges_by_border or len(subobj) == 1:
                                    sel.update(subobj.get_special_selection())

                elif obj_lvl == "normal":

                    for i, mask in enumerate(texels):
                        for j in range(32):
                            if mask & (1 << j):
                                index = 32 * i + j
                                subobj = subobjs[index].get_shared_normal()
                                sel.update(subobj.get_special_selection())

                else:

                    for i, mask in enumerate(texels):
                        for j in range(32):
                            if mask & (1 << j):
                                index = 32 * i + j
                                subobj = subobjs[index].get_merged_object()
                                sel.update(subobj.get_special_selection())

            state_np.clear_attrib(ShaderAttrib)

        new_sel = set()
        region_select_objects(new_sel)
        ge.remove_window(tex_buffer)

        if GlobalData["region_select"]["enclose"]:
            w_b, h_b = tex_buffer.get_size()
            bfr_exp = base.win.make_texture_buffer("tex_buffer_exp", w_b + 4, h_b + 4)
            base.make_camera(bfr_exp, useCamera=cam)
            cam.node().set_lens(lens_exp)
            inverse_sel = set()
            region_select_objects(inverse_sel, True)
            new_sel -= inverse_sel
            ge.remove_window(bfr_exp)

        if pick_via_poly:
            Mgr.update_locally("picking_via_poly", True)

        selection = self._selections[obj_lvl]

        if op == "replace":
            selection.replace(new_sel)
        elif op == "add":
            selection.add(new_sel)
        elif op == "remove":
            selection.remove(new_sel)
        elif op == "toggle":
            old_sel = set(selection)
            selection.remove(old_sel & new_sel)
            selection.add(new_sel - old_sel)

    def __set_subobj_picking_via_poly(self, via_poly=False):

        GlobalData["subobj_edit_options"]["pick_via_poly"] = via_poly

        if not via_poly:

            models = Mgr.get("model_objs")

            for model in models:
                if model.get_geom_type() == "editable_geom":
                    geom_data_obj = model.get_geom_object().get_geom_data_object()
                    geom_data_obj.restore_selection_backup("poly")

        obj_lvl = GlobalData["active_obj_level"]

        if obj_lvl not in ("vert", "edge", "normal"):
            return

        for obj in Mgr.get("selection_top"):
            obj.get_geom_object().get_geom_data_object().init_subobj_picking(obj_lvl)

    def __init_selection_via_poly(self, picked_poly, op):

        if picked_poly:
            Mgr.do("set_transf_gizmo_pickable", False)
            self._picked_poly = picked_poly
            self._selection_op = op
            Mgr.enter_state("picking_via_poly")

    def __init_subobj_picking_via_poly(self, prev_state_id, is_active):

        Mgr.add_task(self.__hilite_subobj, "hilite_subobj")
        Mgr.remove_task("update_cursor")
        subobj_lvl = GlobalData["active_obj_level"]

        if subobj_lvl == "edge" and GlobalData["subobj_edit_options"]["sel_edges_by_border"]:
            category = "border"
        else:
            category = ""

        geom_data_obj = self._picked_poly.get_geom_data_object()
        geom_data_obj.init_subobj_picking_via_poly(subobj_lvl, self._picked_poly, category)
        # temporarily select picked poly
        geom_data_obj.update_selection("poly", [self._picked_poly], [], False)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.get_geom_object().get_geom_data_object()

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable(False)

        Mgr.update_app("status", ["picking_via_poly"])

        cs_type = GlobalData["coord_sys_type"]
        tc_type = GlobalData["transf_center_type"]
        toplvl_obj = self._picked_poly.get_toplevel_object()

        if cs_type == "local":
            Mgr.update_locally("coord_sys", cs_type, toplvl_obj)

        if tc_type == "pivot":
            Mgr.update_locally("transf_center", tc_type, toplvl_obj)

    def __hilite_subobj(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")
        active_transform_type = GlobalData["active_transform_type"]

        if self._pixel_under_mouse != pixel_under_mouse:

            if pixel_under_mouse == VBase4():

                if active_transform_type and self._tmp_color_id is not None:
                    self.__select_subobj_via_poly(transform=True)
                    return

            else:

                r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                color_id = r << 16 | g << 8 | b
                geom_data_obj = self._picked_poly.get_geom_data_object()
                subobj_lvl = GlobalData["active_obj_level"]

                # highlight temporary subobject
                if geom_data_obj.hilite_temp_subobject(subobj_lvl, color_id):
                    self._tmp_color_id = color_id

            self._pixel_under_mouse = pixel_under_mouse

        not_hilited = pixel_under_mouse in (VBase4(), VBase4(1., 1., 1., 1.))
        cursor_id = "main" if not_hilited else ("select" if not active_transform_type
                                                else active_transform_type)

        if GlobalData["subobj_edit_options"]["pick_by_aiming"]:

            aux_pixel_under_mouse = Mgr.get("aux_pixel_under_mouse")

            if not_hilited or self._aux_pixel_under_mouse != aux_pixel_under_mouse:

                if not_hilited and aux_pixel_under_mouse != VBase4():

                    r, g, b, a = [int(round(c * 255.)) for c in aux_pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    geom_data_obj = self._picked_poly.get_geom_data_object()
                    subobj_lvl = GlobalData["active_obj_level"]

                    # highlight temporary subobject
                    if geom_data_obj.hilite_temp_subobject(subobj_lvl, color_id):
                        self._tmp_color_id = color_id
                        cursor_id = "select" if not active_transform_type else active_transform_type

                self._aux_pixel_under_mouse = aux_pixel_under_mouse

        if self._cursor_id != cursor_id:
            Mgr.set_cursor(cursor_id)
            self._cursor_id = cursor_id

        return task.cont

    def __select_subobj_via_poly(self, transform=False):

        Mgr.remove_task("hilite_subobj")
        Mgr.enter_state("selection_mode")
        subobj_lvl = GlobalData["active_obj_level"]
        geom_data_obj = self._picked_poly.get_geom_data_object()

        if self._tmp_color_id is None:

            obj = None

        else:

            if subobj_lvl == "vert":
                vert_id = Mgr.get("vert", self._tmp_color_id).get_id()
                obj = geom_data_obj.get_merged_vertex(vert_id)
            elif subobj_lvl == "edge":
                edge_id = Mgr.get("edge", self._tmp_color_id).get_id()
                obj = geom_data_obj.get_merged_edge(edge_id)
                obj = (None if GlobalData["subobj_edit_options"]["sel_edges_by_border"]
                       and len(obj) > 1 else obj)
            elif subobj_lvl == "normal":
                vert_id = Mgr.get("vert", self._tmp_color_id).get_id()
                obj = geom_data_obj.get_shared_normal(vert_id)

        self._color_id = obj.get_picking_color_id() if obj else None

        ignore_transform = not transform
        self.__select(subobj_lvl, ignore_transform)

        geom_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.get_geom_object().get_geom_data_object()

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None
        active_transform_type = GlobalData["active_transform_type"]

        if transform and obj and obj.get_geom_data_object().is_selected(obj):

            if active_transform_type == "translate":
                picked_point = obj.get_center_pos(self.world)
            elif self.mouse_watcher.has_mouse():
                screen_pos = Point2(self.mouse_watcher.get_mouse())
                picked_point = obj.get_point_at_screen_pos(screen_pos)
            else:
                picked_point = None

            if picked_point:
                selection = self._selections[subobj_lvl]
                selection.update(hide_sets=True)
                Mgr.do("init_transform", picked_point)

            Mgr.set_cursor(active_transform_type)

        if active_transform_type:
            Mgr.do("set_transf_gizmo_pickable")

    def __cancel_select_via_poly(self):

        Mgr.remove_task("hilite_subobj")
        Mgr.enter_state("selection_mode")
        subobj_lvl = GlobalData["active_obj_level"]

        geom_data_obj = self._picked_poly.get_geom_data_object()
        geom_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.get_geom_object().get_geom_data_object()

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

        if GlobalData["active_transform_type"]:
            Mgr.do("set_transf_gizmo_pickable")


MainObjects.add_class(SelectionManager)
