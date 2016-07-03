from ...base import *
from .transform import SelectionTransformBase


class GeomSelectionBase(BaseObject):

    def __init__(self):

        self._subobj_sel_state = subobj_sel_state = {}

        for subobj_type in ("vert", "edge", "poly"):
            subobj_sel_state[subobj_type] = {"selected": [], "unselected": []}

        self._selected_subobj_ids = {"vert": [], "edge": [], "poly": []}

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
                data_rows = dict((unsel_state.index(i), i) for i in row_indices)
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
                data_rows = dict((unsel_state.index(i) * 2, i) for i in row_indices)
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
                data_rows = dict((sel_state.index(i) * 2, i) for i in row_indices)
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
            verts = set(merged_verts[vert_id] for vert_id in selected_subobj_ids)
            selection = list(verts)

        elif subobj_lvl == "edge":

            merged_edges = self._merged_edges
            edges = set(merged_edges[edge_id] for edge_id in selected_subobj_ids)
            selection = list(edges)

        elif subobj_lvl == "poly":

            selection = [subobjs[i] for i in selected_subobj_ids]

        return selection

    def clear_selection(self, subobj_lvl, update_verts_to_transf=True):

        sel_state = self._subobj_sel_state[subobj_lvl]
        sel_state["unselected"].extend(sel_state["selected"])
        sel_state["selected"] = []
        self._selected_subobj_ids[subobj_lvl] = []
        geom_selected = self._geoms[subobj_lvl]["selected"]
        geom_unselected = self._geoms[subobj_lvl]["unselected"]
        handle = geom_selected.node().modify_geom(0).modify_primitive(0).modify_vertices().modify_handle()
        data = handle.get_data()
        handle.set_data("")
        handle = geom_unselected.node().modify_geom(0).modify_primitive(0).modify_vertices().modify_handle()
        handle.set_data(handle.get_data() + data)

        if update_verts_to_transf:
            self._verts_to_transf[subobj_lvl] = {}

    def delete_selection(self, subobj_lvl):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        ordered_polys = self._ordered_polys
        sel_state = self._subobj_sel_state

        for subobj_type in ("vert", "edge", "poly"):
            for state in ("selected", "unselected"):
                sel_state[subobj_type][state] = []
                geom_node = self._geoms[subobj_type][state].node()
                geom_node.modify_geom(0).modify_primitive(0).modify_vertices().modify_handle().set_data("")
                # NOTE: do *NOT* call geom_node.modify_geom(0).modify_primitive(0).clearVertices(),
                # as this will explicitly remove all data from the primitive, and adding new
                # data thru ...modify_primitive(0).modify_vertices().modify_handle().set_data(data)
                # will not internally notify Panda3D that the primitive has now been
                # updated to contain new data! This will result in an assertion error
                # later on.

        selected_subobj_ids = self._selected_subobj_ids
        selected_vert_ids = selected_subobj_ids["vert"]
        selected_edge_ids = selected_subobj_ids["edge"]
        selected_poly_ids = selected_subobj_ids["poly"]
        self._verts_to_transf["vert"] = {}
        self._verts_to_transf["edge"] = {}
        self._verts_to_transf["poly"] = {}
        verts_to_delete = []
        edges_to_delete = []

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

        row_ranges_to_delete = []
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges

        subobjs_to_unreg = self._subobjs_to_unreg

        subobj_change = self._subobj_change
        subobj_change["vert"]["deleted"] = vert_change = {}
        subobj_change["edge"]["deleted"] = edge_change = {}
        subobj_change["poly"]["deleted"] = poly_change = {}
        subobj_change["selection"] = ["vert", "edge", "poly"]

        for poly in polys_to_delete:

            poly_verts = poly.get_vertices()
            vert = poly_verts[0]
            row = vert.get_row_index()
            row_ranges_to_delete.append((row, len(poly_verts)))

            verts_to_delete.extend(poly_verts)
            edges_to_delete.extend(poly.get_edges())

            ordered_polys.remove(poly)
            poly_id = poly.get_id()
            subobjs_to_unreg["poly"][poly_id] = poly
            poly_change[poly] = poly.get_creation_time()

            if poly_id in selected_poly_ids:
                selected_poly_ids.remove(poly_id)

        merged_verts_to_smooth = set()

        for vert in verts_to_delete:

            vert_id = vert.get_id()
            subobjs_to_unreg["vert"][vert_id] = vert
            vert_change[vert] = vert.get_creation_time()

            if vert_id in selected_vert_ids:
                selected_vert_ids.remove(vert_id)

            if vert_id in merged_verts:
                merged_vert = merged_verts[vert_id]
                merged_vert.remove(vert_id)
                del merged_verts[vert_id]
                merged_verts_to_smooth.add(merged_vert)

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

        self.unregister_subobjects(locally=True)

        row_index_offset = 0

        for poly in polys_to_offset:

            if poly in polys_to_delete:
                row_index_offset -= poly.get_vertex_count()
                continue

            poly_verts = poly.get_vertices()

            for vert in poly_verts:
                vert.offset_row_index(row_index_offset)

        row_ranges_to_delete.sort(reverse=True)

        vertex_data_vert = self._vertex_data["vert"]
        vertex_data_edge = self._vertex_data["edge"]
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly_picking = self._vertex_data["poly_picking"]

        vert_array = vertex_data_vert.modify_array(1)
        vert_handle = vert_array.modify_handle()
        vert_stride = vert_array.get_array_format().get_stride()
        edge_array = vertex_data_edge.modify_array(1)
        edge_handle = edge_array.modify_handle()
        edge_stride = edge_array.get_array_format().get_stride()
        picking_array = vertex_data_poly_picking.modify_array(1)
        picking_handle = picking_array.modify_handle()
        picking_stride = picking_array.get_array_format().get_stride()

        poly_arrays = []
        poly_handles = []
        poly_strides = []

        for i in xrange(vertex_data_poly.get_num_arrays()):
            poly_array = vertex_data_poly.modify_array(i)
            poly_arrays.append(poly_array)
            poly_handles.append(poly_array.modify_handle())
            poly_strides.append(poly_array.get_array_format().get_stride())

        pos_array = poly_arrays[0]

        count = self._data_row_count

        for start, size in row_ranges_to_delete:

            vert_handle.set_subdata(start * vert_stride, size * vert_stride, "")
            edge_handle.set_subdata((start + count) * edge_stride, size * edge_stride, "")
            edge_handle.set_subdata(start * edge_stride, size * edge_stride, "")
            picking_handle.set_subdata(start * picking_stride, size * picking_stride, "")

            for poly_handle, poly_stride in zip(poly_handles, poly_strides):
                poly_handle.set_subdata(start * poly_stride, size * poly_stride, "")

            count -= size

        self._data_row_count = count = len(verts)

        vertex_data_vert.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_poly_picking.set_array(0, GeomVertexArrayData(pos_array))
        tmp_array = GeomVertexArrayData(pos_array)
        handle = tmp_array.modify_handle()
        handle.set_data(handle.get_data() * 2)
        vertex_data_edge.set_array(0, tmp_array)

        sel_state["vert"]["unselected"] = range(count)
        sel_state_edge = sel_state["edge"]["unselected"]
        sel_state_poly = sel_state["poly"]["unselected"]

        for poly in ordered_polys:
            sel_state_poly.extend(poly[:])

        geoms = self._geoms

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.reserve_num_vertices(count)
        points_prim.add_next_vertices(count)
        geom_node = geoms["vert"]["unselected"].node()
        geom_node.modify_geom(0).set_primitive(0, points_prim)

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(count * 2)

        tris_prim = GeomTriangles(Geom.UH_static)

        for poly in ordered_polys:

            for edge in poly.get_edges():
                row1, row2 = [verts[v_id].get_row_index() for v_id in edge]
                lines_prim.add_vertices(row1, row2 + count)
                sel_state_edge.append(row1)

            for vert_ids in poly:
                tris_prim.add_vertices(*[verts[v_id].get_row_index() for v_id in vert_ids])

        geom_node = geoms["top"]["wire"].node()
        geom_node.modify_geom(0).set_primitive(0, lines_prim)
        geom_node = geoms["edge"]["unselected"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomLines(lines_prim))

        geom_node_top = self._toplvl_node
        geom_node_top.modify_geom(0).set_primitive(0, tris_prim)

        geom_node = geoms["poly"]["unselected"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomTriangles(tris_prim))

        geom_node = geoms["poly_picking"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomTriangles(tris_prim))

        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()

        for i, poly_array in enumerate(poly_arrays):
            vertex_data_top.set_array(i, poly_array)

        geom_node.modify_geom(0).set_primitive(0, GeomTriangles(tris_prim))

        selected_subobj_ids["vert"] = []
        selected_subobj_ids["edge"] = []
        selected_subobj_ids["poly"] = []

        for vert_id in selected_vert_ids:
            self.set_selected(verts[vert_id], True, False)

        if selected_vert_ids:
            self._update_verts_to_transform("vert")

        for edge_id in selected_edge_ids:
            self.set_selected(edges[edge_id], True, False)

        if selected_edge_ids:
            self._update_verts_to_transform("edge")

        for poly_id in selected_poly_ids:
            self.set_selected(polys[poly_id], True, False)

        if selected_poly_ids:
            self._update_verts_to_transform("poly")

        self._update_vertex_normals(merged_verts_to_smooth)
        self.get_toplevel_object().get_bbox().update(*self._origin.get_tight_bounds())

    def _restore_subobj_selection(self, time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = "subobj_selection"
        data = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)

        for subobj_type in ("vert", "edge", "poly"):

            subobj_ids = data[subobj_type]
            old_sel_subobj_ids = set(self._selected_subobj_ids[subobj_type])
            new_sel_subobj_ids = set(subobj_ids)
            sel_subobj_ids = new_sel_subobj_ids - old_sel_subobj_ids
            unsel_subobj_ids = old_sel_subobj_ids - new_sel_subobj_ids

            subobjs = self._subobjs[subobj_type]

            unsel_subobjs = [subobjs[i] for i in unsel_subobj_ids if i in subobjs]
            sel_subobjs = [subobjs[i] for i in sel_subobj_ids]

            if subobj_type in ("vert", "edge"):

                merged_subobjs = self._merged_verts if subobj_type == "vert" else self._merged_edges
                original_merged_subobjs = {}

                if unsel_subobjs:

                    tmp_merged_subobj = Mgr.do("create_merged_%s" % subobj_type, self)

                    for subobj_id in unsel_subobj_ids:
                        tmp_merged_subobj.append(subobj_id)

                    unsel_id = unsel_subobj_ids.pop()
                    original_merged_subobjs[unsel_id] = merged_subobjs[unsel_id]
                    merged_subobjs[unsel_id] = tmp_merged_subobj
                    unsel_subobjs = [subobjs[unsel_id]]

                if sel_subobjs:

                    tmp_merged_subobj = Mgr.do("create_merged_%s" % subobj_type, self)

                    for subobj_id in sel_subobj_ids:
                        tmp_merged_subobj.append(subobj_id)

                    sel_id = sel_subobj_ids.pop()
                    original_merged_subobjs[sel_id] = merged_subobjs[sel_id]
                    merged_subobjs[sel_id] = tmp_merged_subobj
                    sel_subobjs = [subobjs[sel_id]]

            for subobj in unsel_subobjs:
                self.set_selected(subobj, False, False)

            for subobj in sel_subobjs:
                self.set_selected(subobj, True, False)

            if subobj_type in ("vert", "edge"):
                if unsel_subobjs:
                    merged_subobjs[unsel_id] = original_merged_subobjs[unsel_id]
                if sel_subobjs:
                    merged_subobjs[sel_id] = original_merged_subobjs[sel_id]

            self._update_verts_to_transform(subobj_type)

        if self._tmp_geom:
            self.clear_triangulation_data()
            self.create_triangulation_data()


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

    def get_toplevel_objects(self):

        return [geom_data_obj.get_toplevel_object() for geom_data_obj in self._groups]

    def get_toplevel_object(self):
        """ Return a random top-level object """

        if self._groups:
            return self._groups.keys()[0].get_toplevel_object()

    def update(self):

        self.update_center_pos()
        self.update_ui()

    def add(self, subobj, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_add = set(subobj.get_special_selection())
        common = old_sel & sel_to_add

        if common:
            sel_to_add -= common

        if not sel_to_add:
            return False

        geom_data_objs = set()
        groups = self._groups

        for obj in sel_to_add:
            geom_data_obj = obj.get_geom_data_object()
            geom_data_obj.set_selected(obj, True)
            geom_data_objs.add(geom_data_obj)
            groups.setdefault(geom_data_obj, []).append(obj)

        sel.extend(sel_to_add)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon"}
            event_descr = 'Add to %s selection' % subobj_descr[self._obj_level]
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def remove(self, subobj, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_remove = set(subobj.get_special_selection())
        common = old_sel & sel_to_remove

        if not common:
            return False

        geom_data_objs = set()
        groups = self._groups

        for obj in common:

            sel.remove(obj)
            geom_data_obj = obj.get_geom_data_object()
            geom_data_obj.set_selected(obj, False)
            geom_data_objs.add(geom_data_obj)

            groups[geom_data_obj].remove(obj)

            if not groups[geom_data_obj]:
                del groups[geom_data_obj]

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon"}
            event_descr = 'Remove from %s selection' % subobj_descr[self._obj_level]
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def replace(self, subobj, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        new_sel = set(subobj.get_special_selection())
        common = old_sel & new_sel

        if common:
            old_sel -= common
            new_sel -= common

        if not (old_sel or new_sel):
            return False

        geom_data_objs = set()

        for old_obj in old_sel:
            sel.remove(old_obj)
            geom_data_obj = old_obj.get_geom_data_object()
            geom_data_obj.set_selected(old_obj, False)
            geom_data_objs.add(geom_data_obj)

        for new_obj in new_sel:
            geom_data_obj = new_obj.get_geom_data_object()
            geom_data_obj.set_selected(new_obj, True)
            geom_data_objs.add(geom_data_obj)

        sel.extend(new_sel)

        self._groups = groups = {}

        for obj in common | new_sel:
            groups.setdefault(obj.get_geom_data_object(), []).append(obj)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist and geom_data_objs:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon"}
            event_descr = 'Replace %s selection' % subobj_descr[self._obj_level]
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

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon"}
            event_descr = 'Clear %s selection' % subobj_descr[obj_lvl]
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.get_toplevel_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def delete(self, add_to_hist=True):

        if not self._objs:
            return False

        obj_lvl = self._obj_level
        geom_data_objs = []

        for geom_data_obj in self._groups:
            geom_data_objs.append(geom_data_obj)

        self._groups = {}
        self._objs = []

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        for geom_data_obj in geom_data_objs:
            geom_data_obj.delete_selection(obj_lvl)

        if add_to_hist:

            Mgr.do("update_history_time")

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon"}
            event_descr = 'Delete %s selection' % subobj_descr[obj_lvl]
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

        Mgr.expose("selection_vert", lambda: self._selections["vert"])
        Mgr.expose("selection_edge", lambda: self._selections["edge"])
        Mgr.expose("selection_poly", lambda: self._selections["poly"])
        Mgr.accept("update_selection_vert", lambda: self.__update_selection("vert"))
        Mgr.accept("update_selection_edge", lambda: self.__update_selection("edge"))
        Mgr.accept("update_selection_poly", lambda: self.__update_selection("poly"))
        Mgr.accept("select_vert", lambda *args: self.__select("vert", *args))
        Mgr.accept("select_edge", lambda *args: self.__select("edge", *args))
        Mgr.accept("select_poly", lambda *args: self.__select("poly", *args))
        Mgr.accept("select_single_vert", lambda: self.__select_single("vert"))
        Mgr.accept("select_single_edge", lambda: self.__select_single("edge"))
        Mgr.accept("select_single_poly", lambda: self.__select_single("poly"))
        Mgr.add_app_updater("active_obj_level", lambda: self.__clear_prev_selection(True))

    def __clear_prev_selection(self, check_top=False):

        if check_top and GlobalData["active_obj_level"] != "top":
            return

        if self._prev_obj_lvl:
            self._selections[self._prev_obj_lvl] = None
            self._prev_obj_lvl = None

    def __update_selection(self, obj_lvl):

        self.__clear_prev_selection()
        subobjs = []

        for obj in Mgr.get("selection", "top"):
            subobjs.extend(obj.get_subobj_selection(obj_lvl))

        self._selections[obj_lvl] = sel = Selection(obj_lvl, subobjs)
        sel.update()
        self._prev_obj_lvl = obj_lvl

    def __select(self, obj_lvl, picked_obj, toggle):

        if obj_lvl == "vert":
            obj = picked_obj.get_merged_vertex() if picked_obj else None
        elif obj_lvl == "edge":
            obj = picked_obj.get_merged_edge() if picked_obj else None
        elif obj_lvl == "poly":
            obj = picked_obj

        self._color_id = obj.get_picking_color_id() if obj else None

        if toggle:
            ret = self.__toggle_select(obj_lvl)
        else:
            ret = self.__normal_select(obj_lvl)

        selection = self._selections[obj_lvl]

        if obj not in selection:
            obj = selection[0] if selection else None

        if obj:

            cs_type = GlobalData["coord_sys_type"]
            tc_type = GlobalData["transf_center_type"]
            toplvl_obj = obj.get_toplevel_object()

            if cs_type == "local":
                Mgr.update_locally("coord_sys", cs_type, toplvl_obj)

            if tc_type == "pivot":
                Mgr.update_locally("transf_center", tc_type, toplvl_obj)

        return ret

    def __normal_select(self, obj_lvl):

        obj = Mgr.get(obj_lvl, self._color_id)

        if obj_lvl == "vert":
            obj = obj.get_merged_vertex() if obj else None
        elif obj_lvl == "edge":
            obj = obj.get_merged_edge() if obj else None

        selection = self._selections[obj_lvl]
        can_select_single = False
        start_mouse_checking = False

        if obj:

            if GlobalData["active_transform_type"]:

                if obj in selection and len(selection) > 1:

                    # When the user clicks one of multiple selected objects, updating the
                    # selection must be delayed until it is clear whether he wants to
                    # transform the entire selection or simply have only this object
                    # selected (this is determined by checking if the mouse has moved at
                    # least a certain number of pixels by the time the left mouse button
                    # is released).

                    can_select_single = True

                else:

                    selection.replace(obj)

                start_mouse_checking = True

            else:

                selection.replace(obj)

        else:

            selection.clear()

        return can_select_single, start_mouse_checking

    def __select_single(self, obj_lvl):

        # If multiple objects were selected and no transformation occurred, a single
        # object has been selected out of that previous selection.

        obj = Mgr.get(obj_lvl, self._color_id)

        if obj_lvl == "vert":
            obj = obj.get_merged_vertex() if obj else None
        elif obj_lvl == "edge":
            obj = obj.get_merged_edge() if obj else None

        self._selections[obj_lvl].replace(obj)

    def __toggle_select(self, obj_lvl):

        obj = Mgr.get(obj_lvl, self._color_id)

        if obj_lvl == "vert":
            obj = obj.get_merged_vertex() if obj else None
        elif obj_lvl == "edge":
            obj = obj.get_merged_edge() if obj else None

        selection = self._selections[obj_lvl]
        start_mouse_checking = False

        if obj:

            if obj in selection:
                selection.remove(obj)
                transform_allowed = False
            else:
                selection.add(obj)
                transform_allowed = GlobalData["active_transform_type"]

            if transform_allowed:
                start_mouse_checking = True

        return False, start_mouse_checking


MainObjects.add_class(SelectionManager)
