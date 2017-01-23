from ..base import *
from .vert import Vertex, MergedVertex
from .edge import Edge, MergedEdge


class UVDataSelectionBase(BaseObject):

    def __init__(self, data_copy=None):

        if data_copy:

            selected_subobj_ids = data_copy["selected_subobj_ids"]
            poly_selection_data = data_copy["poly_selection_data"]

        else:

            selected_subobj_ids = {}
            poly_selection_data = {"selected": [], "unselected": []}

            for subobj_type in ("vert", "edge", "poly"):
                selected_subobj_ids[subobj_type] = []

        self._selected_subobj_ids = selected_subobj_ids
        self._poly_selection_data = poly_selection_data

    def copy(self):

        sel_subobj_ids = {}

        for subobj_type in ("vert", "edge", "poly"):
            sel_subobj_ids_src = self._selected_subobj_ids[subobj_type]
            sel_subobj_ids[subobj_type] = sel_subobj_ids_src[:]

        poly_selection_data = self._poly_selection_data
        poly_selection_data_copy = {}

        for state in ("selected", "unselected"):
            poly_selection_data_copy[state] = poly_selection_data[state][:]

        data_copy = {}
        data_copy["selected_subobj_ids"] = sel_subobj_ids
        data_copy["poly_selection_data"] = poly_selection_data_copy

        return data_copy

    def update_selection(self, subobj_type, subobjs_to_select, subobjs_to_deselect,
                         update_verts_to_transf=True):

        selected_subobj_ids = self._selected_subobj_ids[subobj_type]
        geoms = self._geoms[subobj_type]
        sel_state_geom = geoms["sel_state"]
        selected_subobjs = [subobj for subobj in subobjs_to_select
                            if subobj.get_id() not in selected_subobj_ids]
        deselected_subobjs = [subobj for subobj in subobjs_to_deselect
                              if subobj.get_id() in selected_subobj_ids]

        if not (selected_subobjs or deselected_subobjs):
            return False

        if subobj_type == "poly":

            sel_data = self._poly_selection_data
            data_selected = sel_data["selected"]
            data_unselected = sel_data["unselected"]
            prim = sel_state_geom.node().modify_geom(1).modify_primitive(0)
            array = prim.modify_vertices()
            stride = array.get_array_format().get_stride()
            handle_sel = array.modify_handle()
            prim = sel_state_geom.node().modify_geom(0).modify_primitive(0)
            handle_unsel = prim.modify_vertices().modify_handle()
            row_ranges_sel = []
            row_ranges_unsel = []

            for poly in selected_subobjs:
                selected_subobj_ids.append(poly.get_id())
                start = data_unselected.index(poly[0]) * 3
                size = len(poly)
                row_ranges_unsel.append((start, size, poly))

            for poly in deselected_subobjs:
                selected_subobj_ids.remove(poly.get_id())
                start = data_selected.index(poly[0]) * 3
                size = len(poly)
                row_ranges_sel.append((start, size, poly))

            row_ranges_sel.sort(reverse=True)
            row_ranges_unsel.sort(reverse=True)
            subdata_sel = ""
            subdata_unsel = ""

            for start, size, poly in row_ranges_unsel:

                for vert_ids in poly:
                    data_unselected.remove(vert_ids)

                data_selected.extend(poly[:])

                subdata_unsel += handle_unsel.get_subdata(start * stride, size * stride)
                handle_unsel.set_subdata(start * stride, size * stride, "")

            handle_sel.set_data(handle_sel.get_data() + subdata_unsel)

            for start, size, poly in row_ranges_sel:

                for vert_ids in poly:
                    data_selected.remove(vert_ids)

                data_unselected.extend(poly[:])

                subdata_sel += handle_sel.get_subdata(start * stride, size * stride)
                handle_sel.set_subdata(start * stride, size * stride, "")

            handle_unsel.set_data(handle_unsel.get_data() + subdata_sel)

        else:

            merged_subobjs = self._merged_verts if subobj_type == "vert" else self._merged_edges
            selected_subobjs = set(merged_subobjs[subobj.get_id()] for subobj in selected_subobjs)
            deselected_subobjs = set(merged_subobjs[subobj.get_id()] for subobj in deselected_subobjs)

            vertex_data = sel_state_geom.node().modify_geom(0).modify_vertex_data()
            col_writer = GeomVertexWriter(vertex_data, "color")
            sel_colors = UVMgr.get("uv_selection_colors")[subobj_type]
            color_sel = sel_colors["selected"]
            color_unsel = sel_colors["unselected"]

            if subobj_type == "vert":

                for merged_vert in selected_subobjs:

                    selected_subobj_ids.extend(merged_vert[:])

                    for row_index in merged_vert.get_row_indices():
                        col_writer.set_row(row_index)
                        col_writer.set_data4f(color_sel)

                for merged_vert in deselected_subobjs:

                    for v_id in merged_vert:
                        selected_subobj_ids.remove(v_id)

                    for row_index in merged_vert.get_row_indices():
                        col_writer.set_row(row_index)
                        col_writer.set_data4f(color_unsel)

            elif subobj_type == "edge":

                seam_colors = UVMgr.get("uv_selection_colors")["seam"]
                seam_color_sel = seam_colors["selected"]
                seam_color_unsel = seam_colors["unselected"]

                for merged_edge in selected_subobjs:

                    selected_subobj_ids.extend(merged_edge[:])

                    if merged_edge.get_id() in self._seam_edge_ids:
                        color = seam_color_sel
                    else:
                        color = color_sel

                    for row_index in merged_edge.get_row_indices():
                        col_writer.set_row(row_index)
                        col_writer.set_data4f(color)

                for merged_edge in deselected_subobjs:

                    for e_id in merged_edge:
                        selected_subobj_ids.remove(e_id)

                    if merged_edge.get_id() in self._seam_edge_ids:
                        color = seam_color_unsel
                    else:
                        color = color_unsel

                    for row_index in merged_edge.get_row_indices():
                        col_writer.set_row(row_index)
                        col_writer.set_data4f(color)

        if update_verts_to_transf:
            self._update_verts_to_transform(subobj_type)

        return True

    def update_seam_selection(self, edge_ids, color):

        tmp_merged_edge = MergedEdge(self)

        for edge_id in edge_ids:
            tmp_merged_edge.append(edge_id)

        sel_state_geom = self._geoms["edge"]["sel_state"]
        vertex_data = sel_state_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")

        for row_index in tmp_merged_edge.get_row_indices():
            col_writer.set_row(row_index)
            col_writer.set_data4f(color)

    def is_selected(self, subobj):

        subobj_type = subobj.get_type()
        subobj_id = subobj.get_id()
        selected_subobj_ids = self._selected_subobj_ids[subobj_type]

        return subobj_id in selected_subobj_ids

    def get_selection(self, subobj_lvl):

        subobjs = self._subobjs[subobj_lvl]
        selected_subobj_ids = self._selected_subobj_ids[subobj_lvl]

        if subobj_lvl == "vert":
            merged_verts = self._merged_verts
            verts = set(merged_verts[vert_id] for vert_id in selected_subobj_ids)
            selection = list(verts)
        elif subobj_lvl == "edge":
            merged_edges = self._merged_edges
            edges = set(merged_edges[edge_id] for edge_id in selected_subobj_ids)
            selection = list(edges)
        elif subobj_lvl == "poly":
            selection = [subobjs[i] for i in selected_subobj_ids]

        return selection

    def clear_selection(self, subobj_lvl):

        self._selected_subobj_ids[subobj_lvl] = []
        geoms = self._geoms[subobj_lvl]

        if subobj_lvl == "poly":
            sel_state_geom = geoms["sel_state"]
            sel_data = self._poly_selection_data
            sel_data["unselected"].extend(sel_data["selected"])
            sel_data["selected"] = []
            handle = sel_state_geom.node().modify_geom(1).modify_primitive(0).modify_vertices().modify_handle()
            data = handle.get_data()
            handle.set_data("")
            handle = sel_state_geom.node().modify_geom(0).modify_primitive(0).modify_vertices().modify_handle()
            handle.set_data(handle.get_data() + data)
        else:
            vertex_data = geoms["sel_state"].node().modify_geom(0).modify_vertex_data()
            colors = UVMgr.get("uv_selection_colors")[subobj_lvl]
            new_data = vertex_data.set_color(colors["unselected"])
            vertex_data.set_array(1, new_data.get_array(1))

        if subobj_lvl == "edge":

            edge_ids = self._seam_edge_ids

            if not edge_ids:
                return

            tmp_merged_edge = MergedEdge(self)

            for edge_id in edge_ids:
                tmp_merged_edge.append(edge_id)

            sel_state_geom = self._geoms["edge"]["sel_state"]
            vertex_data = sel_state_geom.node().modify_geom(0).modify_vertex_data()
            col_writer = GeomVertexWriter(vertex_data, "color")
            color = UVMgr.get("uv_selection_colors")["seam"]["unselected"]

            for row_index in tmp_merged_edge.get_row_indices():
                col_writer.set_row(row_index)
                col_writer.set_data4f(color)

        self._verts_to_transf[subobj_lvl] = {}
