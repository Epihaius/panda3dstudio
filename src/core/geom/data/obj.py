from ...base import *
from .select import GeomSelectionBase
from .transform import GeomTransformBase
from .history import GeomHistoryBase
from .vert_edit import VertexEditBase
from .edge_edit import EdgeEditBase
from .poly_edit import PolygonEditBase, SmoothingGroup
from .normal_edit import NormalEditBase
from .uv_edit import UVEditBase


class GeomDataObject(GeomSelectionBase, GeomTransformBase, GeomHistoryBase,
                     VertexEditBase, EdgeEditBase, PolygonEditBase,
                     NormalEditBase, UVEditBase):

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_origin"] = NodePath(self._origin.node().make_copy())
        state["_origin"].clear_two_sided()
        del state["_vertex_data"]
        del state["_owner"]
        del state["_toplvl_node"]
        del state["_toplvl_geom"]
        del state["_geoms"]
        del state["_merged_verts"]
        del state["_merged_edges"]
        del state["_shared_normals"]
        del state["_poly_smoothing"]
        del state["_ordered_polys"]
        del state["_subobjs"]
        del state["_is_tangent_space_initialized"]

        GeomSelectionBase.__editstate__(self, state)

        return state

    def __setstate__(self, state):

        self.__dict__ = state

        GeomSelectionBase.__setstate__(self, state)

        self._data_row_count = 0
        self._merged_verts = {}
        self._merged_edges = {}
        self._shared_normals = {}
        self._poly_smoothing = {}
        self._ordered_polys = []
        self._is_tangent_space_initialized = False

        self._subobjs = subobjs = {}
        self._geoms = geoms = {}
        geoms["top"] = None

        for subobj_type in ("vert", "edge", "poly"):
            subobjs[subobj_type] = {}
            geoms[subobj_type] = {"pickable": None, "sel_state": None}

        geoms["normal"] = {"pickable": None, "sel_state": None}
        del geoms["poly"]["sel_state"]
        geoms["poly"]["selected"] = None
        geoms["poly"]["unselected"] = None

        self._vertex_data = {}

    def __init__(self, data_id, owner):

        GeomSelectionBase.__init__(self)
        GeomTransformBase.__init__(self)
        GeomHistoryBase.__init__(self)
        PolygonEditBase.__init__(self)
        NormalEditBase.__init__(self)
        UVEditBase.__init__(self)

        self._id = data_id
        self._owner = owner
        self._origin = None
        self._data_row_count = 0
        self._merged_verts = {}
        self._merged_edges = {}
        self._ordered_polys = []
        self._is_tangent_space_initialized = False

        self._prop_ids = ["subobj_merge", "subobj_selection", "subobj_transform", "poly_tris",
                          "uvs", "uv_set_names", "normals", "normal_lock", "normal_length",
                          "normal_sharing", "smoothing"]
        prop_ids_ext = self._prop_ids + ["vert_pos__extra__", "tri__extra__", "uv__extra__",
                                         "normal__extra__", "normal_lock__extra__",
                                         "verts", "edges", "polys",
                                         "vert__extra__", "edge__extra__", "poly__extra__"]
        self._unique_prop_ids = dict((k, "geom_data_{}_{}".format(data_id, k)) for k in prop_ids_ext)
        self._type_prop_ids = {"vert": [], "edge": [], "poly": [], "normal": ["normal_length"]}

        self._vertex_data = vertex_data = {}
        vertex_data["poly"] = None
        vertex_data["poly_picking"] = None
        self._subobjs = subobjs = {}
        self._subobjs_to_reg = None
        self._subobjs_to_unreg = None
        self._geoms = geoms = {}
        geoms["top"] = None

        for subobj_type in ("vert", "edge", "poly"):
            subobjs[subobj_type] = {}
            geoms[subobj_type] = {"pickable": None, "sel_state": None}

        geoms["normal"] = {"pickable": None, "sel_state": None}
        del geoms["poly"]["sel_state"]
        geoms["poly"]["selected"] = None
        geoms["poly"]["unselected"] = None
        self._toplvl_geom = None
        self._toplvl_node = None

        self._tmp_geom_pickable = None
        self._tmp_geom_sel_state = None
        self._tmp_row_indices = {}

    def __del__(self):

        logging.debug('GeomDataObject garbage-collected.')

    def cancel_creation(self):

        logging.debug('GeomDataObject "{}" creation cancelled.'.format(self._id))

        if self._origin:
            self._origin.remove_node()

        self.__dict__.clear()

    def destroy(self, unregister=True):

        logging.debug('About to destroy GeomDataObject "{}"...'.format(self._id))

        if unregister:
            self.unregister()

        self._origin.remove_node()

        logging.debug('GeomDataObject "{}" destroyed.'.format(self._id))
        self.__dict__.clear()
        self._origin = None

    def register(self, restore=True, locally=False):

        subobjs = (self._subobjs_to_reg if self._subobjs_to_reg else self._subobjs)

        for subobj_type in ("vert", "edge", "poly"):

            Mgr.do("register_{}_objs".format(subobj_type), subobjs[subobj_type].itervalues(), restore)

            if locally:
                self._subobjs[subobj_type].update(subobjs[subobj_type])

        self._subobjs_to_reg = None

    def unregister(self, locally=False):

        subobjs = (self._subobjs_to_unreg if self._subobjs_to_unreg else self._subobjs)

        for subobj_type in ("vert", "edge", "poly"):

            Mgr.do("unregister_{}_objs".format(subobj_type), subobjs[subobj_type].itervalues())

            if locally:

                registered_subobjs = self._subobjs[subobj_type]

                for subobj_id in subobjs[subobj_type]:
                    del registered_subobjs[subobj_id]

        self._subobjs_to_unreg = None

    def get_id(self):

        return self._id

    def get_subobjects(self, subobj_type):

        return self._subobjs[subobj_type]

    def get_subobject(self, subobj_type, subobj_id):

        return self._subobjs[subobj_type].get(subobj_id)

    def get_toplevel_geom(self):

        return self._toplvl_geom

    def get_toplevel_node(self):

        return self._toplvl_node

    def process_geom_data(self, data, gradual=False):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        ordered_polys = self._ordered_polys
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        self._poly_smoothing = poly_smoothing = {}
        smoothing_by_id = {}

        connectivity = {}
        normals = {}
        verts_by_pos = {}
        edges_by_pos = {}
        polys_by_edge = {}

        if gradual:
            poly_count = 0

        for poly_data in data:

            row_index = 0
            tmp_edges = []
            positions = {}
            poly_verts_by_pos = {}
            poly_edges_by_pos = {}
            poly_edges_by_vert_id = {}

            poly_verts = []
            poly_edges = []
            poly_tris = []

            for tri_data in poly_data["tris"]:

                tri_vert_ids = []

                for vert_data in tri_data:

                    pos = vert_data["pos"]

                    if pos in poly_verts_by_pos:

                        vert_id = poly_verts_by_pos[pos]

                    else:

                        vertex = Mgr.do("create_vert", self, pos)
                        vertex.set_row_index(row_index)
                        row_index += 1
                        vertex.set_normal(vert_data["normal"])
                        vertex.set_uvs(vert_data["uvs"])

                        if "color" in vert_data:
                            vertex.set_color(vert_data["color"])

                        vert_id = vertex.get_id()
                        verts[vert_id] = vertex
                        poly_verts_by_pos[pos] = vert_id
                        positions[vert_id] = pos

                    tri_vert_ids.append(vert_id)

                poly_tris.append(tuple(tri_vert_ids))

                for i, j in ((0, 1), (1, 2), (2, 0)):

                    edge_vert_ids = (tri_vert_ids[i], tri_vert_ids[j])
                    reversed_vert_ids = edge_vert_ids[::-1]

                    if reversed_vert_ids in tmp_edges:
                        # if the edge appears twice, it's actually a diagonal
                        tmp_edges.remove(reversed_vert_ids)
                    else:
                        tmp_edges.append(edge_vert_ids)

            for edge_vert_ids in tmp_edges:
                poly_edges_by_vert_id[edge_vert_ids[0]] = edge_vert_ids

            # Define verts and edges in winding order

            vert1_id, vert2_id = edge_vert_ids = poly_edges_by_vert_id[poly_tris[0][0]]
            vert1 = verts[vert1_id]
            vert2 = verts[vert2_id]
            poly_verts.append(vert1)
            edge = Mgr.do("create_edge", self, edge_vert_ids)
            edge1_id = edge.get_id()
            vert2.add_edge_id(edge1_id)
            edges[edge1_id] = edge
            poly_edges.append(edge)
            pos1 = positions[vert1_id]
            pos2 = positions[vert2_id]
            poly_edges_by_pos[(pos1, pos2)] = edge1_id

            while vert2_id != vert1_id:
                poly_verts.append(vert2)
                vert1 = vert2
                edge_vert_ids = poly_edges_by_vert_id[vert2_id]
                vert2_id = edge_vert_ids[1]
                vert2 = verts[vert2_id]
                edge = Mgr.do("create_edge", self, edge_vert_ids)
                edge_id = edge.get_id()
                vert1.add_edge_id(edge_id)
                vert2.add_edge_id(edge_id)
                edges[edge_id] = edge
                poly_edges.append(edge)
                pos1 = pos2
                pos2 = positions[vert2_id]
                poly_edges_by_pos[(pos1, pos2)] = edge_id

            vert2.add_edge_id(edge1_id)

            polygon = Mgr.do("create_poly", self, poly_tris, poly_edges, poly_verts)
            polygon.update_normal()
            ordered_polys.append(polygon)
            poly_id = polygon.get_id()
            normals[poly_id] = normal = V3D(polygon.get_normal().normalized())
            polys[poly_id] = polygon
            verts_by_pos[poly_id] = poly_verts_by_pos
            edges_by_pos[poly_id] = poly_edges_by_pos

            for smoothing_id, use in poly_data["smoothing"]:

                if smoothing_id in smoothing_by_id:
                    smoothing_grp = smoothing_by_id[smoothing_id]
                else:
                    smoothing_grp = SmoothingGroup()
                    smoothing_by_id[smoothing_id] = smoothing_grp

                smoothing_grp.add(poly_id)

                if use:
                    poly_smoothing.setdefault(poly_id, set()).add(smoothing_grp)

            neighbor_count = {}
            poly_connections = {"neighbors": {}, "neighbor_count": neighbor_count}

            for edge_pos in poly_edges_by_pos:

                poly_connections["neighbors"][edge_pos] = neighbors = []
                reversed_edge_pos = edge_pos[::-1]

                if reversed_edge_pos in polys_by_edge:

                    # one or more other polys form a continuous surface with this one

                    for other_poly_id in polys_by_edge[reversed_edge_pos]:

                        other_connections = connectivity[other_poly_id]
                        other_neighbors = other_connections["neighbors"][reversed_edge_pos]

                        if normal * normals[other_poly_id] > -.99:
                            # the other poly's normal is not the inverse of this one's
                            neighbors.append(other_poly_id)
                            other_neighbors.append(poly_id)
                            neighbor_count.setdefault(other_poly_id, 0)
                            neighbor_count[other_poly_id] += 1
                            other_neighbor_count = other_connections["neighbor_count"]
                            other_neighbor_count.setdefault(poly_id, 0)
                            other_neighbor_count[poly_id] += 1

                polys_by_edge.setdefault(edge_pos, []).append(poly_id)

            connectivity[poly_id] = poly_connections

            if gradual:

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

        if gradual:
            poly_count = 0

        for poly_id, connections in connectivity.iteritems():

            for edge_pos, neighbors in connections["neighbors"].iteritems():

                edge_id = edges_by_pos[poly_id][edge_pos]

                if edge_id in merged_edges:
                    continue

                merged_edge = Mgr.do("create_merged_edge", self, edge_id)
                merged_edges[edge_id] = merged_edge

                if neighbors:

                    neighbor_to_keep = neighbors[0]

                    if len(neighbors) > 1:

                        neighbor_count = connections["neighbor_count"]

                        for neighbor_id in neighbors:
                            if neighbor_count[neighbor_id] > neighbor_count[neighbor_to_keep]:
                                neighbor_to_keep = neighbor_id

                        neighbors_to_discard = neighbors[:]
                        neighbors_to_discard.remove(neighbor_to_keep)

                        for neighbor_id in neighbors_to_discard:
                            connectivity[neighbor_id]["neighbors"][edge_pos[::-1]].remove(poly_id)
                            connectivity[neighbor_id]["neighbor_count"][poly_id] -= 1

                    neighbor_edge_id = edges_by_pos[neighbor_to_keep][edge_pos[::-1]]
                    merged_edge.append(neighbor_edge_id)
                    merged_edges[neighbor_edge_id] = merged_edge

            if gradual:

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

        if gradual:
            poly_count = 0

        for poly in ordered_polys:

            for edge_id in poly.get_edge_ids():

                merged_edge = merged_edges[edge_id]
                vert1_id, vert2_id = edges[edge_id]

                if vert1_id in merged_verts:
                    merged_vert1 = merged_verts[vert1_id]
                else:
                    merged_vert1 = Mgr.do("create_merged_vert", self, vert1_id)
                    merged_verts[vert1_id] = merged_vert1

                if vert2_id in merged_verts:
                    merged_vert2 = merged_verts[vert2_id]
                else:
                    merged_vert2 = Mgr.do("create_merged_vert", self, vert2_id)
                    merged_verts[vert2_id] = merged_vert2

                if len(merged_edge) > 1:

                    neighbor_edge_id = merged_edge[0 if merged_edge[1] == edge_id else 1]
                    neighbor_vert1_id, neighbor_vert2_id = edges[neighbor_edge_id]

                    if neighbor_vert1_id not in merged_vert2:

                        if neighbor_vert1_id in merged_verts:

                            merged_vert = merged_verts[neighbor_vert1_id]

                            for vert_id in merged_vert:
                                merged_vert2.append(vert_id)
                                merged_verts[vert_id] = merged_vert2

                        else:

                            merged_vert2.append(neighbor_vert1_id)
                            merged_verts[neighbor_vert1_id] = merged_vert2

                    if neighbor_vert2_id not in merged_vert1:

                        if neighbor_vert2_id in merged_verts:

                            merged_vert = merged_verts[neighbor_vert2_id]

                            for vert_id in merged_vert:
                                merged_vert1.append(vert_id)
                                merged_verts[vert_id] = merged_vert1

                        else:

                            merged_vert1.append(neighbor_vert2_id)
                            merged_verts[neighbor_vert2_id] = merged_vert1

            if gradual:

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

        smoothing_data = {"smoothing": smoothing_by_id}

        yield smoothing_data

    def create_geometry(self, obj_type="", gradual=False, restore=False):

        if restore:
            origin = self._origin
        else:
            node_name = "{}_geom_origin".format(obj_type)
            origin = NodePath(node_name)
            self._origin = origin

        origin.node().set_final(True)
        origin.hide()

        subobjs = self._subobjs
        verts = subobjs["vert"]
        self._data_row_count = count = len(verts)
        tri_vert_count = sum([len(poly) for poly in self._ordered_polys])

        sel_data = self._poly_selection_data["unselected"]

        vertex_format_basic = Mgr.get("vertex_format_basic")
        vertex_format_full = Mgr.get("vertex_format_full")
        vertex_data_vert = GeomVertexData("vert_data", vertex_format_basic, Geom.UH_dynamic)
        vertex_data_vert.reserve_num_rows(count)
        vertex_data_vert.set_num_rows(count)
        vertex_data_edge = GeomVertexData("edge_data", vertex_format_basic, Geom.UH_dynamic)
        vertex_data_edge.reserve_num_rows(count * 2)
        vertex_data_edge.set_num_rows(count * 2)
        vertex_data_poly = GeomVertexData("poly_data", vertex_format_full, Geom.UH_dynamic)
        vertex_data_poly.reserve_num_rows(count)
        vertex_data_poly.set_num_rows(count)
        self._vertex_data["poly"] = vertex_data_poly
        vertex_data_poly_picking = GeomVertexData("poly_picking_data", vertex_format_basic, Geom.UH_dynamic)
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

        if not restore:
            pos_writer = GeomVertexWriter(vertex_data_poly, "vertex")
            normal_writer = GeomVertexWriter(vertex_data_poly, "normal")

        row_index_offset = 0

        if gradual:
            poly_count = 0

        for poly in self._ordered_polys:

            processed_verts = []

            for vert_ids in poly:

                for vert_id in vert_ids:

                    vert = verts[vert_id]

                    if vert not in processed_verts:

                        vert.offset_row_index(row_index_offset)

                        if not restore:
                            pos_writer.add_data3f(vert.get_pos())
                            normal_writer.add_data3f(vert.get_normal())

                        processed_verts.append(vert)

                    tris_prim.add_vertex(vert.get_row_index())

            for edge in poly.get_edges():
                row1, row2 = (verts[v_id].get_row_index() for v_id in edge)
                lines_prim.add_vertices(row1, row2 + count)

            row_index_offset += poly.get_vertex_count()

            sel_data.extend(poly)

            if gradual:

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

        pos_array = vertex_data_poly.get_array(0)
        vertex_data_vert.set_array(0, pos_array)
        vertex_data_poly_picking.set_array(0, pos_array)
        pos_data = pos_array.get_handle().get_data()
        pos_array = GeomVertexArrayData(pos_array)
        pos_array.modify_handle().set_data(pos_data * 2)
        vertex_data_edge.set_array(0, pos_array)

        render_masks = Mgr.get("render_masks")["all"]
        picking_masks = Mgr.get("picking_masks")["all"]
        all_masks = render_masks | picking_masks

        sel_colors = Mgr.get("subobj_selection_colors")

        state_np = NodePath("state")
        state_np.set_light_off()
        state_np.set_color_off()
        state_np.set_texture_off()
        state_np.set_material_off()
        state_np.set_transparency(TransparencyAttrib.M_none)

        normal_state_np = NodePath(state_np.node().make_copy())

        vert_state_np = NodePath(state_np.node().make_copy())
        vert_state_np.set_render_mode_thickness(7)

        edge_state_np = NodePath(state_np.node().make_copy())
        edge_state_np.set_attrib(DepthTestAttrib.make(RenderAttrib.M_less_equal))
        edge_state_np.set_bin("fixed", 1)

        vert_state = vert_state_np.get_state()
        edge_state = edge_state_np.get_state()
        normal_state = normal_state_np.get_state()

        geoms = self._geoms

        points_geom = Geom(vertex_data_vert)
        points_geom.add_primitive(points_prim)
        geom_node = GeomNode("vert_picking_geom")
        geom_node.add_geom(points_geom)
        vert_picking_geom = origin.attach_new_node(geom_node)
        vert_picking_geom.hide(all_masks)
        geoms["vert"]["pickable"] = vert_picking_geom

        vert_sel_state_geom = vert_picking_geom.copy_to(origin)
        vertex_data = vert_sel_state_geom.node().modify_geom(0).modify_vertex_data()
        new_data = vertex_data.set_color(sel_colors["vert"]["unselected"])
        vertex_data.set_array(1, new_data.get_array(1))
        vert_sel_state_geom.set_state(vert_state)
        vert_sel_state_geom.hide(all_masks)
        vert_sel_state_geom.set_name("vert_sel_state_geom")
        geoms["vert"]["sel_state"] = vert_sel_state_geom

        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("edge_picking_geom")
        geom_node.add_geom(lines_geom)
        edge_picking_geom = origin.attach_new_node(geom_node)
        edge_picking_geom.set_state(edge_state)
        edge_picking_geom.hide(all_masks)
        geoms["edge"]["pickable"] = edge_picking_geom

        edge_sel_state_geom = edge_picking_geom.copy_to(origin)
        vertex_data = edge_sel_state_geom.node().modify_geom(0).modify_vertex_data()
        new_data = vertex_data.set_color(sel_colors["edge"]["unselected"])
        vertex_data.set_array(1, new_data.get_array(1))
        edge_sel_state_geom.hide(all_masks)
        edge_sel_state_geom.set_name("edge_sel_state_geom")
        geoms["edge"]["sel_state"] = edge_sel_state_geom

        vertices = tris_prim.get_vertices()
        vertex_data_top = GeomVertexData(vertex_data_poly)
        tris_geom = Geom(vertex_data_top)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("toplevel_geom")
        geom_node.add_geom(tris_geom)
        self._toplvl_node = geom_node
        toplvl_geom = origin.attach_new_node(geom_node)
        toplvl_geom.hide(picking_masks)
        self._toplvl_geom = toplvl_geom
        geoms["top"] = toplvl_geom
        origin.node().set_bounds(geom_node.get_bounds())

        # create the geom with the polygon picking colors
        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.reserve_num_vertices(3)
        tris_prim.set_vertices(GeomVertexArrayData(vertices))
        tris_geom = Geom(vertex_data_poly_picking)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_picking_geom")
        geom_node.add_geom(tris_geom)
        poly_picking_geom = origin.attach_new_node(geom_node)
        poly_picking_geom.hide(render_masks)
        geoms["poly"]["pickable"] = poly_picking_geom

        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.reserve_num_vertices(3)
        tris_prim.set_vertices(GeomVertexArrayData(vertices))
        tris_geom = Geom(vertex_data_poly)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_unselected_geom")
        geom_node.add_geom(tris_geom)
        poly_unselected_geom = origin.attach_new_node(geom_node)
        poly_unselected_geom.hide(all_masks)
        geoms["poly"]["unselected"] = poly_unselected_geom

        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.reserve_num_vertices(3)
        tris_geom = Geom(vertex_data_poly)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_selected_geom")
        geom_node.add_geom(tris_geom)
        poly_selected_geom = origin.attach_new_node(geom_node)
        poly_selected_geom.set_state(Mgr.get("poly_selection_state"))
        poly_selected_geom.set_effects(Mgr.get("poly_selection_effects"))
        poly_selected_geom.hide(all_masks)
        geoms["poly"]["selected"] = poly_selected_geom

        # Create the geoms for the normals

        vertex_format = Mgr.get("vertex_format_normal")
        vertex_data = vertex_data_top.convert_to(vertex_format)
        points_geom = vert_picking_geom.node().get_geom(0)
        geom = Geom(vertex_data)
        geom.add_primitive(GeomPoints(points_geom.get_primitive(0)))
        geom_node = GeomNode("normal_picking_geom")
        geom_node.add_geom(geom)
        geom_node.set_bounds(OmniBoundingVolume())
        geom_node.set_final(True)
        normal_picking_geom = origin.attach_new_node(geom_node)
        normal_picking_geom.set_state(normal_state)
        normal_picking_geom.set_shader_input("normal_length", 1.)
        normal_picking_geom.hide(all_masks)
        geoms["normal"]["pickable"] = normal_picking_geom

        normal_sel_state_geom = normal_picking_geom.copy_to(origin)
        vertex_data = normal_sel_state_geom.node().modify_geom(0).modify_vertex_data()
        new_data = vertex_data.set_color(sel_colors["normal"]["unselected"])
        vertex_data.set_array(1, new_data.get_array(1))
        normal_sel_state_geom.set_name("normal_sel_state_geom")
        normal_sel_state_geom.set_shader_input("normal_length", 1.)
        geoms["normal"]["sel_state"] = normal_sel_state_geom

        model = self.get_toplevel_object()
        self.update_selection_state(model.is_selected())

        render_mode = GlobalData["render_mode"]

        if "shaded" in render_mode:
            toplvl_geom.show(render_masks)
        else:
            toplvl_geom.hide(render_masks)

        if "wire" in render_mode:
            edge_picking_geom.show(render_masks)
        else:
            edge_picking_geom.hide(render_masks)

        if render_mode == "wire":
            edge_picking_geom.show(picking_masks)

        logging.debug('+++++++++++ Geometry created +++++++++++++++')

    def finalize_geometry(self):

        self.init_picking_colors()
        self.init_uvs()
        self._origin.reparent_to(self.get_toplevel_object().get_origin())
        self._origin.show()

    def get_vertex_coords(self):

        verts = self._subobjs["vert"]

        return dict((vert_id, vert.get_pos()) for vert_id, vert in verts.iteritems())

    def set_vertex_coords(self, coords):

        verts = self._subobjs["vert"]
        node = self._toplvl_node
        vertex_data_top = node.modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")

        for vert_id, pos in coords.iteritems():
            row = verts[vert_id].get_row_index()
            pos_writer.set_row(row)
            pos_writer.set_data3f(pos)

    def bake_texture(self, texture):

        vertex_data = self._toplvl_node.modify_geom(0).modify_vertex_data()
        geom_copy = self._toplvl_geom.copy_to(self.world)
        geom_copy.detach_node()
        geom_copy.set_texture(TextureStage.get_default(), texture)
        geom_copy.flatten_light()
        geom_copy.apply_texture_colors()
        vertex_data_copy = geom_copy.node().modify_geom(0).modify_vertex_data()
        index = vertex_data_copy.get_format().get_array_with("color")
        array = vertex_data_copy.modify_array(index)
        self._vertex_data["poly"].set_array(1, array)
        vertex_data.set_array(1, GeomVertexArrayData(array))

    def clear_vertex_colors(self):

        vertex_data_copy = self._vertex_data["poly"].set_color((1., 1., 1., 1.))
        array = vertex_data_copy.get_array(1)
        self._vertex_data["poly"].set_array(1, GeomVertexArrayData(array))
        vertex_data = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data.set_array(1, GeomVertexArrayData(array))

    def set_initial_vertex_colors(self):

        vertex_data_copy = GeomVertexData(self._vertex_data["poly"])
        col_writer = GeomVertexWriter(vertex_data_copy, "color")

        for vert in self._subobjs["vert"].itervalues():
            row = vert.get_row_index()
            col_writer.set_row(row)
            col_writer.set_data4f(vert.get_color())

        array = vertex_data_copy.get_array(1)
        self._vertex_data["poly"].set_array(1, GeomVertexArrayData(array))
        vertex_data = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data.set_array(1, GeomVertexArrayData(array))

    def init_picking_colors(self):

        pickable_id_vert = PickableTypes.get_id("vert")
        pickable_id_edge = PickableTypes.get_id("edge")
        pickable_id_poly = PickableTypes.get_id("poly")
        vertex_data = self._geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        col_writer_vert = GeomVertexWriter(vertex_data, "color")
        vertex_data = self._geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        col_writer_edge = GeomVertexWriter(vertex_data, "color")
        vertex_data = self._vertex_data["poly_picking"]
        col_writer_poly = GeomVertexWriter(vertex_data, "color")

        for poly in self._ordered_polys:

            picking_color = get_color_vec(poly.get_picking_color_id(), pickable_id_poly)
            verts = poly.get_vertices()

            for i in xrange(len(verts)):
                col_writer_poly.add_data4f(picking_color)

            for vert in verts:
                row = vert.get_row_index()
                picking_color = get_color_vec(vert.get_picking_color_id(), pickable_id_vert)
                col_writer_vert.set_row(row)
                col_writer_vert.set_data4f(picking_color)

        vertex_data = self._geoms["vert"]["pickable"].node().get_geom(0).get_vertex_data()
        col_array = vertex_data.get_array(1)
        vertex_data = self._geoms["normal"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(1, col_array)

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

        for row_index in sorted(picking_colors):
            picking_color = picking_colors[row_index]
            col_writer_edge.add_data4f(picking_color)

    def update_tangent_space(self, tangent_flip, bitangent_flip, poly_ids=None):

        vertex_data = GeomVertexData(self._vertex_data["poly"])
        tan_writer = GeomVertexWriter(vertex_data, "tangent")
        bitan_writer = GeomVertexWriter(vertex_data, "binormal")
        polys = self._subobjs["poly"]

        for poly_id in (polys if poly_ids is None else poly_ids):

            poly = polys[poly_id]
            poly.update_tangent_space(tangent_flip, bitangent_flip)

            for vert in poly.get_vertices():
                row = vert.get_row_index()
                tan_writer.set_row(row)
                bitan_writer.set_row(row)
                tangent, bitangent = vert.get_tangent_space()
                tan_writer.set_data3f(tangent)
                bitan_writer.set_data3f(bitangent)

        array = vertex_data.get_array(3)
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_array(3, GeomVertexArrayData(array))
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data_top.set_array(3, GeomVertexArrayData(array))

        self._is_tangent_space_initialized = True

    def init_tangent_space(self):

        if not self._is_tangent_space_initialized:
            tangent_flip, bitangent_flip = self.get_toplevel_object().get_tangent_space_flip()
            self.update_tangent_space(tangent_flip, bitangent_flip)

    def is_tangent_space_initialized(self):

        return self._is_tangent_space_initialized

    def set_wireframe_color(self, color):

        self._geoms["edge"]["pickable"].set_color(color)

    def update_selection_state(self, is_selected=True):

        geoms = self._geoms
        picking_masks = Mgr.get("picking_masks")["all"]
        render_mode = GlobalData["render_mode"]

        if is_selected:

            if render_mode == "wire":
                geoms["poly"]["pickable"].show(picking_masks)
                geoms["edge"]["pickable"].hide(picking_masks)

            self.set_wireframe_color((1., 1., 1., 1.))

        else:

            if render_mode == "wire":
                geoms["poly"]["pickable"].hide(picking_masks)
                geoms["edge"]["pickable"].show(picking_masks)

            self.set_wireframe_color(self.get_toplevel_object().get_color())

    def update_render_mode(self, is_selected):

        render_mode = GlobalData["render_mode"]
        render_masks = Mgr.get("render_masks")["all"]
        picking_masks = Mgr.get("picking_masks")["all"]
        geoms = self._geoms

        if is_selected:

            obj_lvl = GlobalData["active_obj_level"]

        else:

            if render_mode == "wire":
                geoms["poly"]["pickable"].hide(picking_masks)
                geoms["edge"]["pickable"].show(picking_masks)
            else:
                geoms["poly"]["pickable"].show(picking_masks)
                geoms["edge"]["pickable"].hide(picking_masks)

            obj_lvl = "top"

        if "wire" in render_mode:
            if obj_lvl == "edge":
                geoms["edge"]["pickable"].hide(render_masks)
            else:
                geoms["edge"]["pickable"].show(render_masks)
        else:
            geoms["edge"]["pickable"].hide(render_masks)

        if "shaded" in render_mode:
            if obj_lvl == "poly" or (obj_lvl == "top" and self._has_poly_tex_proj):
                geoms["top"].hide(render_masks)
                geoms["poly"]["unselected"].show(render_masks)
            else:
                geoms["top"].show(render_masks)
                geoms["poly"]["unselected"].hide(render_masks)
        else:
            geoms["top"].hide(render_masks)
            geoms["poly"]["unselected"].hide(render_masks)

        if obj_lvl in ("vert", "edge", "normal"):
            self.init_subobj_picking(obj_lvl)

    def show_top_level(self):

        render_masks = Mgr.get("render_masks")["all"]
        picking_masks = Mgr.get("picking_masks")["all"]
        geoms = self._geoms

        for lvl in ("vert", "edge", "normal"):
            geoms[lvl]["pickable"].hide(picking_masks)
            geoms[lvl]["sel_state"].hide(render_masks)

        if GlobalData["subobj_edit_options"]["pick_via_poly"]:
            self.restore_selection_backup("poly")

        self.set_normal_shader(False)
        geoms["poly"]["pickable"].show(picking_masks)

        if self._has_poly_tex_proj:
            geoms["poly"]["selected"].show(render_masks)
            geoms["poly"]["unselected"].show(render_masks)
        else:
            geoms["poly"]["selected"].hide(render_masks)
            geoms["poly"]["unselected"].hide(render_masks)

        self.update_render_mode(self.get_toplevel_object().is_selected())

    def show_subobj_level(self, subobj_lvl):

        render_masks = Mgr.get("render_masks")["all"]
        picking_masks = Mgr.get("picking_masks")["all"]
        all_masks = render_masks | picking_masks

        geoms = self._geoms

        if subobj_lvl == "poly":

            geoms["poly"]["pickable"].show_through(picking_masks)
            geoms["poly"]["selected"].show(render_masks)
            geoms["poly"]["selected"].set_state(Mgr.get("poly_selection_state"))
            geoms["poly"]["unselected"].show(render_masks)

            for lvl in ("vert", "edge", "normal"):
                geoms[lvl]["pickable"].hide(all_masks)
                geoms[lvl]["sel_state"].hide(all_masks)

        else:

            geoms["poly"]["pickable"].show(picking_masks)
            geoms["poly"]["selected"].hide(render_masks)
            geoms["poly"]["unselected"].hide(render_masks)

            other_lvls = ["vert", "edge", "normal"]
            other_lvls.remove(subobj_lvl)
            geoms[subobj_lvl]["pickable"].show_through(picking_masks)
            geoms[subobj_lvl]["sel_state"].show(render_masks)

            for other_lvl in other_lvls:
                geoms[other_lvl]["pickable"].hide(all_masks)
                geoms[other_lvl]["sel_state"].hide(all_masks)

        if GlobalData["subobj_edit_options"]["pick_via_poly"]:
            if subobj_lvl in ("vert", "edge", "normal"):
                self.create_selection_backup("poly")
            else:
                self.restore_selection_backup("poly")

        if subobj_lvl == "normal":
            self.set_normal_shader()
        else:
            self.set_normal_shader(False)

        self.update_render_mode(self.get_toplevel_object().is_selected())

    def set_pickable(self, is_pickable=True):

        geoms = self._geoms
        active_obj_lvl = GlobalData["active_obj_level"]
        picking_masks = Mgr.get("picking_masks")["all"]

        if is_pickable:

            for obj_lvl in ("vert", "edge", "normal", "poly"):
                if obj_lvl == active_obj_lvl:
                    geoms[obj_lvl]["pickable"].show_through(picking_masks)

            self.update_render_mode(True)

        else:

            for obj_lvl in ("vert", "edge", "normal", "poly"):
                geoms[obj_lvl]["pickable"].hide(picking_masks)

    def init_subobj_picking(self, subobj_lvl):

        geoms = self._geoms

        if GlobalData["subobj_edit_options"]["pick_via_poly"]:

            self.create_selection_backup("poly")
            geoms["poly"]["selected"].set_state(Mgr.get("temp_poly_selection_state"))
            self.prepare_subobj_picking_via_poly(subobj_lvl)

        else:

            render_masks = Mgr.get("render_masks")["all"]
            picking_masks = Mgr.get("picking_masks")["all"]
            geoms[subobj_lvl]["pickable"].show_through(picking_masks)
            geoms["poly"]["pickable"].show(picking_masks)
            geoms["poly"]["selected"].hide(render_masks)

            if not geoms["poly"]["unselected"].is_hidden(render_masks):
                geoms["poly"]["unselected"].hide(render_masks)
                geoms["top"].show(render_masks)

    def prepare_subobj_picking_via_poly(self, subobj_type):

        self.clear_selection("poly", False)

        # clean up temporary vertex data
        if self._tmp_geom_pickable:

            self._tmp_geom_pickable.remove_node()
            self._tmp_geom_pickable = None
            self._tmp_geom_sel_state.remove_node()
            self._tmp_geom_sel_state = None
            self._tmp_row_indices = {}

            if GlobalData["subobj_edit_options"]["pick_by_aiming"]:
                aux_picking_root = Mgr.get("aux_picking_root")
                tmp_geom_pickable = aux_picking_root.find("**/tmp_geom_pickable")
                tmp_geom_pickable.remove_node()
                aux_picking_cam = Mgr.get("aux_picking_cam")
                aux_picking_cam.set_active(False)
                Mgr.do("end_drawing_aux_picking_viz")

        # Allow picking polys instead of the subobjects of the given type;
        # as soon as a poly is clicked, its subobjects (of the given type) become
        # pickable instead of polys.

        render_masks = Mgr.get("render_masks")["all"]
        picking_masks = Mgr.get("picking_masks")["all"]
        geoms = self._geoms
        geoms[subobj_type]["pickable"].hide(picking_masks)
        geoms["poly"]["pickable"].show_through(picking_masks)
        geoms["poly"]["selected"].show(render_masks)

        if not geoms["top"].is_hidden(render_masks):
            geoms["top"].hide(render_masks)
            geoms["poly"]["unselected"].show(render_masks)

    def init_subobj_picking_via_poly(self, subobj_lvl, picked_poly, category="", extra_data=None):

        if subobj_lvl == "vert":
            self.init_vertex_picking_via_poly(picked_poly, category)
        elif subobj_lvl == "edge":
            self.init_edge_picking_via_poly(picked_poly, category, extra_data)
        elif subobj_lvl == "normal":
            self.init_normal_picking_via_poly(picked_poly, category)

    def hilite_temp_subobject(self, subobj_lvl, color_id):

        row = self._tmp_row_indices.get(color_id)

        if row is None:
            return False

        colors = Mgr.get("subobj_selection_colors")[subobj_lvl]
        geom = self._tmp_geom_sel_state.node().modify_geom(0)
        vertex_data = geom.get_vertex_data().set_color((.3, .3, .3, .5))
        geom.set_vertex_data(vertex_data)
        col_writer = GeomVertexWriter(geom.modify_vertex_data(), "color")
        col_writer.set_row(row)
        col_writer.set_data4f(colors["selected"])

        if subobj_lvl == "edge":
            col_writer.set_data4f(colors["selected"])

        return True

    def set_owner(self, owner):

        self._owner = owner

    def get_owner(self):

        return self._owner

    def get_toplevel_object(self, get_group=False):

        return self._owner.get_toplevel_object(get_group)

    def set_origin(self, origin):

        self._origin = origin

    def get_origin(self):

        return self._origin

    def get_merged_vertices(self):

        return self._merged_verts

    def get_merged_edges(self):

        return self._merged_edges

    def get_merged_vertex(self, vert_id):

        return self._merged_verts.get(vert_id)

    def get_merged_edge(self, edge_id):

        return self._merged_edges.get(edge_id)

    def get_property_ids(self, unique=False):

        if unique:
            return [self._unique_prop_ids[k] for k in self._prop_ids]

        return self._prop_ids

    def get_type_property_ids(self, obj_lvl="top"):

        if obj_lvl == "top":
            return []

        return self._type_prop_ids[obj_lvl]

    def get_property(self, prop_id, for_remote_update=False, obj_lvl="top"):

        if obj_lvl == "top":
            return

        if prop_id == "normal_length":
            return self._normal_length


class GeomDataManager(ObjectManager):

    def __init__(self):

        ObjectManager.__init__(self, "geom_data", self.__create_data, "sub")

        subobj_edit_options = {
            "pick_via_poly": False,
            "pick_by_aiming": False,
            "normal_preserve": False,
            "sel_edges_by_border": False,
            "sel_polys_by_surface": False,
            "sel_polys_by_smoothing": False,
            "edge_bridge_segments": 1
        }
        copier = dict.copy
        GlobalData.set_default("subobj_edit_options", subobj_edit_options, copier)

        # Define GeomVertexArrayFormats for the various vertex attributes.

        pos_array = GeomVertexArrayFormat()
        pos_array.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)

        col_array = GeomVertexArrayFormat()
        col_array.add_column(InternalName.make("color"), 1, Geom.NT_packed_dabc, Geom.C_color)

        normal_array = GeomVertexArrayFormat()
        normal_array.add_column(InternalName.make("normal"), 3, Geom.NT_float32, Geom.C_normal)

        tan_array = GeomVertexArrayFormat()
        tan_array.add_column(InternalName.make("tangent"), 3, Geom.NT_float32, Geom.C_vector)
        tan_array.add_column(InternalName.make("binormal"), 3, Geom.NT_float32, Geom.C_vector)

        uv_arrays = []
        uv_array = GeomVertexArrayFormat()
        uv_array.add_column(InternalName.make("texcoord"), 2, Geom.NT_float32, Geom.C_texcoord)
        uv_arrays.append(uv_array)

        for i in xrange(1, 8):
            uv_array = GeomVertexArrayFormat()
            uv_array.add_column(InternalName.make("texcoord.{:d}".format(i)), 2, Geom.NT_float32, Geom.C_texcoord)
            uv_arrays.append(uv_array)

        # Define a "basic" GeomVertexFormat that accommodates only position and color.

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(pos_array)
        vertex_format.add_array(col_array)
        vertex_format_basic = GeomVertexFormat.register_format(vertex_format)

        # Define a "full" GeomVertexFormat that also accommodates normal, tangent and
        # bitangent ("binormal"), as well as multiple texture coordinate sets.

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(pos_array)
        vertex_format.add_array(col_array)
        vertex_format.add_array(normal_array)
        vertex_format.add_array(tan_array)

        for uv_array in uv_arrays:
            vertex_format.add_array(uv_array)

        vertex_format_full = GeomVertexFormat.register_format(vertex_format)

        # Define a GeomVertexFormat that accommodates position, color and normal.

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(pos_array)
        vertex_format.add_array(col_array)
        vertex_format.add_array(normal_array)
        vertex_format_normal = GeomVertexFormat.register_format(vertex_format)

        Mgr.expose("vertex_format_basic", lambda: vertex_format_basic)
        Mgr.expose("vertex_format_full", lambda: vertex_format_full)
        Mgr.expose("vertex_format_normal", lambda: vertex_format_normal)

        # create the root of the setup that assists in picking subobjects via the
        # polygon they belong to
        self._aux_picking_root = NodePath("aux_picking_root")
        Mgr.expose("aux_picking_root", lambda: self._aux_picking_root)

        # Create line geometry to visualize a "picking ray" that assists in picking
        # subobjects via the polygon they belong to.

        node = GeomNode("aux_picking_viz")
        state_np = NodePath("state_np")
        state_np.set_transparency(TransparencyAttrib.M_alpha)
        state_np.set_depth_test(False)
        state_np.set_depth_write(False)
        state_np.set_bin("fixed", 101)
        state1 = state_np.get_state()
        state_np.set_bin("fixed", 100)
        state_np.set_render_mode_thickness(3)
        state2 = state_np.get_state()

        vertex_data = GeomVertexData("aux_picking_viz_data", vertex_format_basic, Geom.UH_static)
        vertex_data.set_num_rows(2)
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(1)
        col_writer.set_data4f(1., 1., 1., 0.)

        lines = GeomLines(Geom.UH_dynamic)
        lines.add_next_vertices(2)
        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        node.add_geom(lines_geom, state1)

        lines_geom = lines_geom.make_copy()
        vertex_data = lines_geom.modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(0)
        col_writer.set_data4f(0., 0., 0., 1.)
        col_writer.set_data4f(0., 0., 0., 0.)
        node.add_geom(lines_geom, state2)

        aux_picking_viz = NodePath(node)
        self._aux_picking_viz = aux_picking_viz
        Mgr.expose("aux_picking_viz", lambda: self._aux_picking_viz)

        # Create a rubber band line.

        vertex_format = GeomVertexFormat.get_v3t2()
        vertex_data = GeomVertexData("rubber_band_data", vertex_format, Geom.UH_static)
        vertex_data.set_num_rows(2)

        lines = GeomLines(Geom.UH_dynamic)
        lines.add_next_vertices(2)
        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        node = GeomNode("rubber_band")
        node.add_geom(lines_geom)
        rubber_band = NodePath(node)
        rubber_band.set_bin("fixed", 100)
        rubber_band.set_depth_test(False)
        rubber_band.set_depth_write(False)
        tex = Mgr.load_tex(GFX_PATH + "marquee.png")
        rubber_band.set_texture(tex)
        self._rubber_band = rubber_band

        self._draw_start_pos = {"aux_picking_viz": Point3(), "rubber_band": Point3()}
        self._draw_plane = None

        Mgr.accept("start_drawing_aux_picking_viz", self.__start_drawing_aux_picking_viz)
        Mgr.accept("end_drawing_aux_picking_viz", self.__end_drawing_aux_picking_viz)
        Mgr.accept("start_drawing_rubber_band", self.__start_drawing_rubber_band)
        Mgr.accept("end_drawing_rubber_band", self.__end_drawing_rubber_band)

    def setup(self):

        if "picking_camera_ok" not in MainObjects.get_setup_results():
            return False

        picking_masks = Mgr.get("picking_masks")["all"]
        self._aux_picking_viz.hide(picking_masks)
        self._rubber_band.hide(picking_masks)

        return True

    def __start_drawing_line(self, line, world_start_pos=None):

        cam = self.cam()
        cam_pos = cam.get_pos(self.world)
        normal = self.world.get_relative_vector(cam, Vec3.forward()).normalized()
        plane = Plane(normal, cam_pos + normal * 10.)
        point = Point3()

        if world_start_pos is None:

            if not self.mouse_watcher.has_mouse():
                return

            screen_pos = self.mouse_watcher.get_mouse()
            near_point = Point3()
            far_point = Point3()
            self.cam.lens.extrude(screen_pos, near_point, far_point)
            rel_pt = lambda point: self.world.get_relative_point(cam, point)
            plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))

        else:

            p = cam_pos if self.cam.lens_type == "persp" else world_start_pos - normal * 100.
            plane.intersects_line(point, p, world_start_pos)

        line_node = line.node()

        for i in range(line_node.get_num_geoms()):
            vertex_data = line_node.modify_geom(i).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(0)
            pos_writer.set_data3f(point)

        line.reparent_to(self.world)
        line_type = "rubber_band" if line is self._rubber_band else "aux_picking_viz"
        self._draw_start_pos[line_type] = point
        self._draw_plane = plane

        task = self.__draw_rubber_band if line is self._rubber_band else self.__draw_aux_picking_viz
        task_name = "draw_rubber_band" if line is self._rubber_band else "draw_aux_picking_viz"
        Mgr.add_task(task, task_name, sort=3)

    def __start_drawing_aux_picking_viz(self):

        self.__start_drawing_line(self._aux_picking_viz)

    def __start_drawing_rubber_band(self, start_pos):

        self.__start_drawing_line(self._rubber_band, start_pos)

    def __draw_line(self, line):

        screen_pos = self.mouse_watcher.get_mouse()
        cam = self.cam()
        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)
        point = Point3()
        self._draw_plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))
        line_type = "rubber_band" if line is self._rubber_band else "aux_picking_viz"
        start_pos = self._draw_start_pos[line_type]

        if line is self._aux_picking_viz:
            point = start_pos + (point - start_pos) * 3.

        line_node = line.node()

        for i in range(line_node.get_num_geoms()):
            vertex_data = line_node.modify_geom(i).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(1)
            pos_writer.set_data3f(point)

        if line is self._rubber_band:

            w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "main" else "size"]
            s = max(w, h) / 800.
            length = (point - start_pos).length() * s * 5.

            if self.cam.lens_type == "ortho":
                length /= 40. * self.cam.zoom

            vertex_data = line_node.modify_geom(0).modify_vertex_data()
            uv_writer = GeomVertexWriter(vertex_data, "texcoord")
            uv_writer.set_row(1)
            uv_writer.set_data2f(length, 1.)

    def __draw_aux_picking_viz(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        self.__draw_line(self._aux_picking_viz)

        return task.cont

    def __draw_rubber_band(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        self.__draw_line(self._rubber_band)

        return task.cont

    def __end_drawing_aux_picking_viz(self):

        Mgr.remove_task("draw_aux_picking_viz")
        self._aux_picking_viz.detach_node()

    def __end_drawing_rubber_band(self):

        Mgr.remove_task("draw_rubber_band")
        self._rubber_band.detach_node()

    def __create_data(self, owner):

        return GeomDataObject(self.get_next_id(), owner)


MainObjects.add_class(GeomDataManager)
