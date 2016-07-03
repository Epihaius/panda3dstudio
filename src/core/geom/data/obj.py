from ...base import *
from .select import GeomSelectionBase
from .transform import GeomTransformBase
from .history import GeomHistoryBase
from .poly_create import PolygonCreationBase
from .vert_edit import VertexEditBase
from .edge_edit import EdgeEditBase
from .poly_edit import PolygonEditBase, SmoothingGroup
from .uv import UVEditBase


class GeomDataObject(GeomSelectionBase, GeomTransformBase, GeomHistoryBase,
                     PolygonCreationBase, PolygonEditBase, EdgeEditBase,
                     VertexEditBase, UVEditBase):

    def __getstate__(self):

        orig = self._origin
        orig.get_children().detach()

        state = self.__dict__.copy()
        del state["_vertex_data"]
        del state["_owner"]
        del state["_toplvl_node"]
        del state["_toplvl_geom"]
        del state["_geoms"]
        del state["_geom_roots"]
        del state["_ordered_polys"]
        del state["_merged_verts"]
        del state["_merged_edges"]
        del state["_subobjs"]
        del state["_subobj_sel_state"]
        del state["_selected_subobj_ids"]
        del state["_poly_smoothing"]

        obj_id = self.get_toplevel_object().get_id()
        task = self.__rebuild_node_tree
        task_id = "rebuild_node_tree"
        PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        return state

    def __setstate__(self, state):

        self.__dict__ = state

        self._data_row_count = 0
        self._merged_verts = {}
        self._merged_edges = {}
        self._ordered_polys = []
        self._poly_smoothing = {}

        self._subobjs = subobjs = {}
        self._subobj_sel_state = subobj_sel_state = {}
        self._selected_subobj_ids = selected_subobj_ids = {}
        self._geoms = geoms = {"top": {"shaded": None, "wire": None}}
        geoms["poly_picking"] = None

        for subobj_type in ("vert", "edge", "poly"):
            subobjs[subobj_type] = {}
            subobj_sel_state[subobj_type] = {"selected": [], "unselected": []}
            selected_subobj_ids[subobj_type] = []
            geoms[subobj_type] = {"selected": None, "unselected": None}

        self.__create_subobject_roots()

        toplvl_geom_root = self._geom_roots["top"]
        vert_geom_root = self._geom_roots["vert"]
        edge_geom_root = self._geom_roots["edge"]
        poly_geom_root = self._geom_roots["poly"]

        self._vertex_data = {}
        vertex_format_vert = Mgr.get("vertex_format_vert")
        vertex_data_vert = GeomVertexData("vert_data", vertex_format_vert, Geom.UH_dynamic)
        self._vertex_data["vert"] = vertex_data_vert
        vertex_format_edge = Mgr.get("vertex_format_edge")
        vertex_data_edge = GeomVertexData("edge_data", vertex_format_edge, Geom.UH_dynamic)
        self._vertex_data["edge"] = vertex_data_edge
        vertex_format_poly = Mgr.get("vertex_format_poly")
        vertex_data_poly = GeomVertexData("poly_data", vertex_format_poly, Geom.UH_dynamic)
        self._vertex_data["poly"] = vertex_data_poly
        vertex_data_poly_picking = GeomVertexData("poly_picking_data", vertex_format_vert, Geom.UH_dynamic)
        self._vertex_data["poly_picking"] = vertex_data_poly_picking

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.reserve_num_vertices(3)
        point_geom = Geom(vertex_data_vert)
        point_geom.add_primitive(points_prim)
        geom_node = GeomNode("vert_unselected_geom")
        geom_node.add_geom(point_geom)
        vert_unselected_geom = vert_geom_root.attach_new_node(geom_node)
        vert_unselected_geom.set_color(.5, .5, 1.)
        geoms["vert"]["unselected"] = vert_unselected_geom

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.reserve_num_vertices(3)
        point_geom = Geom(vertex_data_vert)
        point_geom.add_primitive(points_prim)
        geom_node = GeomNode("vert_selected_geom")
        geom_node.add_geom(point_geom)
        vert_selected_geom = vert_geom_root.attach_new_node(geom_node)
        vert_selected_geom.set_color(1., 0., 0.)
        geoms["vert"]["selected"] = vert_selected_geom

        render_masks = Mgr.get("render_masks")
        picking_masks = Mgr.get("picking_masks")

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(6)
        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("toplevel_wire_geom")
        geom_node.add_geom(lines_geom)
        toplvl_wire_geom = toplvl_geom_root.attach_new_node(geom_node)
        toplvl_wire_geom.set_light_off()
        toplvl_wire_geom.set_texture_off()
        toplvl_wire_geom.set_material_off()
        toplvl_wire_geom.set_shader_off()
        toplvl_wire_geom.set_attrib(DepthTestAttrib.make(RenderAttrib.M_less_equal))
        toplvl_wire_geom.set_bin("fixed", 1)
        toplvl_wire_geom.hide(picking_masks["all"])
        geoms["top"]["wire"] = toplvl_wire_geom

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(6)
        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("edge_unselected_geom")
        geom_node.add_geom(lines_geom)
        edge_unselected_geom = edge_geom_root.attach_new_node(geom_node)
        edge_unselected_geom.set_color(1., 1., 1.)
        geoms["edge"]["unselected"] = edge_unselected_geom

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(6)
        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("edge_selected_geom")
        geom_node.add_geom(lines_geom)
        edge_selected_geom = edge_geom_root.attach_new_node(geom_node)
        edge_selected_geom.set_color(1., 0., 0.)
        geoms["edge"]["selected"] = edge_selected_geom

        tris_prim = GeomTriangles(Geom.UH_static)
        tris_geom = Geom(vertex_data_poly)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("toplevel_shaded_geom")
        geom_node.add_geom(tris_geom)
        self._toplvl_node = geom_node
        toplvl_shaded_geom = toplvl_geom_root.attach_new_node(geom_node)
        toplvl_shaded_geom.hide(picking_masks["all"])
        self._toplvl_geom = toplvl_shaded_geom
        geoms["top"]["shaded"] = toplvl_shaded_geom

        # create the geom containing the polygon picking colors
        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.reserve_num_vertices(3)
        tris_geom = Geom(vertex_data_poly_picking)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_picking_geom")
        geom_node.add_geom(tris_geom)
        poly_picking_geom = toplvl_geom_root.attach_new_node(geom_node)
        poly_picking_geom.hide(render_masks["all"])
        geoms["poly_picking"] = poly_picking_geom

        tris_prim = GeomTriangles(Geom.UH_static)
        tris_geom = Geom(vertex_data_poly)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_unselected_geom")
        geom_node.add_geom(tris_geom)
        poly_unselected_geom = poly_geom_root.attach_new_node(geom_node)
        geoms["poly"]["unselected"] = poly_unselected_geom

        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.reserve_num_vertices(3)
        tris_geom = Geom(vertex_data_poly)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_selected_geom")
        geom_node.add_geom(tris_geom)
        poly_selected_geom = poly_geom_root.attach_new_node(geom_node)
        poly_selected_geom.set_state(Mgr.get("poly_selection_state"))
        poly_selected_geom.set_effects(Mgr.get("poly_selection_effects"))
        geoms["poly"]["selected"] = poly_selected_geom

        self._origin.node().set_final(True)
        self._origin.set_two_sided(GlobalData["two_sided"])

        render_mode = GlobalData["render_mode"]

        if "shaded" in render_mode:
            toplvl_shaded_geom.show(render_masks["all"])
        else:
            toplvl_shaded_geom.hide(render_masks["all"])

        if "wire" in render_mode:
            toplvl_wire_geom.show(render_masks["all"])
        else:
            toplvl_wire_geom.hide(render_masks["all"])

        if render_mode == "wire":
            toplvl_wire_geom.show(picking_masks["all"])

    def __rebuild_node_tree(self):
        """ Rebuild the original NodePath hierarchy """

        orig = self._origin
        geom_roots = self._geom_roots
        geom_roots["subobj"].reparent_to(orig)
        geom_roots["top"].reparent_to(orig)

    def __init__(self, owner):

        GeomSelectionBase.__init__(self)
        GeomTransformBase.__init__(self)
        GeomHistoryBase.__init__(self)
        PolygonEditBase.__init__(self)
        UVEditBase.__init__(self)

        self._owner = owner
        self._origin = None
        self._data_row_count = 0
        self._merged_verts = {}
        self._merged_edges = {}
        self._ordered_polys = []

        self._prop_ids = ["subobj_merge", "subobj_selection", "subobj_transform",
                          "smoothing", "poly_tris", "uvs"]
        self._geom_roots = {}

        self._vertex_data = vertex_data = {}
        self._subobjs = subobjs = {}
        self._subobjs_to_reg = subobjs_to_reg = {}
        self._subobjs_to_unreg = subobjs_to_unreg = {}
        self._geoms = geoms = {"top": {"shaded": None, "wire": None}}
        geoms["poly_picking"] = None

        for subobj_type in ("vert", "edge", "poly"):
            vertex_data[subobj_type] = None
            subobjs[subobj_type] = {}
            subobjs_to_reg[subobj_type] = {}
            subobjs_to_unreg[subobj_type] = {}
            geoms[subobj_type] = {"selected": None, "unselected": None}

    def get_subobjects(self, subobj_type):

        return self._subobjs[subobj_type]

    def get_subobject(self, subobj_type, subobj_id):

        return self._subobjs[subobj_type].get(subobj_id)

    def get_toplevel_geom(self):

        return self._toplvl_geom

    def get_toplevel_node(self):

        return self._toplvl_node

    def process_geom_data(self, data):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        ordered_polys = self._ordered_polys
        merged_verts = self._merged_verts
        merged_verts_by_pos = {}
        merged_edges = self._merged_edges
        merged_edges_tmp = {}
        self._poly_smoothing = poly_smoothing = {}
        smoothing_by_id = {}

        for poly_data in data:

            row_index = 0
            verts_by_pos = {}
            poly_verts = []
            edge_data = []
            triangles = []

            for tri_data in poly_data["tris"]:

                tri_vert_ids = []

                for vert_data in tri_data["verts"]:

                    pos = vert_data["pos"]

                    if pos in verts_by_pos:

                        vertex = verts_by_pos[pos]
                        vert_id = vertex.get_id()

                    else:

                        vertex = Mgr.do("create_vert", self, pos[:])
                        vertex.set_row_index(row_index)
                        row_index += 1
                        vertex.set_normal(vert_data["normal"])
                        vertex.set_uvs(vert_data["uvs"])
                        vert_id = vertex.get_id()
                        verts[vert_id] = vertex
                        verts_by_pos[pos] = vertex
                        poly_verts.append(vertex)

                        if pos in merged_verts_by_pos:
                            merged_vert = merged_verts_by_pos[pos]
                        else:
                            merged_vert = Mgr.do("create_merged_vert", self)
                            merged_verts_by_pos[pos] = merged_vert

                        merged_vert.append(vert_id)
                        merged_verts[vert_id] = merged_vert

                    tri_vert_ids.append(vert_id)

                for i, j in ((0, 1), (1, 2), (0, 2)):

                    edge_verts = sorted([verts[tri_vert_ids[i]], verts[tri_vert_ids[j]]])

                    if edge_verts in edge_data:
                        edge_data.remove(edge_verts)
                    else:
                        edge_data.append(edge_verts)

                triangles.append(tuple(tri_vert_ids))

            poly_edges = []

            for edge_verts in edge_data:

                edge = Mgr.do("create_edge", self, edge_verts)
                edge_id = edge.get_id()
                edges[edge_id] = edge
                poly_edges.append(edge)
                vert_ids = [vert.get_id() for vert in edge_verts]
                merged_edge_verts = tuple(sorted([merged_verts[v_id] for v_id in vert_ids]))

                if merged_edge_verts in merged_edges_tmp:
                    merged_edge = merged_edges_tmp[merged_edge_verts]
                else:
                    merged_edge = Mgr.do("create_merged_edge", self)
                    merged_edges_tmp[merged_edge_verts] = merged_edge

                merged_edge.append(edge_id)
                merged_edges[edge_id] = merged_edge

            polygon = Mgr.do("create_poly", self, triangles, poly_edges, poly_verts)
            ordered_polys.append(polygon)
            poly_id = polygon.get_id()
            polys[poly_id] = polygon

            for smoothing_id, use in poly_data["smoothing"]:

                if smoothing_id in smoothing_by_id:
                    smoothing_grp = smoothing_by_id[smoothing_id]
                else:
                    smoothing_grp = SmoothingGroup()
                    smoothing_by_id[smoothing_id] = smoothing_grp

                smoothing_grp.add(poly_id)

                if use:
                    poly_smoothing.setdefault(poly_id, set()).add(smoothing_grp)

        processed_data = {"smoothing": smoothing_by_id}

        return processed_data

    def clear_subobjects(self):

        subobj_change = self._subobj_change

        for subobj_type in ("vert", "edge", "poly"):
            subobjs = self._subobjs[subobj_type].values()
            subobj_change[subobj_type]["deleted"] = subobjs

        self.unregister()

        self._data_row_count = 0
        self._ordered_polys = []
        self._merged_verts = {}
        self._merged_edges = {}

        geoms = self._geoms
        geoms["top"]["shaded"].remove_node()
        geoms["top"]["wire"].remove_node()
        geoms["poly_picking"].remove_node()

        for subobj_type in ("vert", "edge", "poly"):
            geoms[subobj_type]["unselected"].remove_node()
            geoms[subobj_type]["selected"].remove_node()

        self._vertex_data = vertex_data = {}
        self._subobjs = subobjs = {}
        self._subobj_sel_state = subobj_sel_state = {}
        self._selected_subobj_ids = selected_subobj_ids = {}
        self._verts_to_transf = verts_to_transf = {}
        self._geoms = geoms = {"top": {"shaded": None, "wire": None}}
        geoms["poly_picking"] = None

        for subobj_type in ("vert", "edge", "poly"):
            vertex_data[subobj_type] = None
            subobjs[subobj_type] = {}
            subobj_sel_state[subobj_type] = {"selected": [], "unselected": []}
            selected_subobj_ids[subobj_type] = []
            verts_to_transf[subobj_type] = {}
            geoms[subobj_type] = {"selected": None, "unselected": None}

    def create_subobjects(self, rebuild=False):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        self._data_row_count = count = len(verts)
        tri_vert_count = sum([len(poly) for poly in self._ordered_polys])

        sel_state = self._subobj_sel_state
        sel_state["vert"]["unselected"] = range(count)
        sel_state_edge = sel_state["edge"]["unselected"]
        sel_state_poly = sel_state["poly"]["unselected"]

        geom_roots = self._geom_roots
        toplvl_geom_root = geom_roots["top"]
        vert_geom_root = geom_roots["vert"]
        edge_geom_root = geom_roots["edge"]
        poly_geom_root = geom_roots["poly"]

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
        vertex_data_poly_picking = GeomVertexData("poly_picking_data", vertex_format_vert, Geom.UH_dynamic)
        vertex_data_poly_picking.reserve_num_rows(count)
        vertex_data_poly_picking.set_num_rows(count)
        self._vertex_data["poly_picking"] = vertex_data_poly_picking

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.reserve_num_vertices(count)
        points_prim.add_next_vertices(count)
        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(count * 2)
        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.reserve_num_vertices(tri_vert_count)

        pos_writer = GeomVertexWriter(vertex_data_poly, "vertex")
        normal_writer = GeomVertexWriter(vertex_data_poly, "normal")

        row_index_offset = 0

        for poly in self._ordered_polys:

            poly_corners = []
            processed_verts = []

            for vert_ids in poly:

                for vert_id in vert_ids:

                    vert = verts[vert_id]

                    if vert not in processed_verts:
                        vert.offset_row_index(row_index_offset)
                        pos = vert.get_pos()
                        poly_corners.append(pos)
                        pos_writer.add_data3f(pos)
                        normal = vert.get_normal()
                        normal_writer.add_data3f(normal)
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

            row_index_offset += poly.get_vertex_count()

            sel_state_poly.extend(poly[:])

        pos_array = vertex_data_poly.get_array(0)
        pos_data = pos_array.get_handle().get_data()
        vertex_data_vert.set_array(0, pos_array)
        array = GeomVertexArrayData(pos_array)
        array.modify_handle().set_data(pos_data * 2)
        vertex_data_edge.set_array(0, array)
        vertex_data_poly_picking.set_array(0, array)
        geoms = self._geoms

        point_geom = Geom(vertex_data_vert)
        point_geom.add_primitive(points_prim)
        geom_node = GeomNode("vert_unselected_geom")
        geom_node.add_geom(point_geom)
        vert_unselected_geom = vert_geom_root.attach_new_node(geom_node)
        vert_unselected_geom.set_color(.5, .5, 1.)
        geoms["vert"]["unselected"] = vert_unselected_geom

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.reserve_num_vertices(3)
        point_geom = Geom(vertex_data_vert)
        point_geom.add_primitive(points_prim)
        geom_node = GeomNode("vert_selected_geom")
        geom_node.add_geom(point_geom)
        vert_selected_geom = vert_geom_root.attach_new_node(geom_node)
        vert_selected_geom.set_color(1., 0., 0.)
        geoms["vert"]["selected"] = vert_selected_geom

        render_masks = Mgr.get("render_masks")
        picking_masks = Mgr.get("picking_masks")

        vertices = lines_prim.get_vertices()
        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("toplevel_wire_geom")
        geom_node.add_geom(lines_geom)
        toplvl_wire_geom = toplvl_geom_root.attach_new_node(geom_node)
        toplvl_wire_geom.set_light_off()
        toplvl_wire_geom.set_texture_off()
        toplvl_wire_geom.set_material_off()
        toplvl_wire_geom.set_shader_off()
        toplvl_wire_geom.set_attrib(DepthTestAttrib.make(RenderAttrib.M_less_equal))
        toplvl_wire_geom.set_bin("fixed", 1)
        toplvl_wire_geom.hide(picking_masks["all"])
        geoms["top"]["wire"] = toplvl_wire_geom

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(6)
        lines_prim.set_vertices(GeomVertexArrayData(vertices))
        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("edge_unselected_geom")
        geom_node.add_geom(lines_geom)
        edge_unselected_geom = edge_geom_root.attach_new_node(geom_node)
        edge_unselected_geom.set_color(1., 1., 1.)
        geoms["edge"]["unselected"] = edge_unselected_geom

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(6)
        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("edge_selected_geom")
        geom_node.add_geom(lines_geom)
        edge_selected_geom = edge_geom_root.attach_new_node(geom_node)
        edge_selected_geom.set_color(1., 0., 0.)
        geoms["edge"]["selected"] = edge_selected_geom

        vertices = tris_prim.get_vertices()
        tris_geom = Geom(GeomVertexData(vertex_data_poly))
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("toplevel_shaded_geom")
        geom_node.add_geom(tris_geom)
        self._toplvl_node = geom_node
        toplvl_shaded_geom = toplvl_geom_root.attach_new_node(geom_node)
        toplvl_shaded_geom.hide(picking_masks["all"])
        self._toplvl_geom = toplvl_shaded_geom
        geoms["top"]["shaded"] = toplvl_shaded_geom
        self._origin.node().set_bounds(geom_node.get_bounds())

        # create the geom containing the polygon picking colors
        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.reserve_num_vertices(3)
        tris_prim.set_vertices(GeomVertexArrayData(vertices))
        tris_geom = Geom(vertex_data_poly_picking)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_picking_geom")
        geom_node.add_geom(tris_geom)
        poly_picking_geom = toplvl_geom_root.attach_new_node(geom_node)
        poly_picking_geom.hide(render_masks["all"])
        geoms["poly_picking"] = poly_picking_geom

        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.reserve_num_vertices(3)
        tris_prim.set_vertices(GeomVertexArrayData(vertices))
        tris_geom = Geom(vertex_data_poly)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_unselected_geom")
        geom_node.add_geom(tris_geom)
        poly_unselected_geom = poly_geom_root.attach_new_node(geom_node)
        geoms["poly"]["unselected"] = poly_unselected_geom

        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.reserve_num_vertices(3)
        tris_geom = Geom(vertex_data_poly)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_selected_geom")
        geom_node.add_geom(tris_geom)
        poly_selected_geom = poly_geom_root.attach_new_node(geom_node)
        poly_selected_geom.set_state(Mgr.get("poly_selection_state"))
        poly_selected_geom.set_effects(Mgr.get("poly_selection_effects"))
        geoms["poly"]["selected"] = poly_selected_geom
        self.update_selection_state(self.get_toplevel_object().is_selected())

        render_mode = GlobalData["render_mode"]

        if "shaded" in render_mode:
            toplvl_shaded_geom.show(render_masks["all"])
        else:
            toplvl_shaded_geom.hide(render_masks["all"])

        if "wire" in render_mode:
            toplvl_wire_geom.show(render_masks["all"])
        else:
            toplvl_wire_geom.hide(render_masks["all"])

        if render_mode == "wire":
            toplvl_wire_geom.show(picking_masks["all"])

        if rebuild:

            subobj_change = self._subobj_change

            for subobj_type in ("vert", "edge", "poly"):
                subobjs = self._subobjs[subobj_type].values()
                subobj_change[subobj_type]["created"] = subobjs

    def create_geometry(self, obj_type):

        node_name = "%s_geom_origin" % obj_type
        origin = self.get_toplevel_object().get_origin().attach_new_node(node_name)
        origin.node().set_final(True)

        if GlobalData["two_sided"]:
            origin.set_two_sided(True)

        self._origin = origin
        self.__create_subobject_roots()
        self.create_subobjects()

    def __create_subobject_roots(self):

        toplvl_geom_root = self._origin.attach_new_node("toplvl_geom_root")
        subobj_geom_root = self._origin.attach_new_node("subobj_geom_root")
        vert_geom_root = subobj_geom_root.attach_new_node("vert_geom_root")
        edge_geom_root = subobj_geom_root.attach_new_node("edge_geom_root")
        poly_geom_root = subobj_geom_root.attach_new_node("poly_geom_root")

        vert_geom_root.set_render_mode_thickness(7)
        vert_geom_root.set_light_off()
        vert_geom_root.set_texture_off()
        vert_geom_root.set_material_off()
        vert_geom_root.set_shader_off()
        vert_geom_root.set_transparency(TransparencyAttrib.M_none)

        edge_geom_root.set_light_off()
        edge_geom_root.set_texture_off()
        edge_geom_root.set_material_off()
        edge_geom_root.set_shader_off()
        edge_geom_root.set_attrib(DepthTestAttrib.make(RenderAttrib.M_less_equal))
        edge_geom_root.set_bin("fixed", 1)

        self._geom_roots = geom_roots = {}
        geom_roots["top"] = toplvl_geom_root
        geom_roots["subobj"] = subobj_geom_root
        geom_roots["vert"] = vert_geom_root
        geom_roots["edge"] = edge_geom_root
        geom_roots["poly"] = poly_geom_root

        subobj_geom_root.hide(Mgr.get("render_masks")["all"] | Mgr.get("picking_masks")["all"])

    def set_position_data(self, pos_data):

        node = self._toplvl_node
        handle = node.modify_geom(0).modify_vertex_data().modify_array(0).modify_handle()
        handle.set_data(pos_data)

    def get_position_data(self):

        node = self._toplvl_node
        pos_data = node.get_geom(0).get_vertex_data().get_array(0).get_handle().get_data()

        return pos_data

    def bake_transform(self):
        """ Bake the origin's transform into the vertices and reset it to identity """

        mat = self._origin.get_mat()
        geom_node_top = self._toplvl_node
        geom_node_top.modify_geom(0).transform_vertices(mat)
        self._origin.clear_transform()
        vertex_data_top = geom_node_top.get_geom(0).get_vertex_data()
        array = vertex_data_top.get_array(0)

        for geom_type in ("vert", "poly", "poly_picking"):
            vertex_data = self._vertex_data[geom_type]
            vertex_data.set_array(0, array)

        array = GeomVertexArrayData(array)
        handle = array.modify_handle()
        handle.set_data(handle.get_data() * 2)
        self._vertex_data["edge"].set_array(0, array)

        pos_reader = GeomVertexReader(vertex_data_top, "vertex")

        for vert in self._subobjs["vert"].itervalues():
            row = vert.get_row_index()
            pos_reader.set_row(row)
            pos = pos_reader.get_data3f()
            # NOTE: the LVecBase3f returned by the GeomVertexReader is a const
            vert.set_pos(Point3(*pos))

    def init_vertex_colors(self):

        pickable_id_vert = PickableTypes.get_id("vert")
        pickable_id_edge = PickableTypes.get_id("edge")
        pickable_id_poly = PickableTypes.get_id("poly")
        vertex_data = self._vertex_data["vert"]
        col_writer_vert = GeomVertexWriter(vertex_data, "color")
        vertex_data = self._vertex_data["edge"]
        col_writer_edge = GeomVertexWriter(vertex_data, "color")
        vertex_data = self._vertex_data["poly_picking"]
        col_writer_poly = GeomVertexWriter(vertex_data, "color")

        for poly in self._ordered_polys:

            picking_color = get_color_vec(poly.get_picking_color_id(), pickable_id_poly)
            verts = poly.get_vertices()

            for i in xrange(len(verts)):
                col_writer_poly.add_data4f(picking_color)

            for vert in verts:
                picking_color = get_color_vec(vert.get_picking_color_id(), pickable_id_vert)
                col_writer_vert.add_data4f(picking_color)

        vert_subobjs = self._subobjs["vert"]
        edge_subobjs = self._subobjs["edge"]
        picking_colors = {}
        count = self._data_row_count

        for edge in edge_subobjs.itervalues():
            picking_color = get_color_vec(edge.get_picking_color_id(), pickable_id_edge)
            row_index = vert_subobjs[edge[0]].get_row_index()
            picking_colors[row_index] = picking_color
            row_index = vert_subobjs[edge[1]].get_row_index() + count
            picking_colors[row_index] = picking_color

        for row_index in sorted(picking_colors.iterkeys()):
            picking_color = picking_colors[row_index]
            col_writer_edge.add_data4f(picking_color)

    def init_tangent_space(self):

        vertex_data = self._vertex_data["poly"]
        tan_writer = GeomVertexWriter(vertex_data, "tangent")
        bitan_writer = GeomVertexWriter(vertex_data, "binormal")

        for poly in self._ordered_polys:
            for vert in poly.get_vertices():
                tangent, bitangent = vert.get_tangent_space()
                tan_writer.add_data3f(tangent)
                bitan_writer.add_data3f(bitangent)

    def init_poly_normals(self):

        for poly in self._ordered_polys:
            poly.update_normal()

        self._update_vertex_normals(set(self._merged_verts.itervalues()))

    def update_poly_centers(self):

        for poly in self._ordered_polys:
            poly.update_center_pos()

    def finalize_geometry(self, update_poly_centers=True):

        self.init_vertex_colors()
        self.init_uvs()
        self.init_tangent_space()
        self.init_poly_normals()

        if update_poly_centers:
            self.update_poly_centers()

    def update_selection_state(self, is_selected=True):

        geoms = self._geoms
        picking_masks = Mgr.get("picking_masks")
        render_mode = GlobalData["render_mode"]

        if is_selected:

            if render_mode == "wire":
                geoms["poly_picking"].show(picking_masks["all"])
                geoms["top"]["wire"].hide(picking_masks["all"])

            geoms["top"]["wire"].set_color(1., 1., 1.)

        else:

            if render_mode == "wire":
                geoms["poly_picking"].hide(picking_masks["all"])
                geoms["top"]["wire"].show(picking_masks["all"])

            geoms["top"]["wire"].set_color(self.get_toplevel_object().get_color())

    def update_render_mode(self, is_selected):

        render_mode = GlobalData["render_mode"]
        render_masks = Mgr.get("render_masks")
        picking_masks = Mgr.get("picking_masks")
        geoms = self._geoms

        if is_selected:

            obj_lvl = GlobalData["active_obj_level"]

        else:

            if render_mode == "wire":
                geoms["poly_picking"].hide(picking_masks["all"])
                geoms["top"]["wire"].show(picking_masks["all"])
            else:
                geoms["poly_picking"].show(picking_masks["all"])
                geoms["top"]["wire"].hide(picking_masks["all"])

            obj_lvl = "top"

        if "wire" in render_mode:
            if obj_lvl == "edge":
                geoms["top"]["wire"].hide(render_masks["all"])
            else:
                geoms["top"]["wire"].show(render_masks["all"])
        else:
            geoms["top"]["wire"].hide(render_masks["all"])

        if "shaded" in render_mode:
            if obj_lvl == "poly" or (obj_lvl == "top" and self._has_poly_tex_proj):
                geoms["top"]["shaded"].hide(render_masks["all"])
            else:
                geoms["top"]["shaded"].show(render_masks["all"])
            geoms["poly"]["unselected"].show(render_masks["all"])
        else:
            geoms["top"]["shaded"].hide(render_masks["all"])
            geoms["poly"]["unselected"].hide(render_masks["all"])

    def show_top_level(self):

        render_masks = Mgr.get("render_masks")["all"]
        picking_masks = Mgr.get("picking_masks")["all"]
        all_masks = render_masks | picking_masks

        geom_roots = self._geom_roots

        for subobj_lvl in ("vert", "edge"):
            geom_roots[subobj_lvl].show(all_masks)

        geom_roots["poly"].show(render_masks)

        if self._has_poly_tex_proj:
            geom_roots["poly"].show_through(render_masks)

        self._geoms["poly_picking"].show(picking_masks)

        self.update_render_mode(self.get_toplevel_object().is_selected())

    def show_subobj_level(self, subobj_lvl):

        render_masks = Mgr.get("render_masks")["all"]
        picking_masks = Mgr.get("picking_masks")["all"]
        all_masks = render_masks | picking_masks

        geom_roots = self._geom_roots

        if subobj_lvl == "poly":

            self._geoms["poly_picking"].show_through(picking_masks)
            geom_roots[subobj_lvl].show_through(render_masks)

            for lvl in ("vert", "edge"):
                geom_roots[lvl].show(all_masks)

        else:

            self._geoms["poly_picking"].show(picking_masks)
            other_subobj_lvl = "edge" if subobj_lvl == "vert" else "vert"
            geom_roots[subobj_lvl].show_through(all_masks)
            geom_roots[other_subobj_lvl].show(all_masks)
            geom_roots["poly"].show(render_masks)

        self.update_render_mode(self.get_toplevel_object().is_selected())

    def destroy(self):

        self.unregister()
        self._origin.remove_node()
        self._origin = None
        self._ordered_polys = []
        self._subobjs = {"vert": {}, "edge": {}, "poly": {}}
        self._verts_to_transf = {"vert": {}, "edge": {}, "poly": {}}

    def set_owner(self, owner):

        self._owner = owner

    def get_owner(self):

        return self._owner

    def get_toplevel_object(self):

        return self._owner.get_toplevel_object()

    def unregister(self):

        for subobj_type in ("vert", "edge", "poly"):
            Mgr.do("unregister_%s_objs" % subobj_type,
                   self._subobjs[subobj_type].itervalues())

    def set_origin(self, origin):

        self._origin = origin

    def get_origin(self):

        return self._origin

    def get_merged_vertex(self, vert_id):

        return self._merged_verts.get(vert_id)

    def get_merged_edge(self, edge_id):

        return self._merged_edges.get(edge_id)

    def register_subobjects(self, locally=False):

        for subobj_type in ("vert", "edge", "poly"):

            subobjs = self._subobjs_to_reg[subobj_type]
            Mgr.do("register_%s_objs" % subobj_type, subobjs.itervalues())

            if locally:
                self._subobjs[subobj_type].update(subobjs)

        self._subobjs_to_reg = {"vert": {}, "edge": {}, "poly": {}}

    def unregister_subobjects(self, locally=False):

        for subobj_type in ("vert", "edge", "poly"):

            subobjs = self._subobjs_to_unreg[subobj_type]
            Mgr.do("unregister_%s_objs" % subobj_type, subobjs.itervalues())

            if locally:

                registered_subobjs = self._subobjs[subobj_type]

                for subobj_id in subobjs:
                    del registered_subobjs[subobj_id]

        self._subobjs_to_unreg = {"vert": {}, "edge": {}, "poly": {}}

    def get_property_ids(self):

        return self._prop_ids


class GeomDataManager(BaseObject):

    def __init__(self):

        Mgr.accept("create_geom_data", self.__create_data)

    def setup(self):

        sort = PendingTasks.get_sort("set_geom_data", "object")

        if sort is None:
            return False

        task_ids = (
            "merge_subobjs",
            "restore_subobjs",
            "unregister_subobjs",
            "register_subobjs",
            "set_subobj_sel",
            "upd_subobj_sel",
            "upd_verts_to_transf",
            "set_subobj_transf",
            "set_uvs",
            "set_poly_triangles",
            "smooth_polys",
            "upd_vert_normals",
            "rebuild_node_tree"
        )

        for task_id in reversed(task_ids):
            PendingTasks.add_task_id(task_id, "object", sort + 1)

        np = NodePath("poly_sel_state")
        poly_sel_state_off = np.get_state()
        tex_stage = TextureStage("poly_selection")
        tex_stage.set_sort(100)
        tex_stage.set_priority(-1)
        tex_stage.set_mode(TextureStage.M_add)
        np.set_transparency(TransparencyAttrib.M_none)
        np.set_tex_gen(tex_stage, RenderAttrib.M_world_position)
        np.set_tex_projector(tex_stage, self.world, self.cam())
        tex = Texture()
        tex.read(Filename(GFX_PATH + "sel_tex.png"))
        np.set_texture(tex_stage, tex)
        np.set_tex_scale(tex_stage, 100.)
        red = VBase4(1., 0., 0., 1.)
        material = Material("poly_selection")
        material.set_diffuse(red)
        material.set_emission(red * .3)
        np.set_material(material)
        poly_sel_state = np.get_state()
        poly_sel_effects = np.get_effects()
        Mgr.expose("poly_selection_state_off", lambda: poly_sel_state_off)
        Mgr.expose("poly_selection_state", lambda: poly_sel_state)
        Mgr.expose("poly_selection_effects", lambda: poly_sel_effects)

        # Define GeomVertexArrayFormat that accommodates multiple texture coordinate
        # sets, as well as tangents and bitangents ("binormals").

        array1 = GeomVertexArrayFormat()
        array1.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)

        array2 = GeomVertexArrayFormat()
        array2.add_column(InternalName.make("color"), 4, Geom.NT_float32, Geom.C_color)

        array3 = GeomVertexArrayFormat()
        array3.add_column(InternalName.make("color"), 4, Geom.NT_float32, Geom.C_color)
        array3.add_column(InternalName.make("normal"), 3, Geom.NT_float32, Geom.C_normal)
        array3.add_column(InternalName.make("tangent"), 3, Geom.NT_float32, Geom.C_normal)
        array3.add_column(InternalName.make("binormal"), 3, Geom.NT_float32, Geom.C_normal)

        uv_arrays = []
        uv_array = GeomVertexArrayFormat()
        uv_array.add_column(InternalName.make("texcoord"), 2, Geom.NT_float32, Geom.C_texcoord)
        uv_arrays.append(uv_array)

        for i in xrange(1, 8):
            uv_array = GeomVertexArrayFormat()
            uv_array.add_column(InternalName.make("texcoord.%d" % i), 2, Geom.NT_float32, Geom.C_texcoord)
            uv_arrays.append(uv_array)

        vertex_format_vert = GeomVertexFormat()
        vertex_format_vert.add_array(array1)
        vertex_format_vert.add_array(array2)
        vertex_format_vert = GeomVertexFormat.register_format(vertex_format_vert)
        Mgr.expose("vertex_format_vert", lambda: vertex_format_vert)
        Mgr.expose("vertex_format_edge", lambda: vertex_format_vert)

        vertex_format_poly = GeomVertexFormat()
        vertex_format_poly.add_array(array1)
        vertex_format_poly.add_array(array3)

        for uv_array in uv_arrays:
            vertex_format_poly.add_array(uv_array)

        vertex_format_poly = GeomVertexFormat.register_format(vertex_format_poly)
        Mgr.expose("vertex_format_poly", lambda: vertex_format_poly)

        return True

    def __create_data(self, owner):

        return GeomDataObject(owner)


MainObjects.add_class(GeomDataManager)
