from ..base import *
from .vert import Vertex, MergedVertex
from .edge import Edge, MergedEdge
from .poly import Polygon
from .vert_edit import VertexEditBase
from .edge_edit import EdgeEditBase
from .poly_edit import PolygonEditBase
from .select import UVDataSelectionBase
from .transform import UVDataTransformBase


class UVDataObject(UVDataSelectionBase, UVDataTransformBase, VertexEditBase,
                   EdgeEditBase, PolygonEditBase):

    def __init__(self, uv_set_id, uv_registry, geom_data_obj, data_copy=None):

        if data_copy:

            geom_data_obj = data_copy["geom_data_obj"]
            subobjs = data_copy["subobjs"]
            merged_verts = data_copy["merged_verts"]
            merged_edges = data_copy["merged_edges"]
            seam_edge_ids = data_copy["seam_edge_ids"]
            data_row_count = data_copy["data_row_count"]
            vertex_data_poly = data_copy["vertex_data_poly"]
            origin = data_copy["origin"]
            geoms = data_copy["geoms"]

            for subobj_type in ("vert", "edge", "poly"):
                for subobj in subobjs[subobj_type].itervalues():
                    subobj.set_uv_data_object(self)

            for merged_vert in merged_verts.itervalues():
                merged_vert.set_uv_data_object(self)

            for merged_edge in merged_edges.itervalues():
                merged_edge.set_uv_data_object(self)

        else:

            subobjs = {}
            merged_verts = {}
            merged_edges = {}
            seam_edge_ids = []
            data_row_count = 0
            vertex_data_poly = None
            model = geom_data_obj.get_toplevel_object()
            name = "%s_uv_origin" % (model.get_id(),)
            origin = self.geom_root.attach_new_node(name)
            origin.node().set_final(True)
            geoms = {}

            for subobj_type in ("vert", "edge", "poly"):
                subobjs[subobj_type] = {}
                geoms[subobj_type] = {"pickable": None, "sel_state": None}

            del geoms["poly"]["pickable"]

        self._uv_set_id = uv_set_id
        self._geom_data_obj = geom_data_obj
        self._subobjs = subobjs
        self._merged_verts = merged_verts
        self._merged_edges = merged_edges
        self._seam_edge_ids = seam_edge_ids
        self._data_row_count = data_row_count
        self._vertex_data_poly = vertex_data_poly
        self._origin = origin
        self._geoms = geoms

        UVDataSelectionBase.__init__(self, data_copy)
        is_copy = True if data_copy else False
        UVDataTransformBase.__init__(self, is_copy)

        if not data_copy:
            self.__process_geom_data(uv_registry)
            self.__create_geometry()

        if uv_set_id is not None:
            color = UVMgr.get("uv_selection_colors")["seam"]["unselected"]
            geom_data_obj.create_tex_seams(uv_set_id, seam_edge_ids, color)

    def copy(self, uv_set_id=None):

        subobjs = {}
        vertex_data_poly = GeomVertexData(self._vertex_data_poly)
        origin = self._origin
        origin_copy = origin.copy_to(self.geom_root)
        origin_copy.detach_node()
        geoms = {}
        geoms["seam"] = origin_copy.find("**/seam_geom")

        for subobj_type in ("vert", "edge", "poly"):
            subobjs[subobj_type] = dict((k, v.copy()) for k, v in self._subobjs[subobj_type].iteritems())
            geoms[subobj_type] = {}

        for subobj_type in ("vert", "edge"):
            for geom_type in ("pickable", "sel_state"):
                path = "**/%s_%s_geom" % (subobj_type, geom_type)
                src_geom = origin.find(path)
                vertex_data = GeomVertexData(src_geom.node().get_geom(0).get_vertex_data())
                geom = origin_copy.find(path)
                geom.node().modify_geom(0).set_vertex_data(vertex_data)
                geoms[subobj_type][geom_type] = geom

        path = "**/poly_sel_state_geom"
        geom = origin_copy.find(path)
        geom.node().modify_geom(0).set_vertex_data(vertex_data_poly)
        geom.node().modify_geom(1).set_vertex_data(vertex_data_poly)
        geoms["poly"]["sel_state"] = geom

        geom_node = geom.node()
        prim = geom_node.get_geom(1).get_primitive(0)
        data = prim.get_vertices().get_handle().get_data()
        tmp_prim = GeomTriangles(Geom.UH_static)
        tmp_prim.add_vertices(0, 1, 2)
        geom_node.modify_geom(1).set_primitive(0, tmp_prim)

        def update_selected_polys(task):

            Mgr.render_frame()
            tmp_prim.modify_vertices().modify_handle().set_data(data)

            return task.done

        Mgr.do_next_frame(update_selected_polys, "update_sel_polys")

        data_copy = {}
        data_copy["geom_data_obj"] = self._geom_data_obj
        data_copy["subobjs"] = subobjs
        merged_verts = self._merged_verts
        merged_vert_copies = dict((mv, mv.copy()) for mv in set(merged_verts.itervalues()))
        data_copy["merged_verts"] = dict((k, merged_vert_copies[v])
                                         for k, v in merged_verts.iteritems())
        merged_edges = self._merged_edges
        merged_edge_copies = dict((me, me.copy()) for me in set(merged_edges.itervalues()))
        data_copy["merged_edges"] = dict((k, merged_edge_copies[v])
                                         for k, v in merged_edges.iteritems())
        data_copy["seam_edge_ids"] = self._seam_edge_ids[:]
        data_copy["data_row_count"] = self._data_row_count
        data_copy["vertex_data_poly"] = vertex_data_poly
        data_copy["origin"] = origin_copy
        data_copy["geoms"] = geoms
        data_copy.update(UVDataSelectionBase.copy(self))

        return UVDataObject(uv_set_id, None, None, data_copy)

    def destroy(self):

        self._origin.remove_node()
        self._geom_data_obj.destroy_tex_seams(self._uv_set_id)

    def __process_geom_data(self, uv_registry):

        geom_data_obj = self._geom_data_obj

        verts = geom_data_obj.get_subobjects("vert")
        edges = geom_data_obj.get_subobjects("edge")
        polys = geom_data_obj.get_subobjects("poly")

        subobjs = self._subobjs
        uv_verts = subobjs["vert"]
        uv_edges = subobjs["edge"]
        uv_polys = subobjs["poly"]

        uv_set_id = self._uv_set_id

        self._data_row_count = len(verts)

        for poly_id, poly in polys.iteritems():

            uv_poly_verts = []
            uv_poly_edges = []

            row_index = 0

            for vert_ids in poly:
                for vert_id in vert_ids:
                    if vert_id not in uv_verts:
                        vert = verts[vert_id]
                        u, v = vert.get_uvs(uv_set_id)
                        pos = Point3(u, 0., v)
                        picking_col_id = vert.get_picking_color_id()
                        uv_vert = Vertex(vert_id, picking_col_id, self, pos)
                        uv_vert.set_row_index(row_index)
                        row_index += 1
                        uv_registry["vert"][picking_col_id] = uv_vert
                        uv_verts[vert_id] = uv_vert
                        uv_poly_verts.append(uv_vert)

            for edge_id in poly.get_edge_ids():

                edge = edges[edge_id]
                uv_edge_verts = []

                for vert_id in edge:
                    uv_vert = uv_verts[vert_id]
                    uv_edge_verts.append(uv_vert)

                picking_col_id = edge.get_picking_color_id()
                uv_edge = Edge(edge_id, picking_col_id, self, uv_edge_verts)
                uv_registry["edge"][picking_col_id] = uv_edge
                uv_edges[edge_id] = uv_edge
                uv_poly_edges.append(uv_edge)

            picking_col_id = poly.get_picking_color_id()
            uv_poly = Polygon(poly_id, picking_col_id, self, poly[:], uv_poly_edges, uv_poly_verts)
            uv_registry["poly"][picking_col_id] = uv_poly
            uv_polys[poly_id] = uv_poly

        merged_uv_verts = self._merged_verts
        merged_uv_edges = self._merged_edges

        for vert_id, uv_vert in uv_verts.iteritems():

            if vert_id in merged_uv_verts:
                continue

            uv = verts[vert_id].get_uvs(uv_set_id)
            merged_vert = geom_data_obj.get_merged_vertex(vert_id)
            merged_uv_vert = MergedVertex(self)

            for v_id in merged_vert:
                if verts[v_id].get_uvs(uv_set_id) == uv:
                    merged_uv_vert.append(v_id)
                    merged_uv_verts[v_id] = merged_uv_vert

        for edge_id, uv_edge in uv_edges.iteritems():

            if edge_id in merged_uv_edges:
                continue

            merged_uvs = set(merged_uv_verts[v_id] for v_id in uv_edge)
            merged_edge = geom_data_obj.get_merged_edge(edge_id)
            merged_uv_edge = MergedEdge(self)

            for e_id in merged_edge:
                if set(merged_uv_verts[v_id] for v_id in edges[e_id]) == merged_uvs:
                    merged_uv_edge.append(e_id)
                    merged_uv_edges[e_id] = merged_uv_edge

        seam_edge_ids = self._seam_edge_ids

        for edge_id, merged_edge in merged_uv_edges.iteritems():
            if len(merged_edge) == 1:
                seam_edge_ids.append(edge_id)

    def __create_geometry(self):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        polys = subobjs["poly"]
        self._data_row_count = count = len(verts)
        tri_vert_count = sum(len(poly) for poly in polys.itervalues())

        sel_data = self._poly_selection_data["unselected"]

        vertex_format_vert = Mgr.get("vertex_format_basic")
        vertex_data_vert = GeomVertexData("vert_data", vertex_format_vert, Geom.UH_dynamic)
        vertex_data_vert.reserve_num_rows(count)
        vertex_data_vert.set_num_rows(count)
        vertex_format_edge = Mgr.get("vertex_format_basic")
        vertex_data_edge = GeomVertexData("edge_data", vertex_format_edge, Geom.UH_dynamic)
        vertex_data_edge.reserve_num_rows(count * 2)
        vertex_data_edge.set_num_rows(count * 2)
        vertex_format_poly = Mgr.get("vertex_format_full")
        vertex_data_poly = GeomVertexData("poly_data", vertex_format_poly, Geom.UH_dynamic)
        vertex_data_poly.reserve_num_rows(count)
        vertex_data_poly.set_num_rows(count)
        self._vertex_data_poly = vertex_data_poly

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.reserve_num_vertices(count)
        points_prim.add_next_vertices(count)
        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(count * 2)
        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.reserve_num_vertices(tri_vert_count)

        pos_writer = GeomVertexWriter(vertex_data_poly, "vertex")
        col_writer_vert = GeomVertexWriter(vertex_data_vert, "color")
        col_writer_edge = GeomVertexWriter(vertex_data_edge, "color")
        col_writer_poly = GeomVertexWriter(vertex_data_poly, "color")
        pickable_id_vert = PickableTypes.get_id("vert")
        pickable_id_edge = PickableTypes.get_id("edge")
        pickable_id_poly = PickableTypes.get_id("poly")

        row_index_offset = 0

        for poly_id, poly in polys.iteritems():

            poly_corners = []
            processed_verts = []
            picking_color_poly = get_color_vec(poly.get_picking_color_id(),
                                               pickable_id_poly)

            for vert_ids in poly:

                for vert_id in vert_ids:

                    vert = verts[vert_id]

                    if vert not in processed_verts:
                        vert.offset_row_index(row_index_offset)
                        pos = vert.get_pos()
                        poly_corners.append(pos)
                        pos_writer.add_data3f(pos)
                        col_writer_poly.add_data4f(picking_color_poly)
                        picking_color_vert = get_color_vec(vert.get_picking_color_id(),
                                                           pickable_id_vert)
                        col_writer_vert.add_data4f(picking_color_vert)
                        processed_verts.append(vert)

                    tris_prim.add_vertex(vert.get_row_index())

            start_row_indices = []
            end_row_indices = []

            for edge in poly.get_edges():

                row1, row2 = [verts[v_id].get_row_index() for v_id in edge]

                if row1 in start_row_indices or row2 in end_row_indices:
                    row1, row2 = row2, row1
                    edge.reverse_vertex_order()

                start_row_indices.append(row1)
                end_row_indices.append(row2)
                lines_prim.add_vertices(row1, row2 + count)
                picking_color_edge = get_color_vec(edge.get_picking_color_id(),
                                                   pickable_id_edge)
                col_writer_edge.set_row(row1)
                col_writer_edge.set_data4f(picking_color_edge)
                col_writer_edge.set_row(row2 + count)
                col_writer_edge.set_data4f(picking_color_edge)

            row_index_offset += poly.get_vertex_count()

            sel_data.extend(poly[:])

            poly_center = sum(poly_corners, Point3()) / len(poly_corners)
            poly.set_center_pos(poly_center)

        pos_array = vertex_data_poly.get_array(0)
        pos_data = pos_array.get_handle().get_data()
        vertex_data_vert.set_array(0, pos_array)
        array = GeomVertexArrayData(pos_array)
        array.modify_handle().set_data(pos_data * 2)
        vertex_data_edge.set_array(0, array)
        geoms = self._geoms
        origin = self._origin

        render_mask = UVMgr.get("render_mask")
        picking_mask = UVMgr.get("picking_mask")
        masks = render_mask | picking_mask

        uv_template_mask = UVMgr.get("template_mask")

        sel_colors = UVMgr.get("uv_selection_colors")

        points_geom = Geom(vertex_data_vert)
        points_geom.add_primitive(points_prim)
        geom_node = GeomNode("vert_pickable_geom")
        geom_node.add_geom(points_geom)
        vert_pickable_geom = origin.attach_new_node(geom_node)
        vert_pickable_geom.hide(masks)
        geoms["vert"]["pickable"] = vert_pickable_geom

        vert_sel_state_geom = vert_pickable_geom.copy_to(origin)
        vertex_data = vert_sel_state_geom.node().modify_geom(0).modify_vertex_data()
        new_data = vertex_data.set_color(sel_colors["vert"]["unselected"])
        vertex_data.set_array(1, new_data.get_array(1))
        vert_sel_state_geom.set_state(UVMgr.get("vert_render_state"))
        vert_sel_state_geom.set_name("vert_sel_state_geom")
        geoms["vert"]["sel_state"] = vert_sel_state_geom

        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("edge_pickable_geom")
        geom_node.add_geom(lines_geom)
        edge_pickable_geom = origin.attach_new_node(geom_node)
        edge_pickable_geom.set_state(UVMgr.get("edge_render_state"))
        edge_pickable_geom.hide(masks)
        geoms["edge"]["pickable"] = edge_pickable_geom

        edge_sel_state_geom = edge_pickable_geom.copy_to(origin)
        vertex_data = edge_sel_state_geom.node().modify_geom(0).modify_vertex_data()
        new_data = vertex_data.set_color(sel_colors["edge"]["unselected"])
        vertex_data.set_array(1, new_data.get_array(1))
        edge_sel_state_geom.set_name("edge_sel_state_geom")
        geoms["edge"]["sel_state"] = edge_sel_state_geom
        self.clear_selection("edge")

        edge_pickable_geom.show_through(uv_template_mask)
        edge_pickable_geom.set_tag("uv_template", "edge")
        color = self._geom_data_obj.get_toplevel_object().get_color()
        edge_pickable_geom.set_color(color)

        seam_geom = edge_pickable_geom.copy_to(edge_pickable_geom)
        seam_geom.set_name("seam_geom")
        seam_geom.set_color(sel_colors["seam"]["unselected"])
        seam_geom.show(masks)
        seam_geom.set_bin("background", 12)
        seam_geom.set_tag("uv_template", "seam")
        geoms["seam"] = seam_geom

        geom_node = GeomNode("poly_sel_state_geom")
        tris_geom = Geom(vertex_data_poly)
        tris_geom.add_primitive(tris_prim)
        geom_node.add_geom(tris_geom, UVMgr.get("poly_states")["unselected"])
        tris_geom = Geom(vertex_data_poly)
        # although the primitive should be empty, it needs *all* vertices initially,
        # otherwise selected polys will not be rendered later on;
        # the vertices will be removed in the next frame
        tris_geom.add_primitive(GeomTriangles(tris_prim))
        geom_node.add_geom(tris_geom)
        poly_sel_state_geom = origin.attach_new_node(geom_node)
        poly_sel_state_geom.set_state(UVMgr.get("poly_states")["selected"])
        poly_sel_state_geom.set_effects(UVMgr.get("poly_selection_effects"))
        poly_sel_state_geom.set_bin("background", 10)
        poly_sel_state_geom.hide(picking_mask)
        poly_sel_state_geom.show_through(uv_template_mask)
        poly_sel_state_geom.set_tag("uv_template", "poly")
        geoms["poly"]["sel_state"] = poly_sel_state_geom

        Mgr.do_next_frame(self.__clear_selected_polys, "clear_sel_polys")

    def __clear_selected_polys(self, task):

        geoms = self._geoms

        geom = geoms["poly"]["sel_state"]
        geom.set_transparency(TransparencyAttrib.M_alpha)
        prim = geom.node().modify_geom(1).modify_primitive(0)
        handle = prim.modify_vertices().modify_handle()
        handle.set_data("")

        self.update_seams()

        return task.done

    def update_seams(self):

        edges = self._subobjs["edge"]
        seam_edge_ids = self._seam_edge_ids
        geoms = self._geoms

        seam_geom = geoms["seam"]
        seam_prim = seam_geom.node().modify_geom(0).modify_primitive(0)
        seam_handle = seam_prim.modify_vertices().modify_handle()

        edge_geom = geoms["edge"]["pickable"]
        edge_prim = edge_geom.node().get_geom(0).get_primitive(0)

        tmp_merged_edge = Mgr.do("create_merged_edge", self)

        for edge_id in seam_edge_ids:
            tmp_merged_edge.append(edge_id)

        row_indices = tmp_merged_edge.get_start_row_indices()
        array = edge_prim.get_vertices()
        stride = array.get_array_format().get_stride()
        edge_handle = array.get_handle()
        rows = edge_prim.get_vertex_list()[::2]
        data_rows = sorted(rows.index(i) * 2 for i in row_indices)
        data = ""

        for start in data_rows:
            data += edge_handle.get_subdata(start * stride, stride * 2)

        seam_handle.set_data(data)

    def add_seam_edges(self, edge_ids):

        self._seam_edge_ids.extend(edge_ids)
        edges = self._subobjs["edge"]
        row_indices = [edges[edge_id].get_start_row_index() for edge_id in edge_ids]

        geoms = self._geoms

        seam_geom = geoms["seam"]
        seam_prim = seam_geom.node().modify_geom(0).modify_primitive(0)
        seam_handle = seam_prim.modify_vertices().modify_handle()

        edge_geom = geoms["edge"]["pickable"]
        edge_prim = edge_geom.node().get_geom(0).get_primitive(0)
        array = edge_prim.get_vertices()
        rows = edge_prim.get_vertex_list()[::2]
        stride = array.get_array_format().get_stride()
        edge_handle = array.get_handle()
        data_rows = sorted(rows.index(i) * 2 for i in row_indices)
        data = ""

        for start in data_rows:
            data += edge_handle.get_subdata(start * stride, stride * 2)

        seam_handle.set_data(seam_handle.get_data() + data)
        self._geom_data_obj.add_tex_seam_edges(self._uv_set_id, edge_ids)

    def remove_seam_edges(self, edge_ids):

        for edge_id in edge_ids:
            self._seam_edge_ids.remove(edge_id)

        edges = self._subobjs["edge"]
        row_indices = [edges[edge_id].get_start_row_index() for edge_id in edge_ids]

        seam_geom = self._geoms["seam"]
        seam_prim = seam_geom.node().modify_geom(0).modify_primitive(0)
        seam_handle = seam_prim.modify_vertices().modify_handle()
        array = seam_prim.get_vertices()
        rows = seam_prim.get_vertex_list()[::2]
        stride = array.get_array_format().get_stride()
        data_rows = sorted((rows.index(i) * 2 for i in row_indices), reverse=True)

        for start in data_rows:
            seam_handle.set_subdata(start * stride, stride * 2, "")

        self._geom_data_obj.remove_tex_seam_edges(self._uv_set_id, edge_ids)

    def get_geom_data_object(self):

        return self._geom_data_obj

    def get_origin(self):

        return self._origin

    def get_merged_vertex(self, vert_id):

        return self._merged_verts[vert_id]

    def get_merged_edge(self, edge_id):

        return self._merged_edges[edge_id]

    def get_subobjects(self, subobj_type):

        return self._subobjs[subobj_type]

    def get_subobject(self, subobj_type, subobj_id):

        return self._subobjs[subobj_type].get(subobj_id)

    def show_subobj_level(self, subobj_lvl):

        render_mask = UVMgr.get("render_mask")
        picking_mask = UVMgr.get("picking_mask")
        masks = render_mask | picking_mask
        geoms = self._geoms

        if subobj_lvl == "edge":
            geoms["seam"].hide(render_mask)
            geoms["edge"]["sel_state"].show(render_mask)
            geoms["edge"]["pickable"].hide(render_mask)
            geoms["edge"]["pickable"].show(picking_mask)
        else:
            geoms["seam"].show(render_mask)
            geoms["edge"]["sel_state"].hide(render_mask)
            geoms["edge"]["pickable"].show(render_mask)
            geoms["edge"]["pickable"].hide(picking_mask)

        if subobj_lvl == "vert":
            geoms["vert"]["sel_state"].show(render_mask)
            geoms["vert"]["pickable"].show(picking_mask)
        else:
            geoms["vert"]["sel_state"].hide(render_mask)
            geoms["vert"]["pickable"].hide(picking_mask)

        poly_geom = geoms["poly"]["sel_state"]

        if subobj_lvl == "poly":
            poly_geom.set_state(UVMgr.get("poly_states")["selected"])
            poly_geom.show(picking_mask)
        else:
            poly_geom.set_state(UVMgr.get("poly_states")["unselected"])
            poly_geom.hide(picking_mask)

    def set_poly_state(self, sel_state, state):

        if sel_state == "unselected":
            self._geoms["poly"]["sel_state"].node().set_geom_state(0, state)
        else:
            self._geoms["poly"]["sel_state"].set_state(state)

    def show(self):

        self._origin.reparent_to(self.geom_root)

    def hide(self):

        self._origin.detach_node()
