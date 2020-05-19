from .. import *


class BamExporter:

    def __init__(self):

        self.data_formatter = VertexDataFormatter()

    def export(self, filename):

        self.__determine_objs_for_export()
        self.__set_initial_data(filename)
        self.__parse_data()
        self.root.write_bam_file(self.fullpath)
        self.root.detach_node()
        self.root = None

    def __determine_objs_for_export(self):

        self.objs = set(obj.root for obj in Mgr.get("selection_top"))

        if not self.objs:
            self.objs = set(obj.root for obj in Mgr.get("objects"))

    def __set_initial_data(self, filename):

        self.root = NodePath(ModelRoot(os.path.basename(filename)))
        self.fullpath = Filename.from_os_specific(filename)
        self.directory = Filename(self.fullpath.get_dirname())
        self.child_geom_nodes = {}
        self.child_collision_nodes = {}
        self.data = [(self.objs, self.root, None, None)]

    def __parse_data(self):

        while self.data:

            children, self.parent_node, self.geom_node, self.collision_node = self.data.pop()

            for child in children:
                self.__init_child_data(child)
                self.__parse_child_data()
                self.__add_data()

    def __add_data(self):

        if self.child_is_group:
            self.data.append((self.child.get_members(), self.node, self.child_geom_node,
                             self.child_collision_node))

        children = self.child.children

        if children:
            self.data.append((children, self.node, None, None))

    def __init_child_data(self, child):

        self.child = child
        self.child_geom_node = None
        self.child_collision_node = None
        self.child_is_group = self.child.type == "group"

    def __parse_child_data(self):

        if self.child.type == "model":
            self.__parse_model_data()
        else:
            self.__parse_helper_data()

    def __parse_model_data(self):   

        self.__set_model_geom_data()
        self.__set_model_node_data()
        self.__set_model_material()
        self.__set_model_transform()
        node = self.node.node()

        for key, val in self.child.tags.items():
            node.set_tag(key, val)

        self.__create_node()

    def __parse_helper_data(self):

        if self.child_is_group and self.child.get_member_types_id() == "model":
            self.child_geom_node = GeomNode(self.child.name)
            self.child_geom_nodes[self.child.name] = self.child_geom_node
            self.node = self.parent_node.attach_new_node(self.child_geom_node)
        elif self.child_is_group and self.child.get_member_types_id() == "collision":
            self.child_collision_node = CollisionNode(self.child.name)
            self.child_collision_nodes[self.child.name] = self.child_collision_node
            self.node = self.parent_node.attach_new_node(self.child_collision_node)
        else:
            self.node = self.parent_node.attach_new_node(self.child.name)

        self.node.set_transform(self.child.pivot.get_transform(self.child.parent_pivot))
        node = self.node.node()

        for key, val in self.child.tags.items():
            node.set_tag(key, val)

    def __create_node(self):

        if self.geom_node:
            self.__create_geom_node()
        elif self.collision_node:
            self.__create_collision_node()
        else:
            self.node.reparent_to(self.parent_node)

    def __create_geom_node(self):

        state = self.node.get_state()
        geom = self.node.node().modify_geom(0)
        mat = self.pivot.get_mat(self.child.parent_pivot)
        vertex_data = geom.modify_vertex_data()
        vertex_data.transform_vertices(mat)
        self.geom_node.add_geom(geom, state)
        self.node = self.parent_node

    def __create_collision_node(self):

        scale = self.pivot.get_scale()
        self.sx = scale[0]
        self.pivot.set_scale(self.sx)
        self.group_pivot = self.child.group.pivot
        coll_solid = self.__create_collision_solid(scale)
        self.__set_node_data(coll_solid, scale)

    def __set_node_data(self, coll_solid, scale):

        if coll_solid:
            self.collision_node.add_solid(coll_solid)

        self.pivot.set_scale(scale)
        self.node = self.parent_node

    def __create_collision_solid(self, scale):

        coll_solid = None

        if self.geom_type == "sphere":
            coll_solid = self.__create_sphere_collision_solid(coll_solid)
        elif self.geom_type == "cylinder":
            coll_solid = self.__create_cylinder_collision_solid(coll_solid)
        elif self.geom_type == "box":
            coll_solid = self.__create_box_collision_solid(coll_solid)
        elif self.geom_type == "plane":
            coll_solid = self.__create_plane_collision_solid(coll_solid)
        else:
            self.__process_geom(scale)

        return coll_solid

    def __process_geom(self, scale):

        self.pivot.set_scale(scale)

        if self.geom_type == "unlocked_geom":
            polys = iter(self.geom_data_obj.get_subobjects("poly").values())
            verts = self.geom_data_obj.get_subobjects("vert")
            epsilon = 1.e-005
            self.__process_polygons(polys, verts, epsilon)
        else:
            self.__process_locked_geom()

    def __process_locked_geom(self):

        mat = self.pivot.get_mat(self.group_pivot)
        geom = self.node.node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        vertex_data.transform_vertices(mat)
        pos_reader = GeomVertexReader(vertex_data, "vertex")
        index_list = geom.get_primitive(0).get_vertex_list()
        index_count = len(index_list)

        for indices in (index_list[i:i+3] for i in range(0, index_count, 3)):

            points = []

            for index in indices:
                pos_reader.set_row(index)
                points.append(pos_reader.get_data3())

            coll_poly = CollisionPolygon(*points)
            self.collision_node.add_solid(coll_poly)

    def __process_polygons(self, polys, verts, epsilon):

        for poly in polys:

            self.is_quad = False
            self.is_smaller_than_epsilon = False
            self.__process_quads(poly, verts, epsilon)

            if not self.is_smaller_than_epsilon:

                for tri_vert_ids in poly[1 if self.is_quad else 0:]:
                    tri_verts = (verts[v_id] for v_id in tri_vert_ids)
                    points = [v.get_pos(self.group_pivot) for v in tri_verts]
                    coll_poly = CollisionPolygon(*points)
                    self.collision_node.add_solid(coll_poly)

    def __process_quads(self, poly, verts, epsilon):

        if poly.vertex_count == 4:

            self.is_quad = True
            tri_vert_ids = poly[0]
            tri_verts = (verts[v_id] for v_id in tri_vert_ids)
            points = [v.get_pos(self.group_pivot) for v in tri_verts]

            poly_data = self.__check_tri_vert_id_membership(poly, verts, tri_vert_ids)
            point = poly_data[0]
            index = poly_data[1]

            if abs(Plane(*points).dist_to_plane(point)) < epsilon:
                points.insert(index, point)
                self.is_smaller_than_epsilon = True

            coll_poly = CollisionPolygon(*points)
            self.collision_node.add_solid(coll_poly)

    def __check_tri_vert_id_membership(self, poly, verts, tri_vert_ids):

        for i, v_id in enumerate(poly[1]):
            if v_id not in tri_vert_ids:
                point = verts[v_id].get_pos(self.group_pivot)
                preceding_v_id = poly[1][i - 1]
                index = tri_vert_ids.index(preceding_v_id) + 1
                return (point, index)

    def __create_inverted_box_planes(self, dimensions, center):

        size_x = dimensions[0]
        size_y = dimensions[1]
        size_z = dimensions[2]

        if self.geom_obj.has_inverted_geometry():

            x_vec = self.group_pivot.get_relative_vector(self.origin, Vec3.right() * size_x)
            y_vec = self.group_pivot.get_relative_vector(self.origin, Vec3.forward() * size_y)
            z_vec = self.group_pivot.get_relative_vector(self.origin, Vec3.up() * size_z)

            for vec in (x_vec, y_vec, z_vec):
                normal = vec.normalized()
                self.collision_node.add_solid(CollisionPlane(Plane(-normal, center + vec)))
                self.collision_node.add_solid(CollisionPlane(Plane(normal, center - vec)))

            return True

        else:

            return False

    def __create_sphere_collision_solid(self, coll_solid):

        center = self.origin.get_pos(self.group_pivot)
        radius = self.geom_obj.get_property("radius") * self.sx

        if self.geom_obj.has_inverted_geometry():
            coll_solid = CollisionInvSphere(center, radius)
        else:
            coll_solid = CollisionSphere(center, radius)

        return coll_solid

    def __create_cylinder_collision_solid(self, coll_solid):

        pos = self.origin.get_pos()
        height_vec = Vec3.up() * self.geom_obj.get_property("height")
        height_vec = self.pivot.get_relative_vector(self.origin, height_vec)
        point_a = self.group_pivot.get_relative_point(self.pivot, pos)
        point_b = self.group_pivot.get_relative_point(self.pivot, pos + height_vec)
        radius = self.geom_obj.get_property("radius") * self.sx
        coll_solid = CollisionCapsule(point_a, point_b, radius)

        return coll_solid

    def __create_box_collision_solid(self, coll_solid):

        pos = self.origin.get_pos(self.group_pivot)
        size_x = self.geom_obj.get_property("size_x") * .5
        size_y = self.geom_obj.get_property("size_y") * .5
        height = self.geom_obj.get_property("size_z") * .5
        size_z = abs(height)
        height_vec = self.group_pivot.get_relative_vector(self.origin, Vec3.up() * height)
        center = pos + height_vec
        dimensions = (size_x, size_y, size_z)

        if not self.__create_inverted_box_planes(dimensions, center):
            coll_solid = CollisionBox(center, size_x * self.sx, size_y * self.sx, size_z * self.sx)

        return coll_solid

    def __create_plane_collision_solid(self, coll_solid):

        normal = Vec3.down() if self.geom_obj.has_inverted_geometry() else Vec3.up()
        normal = self.group_pivot.get_relative_vector(self.origin, normal)
        point = self.origin.get_pos(self.group_pivot)
        coll_solid = CollisionPlane(Plane(normal, point))

        return coll_solid

    def __set_model_geom_data(self):

        self.geom_obj = self.child.geom_obj
        self.geom_type = self.child.geom_type
        self.geom_data_obj = None
        self.uv_set_names = self.geom_obj.get_uv_set_names()
        self.__check_geom_type()

    def __check_geom_type(self):

        if self.geom_type == "unlocked_geom":

            self.geom_data_obj = self.geom_obj.geom_data_obj
            self.node = Mgr.do("merge_duplicate_verts", self.geom_data_obj)

        else:

            self.node = NodePath(self.geom_obj.geom.node().make_copy())

            for key in self.node.get_tag_keys():
                self.node.clear_tag(key)

    def __set_model_node_data(self):

        masks = Mgr.get("render_mask") | Mgr.get("picking_masks")
        self.node.show(masks)
        self.origin = self.child.origin
        self.pivot = self.child.pivot
        self.node.name = self.child.name
        self.node.set_state(self.origin.get_state())
        tex_stages = self.node.find_all_texture_stages()
        self.data_formatter.update_format(self.node, self.uv_set_names, tex_stages)
        self.__create_texture_filenames(tex_stages)
        self.__check_parent()

    def __create_texture_filenames(self, tex_stages):

        for tex_stage in tex_stages:
            texture = self.node.get_texture(tex_stage).make_copy()
            filename = Filename(texture.get_fullpath())
            filename.make_relative_to(self.directory)
            texture.filename = filename
            texture.fullpath = filename
            filename = Filename(texture.get_alpha_fullpath())
            filename.make_relative_to(self.directory)
            texture.alpha_filename = filename
            texture.alpha_fullpath = filename
            self.node.set_texture(tex_stage, texture)

    def __check_parent(self):

        self.parent = self.child.parent

        if self.parent and self.parent.type != "model":
            self.parent = None

    def __set_model_material(self):

        material = self.child.get_material()
        parent_material = self.parent.get_material() if self.parent else None
        parent_origin = self.parent.origin if self.parent else None
        self.__check_material_equality(material, parent_material, parent_origin)

    def __set_model_transform(self):

        mat = self.origin.get_mat(self.pivot)
        vertex_data = self.node.node().modify_geom(0).modify_vertex_data()
        vertex_data.transform_vertices(mat)
        self.node.set_transform(self.pivot.get_transform(self.parent_node))

    def __check_material_equality(self, material, parent_material, parent_origin):

        if material and parent_material and material.equals(parent_material):
            self.node.set_state(RenderState.make_empty())
        else:
            self.__check_material_attributes(material, parent_material, parent_origin)

    def __check_material_attributes(self, material, parent_material, parent_origin):

        if material and not material.has_base_properties():
            self.node.clear_material()

        if not material:
            self.node.clear_color()

        if self.origin.get_transparency() == TransparencyAttrib.M_none:
            self.node.clear_transparency()
            self.node.clear_color_scale()

        if parent_material:
            self.__check_parent_attributes(parent_origin, parent_material)

    def __check_parent_attributes(self, parent_origin, parent_material):

        if parent_origin.has_color() and not self.node.has_color():
            state = self.node.get_state()
            attr = ColorAttrib.make_off()
            state = state.add_attrib(attr)
            self.node.set_state(state)

        if parent_origin.has_color_scale() and not self.node.has_color_scale():
            self.node.set_color_scale_off()

        if parent_origin.has_material() and not self.node.has_material():
            self.node.set_material_off()

        if parent_material.get_base_properties()["alpha"]["on"]:
            if not self.node.has_transparency():
                self.node.set_transparency(TransparencyAttrib.M_none)

        tex_stages = parent_origin.find_all_texture_stages()

        for tex_stage in tex_stages:
            if parent_origin.has_texture(tex_stage) and not self.node.has_texture(tex_stage):
                self.node.set_texture_off(tex_stage)


class VertexDataFormatter:

    def update_format(self, node, uv_set_names, tex_stages):

        self.__prepare_uv_array_formats(uv_set_names, tex_stages)
        self.__create_array_formats()

        for default_name, uv_name in zip(self.default_uv_names, uv_set_names):
            internal_name = self.__get_internal_uv_name(uv_name)
            self.__add_uv_column(internal_name)
            self.__update_texcoord_names(default_name, uv_name)

        new_vertex_data = self.__update_vertex_data_format(node, uv_set_names)
        node.node().modify_geom(0).set_vertex_data(new_vertex_data)

    def __prepare_uv_array_formats(self, uv_set_names, tex_stages):

        self.default_uv_names = ["", "1", "2", "3", "4", "5", "6", "7"]
        self.stages_by_uv_name = {}

        if uv_set_names != self.default_uv_names:
            for tex_stage in tex_stages:
                internal_name = tex_stage.texcoord_name
                uv_name = internal_name.name
                uv_name = "" if uv_name == "texcoord" else internal_name.basename
                self.stages_by_uv_name.setdefault(uv_name, []).append(tex_stage)

    def __create_array_formats(self):

        self.main_array = GeomVertexArrayFormat()
        self.main_array.add_column(InternalName.get_vertex(), 3, Geom.NT_float32, Geom.C_point)
        self.main_array.add_column(InternalName.get_color(), 1, Geom.NT_packed_dabc, Geom.C_color)
        self.main_array.add_column(InternalName.get_normal(), 3, Geom.NT_float32, Geom.C_normal)
        self.main_array.add_column(InternalName.get_tangent(), 3, Geom.NT_float32, Geom.C_vector)
        self.main_array.add_column(InternalName.get_binormal(), 3, Geom.NT_float32, Geom.C_vector)
        self.uv_arrays = []
        self.single_array_format = GeomVertexArrayFormat(self.main_array)

    def __get_internal_uv_name(self, uv_name):

        if uv_name == "":
            internal_name = InternalName.get_texcoord()
        else:
            internal_name = InternalName.get_texcoord_name(uv_name)

        return internal_name

    def __add_uv_column(self, internal_name):

        args = (internal_name, 2, Geom.NT_float32, Geom.C_texcoord)
        uv_array = GeomVertexArrayFormat()
        uv_array.add_column(*args)
        self.uv_arrays.append(uv_array)
        self.single_array_format.add_column(*args)

    def __update_texcoord_names(self, default_name, uv_name):

        if uv_name != default_name and default_name in self.stages_by_uv_name:
            for tex_stage in self.stages_by_uv_name[default_name]:
                tex_stage.set_texcoord_name(uv_name)

    def __update_vertex_uv_format(self, node, uv_set_names):

        vertex_data = node.node().modify_geom(0).modify_vertex_data()

        if uv_set_names != self.default_uv_names:

            vertex_format = GeomVertexFormat()
            vertex_format.add_array(self.main_array)

            for uv_array in self.uv_arrays:
                vertex_format.add_array(uv_array)

            vertex_format = GeomVertexFormat.register_format(vertex_format)
            new_vertex_data = vertex_data.convert_to(vertex_format)
            node.node().modify_geom(0).set_vertex_data(new_vertex_data)
            new_vertex_data = node.node().modify_geom(0).modify_vertex_data()

            for i in range(8):
                from_array = vertex_data.get_array(4 + i)
                from_view = memoryview(from_array).cast("B")
                to_array = new_vertex_data.modify_array(1 + i)
                to_view = memoryview(to_array).cast("B")
                to_view[:] = from_view

            vertex_data = new_vertex_data

        return vertex_data

    def __update_vertex_data_format(self, node, uv_set_names):

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(self.single_array_format)
        vertex_format = GeomVertexFormat.register_format(vertex_format)
        vertex_data = self.__update_vertex_uv_format(node, uv_set_names)
        new_vertex_data = vertex_data.convert_to(vertex_format)

        return new_vertex_data
