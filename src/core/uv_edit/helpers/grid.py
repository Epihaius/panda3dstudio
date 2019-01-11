from ..base import *


class Grid(BaseObject):

    def __init__(self):

        picking_mask = UVMgr.get("picking_mask")
        self._origin = origin = self.uv_space.attach_new_node("grid")
        origin.hide(picking_mask)
        self._grid_lines = grid_lines = self.__create_lines()
        grid_lines.set_bin("background", 2)
        grid_lines.set_depth_write(False)
        grid_lines.set_depth_test(False)
        grid_lines.reparent_to(self._origin)
        x_axis_line = self.__create_axis_line("x")
        x_axis_line.reparent_to(self._origin)
        x_axis_line.set_bin("background", 3)
        x_axis_line.set_depth_write(False)
        x_axis_line.set_depth_test(False)
        z_axis_line = self.__create_axis_line("z")
        z_axis_line.reparent_to(self._origin)
        z_axis_line.set_bin("background", 3)
        z_axis_line.set_depth_write(False)
        z_axis_line.set_depth_test(False)
        self._axis_lines = {"x": x_axis_line, "z": z_axis_line}
        self._tex_borders = borders = self.__create_tex_borders()
        borders.reparent_to(self._origin)
        borders.set_bin("background", 3)
        borders.set_depth_write(False)
        borders.set_depth_test(False)
        self._background_tex_filename = ""
        self._background = quad = self.__create_quad()
        quad.reparent_to(self.uv_space)
        quad.hide(picking_mask)
        quad.set_light_off()
        quad.set_color_scale(.5)
        quad.set_bin("background", 1)
        quad.set_depth_write(False)
        quad.set_depth_test(False)
        quad.set_pos(.5, 0., .5)
        quad.hide()
        self._background_brightness = .5
        self._background_tiling = 0
        self._background_on_models = False
        self._material = None

        self._scale = 1.

        def update_remotely():

            Mgr.update_interface_remotely("uv", "uv_background", "tex_filename",
                                          self._background_tex_filename)
            Mgr.update_interface_remotely("uv", "uv_background", "brightness",
                                          self._background_brightness)
            Mgr.update_interface_remotely("uv", "uv_background", "tiling",
                                          self._background_tiling)

        UVMgr.accept("remotely_update_background", update_remotely)

    def add_interface_updaters(self):

        Mgr.add_app_updater("uv_background", self.__update_background, interface_id="uv")

    def __update_background(self, value_id, value):

        if value_id == "tex_filename":
            if value:
                self._background.show()
                self._background.set_texture(Mgr.load_tex(Filename.from_os_specific(value)))
            else:
                self._background.hide()
            self._background_tex_filename = value
            if self._background_on_models:
                self.__show_background_on_models(True)
        elif value_id == "brightness":
            self._background_brightness = value
            self._background.set_color_scale(value)
        elif value_id == "tiling":
            self._background_tiling = value
            scale = value * 2 + 1
            self._background.set_scale(scale)
            self._background.set_tex_scale(TextureStage.get_default(), scale)
        elif value_id == "show_on_models":
            self._background_on_models = value
            self.__show_background_on_models(value)

        Mgr.update_interface_remotely("uv", "uv_background", value_id, value)

    def __show_background_on_models(self, show):

        models = [obj for obj in Mgr.get("selection_top") if obj.get_type() == "model"
                  and obj.get_geom_type() != "basic_geom"]

        if show:

            if self._material:
                self._material.strip()
            else:
                for model in models:
                    model.get_geom_object().reset_vertex_colors()
                    origin = model.get_origin()
                    origin.clear_material()
                    origin.clear_texture()
                    origin.clear_tex_transform()
                    origin.clear_color_scale()
                    origin.set_transparency(TransparencyAttrib.M_none)
                    origin.set_color(model.get_color())

            material = Mgr.do("create_material")
            map_data = {}
            map_data["map_type"] = "color"
            map_data["rgb_filename"] = self._background_tex_filename
            map_data["alpha_filename"] = ""
            material.set_texture(map_data)
            self._material = material

            for model in models:
                material.apply(model)

        elif self._material:

            self._material.strip()
            self._material = None

            for model in models:

                material = model.get_material()

                if material:
                    material.apply(model, force=True)

    def __create_line(self):

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("gridline_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.add_data3(-100., 0., 0.)
        pos_writer.add_data3(100., 0., 0.)

        line = GeomLines(Geom.UH_static)
        line.add_vertices(0, 1)
        line_geom = Geom(vertex_data)
        line_geom.add_primitive(line)
        line_node = GeomNode("grid_line_x")
        line_node.add_geom(line_geom)

        return NodePath(line_node)

    def __create_lines(self):

        grid_lines = NodePath("grid_lines")
        grid_lines.set_color(0., 0., .75, 1.)
        grid_lines.set_light_off()
        grid_lines_x = grid_lines.attach_new_node("")
        line = self.__create_line()
        line.reparent_to(grid_lines_x)

        for i in range(1, 101):
            line_copy = line.copy_to(grid_lines_x)
            line_copy.set_z(-i)
            line_copy = line.copy_to(grid_lines_x)
            line_copy.set_z(i)

        grid_lines_x.flatten_strong()
        grid_lines_y = grid_lines_x.copy_to(grid_lines)
        grid_lines_y.set_r(90.)
        grid_lines.flatten_strong()

        return grid_lines

    def __create_axis_line(self, axis):

        axis_line = self.__create_line()
        axis_line.set_color(0., 0., .25, 1.)
        axis_line.set_light_off()
        axis_line.set_render_mode_thickness(3)

        if axis == "z":
            axis_line.set_r(90.)

        return axis_line

    def __create_tex_borders(self):

        tex_borders = NodePath("tex_borders")
        tex_borders.set_color(0., 0., .25, 1.)
        tex_borders.set_light_off()
        tex_borders.set_render_mode_thickness(3)
        tex_border_x = self.__create_line()
        tex_border_x.reparent_to(tex_borders)
        tex_border_x.set_scale(.005)
        tex_border_z = tex_border_x.copy_to(tex_borders)
        tex_border_x.set_pos(.5, 0., 1.)
        tex_border_z.set_r(90.)
        tex_border_z.set_pos(1., 0., .5)
        tex_borders.flatten_strong()

        return tex_borders

    def __create_quad(self):

        vertex_format = GeomVertexFormat.get_v3t2()
        vertex_data = GeomVertexData("quad_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        uv_writer = GeomVertexWriter(vertex_data, "texcoord")
        pos_writer.add_data3(-.5, 0., -.5)
        uv_writer.add_data2(0., 0.)
        pos_writer.add_data3(.5, 0., -.5)
        uv_writer.add_data2(1., 0.)
        pos_writer.add_data3(.5, 0., .5)
        uv_writer.add_data2(1., 1.)
        pos_writer.add_data3(-.5, 0., .5)
        uv_writer.add_data2(0., 1.)

        quad = GeomTriangles(Geom.UH_static)
        quad.add_vertices(0, 1, 2)
        quad.add_vertices(0, 2, 3)
        quad_geom = Geom(vertex_data)
        quad_geom.add_primitive(quad)
        quad_node = GeomNode("tex_quad")
        quad_node.add_geom(quad_geom)

        return NodePath(quad_node)

    def update(self, force=False):

        x, y, z = cam_pos = self.cam.get_pos(self._origin)
        cam_scale = self.cam.get_sx() * .07
        a = 2. ** math.ceil(math.log(cam_scale, 2.))
        b = a * .5
        scale = b if b > cam_scale else a

        grid_lines = self._grid_lines
        axis_lines = self._axis_lines

        if force or scale != self._scale:
            grid_lines.set_scale(scale)
            axis_lines["x"].set_scale(scale)
            axis_lines["z"].set_scale(scale)
            self._scale = scale

        size = 5. * self._scale
        x_offset = abs(x) // size * (-size if x < 0. else size)
        z_offset = abs(z) // size * (-size if z < 0. else size)
        offset = VBase3(x_offset, 0., z_offset)
        grid_lines.set_pos(offset)
        axis_lines["x"].set_x(x_offset)
        axis_lines["z"].set_z(z_offset)
