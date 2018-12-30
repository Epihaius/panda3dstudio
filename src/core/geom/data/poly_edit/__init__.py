from ....base import *
from .create import CreationBase, CreationManager
from .triangulate import TriangulationBase, TriangulationManager
from .smooth import SmoothingBase, SmoothingManager, SmoothingGroup
from .surface import SurfaceBase, SurfaceManager


class PolygonEditBase(CreationBase, TriangulationBase, SmoothingBase, SurfaceBase):

    def __init__(self):

        TriangulationBase.__init__(self)
        SmoothingBase.__init__(self)

    def update_poly_centers(self):

        for poly in self._ordered_polys:
            poly.update_center_pos()

    def update_poly_normals(self):

        for poly in self._ordered_polys:
            poly.update_normal()

    def detach_polygons(self):

        selected_poly_ids = self._selected_subobj_ids["poly"]

        if not selected_poly_ids:
            return False

        merged_edges = self._merged_edges
        polys = self._subobjs["poly"]
        selected_polys = (polys[i] for i in selected_poly_ids)
        border_edges = []

        for poly in selected_polys:

            for edge_id in poly.get_edge_ids():

                merged_edge = merged_edges[edge_id]

                if merged_edge in border_edges:
                    border_edges.remove(merged_edge)
                else:
                    border_edges.append(merged_edge)

        edge_ids = set(e_id for merged_edge in border_edges for e_id in merged_edge)

        return self.split_edges(edge_ids)

    def delete_polygons(self, poly_ids, fix_borders=False):

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

        polys_to_delete = [polys[poly_id] for poly_id in poly_ids]
        poly_index = min(ordered_polys.index(poly) for poly in polys_to_delete)
        polys_to_offset = ordered_polys[poly_index:]

        row_ranges_to_delete = []
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

                if fix_borders:
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

        if fix_borders:

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


class PolygonEditManager(CreationManager, TriangulationManager, SmoothingManager, SurfaceManager):

    def __init__(self):

        CreationManager.__init__(self)
        TriangulationManager.__init__(self)
        SmoothingManager.__init__(self)
        SurfaceManager.__init__(self)

        self._pixel_under_mouse = None

        Mgr.add_app_updater("poly_detach", self.__detach_polygons)

    def __detach_polygons(self):

        selection = Mgr.get("selection_top")
        changed_objs = {}

        for model in selection:

            geom_data_obj = model.get_geom_object().get_geom_data_object()

            if geom_data_obj.detach_polygons():
                changed_objs[model.get_id()] = geom_data_obj

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.items():
            obj_data[obj_id] = geom_data_obj.get_data_to_store("prop_change", "subobj_merge")

        event_descr = "Detach polygon selection"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def _update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont


MainObjects.add_class(PolygonEditManager)
