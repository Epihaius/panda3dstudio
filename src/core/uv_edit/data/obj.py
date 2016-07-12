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

    def __init__(self, uv_registry, geom_data_obj, data_copy=None):

        if data_copy:

            geom_data_obj = data_copy["geom_data_obj"]
            subobjs = data_copy["subobjs"]
            merged_verts = data_copy["merged_verts"]
            merged_edges = data_copy["merged_edges"]
            data_row_count = data_copy["data_row_count"]
            vertex_data = data_copy["vertex_data"]
            origin = data_copy["origin"]
            geom_roots = data_copy["geom_roots"]
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
            data_row_count = 0
            vertex_data = {}
            model = geom_data_obj.get_toplevel_object()
            name = "%s_uv_origin" % (model.get_id(),)
            color = model.get_color()
            origin = self.geom_root.attach_new_node(name)
            origin.set_color(color)
            origin.node().set_final(True)
            geom_roots = {}
            geoms = {}

            for subobj_type in ("vert", "edge", "poly"):
                subobjs[subobj_type] = {}
                vertex_data[subobj_type] = None
                geoms[subobj_type] = {"selected": None, "unselected": None}

        self._geom_data_obj = geom_data_obj
        self._subobjs = subobjs
        self._merged_verts = merged_verts
        self._merged_edges = merged_edges
        self._data_row_count = data_row_count
        self._vertex_data = vertex_data
        self._origin = origin
        self._geom_roots = geom_roots
        self._geoms = geoms

        UVDataSelectionBase.__init__(self, data_copy)
        is_copy = True if data_copy else False
        UVDataTransformBase.__init__(self, is_copy)

        if not data_copy:
            self.__process_geom_data(uv_registry)
            self.__create_geometry()

    def copy(self):

        subobjs = {}
        vertex_data = {}
        origin_copy = self._origin.copy_to(self.geom_root)
        origin_copy.detach_node()
        geom_roots = {}
        geoms = {}
        geoms["wire"] = origin_copy.find("wire_geom")

        for subobj_type in ("vert", "edge", "poly"):

            subobjs[subobj_type] = dict((k, v.copy()) for k, v in self._subobjs[subobj_type].iteritems())
            vertex_data[subobj_type] = GeomVertexData(self._vertex_data[subobj_type])
            geom_roots[subobj_type] = origin_copy.find("%s_geom_root" % subobj_type)

            geoms[subobj_type] = {}

            for state in ("selected", "unselected"):
                path = "**/%s_%s_geom" % (subobj_type, state)
                geom = origin_copy.find(path)
                geom.node().modify_geom(0).set_vertex_data(vertex_data[subobj_type])
                geoms[subobj_type][state] = geom

        geoms["wire"].node().modify_geom(0).set_vertex_data(vertex_data["edge"])

        geom_node = geoms["poly"]["selected"].node()
        prim = geom_node.get_geom(0).get_primitive(0)
        data = prim.get_vertices().get_handle().get_data()
        tmp_prim = GeomTriangles(Geom.UH_static)
        tmp_prim.add_vertices(0, 1, 2)
        geom_node.modify_geom(0).set_primitive(0, tmp_prim)

        def update_selected_polys(task):

            Mgr.render_frame()
            tmp_prim.modify_vertices().modify_handle().set_data(data)

            return task.done

        Mgr.do_next_frame(update_selected_polys, "update_sel_polys")

        data_copy = {}
        data_copy["geom_data_obj"] = self._geom_data_obj
        data_copy["subobjs"] = subobjs
        data_copy["merged_verts"] = dict((k, v.copy()) for k, v in self._merged_verts.iteritems())
        data_copy["merged_edges"] = dict((k, v.copy()) for k, v in self._merged_edges.iteritems())
        data_copy["data_row_count"] = self._data_row_count
        data_copy["vertex_data"] = vertex_data
        data_copy["origin"] = origin_copy
        data_copy["geom_roots"] = geom_roots
        data_copy["geoms"] = geoms
        data_copy.update(UVDataSelectionBase.copy(self))

        return UVDataObject(None, None, data_copy)

    def destroy(self):

        self._origin.remove_node()

    def __process_geom_data(self, uv_registry):

        geom_data_obj = self._geom_data_obj

        verts = geom_data_obj.get_subobjects("vert")
        edges = geom_data_obj.get_subobjects("edge")
        polys = geom_data_obj.get_subobjects("poly")

        subobjs = self._subobjs
        uv_verts = subobjs["vert"]
        uv_edges = subobjs["edge"]
        uv_polys = subobjs["poly"]

        uv_set_id = UVMgr.get("active_uv_set")

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
            uv_poly = Polygon(poly_id, picking_col_id, self, poly[:],
                              uv_poly_edges, uv_poly_verts)
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

    def __create_geometry(self):

        orig = self._origin
        vert_geom_root = orig.attach_new_node("vert_geom_root")
        edge_geom_root = orig.attach_new_node("edge_geom_root")
        poly_geom_root = orig.attach_new_node("poly_geom_root")

        uv_template_mask = UVMgr.get("template_mask")

        vert_geom_root.set_bin("background", 13)
        vert_geom_root.set_depth_write(False)
        vert_geom_root.set_depth_test(False)
        vert_geom_root.set_render_mode_thickness(7)
        vert_geom_root.set_light_off()
        vert_geom_root.set_texture_off()
        vert_geom_root.set_material_off()
        vert_geom_root.set_shader_off()
        vert_geom_root.hide(uv_template_mask)

        edge_geom_root.set_bin("background", 12)
        edge_geom_root.set_depth_write(False)
        edge_geom_root.set_depth_test(False)
        edge_geom_root.set_light_off()
        edge_geom_root.set_texture_off()
        edge_geom_root.set_material_off()
        edge_geom_root.set_shader_off()
        edge_geom_root.hide(uv_template_mask)

        poly_geom_root.set_bin("background", 10)
        poly_geom_root.set_depth_write(False)
        poly_geom_root.set_depth_test(False)
        poly_geom_root.set_two_sided(True)

        geom_roots = self._geom_roots
        geom_roots["vert"] = vert_geom_root
        geom_roots["edge"] = edge_geom_root
        geom_roots["poly"] = poly_geom_root

        subobjs = self._subobjs
        verts = subobjs["vert"]
        polys = subobjs["poly"]
        self._data_row_count = count = len(verts)
        tri_vert_count = sum([len(poly) for poly in polys.itervalues()])

        sel_state = self._subobj_sel_state
        sel_state["vert"]["unselected"] = range(count)
        sel_state_edge = sel_state["edge"]["unselected"]
        sel_state_poly = sel_state["poly"]["unselected"]

        vertex_format_vert = Mgr.get("vertex_format_vert")
        vertex_data_vert = GeomVertexData("vert_data", vertex_format_vert, Geom.UH_dynamic)
        vertex_data_vert.reserve_num_rows(count)
        vertex_data_vert.set_num_rows(count)
        self._vertex_data["vert"] = vertex_data_vert
        vertex_format_edge = Mgr.get("vertex_format_edge")
        vertex_data_edge = GeomVertexData("edge_data", vertex_format_edge, Geom.UH_dynamic)
        vertex_data_edge.reserve_num_rows(count * 2)
        vertex_data_edge.set_num_rows(count * 2)
        self._vertex_data["edge"] = vertex_data_edge
        vertex_format_poly = Mgr.get("vertex_format_poly")
        vertex_data_poly = GeomVertexData("poly_data", vertex_format_poly, Geom.UH_dynamic)
        vertex_data_poly.reserve_num_rows(count)
        vertex_data_poly.set_num_rows(count)
        self._vertex_data["poly"] = vertex_data_poly

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
                sel_state_edge.append(row1)
                picking_color_edge = get_color_vec(edge.get_picking_color_id(),
                                                   pickable_id_edge)
                col_writer_edge.set_row(row1)
                col_writer_edge.set_data4f(picking_color_edge)
                col_writer_edge.set_row(row2 + count)
                col_writer_edge.set_data4f(picking_color_edge)

            row_index_offset += poly.get_vertex_count()

            sel_state_poly.extend(poly[:])

            poly_center = sum(poly_corners, Point3()) / len(poly_corners)
            poly.set_center_pos(poly_center)

        pos_array = vertex_data_poly.get_array(0)
        pos_data = pos_array.get_handle().get_data()
        vertex_data_vert.set_array(0, pos_array)
        array = GeomVertexArrayData(pos_array)
        array.modify_handle().set_data(pos_data * 2)
        vertex_data_edge.set_array(0, array)
        geoms = self._geoms

        points_geom = Geom(vertex_data_vert)
        points_geom.add_primitive(points_prim)
        geom_node = GeomNode("vert_unselected_geom")
        geom_node.add_geom(points_geom)
        vert_unselected_geom = vert_geom_root.attach_new_node(geom_node)
        vert_unselected_geom.set_color(.5, .5, 1.)
        geoms["vert"]["unselected"] = vert_unselected_geom

        points_prim = GeomPoints(points_prim)
        points_geom = Geom(vertex_data_vert)
        points_geom.add_primitive(points_prim)
        geom_node = GeomNode("vert_selected_geom")
        geom_node.add_geom(points_geom)
        vert_selected_geom = vert_geom_root.attach_new_node(geom_node)
        vert_selected_geom.set_color(1., 0., 0.)
        geoms["vert"]["selected"] = vert_selected_geom

        render_mask = UVMgr.get("render_mask")
        picking_mask = UVMgr.get("picking_mask")

        vertices = lines_prim.get_vertices()
        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("wire_geom")
        geom_node.add_geom(lines_geom)
        wire_geom = orig.attach_new_node(geom_node)
        wire_geom.set_bin("background", 11)
        wire_geom.set_depth_write(False)
        wire_geom.set_depth_test(False)
        wire_geom.set_light_off()
        wire_geom.set_texture_off()
        wire_geom.set_material_off()
        wire_geom.set_shader_off()
        wire_geom.hide(picking_mask)
        wire_geom.set_tag("uv_template", "edge")
        geoms["wire"] = wire_geom

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.set_vertices(GeomVertexArrayData(vertices))
        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("edge_unselected_geom")
        geom_node.add_geom(lines_geom)
        edge_unselected_geom = edge_geom_root.attach_new_node(geom_node)
        edge_unselected_geom.set_color(1., 1., 1.)
        geoms["edge"]["unselected"] = edge_unselected_geom

        lines_prim = GeomLines(lines_prim)
        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("edge_selected_geom")
        geom_node.add_geom(lines_geom)
        edge_selected_geom = edge_geom_root.attach_new_node(geom_node)
        edge_selected_geom.set_color(1., 0., 0.)
        geoms["edge"]["selected"] = edge_selected_geom

        tris_geom = Geom(GeomVertexData(vertex_data_poly))
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_unselected_geom")
        geom_node.add_geom(tris_geom)
        poly_unselected_geom = poly_geom_root.attach_new_node(geom_node)
        poly_unselected_geom.hide(render_mask)
        poly_unselected_geom.set_tag("uv_template", "poly")
        geoms["poly"]["unselected"] = poly_unselected_geom

        # although the primitive should be empty, it needs *all* vertices initially,
        # otherwise selected polys will not be rendered later on;
        # the vertices will be removed in the next frame
        tris_prim = GeomTriangles(tris_prim)
        tris_geom = Geom(vertex_data_poly)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_selected_geom")
        geom_node.add_geom(tris_geom)
        poly_selected_geom = poly_geom_root.attach_new_node(geom_node)
        poly_selected_geom.set_state(UVMgr.get("poly_selection_state"))
        poly_selected_geom.set_effects(UVMgr.get("poly_selection_effects"))
        poly_selected_geom.set_tag("uv_template", "poly")
        geoms["poly"]["selected"] = poly_selected_geom

        Mgr.do_next_frame(self.__clear_selected_subobjs, "clear_sel_subobjs")

    def __clear_selected_subobjs(self, task):

        geoms = self._geoms

        geom = geoms["vert"]["selected"]
        prim = geom.node().modify_geom(0).modify_primitive(0)
        handle = prim.modify_vertices().modify_handle()
        handle.set_data("")

        geom = geoms["edge"]["selected"]
        prim = geom.node().modify_geom(0).modify_primitive(0)
        handle = prim.modify_vertices().modify_handle()
        handle.set_data("")

        geom = geoms["poly"]["selected"]
        geom.set_transparency(TransparencyAttrib.M_alpha)
        prim = geom.node().modify_geom(0).modify_primitive(0)
        handle = prim.modify_vertices().modify_handle()
        handle.set_data("")

        return task.done

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

        geom_roots = self._geom_roots
        subobj_lvls = ["vert", "edge", "poly"]
        subobj_lvls.remove(subobj_lvl)

        geom_roots[subobj_lvl].show(masks)

        for lvl in subobj_lvls:
            geom_roots[lvl].hide(masks)

    def show(self):

        self._origin.reparent_to(self.geom_root)

    def hide(self):

        self._origin.detach_node()
