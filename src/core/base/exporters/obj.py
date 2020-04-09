from .. import *


class ObjExporter:

    def export(self, filename):

        self.__determine_objs_for_export()
        self.__set_initial_data()
        self.__create_obj_file(filename)
        self.__parse_objects()
        self.obj_file.close()
        self.__create_mtl_file(filename)
        self.__write_material_data()
        self.mtl_file.close()

    def __determine_objs_for_export(self):

        self.objs = set(obj.root for obj in Mgr.get("selection_top"))

        if not self.objs:
            self.objs = set(obj.root for obj in Mgr.get("objects"))

        self.objs = list(self.objs)

    def __set_initial_data(self):

        self.material_data = {}
        self.flat_color_index = 0
        self.row_offset = 1
        self.namelist = []

    def __create_obj_file(self, filename):

        self.obj_file = open(filename, "w")
        self.obj_file.write("# Created with Panda3D Studio\n\n\n")
        fname = os.path.basename(filename)
        mtllib_name = os.path.splitext(fname)[0]
        self.obj_file.write(f"mtllib {mtllib_name}.mtl\n")

    def __parse_objects(self):

        while self.objs:
            self.obj = self.objs.pop()
            self.__parse_model()
            self.__add_objects()

    def __add_objects(self):

        if self.obj.type == "group":
            children = self.obj.get_members()
        else:
            children = self.obj.children

        if children:
            self.objs.extend(children)

    def __parse_model(self):

        if self.obj.type == "model":
            name = get_unique_name(self.obj.name.replace(" ", "_"), self.namelist)
            self.namelist.append(name)
            self.obj_file.write(f"\ng {name}\n\n")
            self.__set_geom_data()
            self.__check_material()
            self.__set_node_transform()
            self.__write_vertex_data()
            self.__write_material_id()
            self.__write_triangle_data()

    def __set_geom_data(self):

        self.geom_obj = self.obj.geom_obj
        self.geom_type = self.obj.geom_type
        self.geom_data_obj = None
        self.__check_geom_type()

    def __check_geom_type(self):

        if self.geom_type == "unlocked_geom":
            self.geom_data_obj = self.geom_obj.geom_data_obj
            self.node = Mgr.do("merge_duplicate_verts", self.geom_data_obj)
        else:
            self.node = NodePath(self.geom_obj.geom.node().make_copy())

    def __check_material(self):

        material = self.obj.get_material()

        if material:
            self.__add_material(material)
        else:
            self.__add_flat_color()

    def __add_material(self, material):

        self.material_name = material.name

        if not self.material_name:
            self.material_name = "<Unnamed>"

        if material in self.material_data:
            self.material_alias = self.material_data[material]["alias"]
        else:
            self.__add_material_data(material)

    def __add_material_data(self, material):

        data = {}
        self.material_data[material] = data
        self.material_alias = f"material_{len(self.material_data) :03d}"
        data["name"] = self.material_name
        data["alias"] = self.material_alias
        data["is_flat_color"] = False
        base_material = material.get_base_material()
        dif = base_material.get_diffuse() if base_material.has_diffuse() \
            else material.get_flat_color()
        data["diffuse"] = dif
        alpha = material.get_base_properties()["alpha"]

        if alpha["on"]:
            data["dissolve"] = alpha["value"]

        color_map = material.get_tex_map("color")

        if color_map.active and color_map.get_texture():

            rgb_filename, alpha_filename = color_map.get_tex_filenames()
            data["diffuse_map"] = os.path.basename(rgb_filename)

            if alpha_filename:
                data["dissolve_map"] = os.path.basename(alpha_filename)

    def __add_flat_color(self):

        color = (1., 1., 1., 1.)

        if color in self.material_data:
            self.material_name = self.material_data[color]["name"]
            self.material_alias = self.material_data[color]["alias"]
        else:
            self.flat_color_index += 1
            self.material_name = f"Flat color {self.flat_color_index}"
            data = {}
            self.material_data[color] = data
            data["name"] = self.material_name
            self.material_alias = f"material_{len(self.material_data) :03d}"
            data["alias"] = self.material_alias
            data["is_flat_color"] = True

    def __set_node_transform(self):

        vertex_data = self.node.node().modify_geom(0).modify_vertex_data()
        convert_mat = Mat4.convert_mat(CS_default, CS_yup_right)
        origin = self.obj.origin
        mat = origin.get_net_transform().get_mat() * convert_mat
        vertex_data.transform_vertices(mat)

    def __write_vertex_data(self):

        vertex_data = self.node.node().modify_geom(0).modify_vertex_data()
        pos_reader = GeomVertexReader(vertex_data, "vertex")
        uv_reader = GeomVertexReader(vertex_data, "texcoord")
        normal_reader = GeomVertexReader(vertex_data, "normal")
        self.row_count = vertex_data.get_num_rows()
        obj_file = self.obj_file

        for i in range(self.row_count):
            x, y, z = pos_reader.get_data3()
            u, v = uv_reader.get_data2()
            xn, yn, zn = normal_reader.get_data3()
            obj_file.write(f"v {x :.6f} {y :.6f} {z :.6f}\n")
            obj_file.write(f"vt {u :.6f} {v :.6f}\n")
            obj_file.write(f"vn {xn :.6f} {yn :.6f} {zn :.6f}\n")

    def __write_material_id(self):

        self.obj_file.write(f"\nusemtl {self.material_alias}\n")
        self.obj_file.write(f"# {self.material_name}\n")

    def __write_triangle_data(self):

        index_list = self.node.node().get_geom(0).get_primitive(0).get_vertex_list()
        index_count = len(index_list)
        row_offset = self.row_offset
        obj_file = self.obj_file
        obj_file.write("\n")

        for i in range(0, index_count, 3):
            i1, i2, i3 = [j + row_offset for j in index_list[i:i+3]]
            obj_file.write(f"f {i1}/{i1}/{i1} {i2}/{i2}/{i2} {i3}/{i3}/{i3}\n")

        self.row_offset += self.row_count

    def __create_mtl_file(self, filename):

        mtllib_fname = os.path.splitext(filename)[0] + ".mtl"
        self.mtl_file = open(mtllib_fname, "w")
        self.mtl_file.write("# Created with Panda3D Studio\n")

    def __write_material_data(self):

        mtl_file = self.mtl_file

        for material, data in self.material_data.items():

            material_alias = data["alias"]
            mtl_file.write(f"\n\nnewmtl {material_alias}\n")
            material_name = data["name"]
            mtl_file.write(f"# {material_name}\n\n")
            r, g, b, a = material if data["is_flat_color"] else data["diffuse"]
            mtl_file.write(f"Kd {r :.6f} {g :.6f} {b :.6f}\n")

            if "dissolve" in data:
                mtl_file.write(f"d {data['dissolve'] :.6f}\n")

            if "diffuse_map" in data:
                mtl_file.write(f"map_Kd {data['diffuse_map']}\n")

            if "dissolve_map" in data:
                mtl_file.write(f"map_d {data['dissolve_map']}\n")
