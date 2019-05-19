from ...base import *


class ExportBam:
  
    def __init__(self):
      
        self.vertices_merger = VerticesData()
        self.vertices_format_checker = VerticesFormat()

    def export_to_bam(self, filename):
      
        self.__determine_objs_for_bam_export()
        self.__set_initial_data(filename)
        self.__parse_data()
        self.root.write_bam_file(self.fullpath)
        self.root.remove_node()

    def __determine_objs_for_bam_export(self):
      
        self.objs = set(obj.get_root() for obj in Mgr.get("selection_top"))

        if not self.objs:
            self.objs = set(obj.get_root() for obj in Mgr.get("objects"))

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
                self.child = child
                self.__get_child_type()
                self.__check_child_type()
                self.__set_new_data()
    
    def __set_new_data(self):

        if self.child_is_group:
            self.data.append((self.child.get_members(), self.node, self.child_geom_node, self.child_collision_node))

        if self.child.get_children():
            self.data.append((self.child.get_children(), self.node, None, None))
    
    def __get_child_type(self):
      
        self.child_geom_node = None
        self.child_collision_node = None
        self.child_is_group = self.child.get_type() == "group"
    
    def __check_child_type(self):
      
        if self.child.get_type() == "model":
            self.__set_model_data()

        else:
            self.__parse_group_data()
            
    def __set_model_data(self):   
      
        self.__set_geom_model_data()
        self.__set_node_model_data()
        self.__set_node_material()
        self.__object_types_export()
            
    def __parse_group_data(self):
      
        if self.child_is_group and self.child.get_member_types_id() == "model":
            self.child_geom_node = GeomNode(self.child.get_name())
            self.child_geom_nodes[self.child.get_name()] = self.child_geom_node
            self.node = self.parent_node.attach_new_node(self.child_geom_node)
            
        elif self.child_is_group and self.child.get_member_types_id() == "collision":
            self.child_collision_node = CollisionNode(self.child.get_name())
            self.child_collision_nodes[self.child.get_name()] = self.child_collision_node
            self.node = self.parent_node.attach_new_node(self.child_collision_node)
            
        else:
            self.node = self.parent_node.attach_new_node(self.child.get_name())
            
        self.node.set_transform(self.child.get_pivot().get_transform(self.child.get_parent_pivot()))
        self.node.node().copy_tags(self.child.get_origin().node())
            
    def __object_types_export(self):
      
        if self.geom_node:
            self.__create_geom_node()
          
        elif self.collision_node:
            self.__create_collision_node()
          
        else:
            self.node.reparent_to(self.parent_node)
          
    def __create_geom_node(self):
      
        state = self.node.get_state()
        geom = self.node.node().modify_geom(0)
        mat = self.pivot.get_mat(self.child.get_parent_pivot())
        vertex_data = geom.modify_vertex_data()
        vertex_data.transform_vertices(mat)
        self.geom_node.add_geom(geom, state)
        self.node = self.parent_node
        
    def __create_collision_node(self):
      
        scale = self.pivot.get_scale()
        self.sx = scale[0]
        self.pivot.set_scale(self.sx)
        self.group_pivot = self.child.get_group().get_pivot()
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
            self.__check_if_basic_geom(scale)
        
        return coll_solid

    def __check_if_basic_geom(self, scale):
      
        self.pivot.set_scale(scale)
      
        if self.geom_type == "basic_geom":
            self.__process_basic_geom()
          
        else:
            polys = iter(self.geom_data_obj.get_subobjects("poly").values())
            verts = self.geom_data_obj.get_subobjects("vert")
            epsilon = 1.e-005
            self.__process_polygons(polys, verts, epsilon)
            
    def __process_basic_geom(self):

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
      
        if poly.get_vertex_count() == 4:
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
        
        if self.geom_obj.has_flipped_normals():
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

        if self.geom_obj.has_flipped_normals():
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
      
        normal = Vec3.down() if self.geom_obj.has_flipped_normals() else Vec3.up()
        normal = self.group_pivot.get_relative_vector(self.origin, normal)
        point = self.origin.get_pos(self.group_pivot)
        coll_solid = CollisionPlane(Plane(normal, point))
        return coll_solid
    
    def __set_geom_model_data(self):
      
        self.geom_obj = self.child.get_geom_object()
        self.geom_type = self.child.get_geom_type()
        self.geom_data_obj = None
        self.__check_geom_type()
        
    def __check_geom_type(self):
      
        if self.geom_type == "basic_geom":
            self.node = NodePath(self.geom_obj.get_geom().node().make_copy())
            self.uv_set_names = self.geom_obj.get_uv_set_names()

            for key in self.node.get_tag_keys():
                self.node.clear_tag(key)

        else:
            self.geom_data_obj = self.geom_obj.get_geom_data_object()
            self.node = self.vertices_merger.merge_duplicate_vertices(self.geom_data_obj)
            self.uv_set_names = self.geom_data_obj.get_uv_set_names()

            if self.geom_obj.has_flipped_normals():
                self.node.node().modify_geom(0).reverse_in_place()
                
    def __set_node_model_data(self):

        masks = Mgr.get("render_mask") | Mgr.get("picking_masks")
        self.node.show(masks)
        self.origin = self.child.get_origin()
        self.pivot = self.child.get_pivot()
        self.node.set_name(self.child.get_name())
        self.node.set_state(self.origin.get_state())
        tex_stages = self.node.find_all_texture_stages()
        self.node = self.vertices_format_checker.update_vertex_format(self.node, self.uv_set_names, tex_stages)
        self.__create_texture_filenames(tex_stages)
        self.__get_parent_type()
    
    def __create_texture_filenames(self, tex_stages):
      
        for tex_stage in tex_stages:
            texture = self.node.get_texture(tex_stage).make_copy()
            filename = Filename(texture.get_fullpath())
            filename.make_relative_to(self.directory)
            texture.set_filename(filename)
            texture.set_fullpath(filename)
            filename = Filename(texture.get_alpha_fullpath())
            filename.make_relative_to(self.directory)
            texture.set_alpha_filename(filename)
            texture.set_alpha_fullpath(filename)
            self.node.set_texture(tex_stage, texture)
            
    def __get_parent_type(self):
      
        self.parent = self.child.get_parent()

        if self.parent and self.parent.get_type() != "model":
            self.parent = None
            
    def __set_node_material(self):
      
        material = self.child.get_material()
        parent_material = self.parent.get_material() if self.parent else None
        parent_origin = self.parent.get_origin() if self.parent else None
        self.__check_material_equality(material, parent_material, parent_origin)
        mat = self.origin.get_mat(self.pivot)
        vertex_data = self.node.node().modify_geom(0).modify_vertex_data()
        vertex_data.transform_vertices(mat)
        self.node.set_transform(self.pivot.get_transform(self.parent_node))
        self.node.node().copy_tags(self.origin.node())
        
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
            state = node.get_state()
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
          
          
class VerticesData:
    
    def merge_duplicate_vertices(self, geom_data_obj):
      
        self.__create_vertices(geom_data_obj)
        self.__parse_vdata(geom_data_obj)
        self.__create_geom_primitives()
        geom_node = self.__set_geom_node_data()
        return NodePath(geom_node)
      
    def __set_sets_of_vertices_data(self, verts, merged_vert):
      
        self.verts1 = [verts[v_id] for v_id in merged_vert]
        self.verts2 = self.verts1[:]

    def __compare_vertices_data(self):
      
        for vert1 in self.verts1:
            row1 = vert1.get_row_index()

            if row1 not in self.dupes:
                
                for vert2 in self.verts2[:]:
                    dupe_vert_data = self.__compare_vertex_data(vert1, vert2, row1)
       
    def __compare_vertex_data(self, vert1, vert2, row1):
    
        if vert2 is not vert1:
            pos1 = vert1.get_pos()
            normal1 = vert1.get_normal()
            uv1 = vert1.get_uvs()
            col1 = vert1.get_color()
            
            pos2 = vert2.get_pos()
            normal2 = vert2.get_normal()
            uv2 = vert2.get_uvs()
            col2 = vert2.get_color()

            if pos2 == pos1 and normal2 == normal1 and uv2 == uv1 and col2 == col1:
                row2 = vert2.get_row_index()
                self.rows.remove(row2)
                self.verts2.remove(vert2)
                self.dupes[row2] = row1
                
    def __parse_vdata(self, geom_data_obj):
      
        self.geom = geom_data_obj.get_toplevel_node().get_geom(0)
        vdata_src = self.geom.get_vertex_data()
        self.vdata_dest = GeomVertexData(vdata_src)
        self.vdata_dest.unclean_set_num_rows(len(self.rows))
        thread = Thread.get_main_thread()

        for row_dest, row_src in enumerate(self.rows):
            self.vdata_dest.copy_row_from(row_dest, vdata_src, row_src, thread)

        for row2, row1 in list(self.dupes.items()):
            self.dupes[row2] = self.rows.index(row1)
            
    def __create_geom_primitives(self): 
      
        prim_src = self.geom.get_primitive(0)
        self.prim_dest = GeomTriangles(Geom.UH_static)
        rows_src = prim_src.get_vertex_list()
        rows_dest = [self.dupes[row] if row in self.dupes else self.rows.index(row) for row in rows_src]

        for indices in (rows_dest[i:i + 3] for i in range(0, len(rows_dest), 3)):
            self.prim_dest.add_vertices(*indices)
            
    def __set_geom_node_data(self):
      
        geom_dest = Geom(self.vdata_dest)
        geom_dest.add_primitive(self.prim_dest)
        geom_node = GeomNode("")
        geom_node.add_geom(geom_dest)
        return geom_node
      
    def __create_vertices(self, geom_data_obj):
      
        verts = geom_data_obj.get_subobjects("vert")
        merged_verts = set(geom_data_obj.get_merged_vertex(v_id) for v_id in verts)
        self.rows = list(range(len(verts)))
        self.dupes = {}

        for merged_vert in merged_verts:
            self.__set_sets_of_vertices_data(verts, merged_vert)
            self.__compare_vertices_data()
      
      
class VerticesFormat:
  
    def update_vertex_format(self, node, uv_set_names, tex_stages):
      
        self.__set_uv_data(uv_set_names, tex_stages)
        self.__set_array_data()

        for default_name, self.uv_name in zip(self.default_uv_names, uv_set_names):
            self.__set_internal_uv_names()
            self.__set_uv_arrays()
            self.__parse_tex_data(default_name)

        for self.internal_name in self.internal_uv_names:
            self.array.add_column(self.internal_name, 2, Geom.NT_float32, Geom.C_texcoord)

        new_vertex_data = self.__set_vertex_format(node, uv_set_names)
        node.node().modify_geom(0).set_vertex_data(new_vertex_data)
        return node
        
    def __set_uv_data(self, uv_set_names, tex_stages):
      
        self.default_uv_names = ["", "1", "2", "3", "4", "5", "6", "7"]
        self.internal_uv_names = []
        self.stages_by_uv_name = {}

        if uv_set_names != self.default_uv_names:

            for tex_stage in tex_stages:
                self.internal_name = tex_stage.get_texcoord_name()
                self.uv_name = self.internal_name.get_name()
                self.uv_name = "" if self.uv_name == "texcoord" else self.internal_name.get_basename()
                self.stages_by_uv_name.setdefault(self.uv_name, []).append(tex_stage)
                
    def __set_array_data(self):
      
        self.main_array = GeomVertexArrayFormat()
        self.main_array.add_column(InternalName.get_vertex(), 3, Geom.NT_float32, Geom.C_point)
        self.main_array.add_column(InternalName.get_color(), 1, Geom.NT_packed_dabc, Geom.C_color)
        self.main_array.add_column(InternalName.get_normal(), 3, Geom.NT_float32, Geom.C_normal)
        self.main_array.add_column(InternalName.get_tangent(), 3, Geom.NT_float32, Geom.C_vector)
        self.main_array.add_column(InternalName.get_binormal(), 3, Geom.NT_float32, Geom.C_vector)
        self.uv_arrays = []
        self.array = GeomVertexArrayFormat(self.main_array)
        
    def __set_internal_uv_names(self):
      
        if self.uv_name == "":
            self.internal_name = InternalName.get_texcoord()
            
        else:
            self.internal_name = InternalName.get_texcoord_name(self.uv_name)

        self.internal_uv_names.append(self.internal_name)
        
    def __set_uv_arrays(self):
      
        uv_array = GeomVertexArrayFormat()
        uv_array.add_column(self.internal_name, 2, Geom.NT_float32, Geom.C_texcoord)
        self.uv_arrays.append(uv_array)
        
    def __parse_tex_data(self, default_name):
      
        if self.uv_name != default_name and default_name in self.stages_by_uv_name:
              
            for tex_stage in self.stages_by_uv_name[default_name]:
                tex_stage.set_texcoord_name(self.uv_name)
                
    def __set_vertex_data(self, node, uv_set_names):
      
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
      
    def __set_vertex_format(self, node, uv_set_names):
      
        vertex_format = GeomVertexFormat()
        vertex_format.add_array(self.array)
        vertex_data = self.__set_vertex_data(node, uv_set_names)
        vertex_format = GeomVertexFormat.register_format(vertex_format)
        new_vertex_data = vertex_data.convert_to(vertex_format)
        return new_vertex_data
