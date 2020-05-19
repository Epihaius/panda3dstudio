from .base import *
from .transform import TransformMixin


class Selection(TransformMixin):

    def __init__(self):

        TransformMixin.__init__(self)

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

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def clear_prev_obj_ids(self):

        self._prev_obj_ids = None

    def update_obj_props(self, force=False):

        obj_ids = set(obj.id for obj in self._objs)

        if not force and obj_ids == self._prev_obj_ids:
            return

        names = {obj.id: obj.name for obj in self._objs}
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

        GD["sel_color_count"] = sel_color_count
        Mgr.update_app("sel_color_count")

        type_checker = lambda obj, main_type: obj.geom_type if main_type == "model" else main_type
        obj_types = set(type_checker(obj, obj.type) for obj in self._objs)
        Mgr.update_app("selected_obj_types", tuple(obj_types))

        if count == 1:

            obj_type = obj_types.pop()

            for prop_id in sel.get_type_property_ids():
                value = sel.get_property(prop_id, for_remote_update=True)
                Mgr.update_remotely("selected_obj_prop", obj_type, prop_id, value)

        self._prev_obj_ids = obj_ids

        Mgr.update_app("selection_count")

    def update(self, hide_sets=False):

        self.update_center_pos()
        self.update_ui()
        self.update_obj_props()

        if hide_sets:
            Mgr.update_remotely("selection_set", "hide_name")

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
                event_descr = f'Select "{obj.name}"'
            else:
                event_descr = f'Select {count} objects:\n'
                event_descr += "".join([f'\n    "{obj.name}"' for obj in sel_to_add])

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in sel_to_add:
                obj_data[obj.id] = {"selection_state": {"main": True}}

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
                event_descr = f'Deselect "{obj.name}"'
            else:
                event_descr = f'Deselect {count} objects:\n'
                event_descr += "".join([f'\n    "{obj.name}"' for obj in common])

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in common:
                obj_data[obj.id] = {"selection_state": {"main": False}}

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

                    event_descr += f'Select "{new_sel.copy().pop().name}"'

                else:

                    event_descr += f'Select {new_count} objects:\n'

                    for new_obj in new_sel:
                        event_descr += f'\n    "{new_obj.name}"'

            if old_sel:

                event_descr += '\n\n' if new_sel else ''

                if old_count == 1:

                    event_descr += f'Deselect "{old_sel.copy().pop().name}"'

                else:

                    event_descr += f'Deselect {old_count} objects:\n'

                    for old_obj in old_sel:
                        event_descr += f'\n    "{old_obj.name}"'

            if event_descr:

                obj_data = {}
                event_data = {"objects": obj_data}

                for old_obj in old_sel:
                    obj_data[old_obj.id] = {"selection_state": {"main": False}}

                for new_obj in new_sel:
                    obj_data[new_obj.id] = {"selection_state": {"main": True}}

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

                event_descr = f'Deselect {obj_count} objects:\n'

                for obj in sel:
                    event_descr += f'\n    "{obj.name}"'

            else:

                event_descr = f'Deselect "{sel[0].name}"'

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in sel:
                obj_data[obj.id] = {"selection_state": {"main": False}}

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

                event_descr = f'Delete {obj_count} objects:\n'

                for obj in sel:
                    event_descr += f'\n    "{obj.name}"'

            else:

                event_descr = f'Delete "{sel[0].name}"'

            obj_data = {}
            event_data = {"objects": obj_data}
            groups = set()

            for obj in sel:

                obj_data[obj.id] = obj.get_data_to_store("deletion")
                group = obj.group

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


class SelectionManager:

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
        sel_sets = {"top": {}, "vert": {}, "normal": {}, "edge": {}, "poly": {},
                    "uv_vert": {}, "uv_edge": {}, "uv_poly": {}, "uv_part": {}}
        sel_names = {"top": {}, "vert": {}, "normal": {}, "edge": {}, "poly": {},
                     "uv_vert": {}, "uv_edge": {}, "uv_poly": {}, "uv_part": {}}
        self._selection_sets = {"sets": sel_sets, "names": sel_names}
        self._pixel_under_mouse = None

        self.__setup_selection_mask()
        prim_types = ("square", "square_centered", "circle", "circle_centered")
        alt_prim_types = ("rect", "rect_centered", "ellipse", "ellipse_centered")
        self._selection_shapes = shapes = {}

        for shape_type in prim_types:
            shapes[shape_type] = self.__create_selection_shape(shape_type)

        for alt_shape_type, shape_type in zip(alt_prim_types, prim_types):
            shapes[alt_shape_type] = shapes[shape_type]

        shapes["paint"] = shapes["circle_centered"]
        self._sel_brush_size = 50.
        self._sel_brush_size_stale = False

        # Create a card to visualize the interior area of a free-form selection
        # shape; the mask texture used as input for the selection shader will be
        # applied to this card.

        cm = CardMaker("selection_shape_tex_card")
        cm.set_frame(0., 1., -1., 0.)
        card = NodePath(cm.generate())
        card.set_depth_test(False)
        card.set_depth_write(False)
        card.set_bin("fixed", 99)
        card.set_transparency(TransparencyAttrib.M_alpha)
        self._sel_shape_tex_card = card

        self._sel_shape_pos = ()
        self._region_center_pos = ()
        self._region_sel_uvs = False
        self._region_sel_cancelled = False
        self._fence_initialized = False
        self._fence_points = None
        self._fence_point_color_id = 1
        self._fence_point_coords = {}
        self._fence_mouse_coords = [[], []]
        self._fence_point_pick_lens = lens = OrthographicLens()
        lens.film_size = 30.
        lens.near = -10.

        GD.set_default("selection_count", 0)
        GD.set_default("sel_color_count", 0)

        Mgr.expose("selection", self.__get_selection)
        Mgr.expose("selection_top", lambda: self._selection)
        Mgr.expose("selection_sets", lambda: self._selection_sets)
        Mgr.expose("selection_shapes", lambda: self._selection_shapes)
        Mgr.expose("free_selection_shape", lambda: self.__create_selection_shape("free"))
        sel_mask_data = {
                         "root": self._sel_mask_root,
                         "geom_root": self._sel_mask_geom_root,
                         "cam": self._sel_mask_cam,
                         "triangle": self._sel_mask_triangle,
                         "background": self._sel_mask_background,
                         "shape_tex_card": self._sel_shape_tex_card
                        }
        Mgr.expose("selection_mask_data", lambda: sel_mask_data)
        Mgr.accept("select_top", self.__select_toplvl_obj)
        Mgr.accept("select_single_top", self.__select_single)
        Mgr.accept("init_region_select", self.__init_region_select)
        Mgr.accept("set_selection_sets", self.__set_selection_sets)

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

        mod_alt = GD["mod_key_codes"]["alt"]
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        mod_shift = GD["mod_key_codes"]["shift"]
        bind = Mgr.bind_state
        bind("selection_mode", "select (replace)", "mouse1", self.__init_select)
        bind("selection_mode", "select (add)", f"{mod_ctrl}|mouse1",
             lambda: self.__init_select(op="add"))
        bind("selection_mode", "select (remove)", f"{mod_shift}|mouse1",
             lambda: self.__init_select(op="remove"))
        bind("selection_mode", "select (toggle)", f"{mod_ctrl | mod_shift}|mouse1",
             lambda: self.__init_select(op="toggle"))
        bind("selection_mode", "select (replace) alt", f"{mod_alt}|mouse1",
             self.__init_select)
        bind("selection_mode", "select (add) alt", f"{mod_alt | mod_ctrl}|mouse1",
             lambda: self.__init_select(op="add"))
        bind("selection_mode", "select (remove) alt", f"{mod_alt | mod_shift}|mouse1",
             lambda: self.__init_select(op="remove"))
        bind("selection_mode", "select (toggle) alt", f"{mod_alt | mod_ctrl | mod_shift}|mouse1",
             lambda: self.__init_select(op="toggle"))
        bind("selection_mode", "select -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("selection_mode", "handle right-click", "mouse3", self.__on_right_click)
        bind("selection_mode", "handle ctrl-right-click", f"{mod_ctrl}|mouse3",
             self.__on_right_click)
        bind("selection_mode", "del selection", "delete", self.__delete_selection)
        bind("region_selection_mode", "quit region-select", "escape",
             self.__cancel_region_select)
        bind("region_selection_mode", "cancel region-select", "mouse3",
             self.__cancel_region_select)
        bind("region_selection_mode", "abort region-select", "focus_loss",
             self.__cancel_region_select)
        bind("region_selection_mode", "handle region-select mouse1-up", "mouse1-up",
             self.__handle_region_select_mouse_up)

        def cancel_mouse_check():

            Mgr.enter_state("selection_mode")
            self.__cancel_mouse_check()

        bind("checking_mouse_offset", "cancel mouse check",
             "mouse1-up", cancel_mouse_check)

        GD["status"]["select"] = status_data = {}
        info_start = "<Space> to navigate; (<Alt>-)LMB to (region-)select; <Del> to delete selection; "
        info_text = info_start + "<W>, <E>, <R> to set transform type"
        status_data[""] = {"mode": "Select", "info": info_text}
        info_idle = "{}" + info_start + "LMB-drag selection or gizmo handle to {};" \
            " <Q> to disable transforms"
        info_text = "LMB-drag to transform selection; RMB to cancel transformation"

        for transf_type in ("translate", "rotate", "scale"):
            mode_text = f"Select and {transf_type}"
            status_data[transf_type] = {}
            status_data[transf_type]["idle"] = {
                "mode": mode_text,
                "info": info_idle.format("", transf_type)
            }
            status_data[transf_type]["snap_idle"] = {
                "mode": mode_text,
                "info": info_idle.format("[SNAP] ", transf_type)
            }
            status_data[transf_type]["in_progress"] = {"mode": mode_text, "info": info_text}

        info_text = "LMB-drag to draw shape; RMB or <Escape> to cancel"
        status_data["region"] = {"mode": "Draw selection shape", "info": info_text}
        info_text = "Click to add point; <Backspace> to remove point; click existing point or" \
            " <Enter> to finish; RMB or <Escape> to cancel"
        status_data["fence"] = {"mode": "Draw selection fence", "info": info_text}
        info_text = "LMB-drag to paint; MWheel or <+>/<-> to resize brush; RMB or <Escape> to cancel"
        status_data["paint"] = {"mode": "Paint selection", "info": info_text}

    def setup(self):

        cam = Camera("region_selection_cam")
        cam.active = False
        cam.scene = Mgr.get("object_root")
        self._region_sel_cam = GD.cam().attach_new_node(cam)

        return True

    def __setup_selection_mask(self):

        self._sel_mask_root = root = NodePath("selection_mask_root")
        self._sel_mask_geom_root = geom_root = root.attach_new_node("selection_mask_geom_root")
        cam = Camera("selection_mask_cam")
        cam.active = False
        lens = OrthographicLens()
        lens.film_size = 2.
        cam.set_lens(lens)
        self._sel_mask_cam = NodePath(cam)
        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("selection_mask_triangle", vertex_format, Geom.UH_dynamic)
        vertex_data.set_num_rows(3)
        tris = GeomTriangles(Geom.UH_static)
        tris.add_next_vertices(3)
        geom = Geom(vertex_data)
        geom.add_primitive(tris)
        geom_node = GeomNode("selection_mask_triangle")
        geom_node.add_geom(geom)
        self._sel_mask_triangle = tri = geom_root.attach_new_node(geom_node)
        tri.set_two_sided(True)
        tri.hide()
        self._sel_mask_triangle_vertex = 1  # index of the triangle vertex to move
        self._sel_mask_triangle_coords = []
        cm = CardMaker("background")
        cm.set_frame(0., 1., -1., 0.)
        self._sel_mask_background = background = geom_root.attach_new_node(cm.generate())
        background.set_y(2.)
        background.set_color((0., 0., 0., 0.))
        self._sel_mask_tex = None
        self._sel_mask_buffer = None
        self._region_sel_listener = None
        self._mouse_prev = (0., 0.)

    def __transform_picking_cam(self, cam):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        cam.set_pos(mouse_pointer.x, 0., -mouse_pointer.y)

    def __init_fence_point_picking(self, mouse_x, mouse_y):

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("fence_points", vertex_format, Geom.UH_dynamic)
        points = GeomPoints(Geom.UH_static)
        geom = Geom(vertex_data)
        geom.add_primitive(points)
        geom_node = GeomNode("fence_points")
        geom_node.add_geom(geom)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.add_data3(mouse_x, 0., mouse_y)
        col_writer = GeomVertexWriter(vertex_data, "color")
        color_vec = get_color_vec(1, 255)
        col_writer.add_data4(color_vec)
        points.add_vertex(0)
        self._fence_points = fence_points = NodePath(geom_node)
        picking_cam = Mgr.get("picking_cam")
        picking_cam().reparent_to(fence_points)
        picking_cam().node().set_lens(self._fence_point_pick_lens)
        picking_cam().set_hpr(0., 0., 0.)
        picking_cam.set_transformer(self.__transform_picking_cam)

    def __create_selection_shape(self, shape_type):

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("selection_shape", vertex_format, Geom.UH_dynamic)
        lines = GeomLines(Geom.UH_static)

        if shape_type == "free":

            vertex_data.set_num_rows(2)
            lines.add_next_vertices(2)

        else:

            tris = GeomTriangles(Geom.UH_static)
            pos_writer = GeomVertexWriter(vertex_data, "vertex")

            if shape_type in ("square", "square_centered", "rect", "rect_centered"):

                if "centered" in shape_type:
                    pos_writer.add_data3(-1., 0., -1.)
                    pos_writer.add_data3(-1., 0., 1.)
                    pos_writer.add_data3(1., 0., 1.)
                    pos_writer.add_data3(1., 0., -1.)
                else:
                    pos_writer.add_data3(0., 0., 0.)
                    pos_writer.add_data3(0., 0., 1.)
                    pos_writer.add_data3(1., 0., 1.)
                    pos_writer.add_data3(1., 0., 0.)

                lines.add_vertices(0, 1)
                lines.add_vertices(1, 2)
                lines.add_vertices(2, 3)
                lines.add_vertices(3, 0)
                tris.add_vertices(0, 1, 2)
                tris.add_vertices(0, 2, 3)

            else:

                from math import pi, sin, cos

                angle = pi * .02

                if "centered" in shape_type:
                    pos_writer.add_data3(1., 0., 0.)
                    for i in range(1, 100):
                        x = cos(angle * i)
                        z = sin(angle * i)
                        pos_writer.add_data3(x, 0., z)
                        lines.add_vertices(i - 1, i)
                else:
                    pos_writer.add_data3(1., 0., .5)
                    for i in range(1, 100):
                        x = cos(angle * i) * .5 + .5
                        z = sin(angle * i) * .5 + .5
                        pos_writer.add_data3(x, 0., z)
                        lines.add_vertices(i - 1, i)

                lines.add_vertices(i, 0)

                for i in range(3, 101):
                    tris.add_vertices(0, i - 2, i - 1)

        state_np = NodePath("state_np")
        state_np.set_depth_test(False)
        state_np.set_depth_write(False)
        state_np.set_bin("fixed", 101)

        if shape_type == "free":
            rect = self._selection_shapes["rect"]
            color = rect.get_color()
            state_np.set_color(color)

        state1 = state_np.get_state()
        state_np.set_bin("fixed", 100)
        state_np.set_color((0., 0., 0., 1.))
        state_np.set_render_mode_thickness(3)
        state2 = state_np.get_state()
        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        geom_node = GeomNode("selection_shape")
        geom_node.add_geom(geom, state1)
        geom = geom.make_copy()
        geom_node.add_geom(geom, state2)

        if shape_type == "free":
            return NodePath(geom_node)

        shape = NodePath(geom_node)
        shape.set_color(GD["region_select"]["shape_color"])
        geom = Geom(vertex_data)
        geom.add_primitive(tris)
        geom_node = GeomNode("selection_area")
        geom_node.add_geom(geom)
        area = shape.attach_new_node(geom_node)
        area.set_depth_test(False)
        area.set_depth_write(False)
        area.set_bin("fixed", 99)
        area.set_transparency(TransparencyAttrib.M_alpha)
        area.set_color(GD["region_select"]["fill_color"])

        return shape

    def __draw_selection_shape(self, task):

        if not GD.mouse_watcher.has_mouse():
            return task.cont

        x, y = self._sel_shape_pos
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x, mouse_y = mouse_pointer.x, -mouse_pointer.y

        shape_type = GD["region_select"]["type"]

        if shape_type == "paint":

            shape = self._selection_shapes[shape_type]
            w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
            x, y = GD["viewport"]["pos_aux" if GD["viewport"][2] == "main" else "pos"]
            center_x, center_y = GD.mouse_watcher.get_mouse()
            shape.set_pos(mouse_x - x, 0., mouse_y + y)
            geom_root = self._sel_mask_geom_root
            brush = geom_root.find("**/brush")
            brush.set_pos(mouse_x - x, 10., mouse_y + y)

            if self._sel_brush_size_stale:
                shape.set_scale(self._sel_brush_size)
                brush.set_scale(self._sel_brush_size)
                self._sel_brush_size_stale = False

            d_x = self._sel_brush_size * 2. / w
            d_y = self._sel_brush_size * 2. / h
            x_min = center_x - d_x
            x_max = center_x + d_x
            y_min = center_y - d_y
            y_max = center_y + d_y
            x1, y1 = self._mouse_start_pos
            x2, y2 = self._mouse_end_pos

            if x_min < x1:
                x1 = x_min
            elif x_max > x2:
                x2 = x_max

            if y_min < y1:
                y1 = y_min
            elif y_max > y2:
                y2 = y_max

            self._mouse_start_pos = (x1, y1)
            self._mouse_end_pos = (x2, y2)

        elif shape_type in ("fence", "lasso"):

            shape = self._selection_shapes["free"]

            if shape_type == "lasso":

                prev_x, prev_y = self._mouse_prev
                d_x = abs(mouse_x - prev_x)
                d_y = abs(mouse_y - prev_y)

                if max(d_x, d_y) > 5:
                    self.__add_selection_shape_vertex()

            for i in (0, 1):
                vertex_data = shape.node().modify_geom(i).modify_vertex_data()
                row = vertex_data.get_num_rows() - 1
                pos_writer = GeomVertexWriter(vertex_data, "vertex")
                pos_writer.set_row(row)
                pos_writer.set_data3(mouse_x - x, 0., mouse_y - y)

        else:

            sx = mouse_x - x
            sy = mouse_y - y
            shape = self._selection_shapes[shape_type]
            w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]

            if "square" in shape_type or "circle" in shape_type:

                if "centered" in shape_type:
                    s = max(.001, math.sqrt(sx * sx + sy * sy))
                    shape.set_scale(s, 1., s)
                    d_x = s * 2. / w
                    d_y = s * 2. / h
                    center_x, center_y = self._region_center_pos
                    self._mouse_start_pos = (center_x - d_x, center_y - d_y)
                    self._mouse_end_pos = (center_x + d_x, center_y + d_y)
                else:
                    f = max(.001, abs(sx), abs(sy))
                    sx = f * (-1. if sx < 0. else 1.)
                    sy = f * (-1. if sy < 0. else 1.)
                    shape.set_scale(sx, 1., sy)
                    d_x = sx * 2. / w
                    d_y = sy * 2. / h
                    mouse_start_x, mouse_start_y = self._mouse_start_pos
                    self._mouse_end_pos = (mouse_start_x + d_x, mouse_start_y + d_y)

            else:

                sx = .001 if abs(sx) < .001 else sx
                sy = .001 if abs(sy) < .001 else sy
                shape.set_scale(sx, 1., sy)
                self._mouse_end_pos = GD.mouse_watcher.get_mouse()

                if "centered" in shape_type:
                    d_x = sx * 2. / w
                    d_y = sy * 2. / h
                    center_x, center_y = self._region_center_pos
                    self._mouse_start_pos = (center_x - d_x, center_y - d_y)

        return task.cont

    def __add_selection_shape_vertex(self, add_fence_point=False, coords=None):

        if not GD.mouse_watcher.has_mouse():
            return

        x, y = GD.mouse_watcher.get_mouse()

        if add_fence_point:
            mouse_coords_x, mouse_coords_y = self._fence_mouse_coords
            mouse_coords_x.append(x)
            mouse_coords_y.append(y)

        x1, y1 = self._mouse_start_pos
        x2, y2 = self._mouse_end_pos

        if x < x1:
            x1 = x
        elif x > x2:
            x2 = x

        if y < y1:
            y1 = y
        elif y > y2:
            y2 = y

        self._mouse_start_pos = (x1, y1)
        self._mouse_end_pos = (x2, y2)

        if coords:
            mouse_x, mouse_y = coords
        else:
            mouse_pointer = Mgr.get("mouse_pointer", 0)
            mouse_x, mouse_y = mouse_pointer.x, -mouse_pointer.y
            self._mouse_prev = (mouse_x, mouse_y)

        shape = self._selection_shapes["free"]
        x, y = self._sel_shape_pos

        for i in (0, 1):

            vertex_data = shape.node().modify_geom(i).modify_vertex_data()
            count = vertex_data.get_num_rows()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(count - 1)
            pos_writer.add_data3(mouse_x - x, 0., mouse_y - y)
            pos_writer.add_data3(mouse_x - x, 0., mouse_y - y)
            prim = shape.node().modify_geom(i).modify_primitive(0)
            array = prim.modify_vertices()
            row_count = array.get_num_rows()

            if row_count > 2:
                array.set_num_rows(row_count - 2)

            prim.add_vertices(count - 1, count)
            prim.add_vertices(count, 0)

        vertex_data = self._sel_mask_triangle.node().modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        if count == 2:
            self._sel_mask_triangle_vertex = 1
        elif count > 2:
            self._sel_mask_triangle_vertex = 3 - self._sel_mask_triangle_vertex

        pos_writer.set_row(self._sel_mask_triangle_vertex)
        pos_writer.set_data3(mouse_x - x, 0., mouse_y - y)

        if min(x2 - x1, y2 - y1) == 0:
            self._sel_mask_triangle.hide()
        elif count > 2:
            self._sel_mask_triangle.show()
            Mgr.do_next_frame(lambda task: self._sel_mask_triangle.hide(), "hide_sel_mask_triangle")

        if count == 3:
            self._sel_mask_background.set_color((1., 1., 1., 1.))
            self._sel_mask_background.set_texture(self._sel_mask_tex)

        if add_fence_point:

            node = self._fence_points.node()
            vertex_data = node.modify_geom(0).modify_vertex_data()
            row = vertex_data.get_num_rows()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(row)
            pos_writer.add_data3(mouse_x, 0., mouse_y)
            col_writer = GeomVertexWriter(vertex_data, "color")
            col_writer.set_row(row)
            self._fence_point_color_id += 1
            self._fence_point_coords[self._fence_point_color_id] = (mouse_x, mouse_y)
            color_vec = get_color_vec(self._fence_point_color_id, 255)
            col_writer.add_data4(color_vec)
            prim = node.modify_geom(0).modify_primitive(0)
            prim.add_vertex(row)
            self._sel_mask_triangle_coords.append((mouse_x - x, mouse_y - y))

            if count == 2:
                self._region_sel_listener.accept("backspace-up", self.__remove_fence_vertex)

    def __remove_fence_vertex(self):

        if GD["region_select"]["type"] != "fence":
            return

        mouse_coords_x, mouse_coords_y = self._fence_mouse_coords
        mouse_coords_x.pop()
        mouse_coords_y.pop()
        x_min = min(mouse_coords_x)
        x_max = max(mouse_coords_x)
        y_min = min(mouse_coords_y)
        y_max = max(mouse_coords_y)
        self._mouse_start_pos = (x_min, y_min)
        self._mouse_end_pos = (x_max, y_max)

        shape = self._selection_shapes["free"]

        for i in (0, 1):

            vertex_data = shape.node().modify_geom(i).modify_vertex_data()
            count = vertex_data.get_num_rows() - 1
            vertex_data.set_num_rows(count)
            prim = shape.node().modify_geom(i).modify_primitive(0)
            array = prim.modify_vertices()
            row_count = array.get_num_rows()

            if row_count > 2:
                array.set_num_rows(row_count - 4)

            if row_count > 6:
                prim.add_vertices(count - 1, 0)

        x, y = self._sel_shape_pos
        prev_x, prev_y = self._sel_mask_triangle_coords.pop()
        self._mouse_prev = (prev_x + x, prev_y + y)

        if count == 2:
            self._region_sel_listener.ignore("backspace-up")
        elif count == 3:
            self._sel_mask_background.clear_texture()
            self._sel_mask_background.set_color((0., 0., 0., 0.))
            self._sel_mask_triangle.hide()

        if count >= 3:
            self._sel_mask_triangle_vertex = 3 - self._sel_mask_triangle_vertex
            vertex_data = self._sel_mask_triangle.node().modify_geom(0).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(self._sel_mask_triangle_vertex)
            prev_x, prev_y = self._sel_mask_triangle_coords[-1]
            pos_writer.set_data3(prev_x, 0., prev_y)

        if min(x_max - x_min, y_max - y_min) == 0:
            self._sel_mask_triangle.hide()
        elif count > 3:
            self._sel_mask_triangle.show()
            Mgr.do_next_frame(lambda task: self._sel_mask_triangle.hide(), "hide_sel_mask_triangle")

        node = self._fence_points.node()
        vertex_data = node.modify_geom(0).modify_vertex_data()
        count = vertex_data.get_num_rows() - 1
        vertex_data.set_num_rows(count)
        del self._fence_point_coords[self._fence_point_color_id]
        self._fence_point_color_id -= 1
        prim = node.modify_geom(0).modify_primitive(0)
        array = prim.modify_vertices()
        array.set_num_rows(count)

    def __incr_selection_brush_size(self):

        self._sel_brush_size += max(5., self._sel_brush_size * .1)
        self._sel_brush_size_stale = True

    def __decr_selection_brush_size(self):

        self._sel_brush_size = max(1., self._sel_brush_size - max(5., self._sel_brush_size * .1))
        self._sel_brush_size_stale = True

    def __enter_region_selection_mode(self, prev_state_id, active):

        if not GD.mouse_watcher.has_mouse():
            return

        screen_pos = GD.mouse_watcher.get_mouse()
        self._mouse_start_pos = (screen_pos.x, screen_pos.y)

        x, y = GD["viewport"]["pos_aux" if GD["viewport"][2] == "main" else "pos"]
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x, mouse_y = mouse_pointer.x, -mouse_pointer.y
        self._sel_shape_pos = (mouse_x, mouse_y)

        self._region_sel_uvs = prev_state_id == "uv_edit_mode"

        shape_type = GD["region_select"]["type"]

        if "centered" in shape_type:
            self._region_center_pos = (screen_pos.x, screen_pos.y)

        if shape_type == "fence":
            self.__init_fence_point_picking(mouse_x, mouse_y)
            self._fence_point_coords[1] = (mouse_x, mouse_y)
            mouse_coords_x, mouse_coords_y = self._fence_mouse_coords
            mouse_coords_x.append(screen_pos.x)
            mouse_coords_y.append(screen_pos.y)
            Mgr.add_task(self.__update_cursor, "update_cursor")
            self._region_sel_listener = listener = DirectObject()
            listener.accept("enter-up", lambda: Mgr.exit_state("region_selection_mode"))
            Mgr.update_app("status", ["select", "fence"])
        elif shape_type == "paint":
            self._region_sel_listener = listener = DirectObject()
            listener.accept("wheel_up-up", self.__incr_selection_brush_size)
            listener.accept("+", self.__incr_selection_brush_size)
            listener.accept("+-repeat", self.__incr_selection_brush_size)
            listener.accept("wheel_down-up", self.__decr_selection_brush_size)
            listener.accept("-", self.__decr_selection_brush_size)
            listener.accept("--repeat", self.__decr_selection_brush_size)
            Mgr.update_app("status", ["select", "paint"])
        else:
            Mgr.update_app("status", ["select", "region"])

        if shape_type in ("fence", "lasso", "paint"):
            self._sel_mask_tex = tex = Texture()
            w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
            card = self._sel_shape_tex_card
            card.reparent_to(GD.viewport_origin)
            card.set_texture(tex)
            card.set_scale(w, 1., h)
            geom_root = self._sel_mask_geom_root
            geom_root.set_transform(GD.viewport_origin.get_transform())
            sh = shaders.region_sel
            self._sel_mask_buffer = bfr = GD.window.make_texture_buffer(
                                                                        "sel_mask_buffer",
                                                                        w, h,
                                                                        tex,
                                                                        to_ram=True
                                                                       )
            bfr.clear_color = (0., 0., 0., 0.)
            bfr.set_clear_color_active(True)
            cam = self._sel_mask_cam
            GD.showbase.make_camera(bfr, useCamera=cam)
            cam.node().active = True
            cam.reparent_to(self._sel_mask_root)
            cam.set_transform(GD.showbase.cam2d.get_transform())
            background = self._sel_mask_background
            background.set_scale(w, 1., h)
            self._mouse_end_pos = (screen_pos.x, screen_pos.y)

        if shape_type in ("fence", "lasso"):
            self._selection_shapes["free"] = shape = self.__create_selection_shape("free")
            tri = self._sel_mask_triangle
            tri.set_pos(mouse_x - x, 1.5, mouse_y + y)
            shader = shaders.Shaders.region_sel_mask
            tri.set_shader(shader)
            tri.set_shader_input("prev_tex", tex)
            r, g, b, a = GD["region_select"]["fill_color"]
            fill_color = (r, g, b, a) if a else (1., 1., 1., 1.)
            tri.set_shader_input("fill_color", fill_color)
            card.show() if a else card.hide()
        else:
            shape = self._selection_shapes[shape_type]

        if shape_type == "paint":
            card.show()
            shape.set_scale(self._sel_brush_size)
            brush = shape.get_child(0).copy_to(geom_root)
            brush.name = "brush"
            brush.set_scale(self._sel_brush_size)
            brush.clear_attrib(TransparencyAttrib)
            GD.graphics_engine.render_frame()
            background.set_color((1., 1., 1., 1.))
            background.set_texture(tex)

        shape.reparent_to(GD.viewport_origin)
        shape.set_pos(mouse_x - x, 0., mouse_y + y)

        Mgr.add_task(self.__draw_selection_shape, "draw_selection_shape", sort=3)

    def __exit_region_selection_mode(self, next_state_id, active):

        Mgr.remove_task("draw_selection_shape")
        shape_type = GD["region_select"]["type"]

        if shape_type == "fence":
            Mgr.remove_task("update_cursor")
            Mgr.get("picking_cam").adjust_to_lens()
            picking_cam = Mgr.get("picking_cam")
            picking_cam().reparent_to(GD.cam().parent)
            picking_cam.set_transformer(None)
            self._fence_points.detach_node()
            self._fence_points = None
            self._fence_point_color_id = 1
            self._fence_point_coords = {}
            self._fence_mouse_coords = [[], []]
            self._fence_initialized = False
            self._sel_mask_triangle_coords = []

        if shape_type in ("fence", "paint"):
            self._region_sel_listener.ignore_all()
            self._region_sel_listener = None

        if shape_type in ("fence", "lasso", "paint"):
            self._sel_shape_tex_card.detach_node()
            self._sel_shape_tex_card.clear_texture()
            self._sel_mask_cam.node().active = False
            GD.graphics_engine.remove_window(self._sel_mask_buffer)
            self._sel_mask_buffer = None
            self._sel_mask_background.clear_texture()
            self._sel_mask_background.set_color((0., 0., 0., 0.))

        if shape_type in ("fence", "lasso"):
            shape = self._selection_shapes["free"]
            shape.detach_node()
            del self._selection_shapes["free"]
            tri = self._sel_mask_triangle
            tri.hide()
            tri.clear_attrib(ShaderAttrib)
        else:
            shape = self._selection_shapes[shape_type]
            shape.detach_node()

        if shape_type == "paint":
            geom_root = self._sel_mask_geom_root
            brush = geom_root.find("**/brush")
            brush.detach_node()

        x1, y1 = self._mouse_start_pos
        x2, y2 = self._mouse_end_pos
        x1 = max(0., min(1., .5 + x1 * .5))
        y1 = max(0., min(1., .5 + y1 * .5))
        x2 = max(0., min(1., .5 + x2 * .5))
        y2 = max(0., min(1., .5 + y2 * .5))
        l, r = min(x1, x2), max(x1, x2)
        b, t = min(y1, y2), max(y1, y2)
        self.__region_select((l, r, b, t))

        if self._region_sel_uvs:
            Mgr.exit_state("inactive", "uv")

    def __handle_region_select_mouse_up(self):

        shape_type = GD["region_select"]["type"]

        if shape_type == "fence":

            pixel_under_mouse = Mgr.get("pixel_under_mouse")

            if self._fence_initialized:
                if pixel_under_mouse != VBase4():
                    r, g, b, _ = [int(round(c * 255.)) for c in pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    self.__add_selection_shape_vertex(coords=self._fence_point_coords[color_id])
                    GD.graphics_engine.render_frame()
                    Mgr.exit_state("region_selection_mode")
                else:
                    self.__add_selection_shape_vertex(add_fence_point=True)
            else:
                self._fence_initialized = True

        else:

            Mgr.exit_state("region_selection_mode")

    def __cancel_region_select(self):

        self._region_sel_cancelled = True
        Mgr.exit_state("region_selection_mode")
        self._region_sel_cancelled = False

    def __init_region_select(self, op="replace"):

        self._selection_op = op
        Mgr.enter_state("region_selection_mode")

    def __region_select(self, frame):

        region_type = GD["region_select"]["type"]

        if self._region_sel_cancelled:
            if region_type in ("fence", "lasso", "paint"):
                self._sel_mask_tex = None
            return

        lens = GD.cam.lens
        w, h = lens.film_size
        l, r, b, t = frame
        # compute film size and offset
        w_f = (r - l) * w
        h_f = (t - b) * h
        x_f = ((r + l) * .5 - .5) * w
        y_f = ((t + b) * .5 - .5) * h
        w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
        viewport_size = (w, h)
        # compute buffer size
        w_b = int(round((r - l) * w))
        h_b = int(round((t - b) * h))
        bfr_size = (w_b, h_b)

        if min(bfr_size) < 2:
            return

        def get_off_axis_lens(film_size):

            lens = GD.cam.lens
            focal_len = lens.focal_length
            lens = lens.make_copy()
            lens.film_size = film_size
            lens.film_offset = (x_f, y_f)
            lens.focal_length = focal_len

            return lens

        def get_expanded_region_lens():

            l, r, b, t = frame
            w, h = viewport_size
            l_exp = (int(round(l * w)) - 2) / w
            r_exp = (int(round(r * w)) + 2) / w
            b_exp = (int(round(b * h)) - 2) / h
            t_exp = (int(round(t * h)) + 2) / h
            # compute expanded film size
            lens = GD.cam.lens
            w, h = lens.film_size
            w_f = (r_exp - l_exp) * w
            h_f = (t_exp - b_exp) * h

            return get_off_axis_lens((w_f, h_f))

        enclose = GD["region_select"]["enclose"]
        lens_exp = get_expanded_region_lens() if enclose else None

        if "ellipse" in region_type or "circle" in region_type:
            x1, y1 = self._mouse_start_pos
            x2, y2 = self._mouse_end_pos
            x1 = .5 + x1 * .5
            y1 = .5 + y1 * .5
            x2 = .5 + x2 * .5
            y2 = .5 + y2 * .5
            offset_x = (l - min(x1, x2)) * w
            offset_y = (b - min(y1, y2)) * h
            d = abs(x2 - x1) * w
            radius = d * .5
            aspect_ratio = d / (abs(y2 - y1) * h)
            ellipse_data = (radius, aspect_ratio, offset_x, offset_y)
        else:
            ellipse_data = ()

        if region_type in ("fence", "lasso", "paint"):
            img = PNMImage()
            self._sel_mask_tex.store(img)
            cropped_img = PNMImage(*bfr_size, 4)
            cropped_img.copy_sub_image(img, 0, 0, int(round(l * w)), int(round((1. - t) * h)))
            self._sel_mask_tex.load(cropped_img)

        Mgr.get("picking_cam").active = False

        lens = get_off_axis_lens((w_f, h_f))
        picking_mask = Mgr.get("picking_mask")
        cam_np = self._region_sel_cam
        cam = cam_np.node()
        cam.set_lens(lens)
        cam.camera_mask = picking_mask
        bfr = GD.window.make_texture_buffer("tex_buffer", w_b, h_b)
        cam.active = True
        GD.showbase.make_camera(bfr, useCamera=cam_np)
        ge = GD.graphics_engine

        ctrl_down = GD.mouse_watcher.is_button_down("control")
        shift_down = GD.mouse_watcher.is_button_down("shift")

        if ctrl_down:
            op = "toggle" if shift_down else "add"
        elif shift_down:
            op = "remove"
        else:
            op = self._selection_op

        obj_lvl = GD["active_obj_level"]

        if self._region_sel_uvs:

            Mgr.do("region_select_uvs", cam_np, lens_exp, bfr,
                   ellipse_data, self._sel_mask_tex, op)

        elif obj_lvl == "top":

            objs = Mgr.get("objects")
            obj_count = len(objs)

            for i, obj in enumerate(objs):

                obj.pivot.set_shader_input("index", i)

                if obj.type == "model":
                    obj.bbox.hide(picking_mask)

            sh = shaders.region_sel
            vs = sh.VERT_SHADER

            def region_select_objects(sel, enclose=False):

                Mgr.do("make_point_helpers_pickable", False)

                tex = Texture()
                tex.setup_1d_texture(obj_count, Texture.T_int, Texture.F_r32i)
                tex.clear_color = (0., 0., 0., 0.)

                if "rect" in region_type or "square" in region_type:
                    fs = sh.FRAG_SHADER_INV if enclose else sh.FRAG_SHADER
                elif "ellipse" in region_type or "circle" in region_type:
                    fs = sh.FRAG_SHADER_ELLIPSE_INV if enclose else sh.FRAG_SHADER_ELLIPSE
                else:
                    fs = sh.FRAG_SHADER_FREE_INV if enclose else sh.FRAG_SHADER_FREE

                shader = Shader.make(Shader.SL_GLSL, vs, fs)
                state_np = NodePath("state_np")
                state_np.set_shader(shader, 1)
                state_np.set_shader_input("selections", tex, read=False, write=True)

                if "ellipse" in region_type or "circle" in region_type:
                    state_np.set_shader_input("ellipse_data", Vec4(*ellipse_data))
                elif region_type in ("fence", "lasso", "paint"):
                    if enclose:
                        img = PNMImage()
                        self._sel_mask_tex.store(img)
                        img.expand_border(2, 2, 2, 2, (0., 0., 0., 0.))
                        self._sel_mask_tex.load(img)
                    state_np.set_shader_input("mask_tex", self._sel_mask_tex)
                elif enclose:
                    state_np.set_shader_input("buffer_size", Vec2(w_b + 2, h_b + 2))

                state_np.set_light_off(1)
                state_np.set_color_off(1)
                state_np.set_material_off(1)
                state_np.set_texture_off(1)
                state_np.set_transparency(TransparencyAttrib.M_none, 1)
                state = state_np.get_state()
                cam.initial_state = state

                Mgr.update_locally("region_picking", True)

                ge.render_frame()

                if ge.extract_texture_data(tex, GD.window.get_gsg()):

                    texels = memoryview(tex.get_ram_image()).cast("I")

                    for i, mask in enumerate(texels):
                        for j in range(32):
                            if mask & (1 << j):
                                index = 32 * i + j
                                sel.add(objs[index].get_toplevel_object(get_group=True))

                state_np.clear_attrib(ShaderAttrib)
                Mgr.update_locally("region_picking", False)
                Mgr.do("make_point_helpers_pickable")
                Mgr.do("region_select_point_helpers", cam, enclose, bfr_size,
                       ellipse_data, self._sel_mask_tex, sel)

            new_sel = set()
            region_select_objects(new_sel)
            ge.remove_window(bfr)

            if enclose:
                bfr_exp = GD.window.make_texture_buffer("tex_buffer_exp", w_b + 4, h_b + 4)
                GD.showbase.make_camera(bfr_exp, useCamera=cam_np)
                cam.set_lens(lens_exp)
                inverse_sel = set()
                region_select_objects(inverse_sel, True)
                new_sel -= inverse_sel
                ge.remove_window(bfr_exp)

            if op == "replace":
                self._selection.replace(new_sel)
            elif op == "add":
                self._selection.add(new_sel)
            elif op == "remove":
                self._selection.remove(new_sel)
            elif op == "toggle":
                old_sel = set(self._selection)
                self._selection.replace(old_sel ^ new_sel)

            for obj in objs:
                if obj.type == "model":
                    obj.bbox.show(picking_mask)

        else:

            Mgr.do("region_select_subobjs", cam_np, lens_exp, bfr,
                   ellipse_data, self._sel_mask_tex, op)

        if region_type in ("fence", "lasso", "paint"):
            self._sel_mask_tex = None

        cam.active = False
        Mgr.get("picking_cam").active = True
        Mgr.update_remotely("selection_set", "hide_name")

    def __get_selection(self, obj_lvl=""):

        lvl = obj_lvl if obj_lvl else GD["active_obj_level"]

        return Mgr.get("selection_" + lvl)

    def __enter_selection_mode(self, prev_state_id, active):

        Mgr.add_task(self.__update_cursor, "update_cursor")
        Mgr.get("transf_gizmo").enable()

        transf_type = GD["active_transform_type"]

        if transf_type:
            if GD["snap"]["on"][transf_type]:
                Mgr.update_app("status", ["select", transf_type, "snap_idle"])
            else:
                Mgr.update_app("status", ["select", transf_type, "idle"])
        else:
            Mgr.update_app("status", ["select", ""])

    def __exit_selection_mode(self, next_state_id, active):

        if next_state_id != "checking_mouse_offset":
            self._pixel_under_mouse = None  # force an update of the cursor
                                            # next time self.__update_cursor()
                                            # is called
            Mgr.remove_task("update_cursor")
            Mgr.set_cursor("main")

        Mgr.get("transf_gizmo").enable(False)

    def __update_active_selection(self, restore=False):

        Mgr.update_remotely("selection_set", "hide_name")
        obj_lvl = GD["active_obj_level"]

        if obj_lvl == "top":

            Mgr.do("enable_object_name_checking")

        else:

            self._selection.clear_prev_obj_ids()
            Mgr.do("update_selection_" + obj_lvl)
            Mgr.do("disable_object_name_checking")

            toplvl_obj = self.__get_selection(obj_lvl).toplevel_obj

            if toplvl_obj:

                cs_type = GD["coord_sys_type"]
                tc_type = GD["transf_center_type"]

                if cs_type == "local":
                    Mgr.update_locally("coord_sys", cs_type, toplvl_obj)

                if tc_type == "pivot":
                    Mgr.update_locally("transf_center", tc_type, toplvl_obj)

        if restore:
            task = lambda: self.__get_selection().update()
            PendingTasks.add(task, "update_selection", "ui")
        else:
            self.__get_selection().update()

    def __inverse_select(self):

        if "uv" in (GD["viewport"][1], GD["viewport"][2]):
            Mgr.do("inverse_select_uvs")
        elif GD["active_obj_level"] == "top":
            old_sel = set(self._selection)
            new_sel = set(o.get_toplevel_object(get_group=True)
                for o in Mgr.get("objects")) - old_sel
            self._selection.replace(new_sel)
        else:
            Mgr.do("inverse_select_subobjs")

        Mgr.update_remotely("selection_set", "hide_name")

    def __select_all(self):

        if "uv" in (GD["viewport"][1], GD["viewport"][2]):
            Mgr.do("select_all_uvs")
        elif GD["active_obj_level"] == "top":
            self._selection.replace(o.get_toplevel_object(get_group=True)
                for o in Mgr.get("objects"))
        else:
            Mgr.do("select_all_subobjs")

        Mgr.update_remotely("selection_set", "hide_name")

    def __select_none(self):

        if "uv" in (GD["viewport"][1], GD["viewport"][2]):
            Mgr.do("clear_uv_selection")
        elif GD["active_obj_level"] == "top":
            self._selection.clear()
        else:
            Mgr.do("clear_subobj_selection")

        Mgr.update_remotely("selection_set", "hide_name")

    def __add_selection_set(self, name=None):

        obj_level = GD["active_obj_level"]

        if obj_level == "top":
            new_set = set(obj.id for obj in self._selection)
        elif "uv" in (GD["viewport"][1], GD["viewport"][2]):
            obj_level = "uv_" + obj_level
            new_set = Mgr.get("uv_selection_set")
        else:
            new_set = Mgr.get("subobj_selection_set")

        sel_sets = self._selection_sets
        sets = sel_sets["sets"][obj_level]
        set_id = id(new_set)
        sets[set_id] = new_set
        names = sel_sets["names"][obj_level]

        if name is None:
            search_pattern = r"^Set\s*(\d+)$"
            naming_pattern = "Set {:04d}"
        else:
            search_pattern = naming_pattern = ""

        name = get_unique_name(name, list(names.values()), search_pattern, naming_pattern)
        names[set_id] = name
        Mgr.update_remotely("selection_set", "add", set_id, name)

    def __copy_selection_set(self, set_id):

        obj_level = GD["active_obj_level"]

        if "uv" in (GD["viewport"][1], GD["viewport"][2]):
            obj_level = "uv_" + obj_level

        sets = self._selection_sets["sets"][obj_level]
        new_set = sets[set_id].copy()
        new_set_id = id(new_set)
        sets[new_set_id] = new_set
        names = self._selection_sets["names"][obj_level]
        name = names[set_id]
        original_name = re.sub(r" - copy$| - copy \(\d+\)$", "", name, 1)
        copy_name = original_name + " - copy"
        copy_name = get_unique_name(copy_name, list(names.values()))
        names[new_set_id] = copy_name
        Mgr.update_remotely("selection_set", "copy", new_set_id, copy_name)

    def __remove_selection_set(self, set_id):

        obj_level = GD["active_obj_level"]

        if "uv" in (GD["viewport"][1], GD["viewport"][2]):
            obj_level = "uv_" + obj_level

        del self._selection_sets["sets"][obj_level][set_id]
        del self._selection_sets["names"][obj_level][set_id]
        Mgr.update_remotely("selection_set", "remove", set_id)

    def __clear_selection_sets(self):

        obj_level = GD["active_obj_level"]

        if "uv" in (GD["viewport"][1], GD["viewport"][2]):
            obj_level = "uv_" + obj_level

        self._selection_sets["sets"][obj_level].clear()
        self._selection_sets["names"][obj_level].clear()
        Mgr.update_remotely("selection_set", "clear")

    def __rename_selection_set(self, set_id, name):

        obj_level = GD["active_obj_level"]

        if "uv" in (GD["viewport"][1], GD["viewport"][2]):
            obj_level = "uv_" + obj_level

        names = self._selection_sets["names"][obj_level]
        del names[set_id]
        name = get_unique_name(name, list(names.values()))
        names[set_id] = name
        Mgr.update_remotely("selection_set", "rename", set_id, name)

    def __combine_selection_sets(self, set_id1, set_id2, op, in_place):

        obj_level = GD["active_obj_level"]

        if set_id1 == "cur_sel":
            in_place = False
            if obj_level == "top":
                set1 = set(obj.id for obj in self._selection)
            elif "uv" in (GD["viewport"][1], GD["viewport"][2]):
                set1 = Mgr.get("uv_selection_set")
            else:
                set1 = Mgr.get("subobj_selection_set")
        else:
            set1 = None

        if set_id2 == "cur_sel":
            if obj_level == "top":
                set2 = set(obj.id for obj in self._selection)
            elif "uv" in (GD["viewport"][1], GD["viewport"][2]):
                set2 = Mgr.get("uv_selection_set")
            else:
                set2 = Mgr.get("subobj_selection_set")
        else:
            set2 = None

        if "uv" in (GD["viewport"][1], GD["viewport"][2]):
            obj_level = "uv_" + obj_level

        sets = self._selection_sets["sets"][obj_level]

        if set1 is None:
            set1 = sets[set_id1]

        if set2 is None:
            set2 = sets[set_id2]

        if op == "union":
            if in_place:
                set1 |= set2
            else:
                new_set = set1 | set2
        if op == "intersection":
            if in_place:
                set1 &= set2
            else:
                new_set = set1 & set2
        if op == "difference":
            if in_place:
                set1 -= set2
            else:
                new_set = set1 - set2
        if op == "sym_diff":
            if in_place:
                set1 ^= set2
            else:
                new_set = set1 ^ set2

        if in_place:
            Mgr.update_remotely("selection_set", "hide", set_id1)
        else:
            set_id = id(new_set)
            sets[set_id] = new_set
            names = self._selection_sets["names"][obj_level]
            search_pattern = r"^Set\s*(\d+)$"
            naming_pattern = "Set {:04d}"
            name = get_unique_name("", list(names.values()), search_pattern, naming_pattern)
            names[set_id] = name
            Mgr.update_remotely("selection_set", "copy", set_id, name)

    def __apply_selection_set(self, set_id):

        obj_level = GD["active_obj_level"]

        if obj_level == "top":
            sel_set = self._selection_sets["sets"][obj_level][set_id]
            new_sel = set(obj.get_toplevel_object(get_group=True) for obj in
                          (Mgr.get("object", obj_id) for obj_id in sel_set) if obj)
            self._selection.replace(new_sel)
        elif "uv" in (GD["viewport"][1], GD["viewport"][2]):
            obj_level = "uv_" + obj_level
            sel_set = self._selection_sets["sets"][obj_level][set_id]
            Mgr.do("apply_uv_selection_set", sel_set)
        else:
            sel_set = self._selection_sets["sets"][obj_level][set_id]
            Mgr.do("apply_subobj_selection_set", sel_set)

    def __reset_selection_sets(self):

        sets = self._selection_sets["sets"]
        names = self._selection_sets["names"]

        for obj_level in sets:
            sets[obj_level].clear()
            names[obj_level].clear()

        Mgr.update_remotely("selection_set", "reset")

    def __set_selection_sets(self, selection_sets):

        self._selection_sets = selection_sets
        sets = selection_sets["sets"]
        names = selection_sets["names"]
        # for backwards compatibility
        sets.setdefault("uv_part", {})
        names.setdefault("uv_part", {})

        for obj_level in sets:

            Mgr.update_remotely("selection_set", "replace", obj_level)
            lvl_names = names[obj_level]

            for set_id, sel_set in sets[obj_level].items():
                name = lvl_names[set_id]
                Mgr.update_remotely("selection_set", "add", set_id, name)

        Mgr.update_remotely("selection_set", "replace", "top")

    def __update_object_selection(self, update_type="", *args):

        selection = self._selection

        def get_obj_and_sel_set_data(obj_data, sel_set_data):

            for obj in Mgr.get("objects"):

                obj_type = obj.type

                if obj_type not in ("model", "group", "light", "camera"):
                    obj_type = "helper"

                data = (obj.id, obj.is_selected(), obj.name)
                obj_data.setdefault(obj_type, []).append(data)

            sel_sets = self._selection_sets
            sel_set_data["sets"] = sel_sets["sets"]["top"]
            sel_set_data["names"] = sel_sets["names"]["top"]

        if update_type == "get_data":
            get_obj_and_sel_set_data(*args)
        elif update_type == "replace":
            selection.replace([Mgr.get("object", obj_id).get_toplevel_object(get_group=True)
                              for obj_id in args])
            Mgr.update_remotely("selection_set", "hide_name")
        elif update_type == "remove":
            selection.remove([Mgr.get("object", *args)])
            Mgr.update_remotely("selection_set", "hide_name")
        elif update_type == "invert":
            self.__inverse_select()
        elif update_type == "all":
            self.__select_all()
        elif update_type == "clear":
            self.__select_none()
        elif update_type == "region_color":
            shapes = self._selection_shapes
            shape_color = GD["region_select"]["shape_color"]
            fill_color = GD["region_select"]["fill_color"]
            for shape_type in ("square", "square_centered", "circle", "circle_centered"):
                shape = shapes[shape_type]
                shape.set_color(shape_color)
                shape.get_child(0).set_color(fill_color)
        elif update_type == "add_set":
            self.__add_selection_set(*args)
        elif update_type == "copy_set":
            self.__copy_selection_set(*args)
        elif update_type == "remove_set":
            self.__remove_selection_set(*args)
        elif update_type == "clear_sets":
            self.__clear_selection_sets(*args)
        elif update_type == "rename_set":
            self.__rename_selection_set(*args)
        elif update_type == "combine_sets":
            self.__combine_selection_sets(*args)
        elif update_type == "apply_set":
            self.__apply_selection_set(*args)
        elif update_type == "reset_sets":
            self.__reset_selection_sets(*args)

        if update_type in ("replace", "remove", "invert", "all", "clear", "apply_set"):
            if "uv" not in (GD["viewport"][1], GD["viewport"][2]):
                Mgr.exit_states(min_persistence=-99)

        if update_type in ("add_set", "copy_set", "remove_set", "clear_sets",
                           "rename_set", "combine_sets"):
            GD["unsaved_scene"] = True
            Mgr.update_app("unsaved_scene")
            Mgr.do("require_scene_save")

    def __delete_selection(self):

        selection = self.__get_selection()

        if selection.delete():
            Mgr.do("update_picking_col_id_ranges")
            Mgr.update_remotely("selection_set", "hide_name")

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            cursor_id = "main"

            if pixel_under_mouse != VBase4():

                if Mgr.get_state_id() == "region_selection_mode":

                    cursor_id = "select"

                else:

                    if (GD["active_obj_level"] == "edge" and
                            GD["subobj_edit_options"]["sel_edges_by_border"]):

                        r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                        color_id = r << 16 | g << 8 | b
                        pickable_type = PickableTypes.get(a)

                        if pickable_type == "transf_gizmo":

                            cursor_id = "select"

                        elif GD["subobj_edit_options"]["pick_via_poly"]:

                            poly = Mgr.get("poly", color_id)

                            if poly:

                                merged_edges = poly.geom_data_obj.merged_edges

                                for edge_id in poly.edge_ids:
                                    if len(merged_edges[edge_id]) == 1:
                                        cursor_id = "select"
                                        break

                        else:

                            edge = Mgr.get("edge", color_id)
                            merged_edge = edge.merged_edge if edge else None

                            if merged_edge and len(merged_edge) == 1:
                                cursor_id = "select"

                    else:

                        cursor_id = "select"

                    if cursor_id == "select":

                        active_transform_type = GD["active_transform_type"]

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
        mouse_x, mouse_y = mouse_pointer.x, mouse_pointer.y
        mouse_start_x, mouse_start_y = self._mouse_start_pos

        if max(abs(mouse_x - mouse_start_x), abs(mouse_y - mouse_start_y)) > 3:
            if self._picked_point:
                Mgr.do("init_transform", self._picked_point)
                return task.done

        return task.cont

    def __start_mouse_check(self, prev_state_id, active):

        Mgr.add_task(self.__check_mouse_offset, "check_mouse_offset")
        Mgr.remove_task("update_cursor")

    def __cancel_mouse_check(self):

        Mgr.remove_task("check_mouse_offset")

        active_transform_type = GD["active_transform_type"]

        if active_transform_type == "rotate" \
                and GD["axis_constraints"]["rotate"] == "trackball":
            prev_constraints = GD["prev_axis_constraints_rotate"]
            Mgr.update_app("axis_constraints", "rotate", prev_constraints)

        if self._can_select_single:
            obj_lvl = GD["active_obj_level"]
            Mgr.do("select_single_" + obj_lvl)

    def __get_picked_object(self, color_id, obj_type_id):

        if not color_id:
            return "", None

        pickable_type = PickableTypes.get(obj_type_id)

        if not pickable_type:
            return "", None

        if pickable_type == "transf_gizmo":
            return "transf_gizmo", Mgr.get("transf_gizmo").select_handle(color_id)

        picked_obj = Mgr.get(pickable_type, color_id)

        return (pickable_type, picked_obj) if picked_obj else ("", None)

    def __init_select(self, op="replace"):

        alt_down = GD.mouse_watcher.is_button_down("alt")
        region_select = not alt_down if GD["region_select"]["is_default"] else alt_down

        if region_select:
            self.__init_region_select(op)
            return

        if not (GD.mouse_watcher.has_mouse() and self._pixel_under_mouse):
            return

        self._can_select_single = False
        screen_pos = Point2(GD.mouse_watcher.get_mouse())
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        self._mouse_start_pos = (mouse_pointer.x, mouse_pointer.y)
        obj_lvl = GD["active_obj_level"]

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b
        pickable_type, picked_obj = self.__get_picked_object(color_id, a)

        if (GD["active_transform_type"] and obj_lvl not in ("top", "poly")
                and pickable_type == "poly" and GD["subobj_edit_options"]["pick_via_poly"]):
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
        self._obj_id = obj.id if obj else None
        r = self.__select(op)
        selection = self._selection

        if not (obj and obj in selection):
            obj = selection[0] if selection else None

        if obj:

            cs_type = GD["coord_sys_type"]
            tc_type = GD["transf_center_type"]

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

                if GD["active_transform_type"]:

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

                transform_allowed = GD["active_transform_type"]

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
                    transform_allowed = GD["active_transform_type"]

                if transform_allowed:
                    start_mouse_checking = True

        elif op == "replace":

            selection.clear()

        Mgr.update_remotely("selection_set", "hide_name")

        return can_select_single, start_mouse_checking

    def __select_single(self):

        # If multiple objects were selected and no transformation occurred, a single
        # object has been selected out of that previous selection.

        obj = Mgr.get("object", self._obj_id)
        self._selection.replace([obj])

    def __on_right_click(self):

        if not GD.mouse_watcher.has_mouse():
            return

        ctrl_down = GD.mouse_watcher.is_button_down("control")
        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b
        pickable_type = PickableTypes.get(a)

        if pickable_type == "transf_gizmo":

            if ctrl_down:
                Mgr.update_remotely("main_context")
            else:
                Mgr.update_remotely("componentwise_xform")

        elif pickable_type:

            picked_obj = Mgr.get(pickable_type, color_id)
            obj = picked_obj.get_toplevel_object(get_group=True) if picked_obj else None
            obj_lvl = GD["active_obj_level"]

            if obj_lvl == "top" and obj:
                Mgr.do("set_object_id", obj.id)
                if ctrl_down:
                    Mgr.update_remotely("main_context", "obj_props")
                else:
                    Mgr.update_remotely("obj_props")
            elif ctrl_down:
                Mgr.update_remotely("main_context")

        elif ctrl_down:

            Mgr.update_remotely("main_context")


MainObjects.add_class(SelectionManager)
