from .base import *
from .transform import SelectionTransformBase


class Selection(SelectionTransformBase):

    def __init__(self):

        SelectionTransformBase.__init__(self)

        self._objs = []
        self._prev_obj_ids = set()

    def __getitem__(self, index):

        try:
            return self._objs[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __len__(self):

        return len(self._objs)

    def reset(self):

        self._objs = []

    def get_toplevel_object(self, get_group=False):
        """ Return a random top-level object """

        if self._objs:
            return self._objs[0].get_toplevel_object(get_group)

    def clear_prev_obj_ids(self):

        self._prev_obj_ids = None

    def update_obj_props(self, force=False):

        obj_ids = set(obj.get_id() for obj in self._objs)

        if not force and obj_ids == self._prev_obj_ids:
            return

        names = OrderedDict()

        for obj in self._objs:
            names[obj.get_id()] = obj.get_name()

        Mgr.update_remotely("selected_obj_names", names)

        count = len(self._objs)

        if count == 1:
            sel = self._objs[0]

        sel_colors = set(obj.get_color() for obj in self._objs if obj.has_color())
        sel_color_count = len(sel_colors)

        if sel_color_count == 1:
            color = sel_colors.pop()
            color_values = [x for x in color][:3]
            Mgr.update_remotely("selected_obj_color", color_values)

        GlobalData["sel_color_count"] = sel_color_count
        Mgr.update_app("sel_color_count")

        type_checker = lambda obj, main_type: obj.get_geom_type() if main_type == "model" else main_type
        obj_types = set(type_checker(obj, obj.get_type()) for obj in self._objs)
        Mgr.update_app("selected_obj_types", tuple(obj_types))

        if count == 1:

            obj_type = obj_types.pop()

            for prop_id in sel.get_type_property_ids():
                value = sel.get_property(prop_id, for_remote_update=True)
                Mgr.update_remotely("selected_obj_prop", obj_type, prop_id, value)

        self._prev_obj_ids = obj_ids

        Mgr.update_app("selection_count")

    def update(self):

        self.update_center_pos()
        self.update_ui()
        self.update_obj_props()

    def add(self, objs, add_to_hist=True, update=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_add = set(objs)
        common = old_sel & sel_to_add

        if common:
            sel_to_add -= common

        if not sel_to_add:
            return False

        sel.extend(sel_to_add)

        for obj in sel_to_add:
            obj.update_selection_state()

        if update:
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            count = len(sel_to_add)

            if count == 1:
                obj = sel_to_add.copy().pop()
                event_descr = 'Select "{}"'.format(obj.get_name())
            else:
                event_descr = 'Select {:d} objects:\n'.format(count)
                event_descr += "".join(['\n    "{}"'.format(obj.get_name()) for obj in sel_to_add])

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in sel_to_add:
                obj_data[obj.get_id()] = {"selection_state": {"main": True}}

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def remove(self, objs, add_to_hist=True, update=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_remove = set(objs)
        common = old_sel & sel_to_remove

        if not common:
            return False

        for obj in common:
            sel.remove(obj)
            obj.update_selection_state(False)

        if update:
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            count = len(common)

            if count == 1:
                obj = common.copy().pop()
                event_descr = 'Deselect "{}"'.format(obj.get_name())
            else:
                event_descr = 'Deselect {:d} objects:\n'.format(count)
                event_descr += "".join(['\n    "{}"'.format(obj.get_name()) for obj in common])

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in common:
                obj_data[obj.get_id()] = {"selection_state": {"main": False}}

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def replace(self, objs, add_to_hist=True, update=True):

        sel = self._objs
        old_sel = set(sel)
        new_sel = set(objs)
        common = old_sel & new_sel

        if common:
            old_sel -= common
            new_sel -= common

        if not (old_sel or new_sel):
            return False

        for old_obj in old_sel:
            sel.remove(old_obj)
            old_obj.update_selection_state(False)

        for new_obj in new_sel:
            sel.append(new_obj)
            new_obj.update_selection_state()

        if update:
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            event_descr = ''
            old_count = len(old_sel)
            new_count = len(new_sel)

            if new_sel:

                if new_count == 1:

                    event_descr += 'Select "{}"'.format(new_sel.copy().pop().get_name())

                else:

                    event_descr += 'Select {:d} objects:\n'.format(new_count)

                    for new_obj in new_sel:
                        event_descr += '\n    "{}"'.format(new_obj.get_name())

            if old_sel:

                event_descr += '\n\n' if new_sel else ''

                if old_count == 1:

                    event_descr += 'Deselect "{}"'.format(old_sel.copy().pop().get_name())

                else:

                    event_descr += 'Deselect {:d} objects:\n'.format(old_count)

                    for old_obj in old_sel:
                        event_descr += '\n    "{}"'.format(old_obj.get_name())

            if event_descr:

                obj_data = {}
                event_data = {"objects": obj_data}

                for old_obj in old_sel:
                    obj_data[old_obj.get_id()] = {"selection_state": {"main": False}}

                for new_obj in new_sel:
                    obj_data[new_obj.get_id()] = {"selection_state": {"main": True}}

                # make undo/redoable
                Mgr.do("add_history", event_descr, event_data)

        return True

    def clear(self, add_to_hist=True, update=True):

        sel = self._objs

        if not sel:
            return False

        for obj in sel:
            obj.update_selection_state(False)

        sel = sel[:]
        self._objs = []

        if update:
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            obj_count = len(sel)

            if obj_count > 1:

                event_descr = 'Deselect {:d} objects:\n'.format(obj_count)

                for obj in sel:
                    event_descr += '\n    "{}"'.format(obj.get_name())

            else:

                event_descr = 'Deselect "{}"'.format(sel[0].get_name())

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in sel:
                obj_data[obj.get_id()] = {"selection_state": {"main": False}}

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def delete(self, add_to_hist=True, update=True):

        sel = self._objs

        if not sel:
            return False

        if update:
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            Mgr.do("update_history_time")
            obj_count = len(sel)

            if obj_count > 1:

                event_descr = 'Delete {:d} objects:\n'.format(obj_count)

                for obj in sel:
                    event_descr += '\n    "{}"'.format(obj.get_name())

            else:

                event_descr = 'Delete "{}"'.format(sel[0].get_name())

            obj_data = {}
            event_data = {"objects": obj_data}
            groups = set()

            for obj in sel:

                obj_data[obj.get_id()] = obj.get_data_to_store("deletion")
                group = obj.get_group()

                if group and group not in sel:
                    groups.add(group)

        for obj in sel[:]:
            obj.destroy(add_to_hist=add_to_hist)

        if add_to_hist:
            Mgr.do("prune_empty_groups", groups, obj_data)
            event_data["object_ids"] = set(Mgr.get("object_ids"))
            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        return True


class SelectionManager(BaseObject):

    def __init__(self):

        obj_root = Mgr.get("object_root")
        sel_pivot = obj_root.attach_new_node("selection_pivot")
        Mgr.expose("selection_pivot", lambda: sel_pivot)

        self._mouse_start_pos = ()
        self._mouse_end_pos = ()
        self._picked_point = None
        self._can_select_single = False
        self._selection_op = "replace"

        self._obj_id = None
        self._selection = Selection()
        self._pixel_under_mouse = None
        self._region_sel_cam = None
        self._region_sel_cancelled = False

        GlobalData.set_default("selection_count", 0)
        GlobalData.set_default("sel_color_count", 0)

        Mgr.expose("selection", self.__get_selection)
        Mgr.expose("selection_top", lambda: self._selection)
        Mgr.accept("select_top", self.__select_toplvl_obj)
        Mgr.accept("select_single_top", self.__select_single)
        Mgr.accept("init_region_select", self.__init_region_select)

        def force_cursor_update(transf_type):

            self._pixel_under_mouse = None  # force an update of the cursor
                                            # next time self.__update_cursor()
                                            # is called

        Mgr.add_app_updater("active_transform_type", force_cursor_update)
        Mgr.add_app_updater("active_obj_level", self.__update_active_selection,
                            kwargs=["restore"])
        Mgr.add_app_updater("object_selection", self.__update_object_selection)
        Mgr.accept("update_active_selection", self.__update_active_selection)

        add_state = Mgr.add_state
        add_state("selection_mode", 0, self.__enter_selection_mode,
                  self.__exit_selection_mode)
        add_state("region_selection_mode", -11, self.__enter_region_selection_mode,
                  self.__exit_region_selection_mode)
        add_state("checking_mouse_offset", -1, self.__start_mouse_check)

        mod_alt = GlobalData["mod_key_codes"]["alt"]
        mod_ctrl = GlobalData["mod_key_codes"]["ctrl"]
        mod_shift = GlobalData["mod_key_codes"]["shift"]
        bind = Mgr.bind_state
        bind("selection_mode", "replace selection", "mouse1", self.__init_select)
        bind("selection_mode", "add to selection", "{:d}|mouse1".format(mod_ctrl),
             lambda: self.__init_select(op="add"))
        bind("selection_mode", "remove from selection", "{:d}|mouse1".format(mod_shift),
             lambda: self.__init_select(op="remove"))
        bind("selection_mode", "toggle-select", "{:d}|mouse1".format(mod_ctrl | mod_shift),
             lambda: self.__init_select(op="toggle"))
        bind("selection_mode", "region-select (replace)", "{:d}|mouse1".format(mod_alt),
             self.__init_region_select)
        bind("selection_mode", "region-select (add)", "{:d}|mouse1".format(mod_alt | mod_ctrl),
             lambda: self.__init_region_select(op="add"))
        bind("selection_mode", "region-select (remove)", "{:d}|mouse1".format(mod_alt | mod_shift),
             lambda: self.__init_region_select(op="remove"))
        bind("selection_mode", "region-select (toggle)", "{:d}|mouse1".format(mod_alt | mod_ctrl | mod_shift),
             lambda: self.__init_region_select(op="toggle"))
        bind("selection_mode", "select -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("selection_mode", "access obj props", "mouse3", self.__access_obj_props)
        bind("selection_mode", "del selection",
             "delete", self.__delete_selection)
        bind("selection_mode", "transf off", "q",
             self.__set_active_transform_off)
        bind("region_selection_mode", "cancel region-select", "mouse3-up",
             self.__cancel_region_selection)
        bind("region_selection_mode", "exit region-select", "mouse1-up",
             lambda: Mgr.exit_state("region_selection_mode"))

        def cancel_mouse_check():

            Mgr.enter_state("selection_mode")
            self.__cancel_mouse_check()

        bind("checking_mouse_offset", "cancel mouse check",
             "mouse1-up", cancel_mouse_check)

        GlobalData["status_data"]["select"] = status_data = {}
        info_start = "<Space> to navigate; (<Alt>-)LMB to (region-)select; <Del> to delete selection; "
        info_text = info_start + "<W>, <E>, <R> to set transform type"
        status_data[""] = {"mode": "Select", "info": info_text}
        info_idle = info_start + "LMB-drag selection or gizmo handle to transform;" \
            " <Q> to disable transforms"
        info_text = "LMB-drag to transform selection; RMB to cancel transformation"

        for transf_type in ("translate", "rotate", "scale"):
            mode_text = "Select and {}".format(transf_type)
            status_data[transf_type] = {}
            status_data[transf_type]["idle"] = {"mode": mode_text, "info": info_idle}
            status_data[transf_type]["in_progress"] = {"mode": mode_text, "info": info_text}

    def setup(self):

        if "picking_camera_ok" not in MainObjects.get_setup_results():
            return False

        root = Mgr.get("object_root")
        cam = Camera("region_selection_cam")
        cam.set_active(False)
        cam.set_scene(root)
        self._region_sel_cam = self.cam().attach_new_node(cam)
        self._selection_border = self.__create_selection_border()
        self._selection_border_pos = ()
        self._region_sel_uvs = False

        picking_mask = Mgr.get("picking_mask")
        self._selection_border.hide(picking_mask)

        return True

    def __create_selection_border(self):

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("selection_border", vertex_format, Geom.UH_dynamic)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.add_data3f(0., 0., 0.)
        pos_writer.add_data3f(0., 0., 1.)
        pos_writer.add_data3f(1., 0., 1.)
        pos_writer.add_data3f(1., 0., 0.)
        lines = GeomLines(Geom.UH_static)
        lines.add_vertices(0, 1)
        lines.add_vertices(1, 2)
        lines.add_vertices(2, 3)
        lines.add_vertices(3, 0)

        state_np = NodePath("state_np")
        state_np.set_depth_test(False)
        state_np.set_depth_write(False)
        state_np.set_bin("fixed", 101)
        state1 = state_np.get_state()
        state_np.set_bin("fixed", 100)
        state_np.set_color((0., 0., 0., 1.))
        state_np.set_render_mode_thickness(3)
        state2 = state_np.get_state()
        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        geom_node = GeomNode("selection_border")
        geom_node.add_geom(geom, state1)
        geom = geom.make_copy()
        geom_node.add_geom(geom, state2)

        return NodePath(geom_node)

    def __draw_selection_border(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        self._mouse_end_pos = self.mouse_watcher.get_mouse()
        x, y = self._selection_border_pos
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = -mouse_pointer.get_y()
        sx = mouse_x - x
        sx = .001 if abs(sx) < .001 else sx
        sy = mouse_y - y
        sy = .001 if abs(sy) < .001 else sy
        self._selection_border.set_scale(sx, 1., sy)

        return task.cont

    def __enter_region_selection_mode(self, prev_state_id, is_active):

        if not self.mouse_watcher.has_mouse():
            return

        screen_pos = self.mouse_watcher.get_mouse()
        self._mouse_start_pos = (screen_pos.x, screen_pos.y)

        x, y = GlobalData["viewport"]["pos_aux" if GlobalData["viewport"][2] == "main" else "pos"]
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = -mouse_pointer.get_y()
        self._selection_border_pos = (mouse_x, mouse_y)
        self._selection_border.reparent_to(self.viewport)
        self._selection_border.set_pos(mouse_x - x, 0., mouse_y + y)

        self._region_sel_uvs = prev_state_id == "uv_edit_mode"

        Mgr.add_task(self.__draw_selection_border, "draw_selection_border", sort=3)

    def __exit_region_selection_mode(self, next_state_id, is_active):

        Mgr.remove_task("draw_selection_border")
        self._selection_border.detach_node()
        x1, y1 = self._mouse_start_pos
        x2, y2 = self._mouse_end_pos
        x1 = .5 + x1 * .5
        y1 = .5 + y1 * .5
        x2 = max(0., min(1., .5 + x2 * .5))
        y2 = max(0., min(1., .5 + y2 * .5))
        l, r = min(x1, x2), max(x1, x2)
        b, t = min(y1, y2), max(y1, y2)
        self.__region_select((l, r, b, t))

    def __cancel_region_selection(self):

        self._region_sel_cancelled = True
        Mgr.exit_state("region_selection_mode")
        self._region_sel_cancelled = False

    def __init_region_select(self, op="replace"):

        self._selection_op = op
        Mgr.enter_state("region_selection_mode")

    def __region_select(self, frame):

        if self._region_sel_cancelled:
            return

        lens = self.cam.lens
        w, h = lens.get_film_size()
        l, r, b, t = frame
        # compute film size and offset
        w_f = (r - l) * w
        h_f = (t - b) * h
        x_f = ((r + l) * .5 - .5) * w
        y_f = ((t + b) * .5 - .5) * h
        w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "main" else "size"]
        # compute buffer size
        w_b = int(round((r - l) * w))
        h_b = int(round((t - b) * h))

        if min(w_b, h_b) < 2:
            return

        Mgr.get("picking_cam").set_active(False)

        focal_len = lens.get_focal_length()
        lens = lens.make_copy()
        lens.set_film_size(w_f, h_f)
        lens.set_film_offset(x_f, y_f)
        lens.set_focal_length(focal_len)
        picking_mask = Mgr.get("picking_mask")
        cam_np = self._region_sel_cam
        cam = cam_np.node()
        cam.set_lens(lens)
        cam.set_camera_mask(picking_mask)
        base = Mgr.get("base")
        bfr = base.win.make_texture_buffer("tex_buffer", w_b, h_b, Texture(""))
        cam.set_active(True)
        base.make_camera(bfr, useCamera=cam_np)
        ge = base.graphics_engine

        ctrl_down = self.mouse_watcher.is_button_down(KeyboardButton.control())
        shift_down = self.mouse_watcher.is_button_down(KeyboardButton.shift())

        if ctrl_down:
            op = "toggle" if shift_down else "add"
        elif shift_down:
            op = "remove"
        else:
            op = self._selection_op

        obj_lvl = GlobalData["active_obj_level"]

        if self._region_sel_uvs:

            Mgr.do("region_select_uvs", cam, op)

        elif obj_lvl == "top":

            Mgr.do("make_point_helpers_pickable", False)

            objs = Mgr.get("objects", "top")
            obj_count = len(objs)

            tex = Texture()
            tex.setup_1d_texture(obj_count, Texture.T_int, Texture.F_r32i)
            tex.set_clear_color(0)
            shaders = shader.region_sel
            vs = shaders.VERT_SHADER
            fs = shaders.FRAG_SHADER
            sh = Shader.make(Shader.SL_GLSL, vs, fs)
            state_np = NodePath("state_np")
            state_np.set_shader(sh, 1)
            state_np.set_shader_input("selections", tex, read=False, write=True, priority=1)
            state_np.set_light_off(1)
            state = state_np.get_state()
            cam.set_initial_state(state)

            for i, obj in enumerate(objs):
                obj.get_pivot().set_shader_input("index", i)

            Mgr.update_locally("region_picking", True)

            new_sel = set()
            ge.render_frame()

            if ge.extract_texture_data(tex, base.win.get_gsg()):

                texels = memoryview(tex.get_ram_image()).cast("I")

                for i, mask in enumerate(texels):
                    for j in range(32):
                        if mask & (1 << j):
                            index = 32 * i + j
                            new_sel.add(objs[index].get_toplevel_object(get_group=True))

            state_np.clear_shader()
            Mgr.update_locally("region_picking", False)
            Mgr.do("make_point_helpers_pickable")
            Mgr.do("region_select_point_helpers", cam, new_sel)

            if op == "replace":
                self._selection.replace(new_sel)
            elif op == "add":
                self._selection.add(new_sel)
            elif op == "remove":
                self._selection.remove(new_sel)
            elif op == "toggle":
                old_sel = set(self._selection)
                self._selection.remove(old_sel & new_sel)
                self._selection.add(new_sel - old_sel)

        else:

            Mgr.do("region_select_subobjs", cam, op)

        cam.set_active(False)
        ge.remove_window(bfr)
        Mgr.get("picking_cam").set_active()

    def __get_selection(self, obj_lvl=""):

        lvl = obj_lvl if obj_lvl else GlobalData["active_obj_level"]

        return Mgr.get("selection_" + lvl)

    def __enter_selection_mode(self, prev_state_id, is_active):

        Mgr.add_task(self.__update_cursor, "update_cursor")
        Mgr.do("enable_transf_gizmo")

        transf_type = GlobalData["active_transform_type"]

        if transf_type:
            Mgr.update_app("status", ["select", transf_type, "idle"])
        else:
            Mgr.update_app("status", ["select", ""])

    def __exit_selection_mode(self, next_state_id, is_active):

        if next_state_id != "checking_mouse_offset":
            self._pixel_under_mouse = None  # force an update of the cursor
                                            # next time self.__update_cursor()
                                            # is called
            Mgr.remove_task("update_cursor")
            Mgr.set_cursor("main")

        Mgr.do("enable_transf_gizmo", False)

    def __set_active_transform_off(self):

        GlobalData["active_transform_type"] = ""
        Mgr.update_app("active_transform_type", "")
        Mgr.update_app("status", ["select", ""])

    def __update_active_selection(self, restore=False):

        obj_lvl = GlobalData["active_obj_level"]

        if obj_lvl != "top":

            self._selection.clear_prev_obj_ids()
            Mgr.do("update_selection_" + obj_lvl)

            toplvl_obj = self.__get_selection(obj_lvl).get_toplevel_object()

            if toplvl_obj:

                cs_type = GlobalData["coord_sys_type"]
                tc_type = GlobalData["transf_center_type"]

                if cs_type == "local":
                    Mgr.update_locally("coord_sys", cs_type, toplvl_obj)

                if tc_type == "pivot":
                    Mgr.update_locally("transf_center", tc_type, toplvl_obj)

        if restore:
            task = lambda: self.__get_selection().update()
            PendingTasks.add(task, "update_selection", "ui")
        else:
            self.__get_selection().update()

    def __update_object_selection(self, object_id, op="replace"):

        obj = Mgr.get("object", object_id)
        selection = self._selection

        if op == "replace":
            selection.replace([obj])
        elif op == "remove":
            selection.remove([obj])

    def __delete_selection(self):

        selection = self.__get_selection()

        if selection.delete():
            Mgr.do("update_picking_col_id_ranges")

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            cursor_id = "main"

            if pixel_under_mouse != VBase4():

                if (GlobalData["active_obj_level"] == "edge" and
                        GlobalData["subobj_edit_options"]["sel_edges_by_border"]):

                    r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    pickable_type = PickableTypes.get(a)

                    if pickable_type == "transf_gizmo":

                        cursor_id = "select"

                    elif GlobalData["subobj_edit_options"]["pick_via_poly"]:

                        poly = Mgr.get("poly", color_id)

                        if poly:

                            merged_edges = poly.get_geom_data_object().get_merged_edges()

                            for edge_id in poly.get_edge_ids():
                                if len(merged_edges[edge_id]) == 1:
                                    cursor_id = "select"
                                    break

                    else:

                        edge = Mgr.get("edge", color_id)
                        merged_edge = edge.get_merged_edge() if edge else None

                        if merged_edge and len(merged_edge) == 1:
                            cursor_id = "select"

                else:

                    cursor_id = "select"

                if cursor_id == "select":

                    active_transform_type = GlobalData["active_transform_type"]

                    if active_transform_type:
                        cursor_id = active_transform_type

            Mgr.set_cursor(cursor_id)
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __check_mouse_offset(self, task):
        """
        Delay start of transformation until user has moved mouse at least 3 pixels
        in any direction, to avoid accidental transforms.

        """

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = mouse_pointer.get_y()
        mouse_start_x, mouse_start_y = self._mouse_start_pos

        if max(abs(mouse_x - mouse_start_x), abs(mouse_y - mouse_start_y)) > 3:
            if self._picked_point:
                Mgr.do("init_transform", self._picked_point)
                return task.done

        return task.cont

    def __start_mouse_check(self, prev_state_id, is_active):

        Mgr.add_task(self.__check_mouse_offset, "check_mouse_offset")
        Mgr.remove_task("update_cursor")

    def __cancel_mouse_check(self):

        Mgr.remove_task("check_mouse_offset")

        active_transform_type = GlobalData["active_transform_type"]

        if active_transform_type == "rotate" \
                and GlobalData["axis_constraints"]["rotate"] == "trackball":
            prev_constraints = GlobalData["prev_axis_constraints_rotate"]
            Mgr.update_app("axis_constraints", "rotate", prev_constraints)

        if self._can_select_single:
            obj_lvl = GlobalData["active_obj_level"]
            Mgr.do("select_single_" + obj_lvl)

    def __get_picked_object(self, color_id, obj_type_id):

        if not color_id:
            return "", None

        pickable_type = PickableTypes.get(obj_type_id)

        if not pickable_type:
            return "", None

        if pickable_type == "transf_gizmo":
            return "transf_gizmo", Mgr.do("select_transf_gizmo_handle", color_id)

        picked_obj = Mgr.get(pickable_type, color_id)

        return (pickable_type, picked_obj) if picked_obj else ("", None)

    def __init_select(self, op="replace"):

        if not (self.mouse_watcher.has_mouse() and self._pixel_under_mouse):
            return

        self._can_select_single = False
        screen_pos = Point2(self.mouse_watcher.get_mouse())
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        self._mouse_start_pos = (mouse_pointer.get_x(), mouse_pointer.get_y())
        obj_lvl = GlobalData["active_obj_level"]

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b
        pickable_type, picked_obj = self.__get_picked_object(color_id, a)

        if (GlobalData["active_transform_type"] and obj_lvl != pickable_type == "poly"
                and GlobalData["subobj_edit_options"]["pick_via_poly"]):
            Mgr.do("init_selection_via_poly", picked_obj, op)
            return

        self._picked_point = picked_obj.get_point_at_screen_pos(screen_pos) if picked_obj else None

        if pickable_type == "transf_gizmo":
            Mgr.enter_state("checking_mouse_offset")
            return

        can_select_single, start_mouse_checking = Mgr.do("select_" + obj_lvl, picked_obj, op)

        self._can_select_single = can_select_single

        if start_mouse_checking:
            Mgr.enter_state("checking_mouse_offset")

    def __select_toplvl_obj(self, picked_obj, op):

        obj = picked_obj.get_toplevel_object(get_group=True) if picked_obj else None
        self._obj_id = obj.get_id() if obj else None
        r = self.__select(op)
        selection = self._selection

        if not (obj and obj in selection):
            obj = selection[0] if selection else None

        if obj:

            cs_type = GlobalData["coord_sys_type"]
            tc_type = GlobalData["transf_center_type"]

            if cs_type == "local":
                Mgr.update_locally("coord_sys", cs_type, obj)

            if tc_type == "pivot":
                Mgr.update_locally("transf_center", tc_type, obj)

        return r

    def __select(self, op):

        obj = Mgr.get("object", self._obj_id)
        selection = self._selection
        can_select_single = False
        start_mouse_checking = False

        if obj:

            if op == "replace":

                if GlobalData["active_transform_type"]:

                    if obj in selection and len(selection) > 1:

                        # When the user clicks one of multiple selected objects, updating the
                        # selection must be delayed until it is clear whether he wants to
                        # transform the entire selection or simply have only this object
                        # selected (this is determined by checking if the mouse has moved at
                        # least a certain number of pixels by the time the left mouse button
                        # is released).

                        can_select_single = True

                    else:

                        selection.replace([obj])

                    start_mouse_checking = True

                else:

                    selection.replace([obj])

            elif op == "add":

                if obj not in selection:
                    selection.add([obj])

                transform_allowed = GlobalData["active_transform_type"]

                if transform_allowed:
                    start_mouse_checking = True

            elif op == "remove":

                if obj in selection:
                    selection.remove([obj])

            elif op == "toggle":

                if obj in selection:
                    selection.remove([obj])
                    transform_allowed = False
                else:
                    selection.add([obj])
                    transform_allowed = GlobalData["active_transform_type"]

                if transform_allowed:
                    start_mouse_checking = True

        elif op == "replace":

            selection.clear()

        return can_select_single, start_mouse_checking

    def __select_single(self):

        # If multiple objects were selected and no transformation occurred, a single
        # object has been selected out of that previous selection.

        obj = Mgr.get("object", self._obj_id)
        self._selection.replace([obj])

    def __access_obj_props(self):

        obj_lvl = GlobalData["active_obj_level"]

        if obj_lvl != "top" or not self.mouse_watcher.has_mouse():
            return

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b
        pickable_type = PickableTypes.get(a)

        if not pickable_type or pickable_type == "transf_gizmo":
            return

        picked_obj = Mgr.get(pickable_type, color_id)
        obj = picked_obj.get_toplevel_object(get_group=True) if picked_obj else None

        if obj:
            Mgr.update_remotely("obj_props_access", obj.get_id())


MainObjects.add_class(SelectionManager)
