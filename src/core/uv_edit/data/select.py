from ..base import *


class UVDataSelectionBase(BaseObject):

    def __init__(self, data_copy=None):

        if data_copy:

            selected_subobj_ids = data_copy["selected_subobj_ids"]
            subobj_sel_state = data_copy["subobj_sel_state"]

        else:

            selected_subobj_ids = {}
            subobj_sel_state = {}

            for subobj_type in ("vert", "edge", "poly"):
                selected_subobj_ids[subobj_type] = []
                subobj_sel_state[subobj_type] = {
                    "selected": [], "unselected": []}

        self._selected_subobj_ids = selected_subobj_ids
        self._subobj_sel_state = subobj_sel_state

    def copy(self):

        sel_subobj_ids = {}
        subobj_sel_state = {}

        for subobj_type in ("vert", "edge", "poly"):

            sel_subobj_ids_src = self._selected_subobj_ids[subobj_type]
            sel_subobj_ids[subobj_type] = sel_subobj_ids_src[:]

            subobj_sel_state[subobj_type] = subobj_sel_state_copy = {}

            for state in ("selected", "unselected"):
                subobj_sel_state_src = self._subobj_sel_state[
                    subobj_type][state]
                subobj_sel_state_copy[state] = subobj_sel_state_src[:]

        data_copy = {}
        data_copy["selected_subobj_ids"] = sel_subobj_ids
        data_copy["subobj_sel_state"] = subobj_sel_state

        return data_copy

    def set_selected(self, subobj, is_selected=True, update_verts_to_transf=True):

        subobj_type = subobj.get_type()
        subobj_id = subobj.get_id()
        sel_state = self._subobj_sel_state[subobj_type]["selected"]
        unsel_state = self._subobj_sel_state[subobj_type]["unselected"]
        selected_subobj_ids = self._selected_subobj_ids[subobj_type]
        geom_selected = self._geoms[subobj_type]["selected"]
        geom_unselected = self._geoms[subobj_type]["unselected"]

        if is_selected:

            if subobj_id in selected_subobj_ids:
                return False

            if subobj_type == "vert":

                merged_vert = self._merged_verts[subobj_id]
                selected_subobj_ids.extend(merged_vert[:])
                row_indices = merged_vert.get_row_indices()

                prim = geom_unselected.node().modify_geom(0).modify_primitive(0)
                array = prim.modify_vertices()
                stride = array.get_array_format().get_stride()
                handle = array.modify_handle()
                data_rows = dict((unsel_state.index(i), i)
                                 for i in row_indices)
                data = ""

                for start in sorted(data_rows.iterkeys(), reverse=True):
                    row_index = data_rows[start]
                    unsel_state.remove(row_index)
                    sel_state.append(row_index)
                    data += handle.get_subdata(start * stride, stride)
                    handle.set_subdata(start * stride, stride, "")

            elif subobj_type == "edge":

                merged_edge = self._merged_edges[subobj_id]
                selected_subobj_ids.extend(merged_edge[:])
                row_indices = merged_edge.get_start_row_indices()

                prim = geom_unselected.node().modify_geom(0).modify_primitive(0)
                array = prim.modify_vertices()
                stride = array.get_array_format().get_stride()
                handle = array.modify_handle()
                data_rows = dict((unsel_state.index(i) * 2, i)
                                 for i in row_indices)
                data = ""

                for start in sorted(data_rows.iterkeys(), reverse=True):
                    row_index = data_rows[start]
                    unsel_state.remove(row_index)
                    sel_state.append(row_index)
                    data += handle.get_subdata(start * stride, stride * 2)
                    handle.set_subdata(start * stride, stride * 2, "")

            elif subobj_type == "poly":

                selected_subobj_ids.append(subobj_id)

                start = unsel_state.index(subobj[0]) * 3
                size = len(subobj)

                for vert_ids in subobj:
                    unsel_state.remove(vert_ids)

                sel_state.extend(subobj[:])
                prim = geom_unselected.node().modify_geom(0).modify_primitive(0)
                array = prim.modify_vertices()
                stride = array.get_array_format().get_stride()
                handle = array.modify_handle()
                data = handle.get_subdata(start * stride, size * stride)
                handle.set_subdata(start * stride, size * stride, "")

            prim = geom_selected.node().modify_geom(0).modify_primitive(0)
            handle = prim.modify_vertices().modify_handle()
            handle.set_data(handle.get_data() + data)

        else:

            if subobj_id not in selected_subobj_ids:
                return False

            if subobj_type == "vert":

                merged_vert = self._merged_verts[subobj_id]
                for v_id in merged_vert:
                    selected_subobj_ids.remove(v_id)
                row_indices = merged_vert.get_row_indices()

                prim = geom_selected.node().modify_geom(0).modify_primitive(0)
                array = prim.modify_vertices()
                stride = array.get_array_format().get_stride()
                handle = array.modify_handle()
                data_rows = dict((sel_state.index(i), i) for i in row_indices)
                data = ""

                for start in sorted(data_rows.iterkeys(), reverse=True):
                    row_index = data_rows[start]
                    unsel_state.append(row_index)
                    sel_state.remove(row_index)
                    data += handle.get_subdata(start * stride, stride)
                    handle.set_subdata(start * stride, stride, "")

            elif subobj_type == "edge":

                merged_edge = self._merged_edges[subobj_id]
                for e_id in merged_edge:
                    selected_subobj_ids.remove(e_id)
                row_indices = merged_edge.get_start_row_indices()

                prim = geom_selected.node().modify_geom(0).modify_primitive(0)
                array = prim.modify_vertices()
                stride = array.get_array_format().get_stride()
                handle = array.modify_handle()
                data_rows = dict((sel_state.index(i) * 2, i)
                                 for i in row_indices)
                data = ""

                for start in sorted(data_rows.iterkeys(), reverse=True):
                    row_index = data_rows[start]
                    unsel_state.append(row_index)
                    sel_state.remove(row_index)
                    data += handle.get_subdata(start * stride, stride * 2)
                    handle.set_subdata(start * stride, stride * 2, "")

            elif subobj_type == "poly":

                selected_subobj_ids.remove(subobj_id)

                start = sel_state.index(subobj[0]) * 3
                size = len(subobj)

                for vert_ids in subobj:
                    sel_state.remove(vert_ids)

                unsel_state.extend(subobj[:])
                prim = geom_selected.node().modify_geom(0).modify_primitive(0)
                array = prim.modify_vertices()
                stride = array.get_array_format().get_stride()
                handle = array.modify_handle()
                data = handle.get_subdata(start * stride, size * stride)
                handle.set_subdata(start * stride, size * stride, "")

            prim = geom_unselected.node().modify_geom(0).modify_primitive(0)
            handle = prim.modify_vertices().modify_handle()
            handle.set_data(handle.get_data() + data)

        if update_verts_to_transf:
            self._update_verts_to_transform(subobj_type)

        return True

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
            verts = set(merged_verts[vert_id]
                        for vert_id in selected_subobj_ids)
            selection = list(verts)

        elif subobj_lvl == "edge":

            merged_edges = self._merged_edges
            edges = set(merged_edges[edge_id]
                        for edge_id in selected_subobj_ids)
            selection = list(edges)

        elif subobj_lvl == "poly":

            selection = [subobjs[i] for i in selected_subobj_ids]

        return selection

    def clear_selection(self, subobj_lvl):

        sel_state = self._subobj_sel_state[subobj_lvl]
        sel_state["unselected"].extend(sel_state["selected"])
        sel_state["selected"] = []
        self._selected_subobj_ids[subobj_lvl] = []
        geom_selected = self._geoms[subobj_lvl]["selected"]
        geom_unselected = self._geoms[subobj_lvl]["unselected"]
        handle = geom_selected.node().modify_geom(
            0).modify_primitive(0).modify_vertices().modify_handle()
        data = handle.get_data()
        handle.set_data("")
        handle = geom_unselected.node().modify_geom(
            0).modify_primitive(0).modify_vertices().modify_handle()
        handle.set_data(handle.get_data() + data)

        self._verts_to_transf[subobj_lvl] = {}
