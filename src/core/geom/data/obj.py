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

        state = self.__dict__.copy()
        state["_origin"] = NodePath(self._origin.node().make_copy())
        del state["_vertex_data"]
        del state["_owner"]
        del state["_toplvl_node"]
        del state["_toplvl_geom"]
        del state["_geoms"]
        del state["_ordered_polys"]
        del state["_merged_verts"]
        del state["_merged_edges"]
        del state["_subobjs"]
        del state["_poly_smoothing"]

        GeomSelectionBase.__editstate__(self, state)

        return state

    def __setstate__(self, state):

        self.__dict__ = state

        GeomSelectionBase.__setstate__(self, state)

        self._data_row_count = 0
        self._merged_verts = {}
        self._merged_edges = {}
        self._ordered_polys = []
        self._poly_smoothing = {}

        self._subobjs = subobjs = {}
        self._geoms = geoms = {}
        geoms["top"] = None

        for subobj_type in ("vert", "edge", "poly"):
            subobjs[subobj_type] = {}
            geoms[subobj_type] = {"pickable": None, "sel_state": None}

        del geoms["poly"]["sel_state"]
        geoms["poly"]["selected"] = None
        geoms["poly"]["unselected"] = None

        self._vertex_data = {}

    def __init__(self, data_id, owner):

        GeomSelectionBase.__init__(self)
        GeomTransformBase.__init__(self)
        GeomHistoryBase.__init__(self)
        PolygonEditBase.__init__(self)
        UVEditBase.__init__(self)

        self._id = data_id
        self._owner = owner
        self._origin = None
        self._data_row_count = 0
        self._merged_verts = {}
        self._merged_edges = {}
        self._ordered_polys = []
        self._is_tangent_space_initialized = False
        self._has_tangent_space = False
        self._flip_tangent = False
        self._flip_bitangent = False

        self._prop_ids = ["subobj_merge", "subobj_selection", "subobj_transform",
                          "smoothing", "poly_tris", "uvs"]
        prop_ids_ext = self._prop_ids + ["vert_pos__extra__", "tri__extra__", "uv__extra__",
                                         "verts", "edges", "polys",
                                         "vert__extra__", "edge__extra__", "poly__extra__"]
        self._unique_prop_ids = dict((k, "geom_data_%s_%s" % (data_id, k)) for k in prop_ids_ext)

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

        del geoms["poly"]["sel_state"]
        geoms["poly"]["selected"] = None
        geoms["poly"]["unselected"] = None
        self._toplvl_geom = None
        self._toplvl_node = None

    def __del__(self):

        logging.debug('GeomDataObject garbage-collected.')

    def cancel_creation(self):

        logging.debug('GeomDataObject "%s" creation cancelled.', self._id)

        if self._origin:
            self._origin.remove_node()

        self.__dict__.clear()

    def destroy(self, unregister=True):

        logging.debug('About to destroy GeomDataObject "%s"...', self._id)

        if unregister:
            self.unregister()

        self._origin.remove_node()

        logging.debug('GeomDataObject "%s" destroyed.', self._id)
        self.__dict__.clear()

    def register(self, restore=True, locally=False):

        subobjs = (self._subobjs_to_reg if self._subobjs_to_reg else self._subobjs)

        for subobj_type in ("vert", "edge", "poly"):

            Mgr.do("register_%s_objs" % subobj_type, subobjs[subobj_type].itervalues(), restore)

            if locally:
                self._subobjs[subobj_type].update(subobjs[subobj_type])

        self._subobjs_to_reg = None

    def unregister(self, locally=False):

        subobjs = (self._subobjs_to_unreg if self._subobjs_to_unreg else self._subobjs)

        for subobj_type in ("vert", "edge", "poly"):

            Mgr.do("unregister_%s_objs" % subobj_type, subobjs[subobj_type].itervalues())

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
        merged_verts_by_pos = {}
        merged_edges = self._merged_edges
        merged_edges_tmp = {}
        self._poly_smoothing = poly_smoothing = {}
        smoothing_by_id = {}

        if gradual:
            poly_count = 0

        for poly_data in data:

            row_index = 0
            verts_by_pos = {}
            poly_verts = []
            edge_data = []
            triangles = []

            for tri_data in poly_data["tris"]:

                tri_vert_ids = []

                for vert_data in tri_data:

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

                        positions = merged_verts_by_pos.keys()

                        if pos in positions:
                            index = positions.index(pos)
                            p = positions[index]
                            merged_vert = merged_verts_by_pos[p]
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

            if gradual:

                poly_count += 1

                if poly_count == 10:
                    yield
                    poly_count = 0

        logging.debug('New mesh has %d polys.', len(ordered_polys))

        processed_data = {"smoothing": smoothing_by_id}

        yield processed_data

    def create_geometry(self, obj_type="", gradual=False, restore=False):

        if restore:
            origin = self._origin
        else:
            node_name = "%s_geom_origin" % obj_type
            origin = NodePath(node_name)
            self._origin = origin

        origin.node().set_final(True)
        origin.hide()

        if GlobalData["two_sided"]:
            origin.set_two_sided(True)

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
                            pos = vert.get_pos()
                            pos_writer.add_data3f(pos)

                        processed_verts.append(vert)

                    tris_prim.add_vertex(vert.get_row_index())

            if not restore:
                start_row_indices = []
                end_row_indices = []

            for edge in poly.get_edges():

                row1, row2 = [verts[v_id].get_row_index() for v_id in edge]

                if not restore:

                    if row1 in start_row_indices or row2 in end_row_indices:
                        row1, row2 = row2, row1
                        edge.reverse_vertex_order()

                    start_row_indices.append(row1)
                    end_row_indices.append(row2)

                lines_prim.add_vertices(row1, row2 + count)

            row_index_offset += poly.get_vertex_count()

            sel_data.extend(poly[:])

            if gradual:

                poly_count += 1

                if poly_count == 50:
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
        state_np.set_shader_off()
        state_np.set_transparency(TransparencyAttrib.M_none)

        vert_state_np = NodePath(state_np.node().make_copy())
        vert_state_np.set_render_mode_thickness(7)

        edge_state_np = NodePath(state_np.node().make_copy())
        edge_state_np.set_attrib(DepthTestAttrib.make(RenderAttrib.M_less_equal))
        edge_state_np.set_bin("fixed", 1)

        vert_state = vert_state_np.get_state()
        edge_state = edge_state_np.get_state()

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
        tris_geom = Geom(GeomVertexData(vertex_data_poly))
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

        self.update_selection_state(self.get_toplevel_object().is_selected())

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

        if self._has_tangent_space:
            self.update_tangent_space()

        logging.debug('+++++++++++ Geometry created +++++++++++++++')

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

    def reposition_vertices(self, computation):
        """ Change the positions of all vertices using the given computation """

        verts = self._subobjs["vert"]
        geoms = self._geoms
        geom_node_top = self._toplvl_node
        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")

        for vert in self._subobjs["vert"].itervalues():
            row = vert.get_row_index()
            old_pos = vert.get_initial_pos()
            new_pos = computation(Point3(*old_pos))
            pos_writer.set_row(row)
            pos_writer.set_data3f(Point3(*new_pos))
            vert.set_pos(Point3(*new_pos))

        array = vertex_data_top.get_array(0)

        for geom_type in ("poly", "poly_picking"):
            vertex_data = self._vertex_data[geom_type]
            vertex_data.set_array(0, array)

        vertex_data = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, array)
        vertex_data = geoms["vert"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, array)

        array = GeomVertexArrayData(array)
        handle = array.modify_handle()
        handle.set_data(handle.get_data() * 2)
        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, array)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, array)

    def bake_transform(self):
        """ Bake the origin's transform into the vertices and reset it to identity """

        mat = self._origin.get_mat()
        geoms = self._geoms
        geom_node_top = self._toplvl_node
        geom_node_top.modify_geom(0).transform_vertices(mat)
        self._origin.clear_transform()
        vertex_data_top = geom_node_top.get_geom(0).get_vertex_data()
        array = vertex_data_top.get_array(0)

        for geom_type in ("poly", "poly_picking"):
            vertex_data = self._vertex_data[geom_type]
            vertex_data.set_array(0, array)

        vertex_data = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, array)
        vertex_data = geoms["vert"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, array)

        array = GeomVertexArrayData(array)
        handle = array.modify_handle()
        handle.set_data(handle.get_data() * 2)
        vertex_data = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, array)
        vertex_data = geoms["edge"]["sel_state"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(0, array)

        pos_reader = GeomVertexReader(vertex_data_top, "vertex")

        for vert in self._subobjs["vert"].itervalues():
            row = vert.get_row_index()
            pos_reader.set_row(row)
            pos = pos_reader.get_data3f()
            # NOTE: the LVecBase3f returned by the GeomVertexReader is a const
            vert.set_pos(Point3(*pos))

    def bake_texture(self, texture):

        vertex_data = self._toplvl_node.modify_geom(0).modify_vertex_data()
        geom_copy = self._toplvl_geom.copy_to(self.world)
        geom_copy.detach_node()
        geom_copy.set_texture(TextureStage.get_default(), texture)
        geom_copy.flatten_light()
        geom_copy.apply_texture_colors()
        vertex_data_copy = geom_copy.node().modify_geom(0).modify_vertex_data()
        array = vertex_data_copy.modify_array(10)
        self._vertex_data["poly"].set_array(2, array)
        vertex_data.set_array(2, GeomVertexArrayData(array))

    def reset_vertex_colors(self):

        vertex_data_copy = self._vertex_data["poly"].set_color((1., 1., 1., 1.))
        array = vertex_data_copy.get_array(2)
        self._vertex_data["poly"].set_array(2, GeomVertexArrayData(array))
        vertex_data = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data.set_array(2, GeomVertexArrayData(array))

    def init_vertex_colors(self):

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

    def init_poly_normals(self):

        for poly in self._ordered_polys:
            poly.update_normal()

        yield True

        for step in self._update_vertex_normals(set(self._merged_verts.itervalues())):
            yield True

        yield False

    def flip_tangent(self, flip_tangent=True):

        self._flip_tangent = flip_tangent

    def flip_bitangent(self, flip_bitangent=True):

        self._flip_bitangent = flip_bitangent

    def update_tangent_space(self, polys=None):

        vertex_data = GeomVertexData(self._vertex_data["poly"])
        tan_writer = GeomVertexWriter(vertex_data, "tangent")
        bitan_writer = GeomVertexWriter(vertex_data, "binormal")

        for poly in (self._ordered_polys if polys is None else polys):

            poly.update_tangent_space(self._flip_tangent, self._flip_bitangent)

            for vert in poly.get_vertices():
                row = vert.get_row_index()
                tan_writer.set_row(row)
                bitan_writer.set_row(row)
                tangent, bitangent = vert.get_tangent_space()
                tan_writer.set_data3f(tangent)
                bitan_writer.set_data3f(bitangent)

        array = vertex_data.get_array(1)
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_array(1, GeomVertexArrayData(array))
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data_top.set_array(1, GeomVertexArrayData(array))

        self._is_tangent_space_initialized = True
        self._has_tangent_space = True

    def init_tangent_space(self):

        if not self._is_tangent_space_initialized:
            self.update_tangent_space()

        self._has_tangent_space = True

    def is_tangent_space_initialized(self):

        return self._is_tangent_space_initialized

    def clear_tangent_space(self):

        self._has_tangent_space = False

    def has_tangent_space(self):

        return self._has_tangent_space

    def update_poly_centers(self):

        for poly in self._ordered_polys:
            poly.update_center_pos()

    def finalize_geometry(self, update_poly_centers=True):

        self.init_vertex_colors()
        self.init_uvs()

        for step in self.init_poly_normals():
            yield

        if update_poly_centers:
            self.update_poly_centers()

        self._origin.reparent_to(self.get_toplevel_object().get_origin())
        self._origin.show()

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

    def show_top_level(self):

        render_masks = Mgr.get("render_masks")["all"]
        picking_masks = Mgr.get("picking_masks")["all"]
        geoms = self._geoms

        for lvl in ("vert", "edge"):
            geoms[lvl]["pickable"].hide(picking_masks)
            geoms[lvl]["sel_state"].hide(render_masks)

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
            geoms["poly"]["unselected"].show(render_masks)

            for lvl in ("vert", "edge"):
                geoms[lvl]["pickable"].hide(all_masks)
                geoms[lvl]["sel_state"].hide(all_masks)

        else:

            geoms["poly"]["pickable"].show(picking_masks)
            geoms["poly"]["selected"].hide(render_masks)
            geoms["poly"]["unselected"].hide(render_masks)
            other_subobj_lvl = "edge" if subobj_lvl == "vert" else "vert"
            geoms[subobj_lvl]["pickable"].show_through(picking_masks)
            geoms[subobj_lvl]["sel_state"].show(render_masks)
            geoms[other_subobj_lvl]["pickable"].hide(all_masks)
            geoms[other_subobj_lvl]["sel_state"].hide(all_masks)

        self.update_render_mode(self.get_toplevel_object().is_selected())

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

    def get_merged_vertex(self, vert_id):

        return self._merged_verts.get(vert_id)

    def get_merged_edge(self, edge_id):

        return self._merged_edges.get(edge_id)

    def get_property_ids(self, unique=False):

        if unique:
            return [self._unique_prop_ids[k] for k in self._prop_ids]

        return self._prop_ids


class GeomDataManager(ObjectManager):

    def __init__(self):

        ObjectManager.__init__(self, "geom_data", self.__create_data, "sub")

        subobj_edit_options = {"sel_polys_by_smoothing": False}
        copier = dict.copy
        GlobalData.set_default("subobj_edit_options", subobj_edit_options, copier)

        vert_colors = {"selected": (1., 0., 0., 1.), "unselected": (.5, .5, 1., 1.)}
        edge_colors = {"selected": (1., 0., 0., 1.), "unselected": (1., 1., 1., 1.)}
        self._subobj_sel_colors = {"vert": vert_colors, "edge": edge_colors}

        Mgr.expose("subobj_selection_colors", lambda: self._subobj_sel_colors)

    def setup(self):

        sort = PendingTasks.get_sort("clear_geom_data", "object")

        if sort is None:
            return False

        task_ids = (
            "merge_subobjs",
            "restore_geometry",
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
            "upd_tangent_space",
            "set_material"
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
        array3.add_column(InternalName.make("normal"), 3, Geom.NT_float32, Geom.C_normal)
        array3.add_column(InternalName.make("tangent"), 3, Geom.NT_float32, Geom.C_vector)
        array3.add_column(InternalName.make("binormal"), 3, Geom.NT_float32, Geom.C_vector)

        array4 = GeomVertexArrayFormat()
        array4.add_column(InternalName.make("color"), 1, Geom.NT_packed_dabc, Geom.C_color)

        uv_arrays = []
        uv_array = GeomVertexArrayFormat()
        uv_array.add_column(InternalName.make("texcoord"), 2, Geom.NT_float32, Geom.C_texcoord)
        uv_arrays.append(uv_array)

        for i in xrange(1, 8):
            uv_array = GeomVertexArrayFormat()
            uv_array.add_column(InternalName.make("texcoord.%d" % i), 2, Geom.NT_float32, Geom.C_texcoord)
            uv_arrays.append(uv_array)

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(array1)
        vertex_format.add_array(array2)
        vertex_format_basic = GeomVertexFormat.register_format(vertex_format)

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(array1)
        vertex_format.add_array(array3)
        vertex_format.add_array(array4)

        for uv_array in uv_arrays:
            vertex_format.add_array(uv_array)

        vertex_format_full = GeomVertexFormat.register_format(vertex_format)

        Mgr.expose("vertex_format_basic", lambda: vertex_format_basic)
        Mgr.expose("vertex_format_full", lambda: vertex_format_full)

        return True

    def __create_data(self, owner):

        return GeomDataObject(self.get_next_id(), owner)


MainObjects.add_class(GeomDataManager)
