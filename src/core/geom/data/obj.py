from ...base import *
from .select import SelectionMixin
from .transform import GeomTransformMixin
from .history import HistoryMixin
from .vert_edit import VertexEditMixin
from .edge_edit import EdgeEditMixin
from .poly_edit import PolygonEditMixin, SmoothingGroup
from .normal_edit import NormalEditMixin
from .uv_edit import UVEditMixin


class GeomDataObject(SelectionMixin, GeomTransformMixin, HistoryMixin,
                     VertexEditMixin, EdgeEditMixin, PolygonEditMixin,
                     NormalEditMixin, UVEditMixin):

    def __getstate__(self):

        state = self.__dict__.copy()
        state["origin"] = NodePath(self.origin.node().make_copy())
        state["origin"].clear_two_sided()
        del state["_vertex_data"]
        del state["owner"]
        del state["_toplvl_node"]
        del state["toplevel_geom"]
        del state["_geoms"]
        del state["merged_verts"]
        del state["merged_edges"]
        del state["shared_normals"]
        del state["locked_normals"]
        del state["_poly_smoothing"]
        del state["ordered_polys"]
        del state["_subobjs"]
        del state["_indexed_subobjs"]
        del state["is_tangent_space_initialized"]

        SelectionMixin._edit_state(self, state)

        return state

    def __setstate__(self, state):

        self.__dict__ = state

        SelectionMixin.__setstate__(self, state)

        self._data_row_count = 0
        self.merged_verts = {}
        self.merged_edges = {}
        self.shared_normals = {}
        self.locked_normals = set()
        self._poly_smoothing = {}
        self.ordered_polys = []
        self.is_tangent_space_initialized = False
        self._picking_geom_xform_locked = False

        self._subobjs = subobjs = {}
        self._indexed_subobjs = indexed_subobjs = {}
        self._geoms = geoms = {}
        geoms["top"] = None

        for subobj_type in ("vert", "edge", "poly"):
            subobjs[subobj_type] = {}
            indexed_subobjs[subobj_type] = {}
            geoms[subobj_type] = {"pickable": None, "sel_state": None}

        geoms["normal"] = {"pickable": None, "sel_state": None}
        del geoms["poly"]["sel_state"]
        geoms["poly"]["selected"] = None
        geoms["poly"]["unselected"] = None

        self._vertex_data = {}

    def __init__(self, data_id, owner):

        SelectionMixin.__init__(self)
        GeomTransformMixin.__init__(self)
        HistoryMixin.__init__(self)
        PolygonEditMixin.__init__(self)
        NormalEditMixin.__init__(self)
        UVEditMixin.__init__(self)

        self.id = data_id
        self.owner = owner
        self.origin = None
        self._data_row_count = 0
        self.merged_verts = {}
        self.merged_edges = {}
        self.ordered_polys = []
        self.is_tangent_space_initialized = False

        self._prop_ids = ["subobj_merge", "subobj_selection", "subobj_transform", "poly_tris",
                          "uvs", "uv_set_names", "normals", "normal_lock", "normal_length",
                          "normal_sharing", "smoothing"]
        prop_ids_ext = self._prop_ids + ["vert_pos__extra__", "tri__extra__", "uv__extra__",
                                         "normal__extra__", "normal_lock__extra__",
                                         "verts", "edges", "polys",
                                         "vert__extra__", "edge__extra__", "poly__extra__"]
        self._unique_prop_ids = {k: f"geom_data_{data_id}_{k}" for k in prop_ids_ext}
        self._type_prop_ids = {"vert": [], "edge": [], "poly": [], "normal": ["normal_length"]}

        self._vertex_data = vertex_data = {}
        vertex_data["poly"] = None
        vertex_data["poly_picking"] = None
        self._subobjs = subobjs = {}
        self._indexed_subobjs = indexed_subobjs = {}
        self._subobjs_to_reg = None
        self._subobjs_to_unreg = None
        self._geoms = geoms = {}
        geoms["top"] = None

        for subobj_type in ("vert", "edge", "poly"):
            subobjs[subobj_type] = {}
            indexed_subobjs[subobj_type] = {}
            geoms[subobj_type] = {"pickable": None, "sel_state": None}

        geoms["normal"] = {"pickable": None, "sel_state": None}
        del geoms["poly"]["sel_state"]
        geoms["poly"]["selected"] = None
        geoms["poly"]["unselected"] = None
        self.toplevel_geom = None
        self._toplvl_node = None

        self._tmp_geom_pickable = None
        self._tmp_geom_sel_state = None
        self._tmp_row_indices = {}

    def __del__(self):

        Notifiers.geom.debug('GeomDataObject garbage-collected.')

    def cancel_creation(self):

        Notifiers.geom.debug(f'GeomDataObject "{self.id}" creation cancelled.')

        if self.origin:
            self.origin.detach_node()

        self.__dict__.clear()

    def destroy(self, unregister=True):

        Notifiers.geom.debug(f'About to destroy GeomDataObject "{self.id}"...')

        if unregister:
            self.unregister()

        self.origin.detach_node()

        Notifiers.geom.debug(f'GeomDataObject "{self.id}" destroyed.')
        self.__dict__.clear()
        self.origin = None

    def register(self, restore=True, locally=False):

        subobjs = self._subobjs_to_reg if self._subobjs_to_reg else self._subobjs

        for subobj_type in subobjs:

            Mgr.do(f"register_{subobj_type}_objs", iter(subobjs[subobj_type].values()), restore)

            if locally:
                self._subobjs[subobj_type].update(subobjs[subobj_type])

        self._subobjs_to_reg = None

    def unregister(self, locally=False):

        subobjs = self._subobjs_to_unreg if self._subobjs_to_unreg else self._subobjs

        for subobj_type in subobjs:

            Mgr.do(f"unregister_{subobj_type}_objs", iter(subobjs[subobj_type].values()))

            if locally:

                registered_subobjs = self._subobjs[subobj_type]

                for subobj_id in subobjs[subobj_type]:
                    del registered_subobjs[subobj_id]

        self._subobjs_to_unreg = None

    def register_locally(self, subobjs_to_reg=None):

        subobjs = subobjs_to_reg if subobjs_to_reg else self._subobjs

        for subobj_type in subobjs:
            self._subobjs[subobj_type].update(subobjs[subobj_type])

    def unregister_locally(self, subobjs_to_unreg=None):

        subobjs = subobjs_to_unreg if subobjs_to_unreg else self._subobjs

        for subobj_type in subobjs:

            registered_subobjs = self._subobjs[subobj_type]

            for subobj_id in subobjs[subobj_type]:
                del registered_subobjs[subobj_id]

    def get_subobjects(self, subobj_type):

        return self._subobjs[subobj_type]

    def get_subobject(self, subobj_type, subobj_id):

        return self._subobjs[subobj_type].get(subobj_id)

    def get_indexed_subobjects(self, subobj_type):

        return self._indexed_subobjs[subobj_type]

    def process_geom_data(self, geom_data, gradual=False):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        ordered_polys = self.ordered_polys
        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        verts_by_pos_ind = {}

        if gradual:
            poly_count = 0

        for poly_data in geom_data:

            vert_ids_by_data = {}

            poly_verts = []
            poly_edges = []
            poly_tris = []

            for vert_data in poly_data["verts"]:

                pos = vert_data["pos"]
                vertex = Mgr.do("create_vert", self, pos)
                vertex.normal = vert_data["normal"]
                vertex.set_uvs(vert_data["uvs"])

                if "color" in vert_data:
                    vertex.color = vert_data["color"]

                vert_id = vertex.id
                verts[vert_id] = vertex
                vert_ids_by_data[id(vert_data)] = vert_id
                pos_ind = vert_data["pos_ind"]
                verts_by_pos_ind.setdefault(pos_ind, []).append(vertex)
                poly_verts.append(vertex)

            for tri_data in poly_data["tris"]:
                tri = tuple(vert_ids_by_data[id(v_data)] for v_data in tri_data)
                poly_tris.append(tri)

            poly_edge_verts = poly_verts[:]
            poly_edge_verts.append(poly_edge_verts[0])

            for i in range(len(poly_verts)):
                vert1 = poly_edge_verts[i]
                vert2 = poly_edge_verts[i+1]
                edge_vert_ids = (vert1.id, vert2.id)
                edge = Mgr.do("create_edge", self, edge_vert_ids)
                edges[edge.id] = edge
                poly_edges.append(edge)

            for i, vert in enumerate(poly_verts):
                vert.add_edge_id(poly_edges[i-1].id)
                vert.add_edge_id(poly_edges[i].id)

            polygon = Mgr.do("create_poly", self, poly_tris, poly_edges, poly_verts)
            polygon.update_normal()
            ordered_polys.append(polygon)
            poly_id = polygon.id
            polys[poly_id] = polygon

            if gradual:

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

        if gradual:
            vert_count = 0

        for vert_list in verts_by_pos_ind.values():

            merged_vert = Mgr.do("create_merged_vert", self)
            merged_vert.extend(v.id for v in vert_list)
            merged_verts.update({v.id: merged_vert for v in vert_list})

            if gradual:

                vert_count += 1

                if vert_count == 20:
                    yield
                    vert_count = 0

        for edge_id, edge in edges.items():
            if edge_id not in merged_edges:
                mv1, mv2 = (verts[v_id].merged_vertex for v_id in edge)
                edge_ids1 = {e_id for v_id in mv1 for e_id in verts[v_id].edge_ids}
                edge_ids2 = {e_id for v_id in mv2 for e_id in verts[v_id].edge_ids}
                edge_ids = edge_ids1 & edge_ids2
                merged_edge = Mgr.do("create_merged_edge", self)
                merged_edge.extend(edge_ids)
                merged_edges.update({e_id: merged_edge for e_id in edge_ids})

        yield

    def create_geometry(self, obj_type="", gradual=False, restore=False):

        if restore:
            origin = self.origin
        else:
            node_name = f"{obj_type}_geom_origin"
            origin = NodePath(node_name)
            self.origin = origin

        origin.node().final = True
        origin.hide()

        subobjs = self._subobjs
        verts = subobjs["vert"]
        locked_normals = self.locked_normals
        self._data_row_count = count = len(verts)
        tri_vert_count = sum([len(poly) for poly in self.ordered_polys])

        sel_data = self._poly_selection_data["unselected"]

        vertex_format_basic = Mgr.get("vertex_format_basic")
        vertex_format_picking = Mgr.get("vertex_format_picking")
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
        vertex_data_poly_picking = GeomVertexData("poly_picking_data", vertex_format_picking, Geom.UH_dynamic)
        vertex_data_poly_picking.reserve_num_rows(count)
        vertex_data_poly_picking.set_num_rows(count)
        self._vertex_data["poly_picking"] = vertex_data_poly_picking

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.set_index_type(Geom.NT_uint32)
        points_prim.reserve_num_vertices(count)
        points_prim.add_next_vertices(count)
        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.set_index_type(Geom.NT_uint32)
        lines_prim.reserve_num_vertices(count * 2)
        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.set_index_type(Geom.NT_uint32)
        tris_prim.reserve_num_vertices(tri_vert_count)

        if not restore:
            pos_writer = GeomVertexWriter(vertex_data_poly, "vertex")
            normal_writer = GeomVertexWriter(vertex_data_poly, "normal")

        row_index_offset = 0

        if gradual:
            poly_count = 0

        for poly in self.ordered_polys:

            row_index = 0

            for vert in poly.vertices:

                vert.offset_row_index(row_index_offset)

                if vert.has_locked_normal():
                    locked_normals.add(vert.id)

                if not restore:
                    pos_writer.add_data3(vert.get_pos())
                    normal_writer.add_data3(vert.normal)
                    vert.row_index = row_index
                    row_index += 1

            for vert_ids in poly:
                tris_prim.add_vertices(*[verts[v_id].row_index for v_id in vert_ids])

            for edge in poly.edges:
                row1, row2 = (verts[v_id].row_index for v_id in edge)
                lines_prim.add_vertices(row1, row2 + count)

            row_index_offset += poly.vertex_count

            sel_data.extend(poly)

            if gradual:

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

        pos_array_poly = vertex_data_poly.get_array(0)
        vertex_data_vert.set_array(0, pos_array_poly)
        vertex_data_poly_picking.set_array(0, pos_array_poly)

        size = pos_array_poly.data_size_bytes
        pos_array_edge = GeomVertexArrayData(pos_array_poly.array_format, pos_array_poly.usage_hint)
        pos_array_edge.unclean_set_num_rows(pos_array_poly.get_num_rows() * 2)

        from_view = memoryview(pos_array_poly).cast("B")
        to_view = memoryview(pos_array_edge).cast("B")
        to_view[:size] = from_view
        to_view[size:] = from_view

        vertex_data_edge.set_array(0, pos_array_edge)

        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        all_masks = render_mask | picking_mask

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

        vertex_data_vert_picking = GeomVertexData("vert_picking_data",
            vertex_format_picking, Geom.UH_dynamic)
        vertex_data_vert_picking.copy_from(vertex_data_vert, True)
        points_geom = Geom(vertex_data_vert_picking)
        points_geom.add_primitive(points_prim)
        geom_node = GeomNode("vert_picking_geom")
        geom_node.add_geom(points_geom)
        vert_picking_geom = origin.attach_new_node(geom_node)
        vert_picking_geom.hide(all_masks)
        geoms["vert"]["pickable"] = vert_picking_geom

        new_data = vertex_data_vert.set_color(sel_colors["vert"]["unselected"])
        vertex_data_vert.set_array(1, new_data.get_array(1))
        points_geom = Geom(vertex_data_vert)
        points_geom.add_primitive(GeomPoints(points_prim))
        geom_node = GeomNode("vert_sel_state_geom")
        geom_node.add_geom(points_geom)
        vert_sel_state_geom = origin.attach_new_node(geom_node)
        vert_sel_state_geom.set_state(vert_state)
        vert_sel_state_geom.hide(all_masks)
        geoms["vert"]["sel_state"] = vert_sel_state_geom

        vertex_data_edge_picking = GeomVertexData("edge_picking_data",
            vertex_format_picking, Geom.UH_dynamic)
        vertex_data_edge_picking.copy_from(vertex_data_edge, True)
        lines_geom = Geom(vertex_data_edge_picking)
        lines_geom.add_primitive(lines_prim)
        geom_node = GeomNode("edge_picking_geom")
        geom_node.add_geom(lines_geom)
        edge_picking_geom = origin.attach_new_node(geom_node)
        edge_picking_geom.set_state(edge_state)
        edge_picking_geom.hide(all_masks)
        edge_picking_geom.set_color(self.toplevel_obj.get_color())
        geoms["edge"]["pickable"] = edge_picking_geom

        new_data = vertex_data_edge.set_color(sel_colors["edge"]["unselected"])
        vertex_data_edge.set_array(1, new_data.get_array(1))
        lines_geom = Geom(vertex_data_edge)
        lines_geom.add_primitive(GeomLines(lines_prim))
        geom_node = GeomNode("edge_sel_state_geom")
        geom_node.add_geom(lines_geom)
        edge_sel_state_geom = origin.attach_new_node(geom_node)
        edge_sel_state_geom.set_state(edge_state)
        edge_sel_state_geom.hide(all_masks)
        geoms["edge"]["sel_state"] = edge_sel_state_geom

        tris_prim.make_indexed()
        vertices = tris_prim.get_vertices()
        vertex_data_top = GeomVertexData(vertex_data_poly)
        tris_geom = Geom(vertex_data_top)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("toplevel_geom")
        geom_node.add_geom(tris_geom)
        self._toplvl_node = geom_node
        toplvl_geom = origin.attach_new_node(geom_node)
        toplvl_geom.hide(picking_mask)
        self.toplevel_geom = toplvl_geom
        geoms["top"] = toplvl_geom
        origin.node().set_bounds(geom_node.get_bounds())

        # create the geom with the polygon picking colors
        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.set_index_type(Geom.NT_uint32)
        tris_prim.reserve_num_vertices(3)
        tris_prim.set_vertices(GeomVertexArrayData(vertices))
        tris_geom = Geom(vertex_data_poly_picking)
        tris_geom.add_primitive(tris_prim)
        geom_node = GeomNode("poly_picking_geom")
        geom_node.add_geom(tris_geom)
        poly_picking_geom = origin.attach_new_node(geom_node)
        poly_picking_geom.hide(render_mask)
        geoms["poly"]["pickable"] = poly_picking_geom

        tris_prim = GeomTriangles(Geom.UH_static)
        tris_prim.set_index_type(Geom.NT_uint32)
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
        tris_prim.set_index_type(Geom.NT_uint32)
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

        vertex_data_normal = GeomVertexData("normal_data",
            Mgr.get("vertex_format_normal"), Geom.UH_dynamic)
        vertex_data_normal.copy_from(vertex_data_top, True)
        vertex_data_normal_picking = GeomVertexData("normal_picking_data",
            Mgr.get("vertex_format_normal_picking"), Geom.UH_dynamic)
        vertex_data_normal_picking.copy_from(vertex_data_normal, True)
        points_geom = vert_picking_geom.node().get_geom(0)
        geom = Geom(vertex_data_normal_picking)
        geom.add_primitive(GeomPoints(points_geom.get_primitive(0)))
        geom_node = GeomNode("normal_picking_geom")
        geom_node.add_geom(geom)
        geom_node.set_bounds(OmniBoundingVolume())
        geom_node.final = True
        normal_picking_geom = origin.attach_new_node(geom_node)
        normal_picking_geom.set_shader_input("normal_length", 1.)
        normal_picking_geom.hide(all_masks)
        geoms["normal"]["pickable"] = normal_picking_geom

        new_data = vertex_data_normal.set_color(sel_colors["normal"]["unselected"])
        vertex_data_normal.set_array(1, new_data.get_array(1))
        geom = Geom(vertex_data_normal)
        geom.add_primitive(GeomPoints(points_geom.get_primitive(0)))
        geom_node = GeomNode("normal_sel_state_geom")
        geom_node.add_geom(geom)
        geom_node.set_bounds(OmniBoundingVolume())
        geom_node.final = True
        normal_sel_state_geom = origin.attach_new_node(geom_node)
        normal_sel_state_geom.set_state(normal_state)
        normal_sel_state_geom.set_shader_input("normal_length", 1.)
        normal_sel_state_geom.hide(all_masks)
        geoms["normal"]["sel_state"] = normal_sel_state_geom

        model = self.toplevel_obj
        self.update_selection_state(model.is_selected())

        render_mode = GD["render_mode"]

        if "shaded" in render_mode:
            toplvl_geom.show(render_mask)
        else:
            toplvl_geom.hide(render_mask)

        if "wire" in render_mode:
            edge_sel_state_geom.show(render_mask)
        else:
            edge_sel_state_geom.hide(render_mask)

        if render_mode == "wire":
            edge_picking_geom.show(picking_mask)

        Mgr.notify("pickable_geom_altered", self.toplevel_obj)

        Notifiers.geom.debug('+++++++++++ Geometry created +++++++++++++++')

    def finalize_geometry(self):

        self.init_picking_colors()
        self.init_uvs()
        self.origin.reparent_to(self.toplevel_obj.origin)
        self.origin.show()

    @property
    def vertex_coords(self):

        verts = self._subobjs["vert"]

        return {vert_id: vert.get_pos() for vert_id, vert in verts.items()}

    @vertex_coords.setter
    def vertex_coords(self, coords):

        verts = self._subobjs["vert"]
        node = self._toplvl_node
        vertex_data_top = node.modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")

        for vert_id, pos in coords.items():
            row = verts[vert_id].row_index
            pos_writer.set_row(row)
            pos_writer.set_data3(pos)

    def bake_texture(self, texture):

        geom_copy = self.toplevel_geom.copy_to(GD.world)
        geom_copy.detach_node()
        vertex_data_copy = geom_copy.node().modify_geom(0).get_vertex_data()
        vertex_data_copy = vertex_data_copy.set_color((1., 1., 1., 1.))
        geom_copy.node().modify_geom(0).set_vertex_data(vertex_data_copy)
        geom_copy.set_texture(TextureStage.default, texture)
        geom_copy.flatten_light()
        geom_copy.apply_texture_colors()
        vertex_data_copy = geom_copy.node().modify_geom(0).modify_vertex_data()
        index = vertex_data_copy.format.get_array_with("color")
        array = vertex_data_copy.modify_array(index)
        self._vertex_data["poly"].set_array(1, array)
        vertex_data = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data.set_array(1, GeomVertexArrayData(array))

    def update_vertex_colors(self):

        material = self.toplevel_obj.get_material()

        if material:

            vert_color_map = material.get_tex_map("vertex color")
            texture = vert_color_map.get_texture()

            if vert_color_map.active and texture:
                self.bake_texture(texture)

    def clear_vertex_colors(self):

        vertex_data_copy = self._vertex_data["poly"].set_color((1., 1., 1., 1.))
        array = vertex_data_copy.get_array(1)
        self._vertex_data["poly"].set_array(1, GeomVertexArrayData(array))
        vertex_data = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data.set_array(1, GeomVertexArrayData(array))

    def set_initial_vertex_colors(self):

        vertex_data_copy = GeomVertexData(self._vertex_data["poly"])
        col_writer = GeomVertexWriter(vertex_data_copy, "color")

        for vert in self._subobjs["vert"].values():
            row = vert.row_index
            col_writer.set_row(row)
            col_writer.set_data4(vert.color)

        array = vertex_data_copy.get_array(1)
        self._vertex_data["poly"].set_array(1, GeomVertexArrayData(array))
        vertex_data = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data.set_array(1, GeomVertexArrayData(array))

    def init_picking_colors(self):

        indexed_subobjs = self._indexed_subobjs
        indexed_verts = indexed_subobjs["vert"]
        indexed_edges = indexed_subobjs["edge"]
        indexed_polys = indexed_subobjs["poly"]
        pickable_id_vert = PickableTypes.get_id("vert")
        pickable_id_edge = PickableTypes.get_id("edge")
        pickable_id_poly = PickableTypes.get_id("poly")
        vertex_data = self._geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        col_writer_vert = GeomVertexWriter(vertex_data, "color")
        ind_writer_vert = GeomVertexWriter(vertex_data, "index")
        vertex_data = self._geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        col_writer_edge = GeomVertexWriter(vertex_data, "color")
        ind_writer_edge = GeomVertexWriter(vertex_data, "index")
        vertex_data = self._vertex_data["poly_picking"]
        col_writer_poly = GeomVertexWriter(vertex_data, "color")
        ind_writer_poly = GeomVertexWriter(vertex_data, "index")

        vert_index = 0
        edge_index = 0
        poly_index = 0

        for poly in self.ordered_polys:

            picking_color = get_color_vec(poly.picking_color_id, pickable_id_poly)
            verts = poly.vertices

            for i in range(len(verts)):
                col_writer_poly.add_data4(picking_color)
                ind_writer_poly.add_data1i(poly_index)

            for vert in verts:
                row = vert.row_index
                picking_color = get_color_vec(vert.picking_color_id, pickable_id_vert)
                col_writer_vert.set_row(row)
                col_writer_vert.set_data4(picking_color)
                ind_writer_vert.set_row(row)
                ind_writer_vert.set_data1i(vert_index)
                indexed_verts[vert_index] = vert
                vert_index += 1

            indexed_polys[poly_index] = poly
            poly_index += 1

        vertex_data = self._geoms["vert"]["pickable"].node().get_geom(0).get_vertex_data()
        col_array = vertex_data.get_array(1)
        vertex_data = self._geoms["normal"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(1, col_array)

        vert_subobjs = self._subobjs["vert"]
        edge_subobjs = self._subobjs["edge"]
        picking_colors = {}
        indices = {}
        count = self._data_row_count

        for edge in edge_subobjs.values():
            picking_color = get_color_vec(edge.picking_color_id, pickable_id_edge)
            row_index = vert_subobjs[edge[0]].row_index
            picking_colors[row_index] = picking_color
            indices[row_index] = edge_index
            row_index = vert_subobjs[edge[1]].row_index + count
            picking_colors[row_index] = picking_color
            indices[row_index] = edge_index
            indexed_edges[edge_index] = edge
            edge_index += 1

        for row_index in sorted(picking_colors):
            picking_color = picking_colors[row_index]
            col_writer_edge.add_data4(picking_color)
            index = indices[row_index]
            ind_writer_edge.add_data1i(index)

    def update_subobject_indices(self):

        # Update the indices used for region-selection.

        indexed_subobjs = self._indexed_subobjs
        indexed_verts = indexed_subobjs["vert"]
        indexed_edges = indexed_subobjs["edge"]
        indexed_polys = indexed_subobjs["poly"]
        indexed_verts.clear()
        indexed_edges.clear()
        indexed_polys.clear()

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]

        geoms = self._geoms
        vertex_data_vert = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_edge = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_normal = geoms["normal"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_poly_picking = self._vertex_data["poly_picking"]
        ind_writer_vert = GeomVertexWriter(vertex_data_vert, "index")
        ind_writer_edge = GeomVertexWriter(vertex_data_edge, "index")
        ind_writer_poly = GeomVertexWriter(vertex_data_poly_picking, "index")
        vert_index = 0
        edge_index = 0
        poly_index = 0

        for vert in verts.values():
            row = vert.row_index
            ind_writer_vert.set_row(row)
            ind_writer_vert.set_data1i(vert_index)
            indexed_verts[vert_index] = vert
            vert_index += 1

        for edge in edges.values():

            for row in edge.row_indices:
                ind_writer_edge.set_row(row)
                ind_writer_edge.set_data1i(edge_index)

            indexed_edges[edge_index] = edge
            edge_index += 1

        for poly in polys.values():

            for row in poly.row_indices:
                ind_writer_poly.set_row(row)
                ind_writer_poly.set_data1i(poly_index)

            indexed_polys[poly_index] = poly
            poly_index += 1

        array = vertex_data_vert.get_array(1)
        vertex_data_normal.set_array(1, GeomVertexArrayData(array))

    def update_tangent_space(self, tangent_flip, bitangent_flip, poly_ids=None):

        vertex_data = GeomVertexData(self._vertex_data["poly"])
        tan_writer = GeomVertexWriter(vertex_data, "tangent")
        bitan_writer = GeomVertexWriter(vertex_data, "binormal")
        polys = self._subobjs["poly"]

        for poly_id in (polys if poly_ids is None else poly_ids):

            poly = polys[poly_id]
            poly.update_tangent_space(tangent_flip, bitangent_flip)

            for vert in poly.vertices:
                row = vert.row_index
                tan_writer.set_row(row)
                bitan_writer.set_row(row)
                tangent, bitangent = vert.tangent_space
                tan_writer.set_data3(tangent)
                bitan_writer.set_data3(bitangent)

        array = vertex_data.get_array(3)
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_array(3, GeomVertexArrayData(array))
        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data_top.set_array(3, GeomVertexArrayData(array))

        self.is_tangent_space_initialized = True

    def init_tangent_space(self):

        if not self.is_tangent_space_initialized:
            tangent_flip, bitangent_flip = self.toplevel_obj.get_tangent_space_flip()
            self.update_tangent_space(tangent_flip, bitangent_flip)

    def set_wireframe_color(self, color):

        self._geoms["edge"]["sel_state"].set_color(color)

    def update_selection_state(self, is_selected=True):

        geoms = self._geoms
        picking_mask = Mgr.get("picking_mask")
        render_mode = GD["render_mode"]

        if is_selected:

            if render_mode == "wire":
                geoms["poly"]["pickable"].show(picking_mask)
                geoms["edge"]["pickable"].hide(picking_mask)

            self.set_wireframe_color((1., 1., 1., 1.))

        else:

            if render_mode == "wire":
                geoms["poly"]["pickable"].hide(picking_mask)
                geoms["edge"]["pickable"].show(picking_mask)

            self.set_wireframe_color(self.toplevel_obj.get_color())

    def update_render_mode(self, is_selected):

        render_mode = GD["render_mode"]
        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        geoms = self._geoms

        if is_selected:

            obj_lvl = GD["active_obj_level"]

        else:

            if render_mode == "wire":
                geoms["poly"]["pickable"].hide(picking_mask)
                geoms["edge"]["pickable"].show(picking_mask)
            else:
                geoms["poly"]["pickable"].show(picking_mask)
                geoms["edge"]["pickable"].hide(picking_mask)

            obj_lvl = "top"

        if "wire" in render_mode or obj_lvl == "edge":
            geoms["edge"]["sel_state"].show(render_mask)
        else:
            geoms["edge"]["sel_state"].hide(render_mask)

        if obj_lvl == "edge":
            geoms["edge"]["sel_state"].set_color_off()
        elif is_selected:
            geoms["edge"]["sel_state"].set_color((1., 1., 1., 1.))
        else:
            geoms["edge"]["sel_state"].set_color(self.toplevel_obj.get_color())

        if "shaded" in render_mode:
            if obj_lvl == "poly" or (obj_lvl == "top" and self._has_poly_tex_proj):
                geoms["top"].hide(render_mask)
                geoms["poly"]["unselected"].show(render_mask)
            else:
                geoms["top"].show(render_mask)
                geoms["poly"]["unselected"].hide(render_mask)
        else:
            geoms["top"].hide(render_mask)
            geoms["poly"]["unselected"].hide(render_mask)

        if obj_lvl in ("vert", "edge", "normal"):
            self.init_subobj_picking(obj_lvl)

    def show_top_level(self):

        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        geoms = self._geoms

        for lvl in ("vert", "edge", "normal"):
            geoms[lvl]["pickable"].hide(picking_mask)
            geoms[lvl]["sel_state"].hide(render_mask)

        if GD["subobj_edit_options"]["pick_via_poly"]:
            self.restore_selection_backup("poly")

        self.set_normal_shader(False)
        geoms["poly"]["pickable"].show(picking_mask)

        if self._has_poly_tex_proj:
            geoms["poly"]["selected"].show(render_mask)
            geoms["poly"]["unselected"].show(render_mask)
        else:
            geoms["poly"]["selected"].hide(render_mask)
            geoms["poly"]["unselected"].hide(render_mask)

        self.update_render_mode(self.toplevel_obj.is_selected())

    def show_subobj_level(self, subobj_lvl):

        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        all_masks = render_mask | picking_mask

        geoms = self._geoms

        if subobj_lvl == "poly":

            geoms["poly"]["pickable"].show_through(picking_mask)
            geoms["poly"]["selected"].show(render_mask)
            geoms["poly"]["selected"].set_state(Mgr.get("poly_selection_state"))
            geoms["poly"]["unselected"].show(render_mask)

            for lvl in ("vert", "edge", "normal"):
                geoms[lvl]["pickable"].hide(all_masks)
                geoms[lvl]["sel_state"].hide(all_masks)

        else:

            geoms["poly"]["pickable"].show(picking_mask)
            geoms["poly"]["selected"].hide(render_mask)
            geoms["poly"]["unselected"].hide(render_mask)

            other_lvls = ["vert", "edge", "normal"]
            other_lvls.remove(subobj_lvl)
            geoms[subobj_lvl]["pickable"].show_through(picking_mask)
            geoms[subobj_lvl]["sel_state"].show(render_mask)

            for other_lvl in other_lvls:
                geoms[other_lvl]["pickable"].hide(all_masks)
                geoms[other_lvl]["sel_state"].hide(all_masks)

        if GD["subobj_edit_options"]["pick_via_poly"]:
            if subobj_lvl in ("vert", "edge", "normal"):
                self.create_selection_backup("poly")
            else:
                self.restore_selection_backup("poly")

        if subobj_lvl == "normal":
            self.set_normal_shader()
        else:
            self.set_normal_shader(False)

        self.update_render_mode(self.toplevel_obj.is_selected())

    def set_pickable(self, pickable=True):

        geoms = self._geoms
        active_obj_lvl = GD["active_obj_level"]
        picking_mask = Mgr.get("picking_mask")

        if pickable:

            for obj_lvl in ("vert", "edge", "normal", "poly"):
                if obj_lvl == active_obj_lvl:
                    geoms[obj_lvl]["pickable"].show_through(picking_mask)

            self.update_render_mode(True)

        else:

            for obj_lvl in ("vert", "edge", "normal", "poly"):
                geoms[obj_lvl]["pickable"].hide(picking_mask)

    def get_pickable_vertex_data(self, subobj_lvl):

        if subobj_lvl == "poly":
            return self._vertex_data["poly_picking"]

        return self._geoms[subobj_lvl]["pickable"].node().modify_geom(0).modify_vertex_data()

    def make_polys_pickable(self, pickable=True):

        if GD["active_obj_level"] == "poly":
            return

        picking_mask = Mgr.get("picking_mask")
        geoms = self._geoms

        if pickable:
            geoms["poly"]["pickable"].show_through(picking_mask)
        else:
            geoms["poly"]["pickable"].hide(picking_mask)

    def make_subobjs_pickable(self, subobj_lvl, mask_index, pickable=True):

        picking_mask = Mgr.get("picking_mask", mask_index)
        geoms = self._geoms

        if pickable:
            if geoms[subobj_lvl]["pickable"]:
                geoms[subobj_lvl]["pickable"].show_through(picking_mask)
        else:
            if geoms[subobj_lvl]["pickable"]:
                geoms[subobj_lvl]["pickable"].hide(picking_mask)

    def init_subobj_picking(self, subobj_lvl):

        geoms = self._geoms

        if GD["subobj_edit_options"]["pick_via_poly"]:

            self.create_selection_backup("poly")
            geoms["poly"]["selected"].set_state(Mgr.get("temp_poly_selection_state"))
            self.prepare_subobj_picking_via_poly(subobj_lvl)

        else:

            render_mask = Mgr.get("render_mask")
            picking_mask = Mgr.get("picking_mask")
            geoms[subobj_lvl]["pickable"].show_through(picking_mask)
            geoms["poly"]["pickable"].show(picking_mask)
            geoms["poly"]["selected"].hide(render_mask)

            if not geoms["poly"]["unselected"].is_hidden(render_mask):
                geoms["poly"]["unselected"].hide(render_mask)
                geoms["top"].show(render_mask)

    def prepare_subobj_picking_via_poly(self, subobj_type):

        self.clear_selection("poly", False)

        # clean up temporary vertex data
        if self._tmp_geom_pickable:

            self._tmp_geom_pickable.detach_node()
            self._tmp_geom_pickable = None
            self._tmp_geom_sel_state.detach_node()
            self._tmp_geom_sel_state = None
            self._tmp_row_indices = {}

            if GD["subobj_edit_options"]["pick_by_aiming"]:
                aux_picking_root = Mgr.get("aux_picking_root")
                tmp_geom_pickable = aux_picking_root.find("**/tmp_geom_pickable")
                tmp_geom_pickable.detach_node()
                aux_picking_cam = Mgr.get("aux_picking_cam")
                aux_picking_cam.active = False
                Mgr.do("end_drawing_aux_picking_viz")

        # Allow picking polys instead of the subobjects of the given type;
        # as soon as a poly is clicked, its subobjects (of the given type) become
        # pickable instead of polys.

        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        geoms = self._geoms
        geoms[subobj_type]["pickable"].hide(picking_mask)
        geoms["poly"]["pickable"].show_through(picking_mask)
        geoms["poly"]["selected"].show(render_mask)

        if not geoms["top"].is_hidden(render_mask):
            geoms["top"].hide(render_mask)
            geoms["poly"]["unselected"].show(render_mask)

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
        col_writer.set_data4(colors["selected"])

        if subobj_lvl == "edge":
            col_writer.set_data4(colors["selected"])

        return True

    def get_toplevel_object(self, get_group=False):

        return self.owner.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def get_merged_vertex(self, vert_id):

        return self.merged_verts.get(vert_id)

    def get_merged_edge(self, edge_id):

        return self.merged_edges.get(edge_id)

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
        GD.set_default("subobj_edit_options", subobj_edit_options, copier)

        # Define GeomVertexArrayFormats for the various vertex attributes.

        pos_array = GeomVertexArrayFormat()
        pos_array.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)

        col_array = GeomVertexArrayFormat()
        col_array.add_column(InternalName.make("color"), 4, Geom.NT_uint8, Geom.C_color)

        colind_array = GeomVertexArrayFormat()
        colind_array.add_column(InternalName.make("color"), 4, Geom.NT_uint8, Geom.C_color)
        colind_array.add_column(InternalName.make("index"), 1, Geom.NT_int32, Geom.C_index)

        normal_array = GeomVertexArrayFormat()
        normal_array.add_column(InternalName.make("normal"), 3, Geom.NT_float32, Geom.C_normal)

        tan_array = GeomVertexArrayFormat()
        tan_array.add_column(InternalName.make("tangent"), 3, Geom.NT_float32, Geom.C_vector)
        tan_array.add_column(InternalName.make("binormal"), 3, Geom.NT_float32, Geom.C_vector)

        uv_arrays = []
        uv_array = GeomVertexArrayFormat()
        uv_array.add_column(InternalName.make("texcoord"), 2, Geom.NT_float32, Geom.C_texcoord)
        uv_arrays.append(uv_array)

        for i in range(1, 8):
            uv_array = GeomVertexArrayFormat()
            uv_array.add_column(InternalName.make(f"texcoord.{i}"), 2, Geom.NT_float32, Geom.C_texcoord)
            uv_arrays.append(uv_array)

        # Define a "basic" GeomVertexFormat that accommodates only position and color.

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(pos_array)
        vertex_format.add_array(col_array)
        vertex_format_basic = GeomVertexFormat.register_format(vertex_format)

        # Define a "picking" GeomVertexFormat that accommodates position, color and index,
        # for the purpose of picking vertices, edges and polygons.

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(pos_array)
        vertex_format.add_array(colind_array)
        vertex_format_picking = GeomVertexFormat.register_format(vertex_format)

        # Define a "full" GeomVertexFormat that accommodates position, color, normal, tangent and
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

        # Define a GeomVertexFormat that accommodates position, color, index and normal,
        # for the purpose of picking normals.

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(pos_array)
        vertex_format.add_array(colind_array)
        vertex_format.add_array(normal_array)
        vertex_format_normal_picking = GeomVertexFormat.register_format(vertex_format)

        Mgr.expose("vertex_format_basic", lambda: vertex_format_basic)
        Mgr.expose("vertex_format_picking", lambda: vertex_format_picking)
        Mgr.expose("vertex_format_full", lambda: vertex_format_full)
        Mgr.expose("vertex_format_normal", lambda: vertex_format_normal)
        Mgr.expose("vertex_format_normal_picking", lambda: vertex_format_normal_picking)

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

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("aux_picking_viz_data", vertex_format, Geom.UH_static)
        vertex_data.set_num_rows(2)
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(1)
        col_writer.set_data4(1., 1., 1., 0.)

        lines = GeomLines(Geom.UH_dynamic)
        lines.add_next_vertices(2)
        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        node.add_geom(lines_geom, state1)

        lines_geom = lines_geom.make_copy()
        vertex_data = lines_geom.modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(0)
        col_writer.set_data4(0., 0., 0., 1.)
        col_writer.set_data4(0., 0., 0., 0.)
        node.add_geom(lines_geom, state2)

        aux_picking_viz = NodePath(node)
        self._aux_picking_viz = aux_picking_viz
        Mgr.expose("aux_picking_viz", lambda: self._aux_picking_viz)

        # Create a dashed rubber band line.

        vertex_format = GeomVertexFormat.get_v3t2()
        vertex_data = GeomVertexData("dashed_line_data", vertex_format, Geom.UH_static)
        vertex_data.set_num_rows(2)

        lines = GeomLines(Geom.UH_dynamic)
        lines.add_next_vertices(2)
        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        node = GeomNode("dashed_line")
        node.add_geom(lines_geom)
        dashed_line = NodePath(node)
        dashed_line.set_bin("fixed", 100)
        dashed_line.set_depth_test(False)
        dashed_line.set_depth_write(False)
        tex = Mgr.load_tex(GFX_PATH + "marquee.png")
        dashed_line.set_texture(tex)
        self._dashed_line = dashed_line
        Mgr.expose("dashed_line", lambda: self._dashed_line)

        self._draw_start_pos = {"aux_picking_viz": Point3(), "rubber_band": Point3()}
        self._draw_plane = None

        Mgr.accept("start_drawing_aux_picking_viz", self.__start_drawing_aux_picking_viz)
        Mgr.accept("end_drawing_aux_picking_viz", self.__end_drawing_aux_picking_viz)
        Mgr.accept("start_drawing_rubber_band", self.__start_drawing_rubber_band)
        Mgr.accept("end_drawing_rubber_band", self.__end_drawing_rubber_band)
        Mgr.accept("set_dashed_line_start_pos", self.__set_dashed_line_start_pos)
        Mgr.accept("draw_dashed_line", self.__draw_dashed_line)

    def setup(self):

        if "picking_camera_ok" not in MainObjects.get_setup_results():
            return False

        picking_mask = Mgr.get("picking_mask")
        self._aux_picking_viz.hide(picking_mask)
        self._dashed_line.hide(picking_mask)

        return True

    def __start_drawing_line(self, line, world_start_pos=None):

        cam = GD.cam()
        cam_pos = cam.get_pos(GD.world)
        normal = GD.world.get_relative_vector(cam, Vec3.forward()).normalized()
        plane = Plane(normal, cam_pos + normal * 10.)
        point = Point3()

        if world_start_pos is None:

            if not GD.mouse_watcher.has_mouse():
                return

            screen_pos = GD.mouse_watcher.get_mouse()
            near_point = Point3()
            far_point = Point3()
            GD.cam.lens.extrude(screen_pos, near_point, far_point)
            rel_pt = lambda point: GD.world.get_relative_point(cam, point)
            plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))

        else:

            p = cam_pos if GD.cam.lens_type == "persp" else world_start_pos - normal * 100.
            plane.intersects_line(point, p, world_start_pos)

        line_node = line.node()

        for i in range(line_node.get_num_geoms()):
            vertex_data = line_node.modify_geom(i).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(0)
            pos_writer.set_data3(point)

        line.reparent_to(GD.world)
        line_type = "rubber_band" if line is self._dashed_line else "aux_picking_viz"
        self._draw_start_pos[line_type] = point
        self._draw_plane = plane

        task = self.__draw_rubber_band if line is self._dashed_line else self.__draw_aux_picking_viz
        task_name = "draw_rubber_band" if line is self._dashed_line else "draw_aux_picking_viz"
        Mgr.add_task(task, task_name, sort=3)

    def __start_drawing_aux_picking_viz(self):

        self.__start_drawing_line(self._aux_picking_viz)

    def __start_drawing_rubber_band(self, start_pos):

        self.__start_drawing_line(self._dashed_line, start_pos)

    def __set_dashed_line_start_pos(self, start_pos):

        cam = GD.cam()
        cam_pos = cam.get_pos(GD.world)
        normal = GD.world.get_relative_vector(cam, Vec3.forward()).normalized()
        plane = Plane(normal, cam_pos + normal * 10.)
        point = Point3()
        p = cam_pos if GD.cam.lens_type == "persp" else start_pos - normal * 100.
        plane.intersects_line(point, p, start_pos)
        self._draw_start_pos["rubber_band"] = point
        self._draw_plane = plane

        line_node = self._dashed_line.node()

        for i in range(line_node.get_num_geoms()):
            vertex_data = line_node.modify_geom(i).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(0)
            pos_writer.set_data3(point)

    def __draw_dashed_line(self, end_pos, end_pos_on_plane=False):

        start_point = self._draw_start_pos["rubber_band"]

        if end_pos_on_plane:
            end_point = end_pos
        elif not self._draw_plane:
            return
        else:
            cam_pos = GD.cam().get_pos(GD.world)
            normal = self._draw_plane.get_normal()
            p = cam_pos if GD.cam.lens_type == "persp" else end_pos - normal * 100.
            end_point = Point3()
            self._draw_plane.intersects_line(end_point, p, end_pos)

        line_node = self._dashed_line.node()

        for i in range(line_node.get_num_geoms()):
            vertex_data = line_node.modify_geom(i).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(1)
            pos_writer.set_data3(end_point)

        vp_data = GD["viewport"]
        w, h = vp_data["size_aux" if vp_data[2] == "main" else "size"]
        s = max(w, h) / 800.
        length = (end_point - start_point).length() * s * 5.

        if GD.cam.lens_type == "ortho":
            length /= 40. * GD.cam.zoom

        vertex_data = line_node.modify_geom(0).modify_vertex_data()
        uv_writer = GeomVertexWriter(vertex_data, "texcoord")
        uv_writer.set_row(1)
        uv_writer.set_data2(length, 1.)

    def __draw_line(self, line):

        if not GD.mouse_watcher.has_mouse():
            return

        screen_pos = GD.mouse_watcher.get_mouse()
        cam = GD.cam()
        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.world.get_relative_point(cam, point)
        point = Point3()
        self._draw_plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))

        if line is self._dashed_line:

            self.__draw_dashed_line(point, end_pos_on_plane=True)

        else:

            start_pos = self._draw_start_pos["aux_picking_viz"]
            point = start_pos + (point - start_pos) * 3.
            line_node = line.node()

            for i in range(line_node.get_num_geoms()):
                vertex_data = line_node.modify_geom(i).modify_vertex_data()
                pos_writer = GeomVertexWriter(vertex_data, "vertex")
                pos_writer.set_row(1)
                pos_writer.set_data3(point)

    def __draw_aux_picking_viz(self, task):

        self.__draw_line(self._aux_picking_viz)

        return task.cont

    def __draw_rubber_band(self, task):

        self.__draw_line(self._dashed_line)

        return task.cont

    def __end_drawing_aux_picking_viz(self):

        Mgr.remove_task("draw_aux_picking_viz")
        self._aux_picking_viz.detach_node()

    def __end_drawing_rubber_band(self):

        Mgr.remove_task("draw_rubber_band")
        self._dashed_line.detach_node()

    def __create_data(self, owner):

        return GeomDataObject(self.get_next_id(), owner)


MainObjects.add_class(GeomDataManager)
