from .base import *
from .material import render_state_to_material


class BasicGeom:

    _render_state_ids = {}
    _render_states = {}

    @classmethod
    def init_render_states(cls):

        state_empty = RenderState.make_empty()
        np = NodePath("render_state")
        np.set_light_off()
        np.set_texture_off()
        np.set_material_off()
        np.set_shader_off()
        state_flat = np.get_state()
        np.set_color((1., 1., 1., 1.))
        state_flat_white = np.get_state()
        attrib = RenderModeAttrib.make(RenderModeAttrib.M_wireframe)
        state_wire_white = state_flat_white.add_attrib(attrib)
        attrib = RenderModeAttrib.make(RenderModeAttrib.M_filled_wireframe, 1.,
                                       False, (1., 1., 1., 1.))
        state_filled_wire_white = state_empty.add_attrib(attrib)
        render_state_ids = cls._render_state_ids
        render_state_ids["shaded"] = {}
        render_state_ids["shaded"]["unselected"] = "filled_unselected"
        render_state_ids["shaded"]["selected"] = "filled_selected"
        render_state_ids["flat"] = "flat"
        render_state_ids["wire"] = {}
        render_state_ids["wire"]["unselected"] = "wire_unselected"
        render_state_ids["wire"]["selected"] = "wire_selected"
        render_state_ids["shaded+wire"] = {}
        render_state_ids["shaded+wire"]["unselected"] = "filled_wire_unselected"
        render_state_ids["shaded+wire"]["selected"] = "filled_wire_selected"
        render_states = cls._render_states
        render_states["filled_unselected"] = state_empty
        render_states["filled_selected"] = state_empty
        render_states["flat"] = state_flat
        render_states["wire_selected"] = state_wire_white
        render_states["filled_wire_selected"] = state_filled_wire_white

    def __make_wireframe_render_state(self, render_state_id, color):

        if render_state_id == "wire_unselected":
            render_state = self._render_states["flat"]
            attrib = ColorAttrib.make_flat(color)
            render_state = render_state.add_attrib(attrib)
            attrib = RenderModeAttrib.make(RenderModeAttrib.M_wireframe)
            render_state = render_state.add_attrib(attrib)
        elif render_state_id == "filled_wire_unselected":
            render_state = RenderState.make_empty()
            attrib = RenderModeAttrib.make(RenderModeAttrib.M_filled_wireframe,
                                           1., False, color)
            render_state = render_state.add_attrib(attrib)

        return render_state

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_geom"] = geom = NodePath(self.geom.node().make_copy())
        geom.set_state(RenderState.make_empty())
        del state["model"]
        del state["_picking_states"]
        del state["_initial_vertex_colors"]
        del state["_is_tangent_space_initialized"]
        state["_type"] = state.pop("type")
        state["_picking_col_id"] = state.pop("picking_color_id")
        del state["geom"]

        return state

    def __setstate__(self, state):

        state["type"] = state.pop("_type")
        state["picking_color_id"] = state.pop("_picking_col_id")
        state["geom"] = state.pop("_geom")
        self.__dict__ = state

        picking_col_id = self.picking_color_id
        pickable_type_id = PickableTypes.get_id("basic_geom")
        picking_color = get_color_vec(picking_col_id, pickable_type_id)
        np = NodePath("picking_color_state")
        np.set_color(picking_color, 1)
        picking_states = {"filled": np.get_state()}
        np.set_render_mode_wireframe(1)
        np.set_render_mode_thickness(5, 1)
        picking_states["wire"] = np.get_state()
        self._picking_states = picking_states
        vertex_data = self.geom.node().get_geom(0).get_vertex_data()
        array = GeomVertexArrayData(vertex_data.get_array(1))
        self._initial_vertex_colors = array
        self._is_tangent_space_initialized = False

    def __init__(self, model, geom, picking_col_id, materials=None):

        self._prop_ids = []
        self._type_prop_ids = ["uv_set_names", "normal_flip", "normal_viz",
                               "normal_color", "normal_length"]
        self.type = "basic_geom"
        self.model = model
        self.geom = geom
        self.picking_color_id = picking_col_id
        self._is_tangent_space_initialized = False
        self._normals_flipped = False
        self._normals_shown = False
        self._normal_color = (.75, .75, 0., 1.)
        self._geometry_unlock_started = False
        self._geometry_unlock_ended = False
        prim_count = geom.node().get_geom(0).get_primitive(0).get_num_primitives()
        p1, p2 = geom.get_tight_bounds()
        x, y, z = p2 - p1
        a = (x + y + z) / 3.
        self._normal_length = min(a * .25, max(.001, 500. * a / prim_count))

        model.geom_obj = self
        model.pivot.set_transform(geom.get_transform())
        geom.clear_transform()
        model_orig = model.origin
        render_state = geom.get_state()
        geom.set_state(RenderState.make_empty())
        src_vert_data = geom.node().get_geom(0).get_vertex_data()
        src_format = src_vert_data.format
        dest_format = Mgr.get("vertex_format_full")
        dest_vert_data = src_vert_data.convert_to(dest_format)
        self._initial_vertex_colors = dest_vert_data.get_array(1)
        geom.node().modify_geom(0).set_vertex_data(dest_vert_data)
        dest_vert_data = geom.node().modify_geom(0).modify_vertex_data()
        num_rows = src_vert_data.get_num_rows()
        uv_set_list = [InternalName.get_texcoord()]
        uv_set_list += [InternalName.get_texcoord_name(str(i)) for i in range(1, 8)]
        src_uv_set_names = ["", "1", "2", "3", "4", "5", "6", "7"]

        material, uv_set_names = render_state_to_material(render_state, src_format, materials)

        for src_uv_set, dest_uv_set in uv_set_names.items():

            uv_set_id = uv_set_list.index(dest_uv_set)
            uv_name = src_uv_set.name
            uv_name = "" if uv_name == "texcoord" else src_uv_set.basename
            src_uv_set_names[uv_set_id] = uv_name
            uv_reader = GeomVertexReader(src_vert_data, src_uv_set)
            uv_writer = GeomVertexWriter(dest_vert_data, dest_uv_set)

            for i in range(num_rows):
                uv = uv_reader.get_data2()
                uv_writer.set_data2(uv)

        self._uv_set_names = src_uv_set_names

        if material:
            model.set_material(material)

        color = tuple([random.random() * .4 + .5 for i in range(3)] + [1.])
        model.set_color(color, update_app=False)
        geom.reparent_to(model_orig)

        pickable_type_id = PickableTypes.get_id("basic_geom")
        picking_color = get_color_vec(picking_col_id, pickable_type_id)
        np = NodePath("picking_color_state")
        np.set_color(picking_color, 1)
        state = np.get_state()
        picking_col_id_str = str(picking_col_id)
        geom.set_tag("picking_color", picking_col_id_str)
        Mgr.do("set_basic_geom_picking_color", picking_col_id_str, state)
        picking_states = {"filled": state}
        np.set_render_mode_wireframe(1)
        np.set_render_mode_thickness(5, 1)
        state = np.get_state()
        picking_states["wire"] = state
        self._picking_states = picking_states

        def update_render_mode():

            self.update_render_mode(False)

        obj_id = model.id
        PendingTasks.add(update_render_mode, "update_render_mode", "object", 0, obj_id)

    def __del__(self):

        logging.debug('BasicGeom garbage-collected.')

    def destroy(self, unregister=True):

        self.geom.remove_node()
        self.geom = None

        if unregister:
            Mgr.do("unregister_basic_geom", self)

        Mgr.do("clear_basic_geom_picking_color", str(self.picking_color_id))

    def register(self, restore=True):

        Mgr.do("register_basic_geom", self, restore)

        if restore:
            Mgr.notify("pickable_geom_altered", self.toplevel_obj)

    def unregister(self):

        Mgr.do("unregister_basic_geom", self)

    def get_toplevel_object(self, get_group=False):

        return self.model.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def get_point_at_screen_pos(self, screen_pos):

        cam = GD.cam()
        normal = V3D(GD.world.get_relative_vector(cam, Vec3.forward()))
        point = self.geom.get_pos(GD.world)
        plane = Plane(normal, point)

        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.world.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point

    def update_tangent_space(self, flip_tangent, flip_bitangent):

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        vert_indices = self.geom.node().get_geom(0).get_primitive(0).get_vertex_list()

        pos_reader = GeomVertexReader(vertex_data, "vertex")
        normal_reader = GeomVertexReader(vertex_data, "normal")
        uv_reader = GeomVertexReader(vertex_data, "texcoord")
        tan_writer = GeomVertexWriter(vertex_data, "tangent")
        bitan_writer = GeomVertexWriter(vertex_data, "binormal")
        vert_handlers = (pos_reader, normal_reader, uv_reader, tan_writer, bitan_writer)

        processed_rows = []
        epsilon = 1.e-010

        for rows in (vert_indices[i:i + 3] for i in range(0, len(vert_indices), 3)):

            for row in rows:

                if row in processed_rows:
                    continue

                other_rows = list(rows)
                other_rows.remove(row)
                row1, row2 = other_rows

                for handler in vert_handlers:
                    handler.set_row(row)

                pos = pos_reader.get_data3()
                normal = normal_reader.get_data3()
                uv = uv_reader.get_data2()

                pos_reader.set_row(row1)
                pos1 = pos_reader.get_data3()
                pos_reader.set_row(row2)
                pos2 = pos_reader.get_data3()
                pos_vec1 = pos1 - pos
                pos_vec2 = pos2 - pos

                uv_reader.set_row(row1)
                uv1 = uv_reader.get_data2()
                uv_reader.set_row(row2)
                uv2 = uv_reader.get_data2()
                uv_vec1 = uv1 - uv
                uv_vec2 = uv2 - uv

                # compute a vector pointing in the +U direction, in texture space
                # and in world space

                if abs(uv_vec1.y) < epsilon:
                    u_vec_local = uv_vec1
                    u_vec_world = Vec3(pos_vec1)
                elif abs(uv_vec2.y) < epsilon:
                    u_vec_local = uv_vec2
                    u_vec_world = Vec3(pos_vec2)
                else:
                    scale = (uv_vec1.y / uv_vec2.y)
                    u_vec_local = uv_vec1 - uv_vec2 * scale
                    # u_vec_local.y will be 0 and thus point in the -/+U direction;
                    # replacing the texture-space vectors with the corresponding
                    # world-space vectors will therefore yield a world-space U-vector
                    u_vec_world = pos_vec1 - pos_vec2 * scale

                if u_vec_local.x < 0.:
                    u_vec_world *= -1.

                # compute a vector pointing in the +V direction, in texture space
                # and in world space

                if abs(uv_vec1.x) < epsilon:
                    v_vec_local = uv_vec1
                    v_vec_world = Vec3(pos_vec1)
                elif abs(uv_vec2.x) < epsilon:
                    v_vec_local = uv_vec2
                    v_vec_world = Vec3(pos_vec2)
                else:
                    scale = (uv_vec1.x / uv_vec2.x)
                    v_vec_local = uv_vec1 - uv_vec2 * scale
                    # v_vec_local.x will be 0 and thus point in the -/+V direction;
                    # replacing the texture-space vectors with the corresponding
                    # world-space vectors will therefore yield a world-space V-vector
                    v_vec_world = pos_vec1 - pos_vec2 * scale

                if v_vec_local.y < 0.:
                    v_vec_world *= -1.

                tangent_plane = Plane(normal, Point3())
                # the tangent vector is the world-space U-vector projected onto
                # the tangent plane
                tangent = Vec3(tangent_plane.project(Point3(u_vec_world)))

                if not tangent.normalize():
                    continue

                # the bitangent vector is the world-space V-vector projected onto
                # the tangent plane
                bitangent = Vec3(tangent_plane.project(Point3(v_vec_world)))

                if not bitangent.normalize():
                    continue

                if flip_tangent:
                    tangent *= -1.

                if flip_bitangent:
                    bitangent *= -1.

                tan_writer.set_data3(tangent)
                bitan_writer.set_data3(bitangent)
                processed_rows.append(row)

        self._is_tangent_space_initialized = True

    def init_tangent_space(self):

        if not self._is_tangent_space_initialized:
            flip_tangent, flip_bitangent = self.model.get_tangent_space_flip()
            self.update_tangent_space(flip_tangent, flip_bitangent)

    def is_tangent_space_initialized(self):

        return self._is_tangent_space_initialized

    def bake_texture(self, texture):

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        geom_copy = self.geom.copy_to(GD.world)
        geom_copy.detach_node()
        geom_copy.set_texture(TextureStage.default, texture)
        geom_copy.flatten_light()
        geom_copy.apply_texture_colors()
        vertex_data_copy = geom_copy.node().modify_geom(0).modify_vertex_data()
        index = vertex_data_copy.format.get_array_with("color")
        array = vertex_data_copy.modify_array(index)
        vertex_data.set_array(1, array)

    def reset_vertex_colors(self):

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        array = GeomVertexArrayData(self._initial_vertex_colors)
        vertex_data.set_array(1, array)

    def get_subobj_selection(self, subobj_lvl):

        return []

    def set_wireframe_color(self, color):

        render_mode = GD["render_mode"]
        state_id = self._render_state_ids[render_mode]["unselected"]

        if state_id in ("wire_unselected", "filled_wire_unselected"):
            render_state = self.__make_wireframe_render_state(state_id, color)
            self.geom.set_state(render_state)

    def update_selection_state(self, is_selected=True):

        render_mode = GD["render_mode"]

        if render_mode == "shaded":
            return

        self.update_render_mode(is_selected)

    def update_render_mode(self, is_selected):

        render_mode = GD["render_mode"]
        selection_state = "selected" if is_selected else "unselected"
        state_id = self._render_state_ids[render_mode][selection_state]

        if state_id in ("wire_unselected", "filled_wire_unselected"):
            color = self.model.get_color()
            render_state = self.__make_wireframe_render_state(state_id, color)
        else:
            render_state = self._render_states[state_id]

        self.geom.set_state(render_state)

        state_id = "filled" if (is_selected or render_mode != "wire") else "wire"
        picking_state = self._picking_states[state_id]
        Mgr.do("set_basic_geom_picking_color", str(self.picking_color_id), picking_state)

    def set_uv_set_name(self, uv_set_id, uv_set_name):

        uv_set_names = self._uv_set_names[:]
        del uv_set_names[uv_set_id]

        if uv_set_name == "" and "" in uv_set_names:
            uv_set_name = "0"

        if uv_set_name != "":
            uv_set_name = get_unique_name(uv_set_name, uv_set_names)

        change = True

        if self._uv_set_names[uv_set_id] == uv_set_name:
            change = False

        self._uv_set_names[uv_set_id] = uv_set_name
        Mgr.update_remotely("uv_set_name", self._uv_set_names)

        return change

    def set_uv_set_names(self, uv_set_names):

        if self._uv_set_names == uv_set_names:
            return False

        self._uv_set_names = uv_set_names

        return True

    def get_uv_set_names(self):

        return self._uv_set_names

    def show_normals(self, show=True):

        if self._normals_shown == show:
            return False

        if show:
            points_geom = self.geom.node().get_geom(0).make_points()
            node = GeomNode("normals_geom")
            node.add_geom(points_geom)
            node.set_bounds(OmniBoundingVolume())
            node.final = True
            normals_geom = self.geom.attach_new_node(node)
            sh = shaders.normal
            vs = sh.VERT_SHADER
            fs = sh.FRAG_SHADER
            gs = sh.GEOM_SHADER
            shader = Shader.make(Shader.SL_GLSL, vs, fs, gs)
            normals_geom.set_shader(shader)
            normals_geom.set_shader_input("normal_length", self._normal_length)
            normals_geom.set_color(self._normal_color)
            normals_geom.hide(Mgr.get("picking_mask"))
        else:
            normals_geom = self.geom.find("**/normals_geom")
            normals_geom.remove_node()

        self._normals_shown = show

        return True

    def flip_normals(self, flip=True):

        if self._normals_flipped == flip:
            return False

        geom = self.geom.node().modify_geom(0)
        geom.reverse_in_place()
        vertex_data = geom.get_vertex_data().reverse_normals()
        geom.set_vertex_data(vertex_data)

        if self._normals_shown:
            self.show_normals(False)
            self.show_normals()

        self._normals_flipped = flip

        return True

    def has_flipped_normals(self):

        return self._normals_flipped

    def set_normal_color(self, color):

        if self._normal_color == color:
            return False

        if self._normals_shown:
            normals_geom = self.geom.find("**/normals_geom")
            normals_geom.set_color(color)

        self._normal_color = color

        return True

    def set_normal_length(self, length):

        if self._normal_length == length:
            return False

        if self._normals_shown:
            normals_geom = self.geom.find("**/normals_geom")
            normals_geom.set_shader_input("normal_length", length)

        self._normal_length = length

        return True

    def get_data_to_store(self, event_type, prop_id=""):

        data = {}

        if event_type == "creation":

            data["geom_obj"] = {"main": self}
            prop_ids = self.get_property_ids()

            for prop_id in prop_ids:
                data[prop_id] = {"main": self.get_property(prop_id)}

        elif event_type == "prop_change":

            if prop_id in self.get_property_ids():
                data[prop_id] = {"main": self.get_property(prop_id)}

        return data

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id

        if "self" in data_ids:

            for prop_id in self.get_property_ids():
                val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
                self.set_property(prop_id, val, restore_type)

            self.geom.reparent_to(self.model.origin)
            self.register()
            self.update_render_mode(self.model.is_selected())

        else:

            for prop_id in self.get_property_ids():
                if prop_id in data_ids:
                    val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
                    self.set_property(prop_id, val, restore_type)
                    data_ids.remove(prop_id)

    def get_property_ids(self, for_hist=False):

        return self._prop_ids + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "uv_set_names":
            return self._uv_set_names
        elif prop_id == "normal_flip":
            return self._normals_flipped
        elif prop_id == "normal_viz":
            return self._normals_shown
        elif prop_id == "normal_color":
            if for_remote_update:
                return [x for x in self._normal_color][:3]
            else:
                return self._normal_color
        elif prop_id == "normal_length":
            return self._normal_length

    def set_property(self, prop_id, value, restore=""):

        if prop_id == "uv_set_names":
            r = self.set_uv_set_names(value)
        elif prop_id == "normal_flip":
            r = self.flip_normals(value)
        elif prop_id == "normal_viz":
            r = self.show_normals(value)
        elif prop_id == "normal_color":
            if restore:
                self.set_normal_color(value)
            else:
                r, g, b = value
                color = (r, g, b, 1.)
                r = self.set_normal_color(color)
                Mgr.update_remotely("selected_obj_prop", "basic_geom", prop_id, value)
        elif prop_id == "normal_length":
            r = self.set_normal_length(value)

        if restore:
            Mgr.update_remotely("selected_obj_prop", "basic_geom", prop_id, value)
        else:
            return r

    def __define_geom_data(self):

        geom_data = []
        coords = []

        geom = self.geom.node().get_geom(0)
        vertex_data = geom.get_vertex_data()
        vertex_format = vertex_data.format
        pos_reader = GeomVertexReader(vertex_data, "vertex")
        normal_reader = GeomVertexReader(vertex_data, "normal")
        col_reader = GeomVertexReader(vertex_data, "color")

        uv_set_list = [InternalName.get_texcoord()]
        uv_set_list += [InternalName.get_texcoord_name(str(i)) for i in range(1, 8)]
        uv_readers = []

        for uv_set_id in range(8):
            uv_reader = GeomVertexReader(vertex_data, uv_set_list[uv_set_id])
            uv_readers.append(uv_reader)

        extracted_data = {}
        indices = geom.get_primitive(0).get_vertex_list()
        f = -1. if self.has_flipped_normals() else 1.

        if self.has_flipped_normals():
            indices = indices[::-1]

        for rows in (indices[i:i+3] for i in range(0, len(indices), 3)):

            tri_data = []

            for row in rows:

                if row in extracted_data:

                    vert_data = extracted_data[row]

                else:

                    vert_data = {}
                    pos_reader.set_row(row)
                    pos = Point3(pos_reader.get_data3())

                    for crd in coords:
                        if pos == crd:
                            pos = crd
                            break
                    else:
                        coords.append(pos)

                    vert_data["pos"] = pos
                    normal_reader.set_row(row)
                    vert_data["normal"] = Vec3(normal_reader.get_data3()) * f
                    col_reader.set_row(row)
                    vert_data["color"] = tuple(x for x in col_reader.get_data4())

                    uvs = {}

                    for uv_set_id, uv_reader in enumerate(uv_readers):
                        uv_reader.set_row(row)
                        u, v = uv_reader.get_data2()
                        uvs[uv_set_id] = (u, v)

                    vert_data["uvs"] = uvs
                    extracted_data[row] = vert_data

                tri_data.append(vert_data)

            poly_data = {"tris": [tri_data], "smoothing": [(0, False)]}
            geom_data.append(poly_data)

        return geom_data

    def __cancel_geometry_unlock(self, info):

        if self._geometry_unlock_started:
            self.model.geom_obj.geom_data_obj.cancel_creation()
        elif self._geometry_unlock_ended:
            self.model.geom_obj.geom_data_obj.destroy(unregister=False)

        if info == "geometry_unlock":
            self.model.geom_obj = self

    def unlock_geometry(self, editable_geom):

        obj_id = self.toplevel_obj.id
        id_str = str(obj_id) + "_geom_data"
        handler = self.__cancel_geometry_unlock
        Mgr.add_notification_handler("long_process_cancelled", id_str, handler, once=True)
        task = lambda: Mgr.remove_notification_handler("long_process_cancelled", id_str)
        task_id = "remove_notification_handler"
        PendingTasks.add(task, task_id, "object", id_prefix=id_str, sort=100)

        Mgr.do("create_registry_backups")
        Mgr.do("create_id_range_backups")
        Mgr.do("update_picking_col_id_ranges")
        Mgr.update_locally("screenshot_removal")

        def task():

            self._geometry_unlock_started = True
            self._geometry_unlock_ended = False

            geom_data = self.__define_geom_data()
            poly_count = len(geom_data)
            progress_steps = (poly_count // 20) * 4
            gradual = progress_steps > 80

            if gradual:
                Mgr.update_remotely("screenshot", "create")
                GD["progress_steps"] = progress_steps

            geom_data_obj = editable_geom.geom_data_obj
            editable_geom.geom_data_obj = geom_data_obj

            for step in geom_data_obj.process_geom_data(geom_data, gradual=gradual):
                if gradual:
                    yield True

            geom_data_obj.init_normal_sharing()
            geom_data_obj.update_smoothing()

            for step in geom_data_obj.create_geometry("editable", gradual=gradual):
                if gradual:
                    yield True

            if self.has_flipped_normals():
                geom_data_obj.flip_normals(delay=False)

            geom_data_obj.finalize_geometry()
            geom_data_obj.update_poly_centers()
            geom_data_obj.register(restore=False)

            if self.model.has_tangent_space():
                geom_data_obj.init_tangent_space()

            geom_data_obj.init_normal_length()
            geom_data_obj.init_normal_sharing()
            geom_data_obj.update_smoothing()
            geom_data_obj.set_initial_vertex_colors()

            self._geometry_unlock_started = False
            self._geometry_unlock_ended = True

            Mgr.notify("pickable_geom_altered", self.toplevel_obj)

            yield False

        task_id = "set_geom_data"
        descr = "Unlocking geometry..."
        PendingTasks.add(task, task_id, "object", id_prefix=obj_id, gradual=True,
                         process_id="geometry_unlock", descr=descr, cancellable=True)

        def task():

            self.destroy()
            self.model.bbox.color = (1., 1., 1., 1.)

        task_id = "set_geom_data"
        PendingTasks.add(task, task_id, "object", 99, id_prefix=obj_id)

    def make_pickable(self, mask_index=0, pickable=True, show_through=True):

        mask = Mgr.get("picking_mask", mask_index)
        geom = self.geom

        if pickable:
            geom.show_through(mask) if show_through else geom.show(mask)
        else:
            geom.hide(mask)


class BasicGeomManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "basic_geom", self.__create, "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("basic_geom")

        self._id_generator = id_generator()

        Mgr.add_app_updater("uv_set_id", self.__update_uv_set_id)
        Mgr.add_app_updater("uv_set_name", self.__set_uv_set_name)
        Mgr.add_app_updater("normal_viz", self.__show_normals)
        Mgr.add_app_updater("normal_color", self.__set_normal_color)

        BasicGeom.init_render_states()

    def __create(self, geom, name, materials=None):

        model_id = ("basic_geom",) + next(self._id_generator)
        model = Mgr.do("create_model", model_id, name, Point3(), (.7, .7, 1., 1.))
        picking_col_id = self.get_next_picking_color_id()
        basic_geom = BasicGeom(model, geom, picking_col_id, materials)

        return basic_geom

    def __update_uv_set_id(self):

        selection = Mgr.get("selection_top")

        if len(selection) == 1:
            obj = selection[0]
            uv_set_names = obj.geom_obj.get_uv_set_names()
            Mgr.update_remotely("uv_set_name", uv_set_names)

    def __set_uv_set_name(self, uv_set_id, uv_set_name):

        selection = Mgr.get("selection_top")
        changed_objs = []

        for obj in selection:
            if obj.geom_obj.set_uv_set_name(uv_set_id, uv_set_name):
                changed_objs.append(obj)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in changed_objs:
            obj_data[obj.id] = obj.get_data_to_store("prop_change", "uv_set_names")

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'Change UV set name {uv_set_id} of "{obj.name}"'
            event_descr += f'\nto "{obj.geom_obj.get_uv_set_names()[uv_set_id]}"'
        else:
            event_descr = f'Change UV set name {uv_set_id} of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __show_normals(self, show=True):

        selection = Mgr.get("selection_top")
        changed_objs = []

        for obj in selection:
            if obj.geom_obj.show_normals(show):
                changed_objs.append(obj)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in changed_objs:
            obj_data[obj.id] = obj.get_data_to_store("prop_change", "normal_viz")

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'{"Show" if show else "Hide"} normals of "{obj.name}"'
        else:
            event_descr = f'{"Show" if show else "Hide"} normals of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __set_normal_color(self, color_values):

        r, g, b = color_values[:3]
        selection = Mgr.get("selection_top")
        changed_objs = []

        for obj in selection:
            if obj.geom_obj.set_property("normal_color", color_values[:3]):
                changed_objs.append(obj)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in changed_objs:
            obj_data[obj.id] = obj.get_data_to_store("prop_change", "normal_color")

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'Change normal color of "{obj.name}"'
            event_descr += f'\nto R:{r :.3f} | G:{g :.3f} | B:{b :.3f}'
        else:
            event_descr = 'Change normal color of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])
            event_descr += f'\n\nto R:{r :.3f} | G:{g :.3f} | B:{b :.3f}'

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(BasicGeomManager)
