from .base import *
#from .file_export_types import export_bam_files

class ExportManager(BaseObject):

    def __init__(self):

        Mgr.add_app_updater("export", self.__update_export)

    def __prepare_export(self):

        if Mgr.get("selection_top"):
            Mgr.update_remotely("export", "export")
        elif Mgr.get("objects"):
            Mgr.update_remotely("export", "confirm_entire_scene")
        else:
            Mgr.update_remotely("export", "empty_scene")


    def __export_to_obj(self, filename):

        objs = list(set(obj.get_root() for obj in Mgr.get("selection_top")))

        if not objs:
            return

        material_data = {}
        flat_color_index = 0
        row_offset = 1
        namelist = []

        with open(filename, "w") as obj_file:

            obj_file.write("# Created with Panda3D Studio\n\n")
            fname = os.path.basename(filename)
            mtllib_name = os.path.splitext(fname)[0]
            obj_file.write("mtllib {}.mtl\n".format(mtllib_name))

            while objs:

                obj = objs.pop()

                if obj.get_type() == "model":

                    name = get_unique_name(obj.get_name().replace(" ", "_"), namelist)
                    namelist.append(name)
                    obj_file.write("\ng {}\n\n".format(name))

                    geom_obj = obj.get_geom_object()

                    if obj.get_geom_type() == "basic_geom":

                        node = NodePath(geom_obj.get_geom().node().make_copy())

                    else:

                        geom_data_obj = geom_obj.get_geom_data_object()
                        node = NodePath(geom_data_obj.get_toplevel_geom().node().make_copy())

                        if geom_obj.has_flipped_normals():
                            node.node().modify_geom(0).reverse_in_place()

                    material = obj.get_material()

                    if material:

                        material_name = material.get_name()

                        if not material_name:
                            material_name = "<Unnamed>"

                        if material in material_data:

                            material_alias = material_data[material]["alias"]

                        else:

                            data = {}
                            material_data[material] = data
                            material_alias = "material_{:03d}".format(len(material_data))
                            data["name"] = material_name
                            data["alias"] = material_alias
                            data["is_flat_color"] = False
                            base_material = material.get_base_material()
                            dif = base_material.get_diffuse() if base_material.has_diffuse() \
                                else material.get_flat_color()
                            data["diffuse"] = dif
                            alpha = material.get_base_properties()["alpha"]

                            if alpha["on"]:
                                data["dissolve"] = alpha["value"]

                            color_map = material.get_tex_map("color")

                            if color_map.is_active() and color_map.get_texture():

                                rgb_filename, alpha_filename = color_map.get_tex_filenames()
                                data["diffuse_map"] = os.path.basename(rgb_filename)

                                if alpha_filename:
                                    data["dissolve_map"] = os.path.basename(alpha_filename)

                    else:

                        color = (1., 1., 1., 1.)

                        if color in material_data:
                            material_name = material_data[color]["name"]
                            material_alias = material_data[color]["alias"]
                        else:
                            flat_color_index += 1
                            material_name = "Flat color {:d}".format(flat_color_index)
                            data = {}
                            material_data[color] = data
                            data["name"] = material_name
                            material_alias = "material_{:03d}".format(len(material_data))
                            data["alias"] = material_alias
                            data["is_flat_color"] = True

                    vertex_data = node.node().modify_geom(0).modify_vertex_data()
                    convert_mat = Mat4.convert_mat(CS_default, CS_yup_right)
                    origin = obj.get_origin()
                    mat = origin.get_net_transform().get_mat() * convert_mat
                    vertex_data.transform_vertices(mat)
                    pos_reader = GeomVertexReader(vertex_data, "vertex")
                    uv_reader = GeomVertexReader(vertex_data, "texcoord")
                    normal_reader = GeomVertexReader(vertex_data, "normal")
                    row_count = vertex_data.get_num_rows()

                    for i in range(row_count):
                        x, y, z = pos_reader.get_data3()
                        u, v = uv_reader.get_data2()
                        xn, yn, zn = normal_reader.get_data3()
                        obj_file.write("v {:.6f} {:.6f} {:.6f}\n".format(x, y, z))
                        obj_file.write("vt {:.6f} {:.6f}\n".format(u, v))
                        obj_file.write("vn {:.6f} {:.6f} {:.6f}\n".format(xn, yn, zn))

                    obj_file.write("\nusemtl {}\n".format(material_alias))
                    obj_file.write("# {}\n".format(material_name))

                    index_list = node.node().get_geom(0).get_primitive(0).get_vertex_list()
                    index_count = len(index_list)

                    for i in range(0, index_count, 3):
                        i1, i2, i3 = [j + row_offset for j in index_list[i:i+3]]
                        indices = (i1, i1, i1, i2, i2, i2, i3, i3, i3)
                        obj_file.write("f {:d}/{:d}/{:d} {:d}/{:d}/{:d} {:d}/{:d}/{:d}\n".format(*indices))

                    row_offset += row_count

                if obj.get_type() == "group":
                    children = obj.get_members()
                else:
                    children = obj.get_children()

                if children:
                    objs.extend(children)

        mtllib_fname = os.path.splitext(filename)[0] + ".mtl"

        with open(mtllib_fname, "w") as mtl_file:

            mtl_file.write("# Created with Panda3D Studio\n\n")

            for material, data in material_data.items():

                material_alias = data["alias"]
                mtl_file.write("\n\nnewmtl {}\n".format(material_alias))
                material_name = data["name"]
                mtl_file.write("# {}\n\n".format(material_name))
                r, g, b, a = material if data["is_flat_color"] else data["diffuse"]
                mtl_file.write("Kd {:.6f} {:.6f} {:.6f}\n".format(r, g, b))

                if "dissolve" in data:
                    mtl_file.write("d {:.6f}\n".format(data["dissolve"]))

                if "diffuse_map" in data:
                    mtl_file.write("map_Kd {}\n".format(data["diffuse_map"]))

                if "dissolve_map" in data:
                    mtl_file.write("map_d {}\n".format(data["dissolve_map"]))

    def __export(self, filename):

        ext = os.path.splitext(filename)[1]

        if ext == ".bam":
            self.bam_exporter = file_export_types.export_bam_files.ExportBam()
            self.bam_exporter.export_to_bam(filename)
        elif ext == ".obj":
            self.__export_to_obj(filename)

    def __update_export(self, update_type, *args):

        if update_type == "prepare":
            self.__prepare_export()
        elif update_type == "export":
            self.__export(*args)


MainObjects.add_class(ExportManager)
