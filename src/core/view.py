from .base import *
from direct.showbase.ShowBase import DirectObject
from direct.interval.IntervalGlobal import (LerpPosInterval, LerpQuatInterval,
    LerpScaleInterval, LerpQuatScaleInterval, Parallel)


class ViewTileFrame(object):

    _offset_x = 0.
    _offset_z = 0.
    _left = 0.
    _right = 0.
    _bottom = 0.
    _top = 0.

    @classmethod
    def init(cls):

        win_props = Mgr.get("core").win.get_properties()
        win_w, win_h = win_props.get_size()
        aspect_ratio = 1. * win_h / win_w
        cls._offset_x = 2.1 * .06 * aspect_ratio
        cls._offset_z = -1.3 * .06
        cls._left = (-1.26 - 1.2 * .06) * aspect_ratio
        cls._right = (-1.26 + .9 * .06) * aspect_ratio
        cls._bottom = .9 - 1.3 * .06
        cls._top = .9

    @classmethod
    def get(cls, index, row_size):

        col = (index % row_size)
        row = (index // row_size)
        x = col * 2.1
        z = row * -1.3 - .95
        pos = Point3(x, 0., z)

        x = col * cls._offset_x
        z = row * cls._offset_z
        l = x + cls._left
        r = x + cls._right
        b = z + cls._bottom
        t = z + cls._top
        frame = (l, r, b, t)

        return pos, frame


class ViewManager(BaseObject):

    def __is_front_custom(self):

        return self._is_front_custom[Mgr.get_global("view")]

    def __set_front_custom(self, is_front_custom):

        self._is_front_custom[Mgr.get_global("view")] = is_front_custom

    is_front_custom = property(__is_front_custom, __set_front_custom)

    def __get_default_front_quat(self):

        return self._default_front_quats[Mgr.get_global("view")]

    def __set_default_front_quat(self, quat):

        self._default_front_quats[Mgr.get_global("view")] = quat

    default_front_quat = property(__get_default_front_quat, __set_default_front_quat)

    def __get_default_home_default_pos(self):

        return self._default_home_default_transforms[Mgr.get_global("view")]["pos"]

    def __get_default_home_default_quat(self):

        return self._default_home_default_transforms[Mgr.get_global("view")]["quat"]

    def __get_default_home_default_zoom(self):

        return self._default_home_default_transforms[Mgr.get_global("view")]["zoom"]

    default_home_default_pos = property(__get_default_home_default_pos)
    default_home_default_quat = property(__get_default_home_default_quat)
    default_home_default_zoom = property(__get_default_home_default_zoom)

    def __get_custom_home_default_pos(self):

        return self._custom_home_default_transforms[Mgr.get_global("view")]["pos"]

    def __set_custom_home_default_pos(self, pos):

        self._custom_home_default_transforms[Mgr.get_global("view")]["pos"] = pos

    def __get_custom_home_default_quat(self):

        return self._custom_home_default_transforms[Mgr.get_global("view")]["quat"]

    def __set_custom_home_default_quat(self, quat):

        self._custom_home_default_transforms[Mgr.get_global("view")]["quat"] = quat

    def __get_custom_home_default_zoom(self):

        return self._custom_home_default_transforms[Mgr.get_global("view")]["zoom"]

    def __set_custom_home_default_zoom(self, zoom):

        self._custom_home_default_transforms[Mgr.get_global("view")]["zoom"] = zoom

    custom_home_default_pos = property(__get_custom_home_default_pos, __set_custom_home_default_pos)
    custom_home_default_quat = property(__get_custom_home_default_quat, __set_custom_home_default_quat)
    custom_home_default_zoom = property(__get_custom_home_default_zoom, __set_custom_home_default_zoom)

    def __get_custom_home_custom_pos(self):

        return self._custom_home_custom_transforms[Mgr.get_global("view")]["pos"]

    def __set_custom_home_custom_pos(self, pos):

        self._custom_home_custom_transforms[Mgr.get_global("view")]["pos"] = pos

    def __get_custom_home_custom_quat(self):

        return self._custom_home_custom_transforms[Mgr.get_global("view")]["quat"]

    def __set_custom_home_custom_quat(self, quat):

        self._custom_home_custom_transforms[Mgr.get_global("view")]["quat"] = quat

    def __get_custom_home_custom_zoom(self):

        return self._custom_home_custom_transforms[Mgr.get_global("view")]["zoom"]

    def __set_custom_home_custom_zoom(self, zoom):

        self._custom_home_custom_transforms[Mgr.get_global("view")]["zoom"] = zoom

    custom_home_custom_pos = property(__get_custom_home_custom_pos, __set_custom_home_custom_pos)
    custom_home_custom_quat = property(__get_custom_home_custom_quat, __set_custom_home_custom_quat)
    custom_home_custom_zoom = property(__get_custom_home_custom_zoom, __set_custom_home_custom_zoom)

    def __get_default_home_custom_pos(self):

        pos = self._default_home_custom_transforms[Mgr.get_global("view")]["pos"]

        return self.default_home_default_pos if pos is None else pos

    def __set_default_home_custom_pos(self, pos):

        self._default_home_custom_transforms[Mgr.get_global("view")]["pos"] = pos

    def __get_default_home_custom_quat(self):

        quat = self._default_home_custom_transforms[Mgr.get_global("view")]["quat"]

        return self.default_home_default_quat if quat is None else quat

    def __set_default_home_custom_quat(self, quat):

        self._default_home_custom_transforms[Mgr.get_global("view")]["quat"] = quat

    def __get_default_home_custom_zoom(self):

        zoom = self._default_home_custom_transforms[Mgr.get_global("view")]["zoom"]

        return self.default_home_default_zoom if zoom is None else zoom

    def __set_default_home_custom_zoom(self, zoom):

        self._default_home_custom_transforms[Mgr.get_global("view")]["zoom"] = zoom

    default_home_custom_pos = property(__get_default_home_custom_pos, __set_default_home_custom_pos)
    default_home_custom_quat = property(__get_default_home_custom_quat, __set_default_home_custom_quat)
    default_home_custom_zoom = property(__get_default_home_custom_zoom, __set_default_home_custom_zoom)

    def __get_home_default_pos(self):

        return self.custom_home_default_pos if self.is_front_custom else self.default_home_default_pos

    def __get_home_default_quat(self):

        return self.custom_home_default_quat if self.is_front_custom else self.default_home_default_quat

    def __get_home_default_zoom(self):

        return self.custom_home_default_zoom if self.is_front_custom else self.default_home_default_zoom

    home_default_pos = property(__get_home_default_pos)
    home_default_quat = property(__get_home_default_quat)
    home_default_zoom = property(__get_home_default_zoom)

    def __get_home_pos(self):

        return self.custom_home_custom_pos if self.is_front_custom else self.default_home_custom_pos

    def __set_home_pos(self, pos):

        if self.is_front_custom:
            self.custom_home_custom_pos = pos
        else:
            self.default_home_custom_pos = pos

    def __get_home_quat(self):

        return self.custom_home_custom_quat if self.is_front_custom else self.default_home_custom_quat

    def __set_home_quat(self, quat):

        if self.is_front_custom:
            self.custom_home_custom_quat = quat
        else:
            self.default_home_custom_quat = quat

    def __get_home_zoom(self):

        return self.custom_home_custom_zoom if self.is_front_custom else self.default_home_custom_zoom

    def __set_home_zoom(self, zoom):

        if self.is_front_custom:
            self.custom_home_custom_zoom = zoom
        else:
            self.default_home_custom_zoom = zoom

    home_pos = property(__get_home_pos, __set_home_pos)
    home_quat = property(__get_home_quat, __set_home_quat)
    home_zoom = property(__get_home_zoom, __set_home_zoom)

    def __get_reset_interval(self):

        interval1 = LerpPosInterval(self.cam.pivot, .5, self.home_pos,
                                    blendType="easeInOut")

        if self.cam.lens_type == "persp":
            interval2 = LerpQuatInterval(self.cam.target, .5, self.home_quat,
                                         blendType="easeInOut")
            interval3 = LerpPosInterval(self.cam.origin, .5, Point3(0., self.home_zoom, 0.),
                                        blendType="easeInOut")
            lerp_interval = Parallel(interval1, interval2, interval3)
        else:
            interval2 = LerpQuatScaleInterval(self.cam.target, .5, self.home_quat,
                                              self.home_zoom, blendType="easeInOut")
            lerp_interval = Parallel(interval1, interval2)

        return lerp_interval

    reset_interval = property(__get_reset_interval)

    def __get_default_grid_plane(self):

        return self._grid_plane_defaults[Mgr.get_global("view")]

    def __get_grid_plane(self):

        return self._grid_planes[Mgr.get_global("view")]

    def __set_grid_plane(self, grid_plane):

        self._grid_planes[Mgr.get_global("view")] = grid_plane

    default_grid_plane = property(__get_default_grid_plane)
    grid_plane = property(__get_grid_plane, __set_grid_plane)

    def __get_default_render_mode(self):

        return self._render_mode_defaults[Mgr.get_global("view")]

    def __get_render_mode(self):

        return self._render_modes[Mgr.get_global("view")]

    def __set_render_mode(self, render_mode):

        self._render_modes[Mgr.get_global("view")] = render_mode

    default_render_mode = property(__get_default_render_mode)
    render_mode = property(__get_render_mode, __set_render_mode)

    def __init__(self):

        Mgr.set_global("view", "persp")

        ViewTileFrame.init()

        frame = (-1., -.9, .9, 1.)
        region = MouseWatcherRegion("view_tiles_icon_region", frame)
        region.set_sort(1)
        self.mouse_watcher.add_region(region)

        self._listener = listener = DirectObject.DirectObject()
        listener.accept("region_enter", self.__on_region_enter)
        listener.accept("region_leave", self.__on_region_leave)
        listener.accept("region_within", self.__on_region_within)
        listener.accept("region_without", self.__on_region_without)
        self._is_clicked = False
        self._mouse_start_pos = ()
        self._view_tiles_shown = False
        self._lerp_interval = None
        self._transition_done = True
        self._dest_view = ""
        self._clock = ClockObject()
        self._mouse_prev = Point2()
        self._checking_view = False
        self._previewing = False
        self._pixel_under_mouse = VBase4()

        self._user_views = []
        self._user_lens_types = {}
        self._user_view_id = 0
        self._is_front_custom = {}
        self._default_front_quats = {}
        self._default_home_default_transforms = {}
        self._default_home_custom_transforms = {}
        self._custom_home_default_transforms = {}
        self._custom_home_custom_transforms = {}

        icon = self.screen.attach_new_node(self.__create_view_tiles_icon())
        icon.set_scale(.023, 1., .0146)
        icon.set_pos(-1.321, 0., .9851)
        self._view_tiles_icon = icon
        self._view_tiles_icon_region = region
        self._view_tile_root, self._view_tiles = self.__create_view_tiles()
        self._quick_view_select = False
        self._view_tile_entered = ""
        self._view_tiles_icon_entered = ""
        self._view_before_preview = ""
        self._view_names = {}
        self._view_label_node = label_node = TextNode("view_label")
        label_node.set_text("Perspective")
        self._view_label = label = self.screen.attach_new_node(label_node)
        label.set_scale(.05)
        label.set_pos(-1.17, 0., .94)
        self._align_info_node = info_node = TextNode("align_info")
        info_node.set_text("Pick object to align view to")
        info_node.set_align(TextNode.A_center)
        info_node.set_card_as_margin(.1, .1, .2, .1)
        info_node.set_card_color(0., 0., .3, .7)
        self._align_info = info = self.screen.attach_new_node(info_node)
        info.set_scale(.05)
        info.set_pos(0., 0., -.94)
        info.set_color(0., 1., 1.)
        info.hide()

        self._grid_planes = {}
        self._grid_plane_defaults = {}
        self._render_modes = {}
        self._render_mode_defaults = {}

        Mgr.expose("is_front_view_custom", lambda view: self._is_front_custom[view])
        Mgr.expose("view_transition_done", lambda: self._transition_done)
        Mgr.expose("view_data", self.__get_view_data)
        Mgr.accept("set_view_data", self.__set_view_data)
        Mgr.accept("start_view_transition", self.__start_view_transition)
        Mgr.accept("center_view_on_objects", self.__center_view_on_objects)
        Mgr.accept("enable_view_tiles", self.__enable_view_tiles)
        Mgr.accept("clear_user_views", self.__clear_user_views)
        Mgr.add_app_updater("view", self.__update_view)
        Mgr.add_app_updater("active_grid_plane", self.__update_grid_plane)
        Mgr.add_app_updater("render_mode", self.__update_render_mode)

    def setup(self):

        views = ("persp", "ortho", "front", "back", "left", "right", "top", "bottom")

        hprs = (VBase3(-45., -45., 0.), VBase3(-45., -45., 0.), VBase3(), VBase3(180., 0., 0.),
                VBase3(-90., 0., 0.), VBase3(90., 0., 0.), VBase3(0., -90., 0.), VBase3(180., 90., 0.))
        zooms = (-400.,) + (1.,) * 7

        def create_quat(hpr):

            quat = Quat()
            quat.set_hpr(hpr)

            return quat

        self._is_front_custom = dict((view, False) for view in views)
        self._default_front_quats = dict((view, Quat()) for view in views)
        self._default_home_default_transforms = default_default = {}
        self._default_home_custom_transforms = default_custom = {}
        self._custom_home_default_transforms = custom_default = {}
        self._custom_home_custom_transforms = custom_custom = {}
        initial_values = {"pos": None, "quat": None, "zoom": None}
        lens_types = ("persp",) + ("ortho",) * 7
        cam = self.cam

        for view, hpr, zoom, lens_type in zip(views, hprs, zooms, lens_types):
            default_default[view] = {"pos": Point3(), "quat": create_quat(hpr), "zoom": zoom}
            default_custom[view] = initial_values.copy()
            custom_default[view] = initial_values.copy()
            custom_custom[view] = initial_values.copy()
            cam.add_rig(view, VBase3(), Point3(), hpr, lens_type, zoom)

        names = ["Perspective", "Orthographic"] + [view.title() for view in views[2:]]
        self._view_names = dict((view, name) for view, name in zip(views, names))
        planes = ("xy", "xy", "xz", "xz", "yz", "yz", "xy", "xy")
        self._grid_planes = dict((view, plane) for view, plane in zip(views, planes))
        self._grid_plane_defaults = self._grid_planes.copy()
        self._render_modes = dict((view, "shaded") for view in views)
        self._render_mode_defaults = self._render_modes.copy()

        self.__update_view_tile_region()

        add_state = Mgr.add_state
        add_state("view_obj_picking_mode", -75, self.__enter_picking_mode,
                  self.__exit_picking_mode)

        def exit_view_obj_picking_mode():

            Mgr.exit_state("view_obj_picking_mode")

        bind = Mgr.bind_state
        bind("view_obj_picking_mode", "pick view obj -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("view_obj_picking_mode", "pick view obj", "mouse1", self.__pick)
        bind("view_obj_picking_mode", "exit view obj picking", "escape",
             exit_view_obj_picking_mode)
        bind("view_obj_picking_mode", "cancel view obj picking", "mouse3-up",
             exit_view_obj_picking_mode)

        status_data = Mgr.get_global("status_data")
        mode_text = "Pick object to align to"
        info_text = "LMB to pick object; RMB to end"
        status_data["pick_view_obj"] = {"mode": mode_text, "info": info_text}

        return "views_ok"

    def __enter_picking_mode(self, prev_state_id, is_active):

        if Mgr.get_global("active_obj_level") != "top":
            Mgr.set_global("active_obj_level", "top")
            Mgr.update_app("active_obj_level")

        self._align_info.show()
        Mgr.add_task(self.__update_cursor, "update_view_obj_picking_cursor")
        Mgr.update_app("status", "pick_view_obj")

    def __exit_picking_mode(self, next_state_id, is_active):

        self._align_info.hide()
        self._pixel_under_mouse = VBase4() # force an update of the cursor
                                           # next time self.__update_cursor()
                                           # is called
        Mgr.remove_task("update_view_obj_picking_cursor")
        Mgr.set_cursor("main")

    def __pick(self):

        obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if obj:
            self.__center_view_on_objects(obj_to_align_to=obj)

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __create_view_tiles_icon(self):

        vertex_format = GeomVertexFormat.get_v3()

        vertex_data = GeomVertexData("icon_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        lines = GeomLines(Geom.UH_static)
        vert_index = 0

        for i in range(3):

            x_offset = i * 1.4

            for j in range(3):

                z_offset = j * -1.4
                x1 = x_offset + .2
                x2 = x1 + 1.
                z1 = z_offset - .2
                z2 = z1 - 1.
                pos_writer.add_data3f(x1, 0., z1)
                pos_writer.add_data3f(x2, 0., z1)
                pos_writer.add_data3f(x1, 0., z2)
                pos_writer.add_data3f(x2, 0., z2)
                lines.add_vertices(vert_index, vert_index + 1)
                lines.add_vertices(vert_index + 2, vert_index + 3)
                lines.add_vertices(vert_index, vert_index + 2)
                lines.add_vertices(vert_index + 1, vert_index + 3)
                vert_index += 4

        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        icon_node = GeomNode("view_tiles_icon")
        icon_node.add_geom(lines_geom)

        return icon_node

    def __create_view_tiles(self):

        views = ("persp", "front", "left", "top", "ortho", "back", "right", "bottom")
        labels = [view[0].upper() for view in views]
        tile_root = self.screen.attach_new_node("view_tile_root")
        tile_root.hide()
        tile_root.set_pos(-1.26, 0., .9)
        tile_root.set_scale(.06)
        tiles = {}
        index = 0

        self._view_tile_region_group = regions = []

        for view, label in zip(views, labels):
            tile_node = TextNode("view_tile")
            tile_node.set_text(label)
            tile_node.set_align(TextNode.A_center)
            tile_node.set_frame_color(1., 1., 1., 1.)
            tile_node.set_frame_actual(-.9, .9, -.2, .8)
            tile_node.set_frame_line_width(2)
            tile_node.set_flatten_flags(TextNode.FF_strong)
            tile = tile_root.attach_new_node(tile_node)
            pos, frame = ViewTileFrame.get(index, 4)
            tile.set_pos(pos)
            tiles[view] = tile
            region = MouseWatcherRegion("view_tile_region_%s" % view, frame)
            region.set_active(False)
            region.set_sort(-1)
            regions.append(region)
            self.mouse_watcher.add_region(region)
            index += 1

        tiles["persp"].set_color(0., 1., 1., 1.)
        tiles["persp"].node().set_frame_color(0., 1., 1., 1.)

        region = MouseWatcherRegion("view_tiles_region", -1., 1., -1., 1.)
        region.set_active(False)
        self._view_tiles_region = region
        self.mouse_watcher.add_region(region)

        return tile_root, tiles

    def __append_view_tile(self, view):

        index = len(self._view_tiles)
        label = str(index - 7)

        tile_node = TextNode("view_tile")
        tile_node.set_text(label)
        tile_node.set_align(TextNode.A_center)
        tile_node.set_frame_color(1., 1., 1., 1.)
        tile_node.set_frame_actual(-.9, .9, -.2, .8)
        tile_node.set_frame_line_width(2)
        tile_node.set_flatten_flags(TextNode.FF_strong)
        tile = self._view_tile_root.attach_new_node(tile_node)
        pos, frame = ViewTileFrame.get(index, 4)
        tile.set_pos(pos)
        self._view_tiles[view] = tile
        region = MouseWatcherRegion("view_tile_region_%s" % view, frame)
        region.set_active(self._view_tiles_shown)
        region.set_sort(-1)
        self._view_tile_region_group.append(region)
        self.mouse_watcher.add_region(region)

    def __remove_view_tile(self, view):

        region_group = self._view_tile_region_group
        last_region = region_group.pop()
        self.mouse_watcher.remove_region(last_region)
        last_view = last_region.get_name().replace("view_tile_region_", "")
        tiles = self._view_tiles
        tile = tiles[last_view]
        tile.remove_node()

        if view == last_view:
            del tiles[view]
            return

        for region in reversed(region_group):

            cur_view = region.get_name().replace("view_tile_region_", "")
            region.set_name("view_tile_region_" + last_view)
            tiles[last_view] = tiles[cur_view]
            last_view = cur_view

            if cur_view == view:
                break

        del tiles[view]

    def __update_view_tile_region(self):

        win_w, win_h = Mgr.get("core").win.get_properties().get_size()
        aspect_ratio = 1. * win_h / win_w

        tile_count = len(self._view_tiles) - 1
        width = 4 * .06 * 2.1 * aspect_ratio
        height = ((tile_count // 4) + 1) * .06 * 1.3
        frame = (-1., -1. + width, .9 - height, .9)
        self._view_tiles_region.set_frame(frame)

    def __get_view_data(self):

        cam = self.cam
        data = {}
        data["custom"] = self._is_front_custom
        data["default_home_custom"] = self._default_home_custom_transforms
        data["custom_home_default"] = self._custom_home_default_transforms
        data["custom_home_custom"] = self._custom_home_custom_transforms
        data["user"] = user_views = self._user_views
        data["user_lenses"] = self._user_lens_types
        data["user_id"] = self._user_view_id
        names = self._view_names
        data["user_names"] = dict((view, names[view]) for view in user_views)
        front_quats = self._default_front_quats
        data["user_front_quats"] = dict((view, front_quats[view]) for view in user_views)
        default_transforms = self._default_home_default_transforms
        data["user_defaults"] = dict((view, default_transforms[view]) for view in user_views)
        data["cam_pivot_pos"] = cam.get_pivot_positions()
        data["cam_pivot_hpr"] = cam.get_pivot_hprs()
        data["cam_target_hpr"] = cam.get_target_hprs()
        data["cam_zoom"] = cam.get_zooms()
        data["grid"] = self._grid_planes
        grid_defaults = self._grid_plane_defaults
        data["grid_user"] = dict((view, grid_defaults[view]) for view in user_views)
        data["render_mode"] = self._render_modes
        render_mode_defaults = self._render_mode_defaults
        data["render_mode_user"] = dict((view, render_mode_defaults[view]) for view in user_views)
        data["view"] = Mgr.get_global("view")

        return data

    def __set_view_data(self, data):

        self._is_front_custom = data["custom"]
        self._default_home_custom_transforms = data["default_home_custom"]
        self._custom_home_default_transforms = data["custom_home_default"]
        self._custom_home_custom_transforms = data["custom_home_custom"]
        self._user_views = user_views = data["user"]
        self._user_lens_types = lens_types = data["user_lenses"]
        self._user_view_id = data["user_id"]
        view_names = self._view_names
        user_names = data["user_names"]
        view_names.update(user_names)
        user_defaults = data["user_defaults"]
        self._default_home_default_transforms.update(user_defaults)
        front_quats = data["user_front_quats"]
        self._default_front_quats.update(front_quats)
        cam = self.cam

        for view in user_views:
            defaults = user_defaults[view]
            self.__append_view_tile(view)
            cam.add_rig(view, front_quats[view].get_hpr(), defaults["pos"],
                        defaults["quat"].get_hpr(), lens_types[view], defaults["zoom"])
            Mgr.update_remotely("view", "add", view, view_names[view])

        self.__update_view_tile_region()

        cam.set_pivot_positions(data["cam_pivot_pos"])
        cam.set_pivot_hprs(data["cam_pivot_hpr"])
        cam.set_target_hprs(data["cam_target_hpr"])
        cam.set_zooms(data["cam_zoom"])

        self._grid_planes = data["grid"]
        grid_defaults = self._grid_plane_defaults

        for view, plane in data["grid_user"].iteritems():
            grid_defaults[view] = plane

        self._render_modes = data["render_mode"]
        render_mode_defaults = self._render_mode_defaults

        for view, render_mode in data["render_mode_user"].iteritems():
            render_mode_defaults[view] = render_mode

        self.__set_view(data["view"], force=True)

    def __clear_user_views(self):

        if self._view_tile_entered in self._user_views:
            self.__on_region_leave(self._view_tiles_region)
        elif self._view_before_preview in self._user_views:
            self.__set_view("persp")

        if Mgr.get_global("view") in self._user_views:
            self.__set_view("persp")

        cam = self.cam
        view_names = self._view_names
        default_front = self._default_front_quats
        default_default = self._default_home_default_transforms
        default_custom = self._default_home_custom_transforms
        custom_default = self._custom_home_default_transforms
        custom_custom = self._custom_home_custom_transforms
        grid_plane_def =self._grid_plane_defaults
        grid_planes = self._grid_planes
        render_mode_def = self._render_mode_defaults
        render_modes = self._render_modes

        for view in self._user_views[::-1]:
            del view_names[view]
            del default_front[view]
            del default_default[view]
            del default_custom[view]
            del custom_default[view]
            del custom_custom[view]
            del grid_plane_def[view]
            del grid_planes[view]
            del render_mode_def[view]
            del render_modes[view]
            cam.remove_rig(view)
            self.__remove_view_tile(view)
            Mgr.update_remotely("view", "remove", view)

        self.__update_view_tile_region()
        self._user_views = []
        self._user_lens_types = {}
        self._user_view_id = 0

    def __update_grid_plane(self, grid_plane):

        self.grid_plane = grid_plane

    def __update_render_mode(self):

        self.render_mode = Mgr.get_global("render_mode")

    def __update_view(self, update_type, *args):

        view = Mgr.get_global("view")

        if update_type == "set":
            self.__set_view(*args)
        elif update_type == "center":
            self.__center_view_on_objects(*args)
        elif update_type == "reset":
            self.__reset_view(*args)
        elif update_type == "reset_all":
            self.__reset_all_views(*args)
        elif update_type == "set_as_home":
            self.__set_as_home_view()
        elif update_type == "reset_home":
            self.__reset_home_view()
        elif update_type == "set_as_front":
            self.__set_as_front_view()
        elif update_type == "reset_front":
            self.__reset_front_view()
        elif update_type == "init_copy":
            lens_type = args[0]
            Mgr.update_remotely("view", "get_copy_name", lens_type, self._view_names[view])
        elif update_type == "copy":
            self.__copy_view(*args)
        elif update_type == "take_snapshot":
            self.__take_snapshot(*args)
        elif update_type == "convert":
            self.__convert_view(*args)
        elif update_type == "init_remove":
            if view in self._user_views:
                Mgr.update_remotely("view", "confirm_remove", self._view_names[view])
        elif update_type == "remove":
            self.__remove_user_view()
        elif update_type == "init_clear":
            if self._user_views:
                Mgr.update_remotely("view", "confirm_clear", len(self._user_views))
        elif update_type == "clear":
            self.__clear_user_views()
        elif update_type == "init_rename":
            if view in self._user_views:
                Mgr.update_remotely("view", "get_new_name", self._view_names[view])
        elif update_type == "rename":
            name = args[0]
            namestring = "\n".join(self._view_names.itervalues())
            name = get_unique_name(name, namestring)
            self._view_names[view] = name
            self._view_label_node.set_text("User %s - %s" % (self.cam.lens_type, name))
            Mgr.update_remotely("view", "rename", view, name)
        elif update_type == "obj_align":
            Mgr.enter_state("view_obj_picking_mode")

    def __convert_view(self, lens_type):

        view = Mgr.get_global("view")

        if view not in self._user_views:
            return

        cam = self.cam
        current_lens_type = cam.lens_type

        if current_lens_type == lens_type:
            return

        self._user_lens_types[view] = lens_type
        default_default = self._default_home_default_transforms[view]
        default_default["zoom"] = cam.convert_zoom(lens_type, zoom=default_default["zoom"])
        default_custom = self._default_home_custom_transforms[view]
        custom_default = self._custom_home_default_transforms[view]
        custom_custom = self._custom_home_custom_transforms[view]

        for transforms in (default_custom, custom_default, custom_custom):

            zoom = transforms["zoom"]

            if zoom is not None:
                zoom = cam.convert_zoom(lens_type, zoom=zoom)
                transforms["zoom"] = zoom

        zoom = cam.convert_zoom(lens_type)
        cam.lens_type = lens_type
        cam.zoom = zoom
        cam.update()
        self._view_label_node.set_text("User %s - %s" % (lens_type, self._view_names[view]))
        Mgr.do("adjust_grid_to_lens")
        Mgr.do("adjust_picking_cam_to_lens")
        Mgr.do("adjust_transform_gizmo_to_lens", current_lens_type, lens_type)

    def __set_view(self, view, force=False):
        """ Switch to a different view """

        current_view = self._view_before_preview if self._view_tile_entered else Mgr.get_global("view")
        self._view_tiles[current_view].set_color(1., 1., 1., 1.)
        self._view_tiles[current_view].node().set_frame_color(1., 1., 1., 1.)
        self._view_tiles[view].set_color(0., 1., 1., 1.)
        self._view_tiles[view].node().set_frame_color(0., 1., 1., 1.)

        if self._view_tile_entered:

            self._view_before_preview = view
            return

        else:

            name = self._view_names[view]

            if view in self._user_views:
                name = "User %s - %s" % (self._user_lens_types[view], name)

            self._view_label_node.set_text(name)

        if not force and current_view == view:
            return

        cam = self.cam
        current_lens_type = cam.lens_type
        Mgr.set_global("view", view)
        cam.update()
        lens_type = cam.lens_type

        Mgr.update_app("active_grid_plane", self.grid_plane)
        Mgr.set_global("render_mode", self.render_mode)
        Mgr.update_app("render_mode")

        if current_lens_type != lens_type:
            Mgr.do("adjust_grid_to_lens")
            Mgr.do("adjust_picking_cam_to_lens")
            Mgr.do("adjust_transform_gizmo_to_lens", current_lens_type, lens_type)

        Mgr.do("update_zoom_indicator")
        Mgr.do("update_view_gizmo", cube=False, hpr=True)
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")

    def __copy_view(self, lens_type, name):
        """ Copy the current view using the given lens type and make it a user view """

        current_view = Mgr.get_global("view")
        namestring = "\n".join(self._view_names.itervalues())
        name = get_unique_name(name, namestring)
        view = str(self._user_view_id)
        self._view_names[view] = name

        cam = self.cam

        pivot_pos = cam.pivot.get_pos()
        pivot_hpr = cam.pivot.get_hpr()
        target_hpr = cam.target.get_hpr()
        zoom = cam.convert_zoom(lens_type)

        self._is_front_custom[view] = self._is_front_custom[current_view]

        default_front = self._default_front_quats
        default_front[view] = default_front[current_view]
        default_default = self._default_home_default_transforms
        default_default[view] = default_default[current_view].copy()
        default_custom = self._default_home_custom_transforms
        default_custom[view] = default_custom[current_view].copy()
        custom_default = self._custom_home_default_transforms
        custom_default[view] = custom_default[current_view].copy()
        custom_custom = self._custom_home_custom_transforms
        custom_custom[view] = custom_custom[current_view].copy()

        self._grid_plane_defaults[view] = self._grid_plane_defaults[current_view]
        self._grid_planes[view] = self._grid_planes[current_view]
        self._render_mode_defaults[view] = self._render_mode_defaults[current_view]
        self._render_modes[view] = self._render_modes[current_view]

        self.__append_view_tile(view)
        self.__update_view_tile_region()
        self._user_views.append(view)
        self._user_lens_types[view] = lens_type
        self._user_view_id += 1
        cam.add_rig(view, pivot_hpr, pivot_pos, target_hpr, lens_type, zoom)

        zoom = cam.convert_zoom(lens_type, zoom=default_default[current_view]["zoom"])
        default_default[view]["zoom"] = zoom

        for transforms in (default_custom, custom_default, custom_custom):

            zoom = transforms[current_view]["zoom"]

            if zoom is not None:
                zoom = cam.convert_zoom(lens_type, zoom=zoom)
                transforms[view]["zoom"] = zoom

        Mgr.update_remotely("view", "add", view, name)

        self.__set_view(view)

    def __take_snapshot(self, view_name):
        """ Take a snapshot of the current view and make it a user view """

        current_view = Mgr.get_global("view")
        namestring = "\n".join(self._view_names.itervalues())
        name = get_unique_name(view_name, namestring)
        view = str(self._user_view_id)
        self._view_names[view] = name

        self._is_front_custom[view] = False

        cam = self.cam

        pivot = cam.pivot
        pivot_pos = pivot.get_pos()
        pivot_hpr = pivot.get_hpr()
        front_quat = pivot.get_quat()
        target = cam.target
        target_hpr = target.get_hpr()
        quat = target.get_quat()
        zoom = cam.zoom
        initial_values = {"pos": None, "quat": None, "zoom": None}
        default_front = self._default_front_quats
        default_front[view] = front_quat
        default_default = self._default_home_default_transforms
        default_default[view] = {"pos": pivot_pos, "quat": quat, "zoom": zoom}
        default_custom = self._default_home_custom_transforms
        default_custom[view] = initial_values.copy()
        custom_default = self._custom_home_default_transforms
        custom_default[view] = initial_values.copy()
        custom_custom = self._custom_home_custom_transforms
        custom_custom[view] = initial_values.copy()

        grid_plane = self._grid_planes[current_view]
        self._grid_plane_defaults[view] = grid_plane
        self._grid_planes[view] = grid_plane
        render_mode = self._render_modes[current_view]
        self._render_mode_defaults[view] = render_mode
        self._render_modes[view] = render_mode

        self.__append_view_tile(view)
        self.__update_view_tile_region()
        self._user_views.append(view)
        lens_type = cam.lens_type
        self._user_lens_types[view] = lens_type
        self._user_view_id += 1
        cam.add_rig(view, pivot_hpr, pivot_pos, target_hpr, lens_type, zoom)

        Mgr.update_remotely("view", "add", view, name)

        self.__set_view(view)

    def __remove_user_view(self):

        view = Mgr.get_global("view")

        if view not in self._user_views:
            return

        if self._view_tile_entered in self._user_views:
            self.__on_region_leave(self._view_tiles_region)
        elif self._view_before_preview in self._user_views:
            self.__set_view("persp")

        if Mgr.get_global("view") in self._user_views:
            self.__set_view("persp")

        cam = self.cam

        del self._view_names[view]
        del self._default_front_quats[view]
        del self._default_home_default_transforms[view]
        del self._default_home_custom_transforms[view]
        del self._custom_home_default_transforms[view]
        del self._custom_home_custom_transforms[view]
        del self._grid_plane_defaults[view]
        del self._grid_planes[view]
        del self._render_mode_defaults[view]
        del self._render_modes[view]
        cam.remove_rig(view)
        self.__remove_view_tile(view)
        Mgr.update_remotely("view", "remove", view)

        self.__update_view_tile_region()
        self._user_views.remove(view)
        del self._user_lens_types[view]

    def __adjust_transition_hpr(self, task):

        cam_target = self.cam.target
        quat = cam_target.get_quat()

        # prevent the bottom view from flipping 180 degrees when orbiting
        # the view later, due to a negative heading
        if self._dest_view == "-z":
            hpr = Vec3(180., 90., 0.)
        else:
            hpr = quat.get_hpr()

        cam_target.set_hpr(hpr)

        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")
        Mgr.do("update_zoom_indicator")

    def __transition_view(self, task):

        if self._lerp_interval.is_stopped():
            self._lerp_interval = None
            self._transition_done = True
            return

        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")
        Mgr.do("update_zoom_indicator")

        return task.cont

    def __start_view_transition(self, dest_view, quat):

        self._dest_view = dest_view
        lerp_interval = LerpQuatInterval(self.cam.target, .5, quat,
                                         blendType="easeInOut")
        self._lerp_interval = lerp_interval
        lerp_interval.start()
        self._transition_done = False
        Mgr.add_task(self.__transition_view, "transition_view", sort=30,
                     uponDeath=self.__adjust_transition_hpr)
        Mgr.do("start_view_gizmo_transition")

    def __set_as_front_view(self, view=None):
        """ Set the given or current view as a custom Front view """

        if view:
            current_view = Mgr.get_global("view")
            Mgr.set_global("view", view)

        cam = self.cam
        self.is_front_custom = True
        pos = cam.pivot.get_pos()
        quat = Quat()
        zoom = cam.zoom
        self.custom_home_default_pos = pos
        self.custom_home_default_quat = quat
        self.custom_home_default_zoom = zoom
        self.home_pos = pos
        self.home_quat = quat
        self.home_zoom = zoom
        hpr = cam.target.get_hpr(self.world)
        cam.target.set_hpr(0., 0., 0.)
        cam.pivot.set_hpr(hpr)

        if not view or view == current_view:
            Mgr.do("update_view_gizmo", False, True)

        if view:
            Mgr.set_global("view", current_view)

    def __reset_front_view(self, view=None, transition=True, reset_roll=True):
        """ Realigns the Front view to the world (or original user view space) """

        if view:
            current_view = Mgr.get_global("view")
            Mgr.set_global("view", view)

        if not self.is_front_custom:

            if view:
                Mgr.set_global("view", current_view)

            return

        cam = self.cam
        ref_node = NodePath("ref_node")
        def_front_quat = self.default_front_quat
        ref_node.set_quat(def_front_quat)
        hpr = cam.target.get_hpr(ref_node)
        quat = Quat()

        if reset_roll:
            forward_vec = ref_node.get_relative_vector(cam.target, Vec3.forward())
            look_at(quat, forward_vec, Vec3.up())
        else:
            quat.set_hpr(hpr)

        if transition and (not view or view == current_view):

            cam.target.set_hpr(hpr)
            cam.pivot.set_quat(def_front_quat)
            self._transition_done = False
            interval1 = LerpQuatInterval(cam.target, .5, quat, blendType="easeInOut")
            interval2 = LerpQuatInterval(Mgr.get("view_gizmo_root"), .5,
                                         def_front_quat, blendType="easeInOut")
            lerp_interval = Parallel(interval1, interval2)
            Mgr.do("start_view_gizmo_transition")
            self._lerp_interval = lerp_interval
            lerp_interval.start()
            Mgr.add_task(self.__transition_view, "transition_view", sort=30,
                         uponDeath=self.__adjust_transition_hpr)
            self._dest_view = ""

        else:

            cam.target.set_quat(quat)
            cam.pivot.set_quat(def_front_quat)

            if not view or view == current_view:
                Mgr.do("update_view_gizmo", False, True)

        self.is_front_custom = False

        if view:
            Mgr.set_global("view", current_view)

    def __set_as_home_view(self):
        """ Set the current view as the Home view """

        cam = self.cam
        self.home_pos = cam.pivot.get_pos()
        self.home_quat = cam.target.get_quat()
        self.home_zoom = cam.zoom

    def __reset_home_view(self):
        """ Reset the Home view """

        self.home_pos = self.home_default_pos
        self.home_quat = self.home_default_quat
        self.home_zoom = self.home_default_zoom

    def __reset_view(self, to_default=True, transition=False):
        """ Make the Home view the current view """

        cam = self.cam
        lerp_view_gizmo = False

        if to_default:

            if transition and self.is_front_custom:
                lerp_view_gizmo = True
                gizmo_root = Mgr.get("view_gizmo_root")
                hpr = gizmo_root.get_hpr()

            self.__reset_front_view(transition=False, reset_roll=False)
            self.__reset_home_view()
            Mgr.update_app("active_grid_plane", self.default_grid_plane)
            Mgr.set_global("render_mode", self.default_render_mode)
            Mgr.update_app("render_mode")

            if lerp_view_gizmo:
                gizmo_root.set_hpr(hpr)

        current_quat = cam.target.get_quat()
        pos = self.home_pos
        quat = self.home_quat
        zoom = self.home_zoom
        almost_same_zoom = Vec3(0., zoom, 0.) == Vec3(0., cam.zoom, 0.)
        def_front_quat = self.default_front_quat

        if current_quat.almost_same_direction(quat, .000001) \
                and cam.pivot.get_pos() == pos and almost_same_zoom:

            if lerp_view_gizmo:
                gizmo_interval = LerpQuatInterval(gizmo_root, .5, def_front_quat, blendType="easeInOut")
                self._lerp_interval = gizmo_interval
                gizmo_interval.start()
                Mgr.add_task(self.__transition_view, "transition_view", sort=30,
                             uponDeath=self.__adjust_transition_hpr)
                Mgr.do("start_view_gizmo_transition")
                self._dest_view = "home"
                self._transition_done = False

            return

        if transition:

            lerp_interval = self.reset_interval

            if lerp_view_gizmo:
                gizmo_interval = LerpQuatInterval(gizmo_root, .5, def_front_quat, blendType="easeInOut")
                lerp_interval.append(gizmo_interval)

            self._lerp_interval = lerp_interval
            lerp_interval.start()
            Mgr.add_task(self.__transition_view, "transition_view", sort=30,
                         uponDeath=self.__adjust_transition_hpr)
            Mgr.do("start_view_gizmo_transition")
            self._dest_view = "home"
            self._transition_done = False

        else:

            cam.pivot.set_pos(pos)
            cam.target.set_quat(quat)
            cam.zoom = zoom
            Mgr.do("update_transf_gizmo")
            Mgr.do("update_coord_sys")
            Mgr.do("update_zoom_indicator")
            Mgr.do("update_view_gizmo")

    def __reset_all_views(self, to_default=True, transition=False):

        current_view = Mgr.get_global("view")
        views = ("persp", "ortho", "front", "back", "left", "right", "top", "bottom")

        for view in views:
            Mgr.set_global("view", view)
            self.__reset_view(to_default, transition)

        def task():

            Mgr.set_global("view", current_view)
            self.__set_view("persp")

        PendingTasks.add(task, "set_persp_view", "ui")

    def __center_view_on_objects(self, transition=True, obj_to_align_to=None):

        if self._lerp_interval:
            return

        from math import tan, radians

        if obj_to_align_to:

            objs = [obj_to_align_to]

        else:

            pixel_color = Mgr.get("pixel_under_mouse")
            obj = Mgr.get("object", pixel_color=pixel_color)

            if obj:

                objs = [obj]

            else:

                selection = Mgr.get("selection", "top")

                if selection:
                    objs = selection
                else:
                    objs = Mgr.get("objects")

        if not objs:
            return

        obj_root = Mgr.get("object_root")
        cam = self.cam
        bounds_np = cam.origin.attach_new_node("cam_aligned_node")
        tmp_np = bounds_np.attach_new_node("tmp_node")

        if obj_to_align_to:
            bounds_np.set_hpr(obj_to_align_to.get_pivot(), 0., 0., 0.)

        parents = {}
        parent_copies = {}

        bboxes = dict((obj, obj.get_bbox()) for obj in objs if obj.get_type() == "model")

        for bbox in bboxes.itervalues():
            bbox.get_origin().detach_node()

        for obj in objs:

            orig = obj.get_origin()
            parent = orig.get_parent()
            parents[orig] = parent

            if parent in parent_copies:
                parent_copy = parent_copies[parent]
            else:
                parent_copy = NodePath("parent_copy")
                parent_copy.set_transform(parent.get_transform(self.world))
                parent_copy.wrt_reparent_to(tmp_np)
                parent_copies[parent] = parent_copy

            orig.reparent_to(parent_copy)

        bounds = tmp_np.get_tight_bounds()

        for orig, parent in parents.iteritems():
            orig.reparent_to(parent)

        for obj, bbox in bboxes.iteritems():
            bbox.get_origin().reparent_to(obj.get_origin())

        centers = {}

        for obj in objs:

            center = obj.get_center_pos(tmp_np)

            if centers:
                centers["min"].x = min(centers["min"].x, center.x)
                centers["min"].y = min(centers["min"].y, center.y)
                centers["min"].z = min(centers["min"].z, center.z)
                centers["max"].x = max(centers["max"].x, center.x)
                centers["max"].y = max(centers["max"].y, center.y)
                centers["max"].z = max(centers["max"].z, center.z)
            else:
                centers = {"min": center, "max": VBase3(center)}

        if bounds:
            point_min, point_max = bounds
            point_min.x = min(point_min.x, centers["min"].x)
            point_min.y = min(point_min.y, centers["min"].y)
            point_min.z = min(point_min.z, centers["min"].z)
            point_max.x = max(point_max.x, centers["max"].x)
            point_max.y = max(point_max.y, centers["max"].y)
            point_max.z = max(point_max.z, centers["max"].z)
        else:
            point_min, point_max = centers["min"], centers["max"]

        if cam.lens.is_perspective():
            vec = (point_min - point_max) * .5
            center_pos = self.world.get_relative_point(tmp_np, point_max + vec)
        else:
            vec = point_max - point_min
            center_pos = self.world.get_relative_point(tmp_np, point_min + vec * .5)

        bounds_np.remove_node()

        if cam.lens.is_perspective():

            fov_h, fov_v = cam.lens.get_fov()
            x, y, z = vec
            x = min(-.01, x)
            y = min(-.01, y)
            z = min(-.01, z)

            if vec.length_squared() < .000001:
                zoom = None
            else:
                zoom = y + ((x / tan(radians(fov_h * .5))) if x / z > fov_h / fov_v
                    else (z / tan(radians(fov_v * .5))))
                zoom = max(-1000000., min(-cam.lens.get_near(), zoom))

            if transition:
                if zoom is None:
                    interval1 = None
                else:
                    interval1 = LerpPosInterval(cam.origin, .3, Point3(0., zoom, 0.),
                                                blendType="easeInOut")
            else:
                set_zoom = lambda: None if zoom is None else cam.origin.set_y(zoom)

        else:

            size_h, size_v = cam.lens.get_film_size()
            x, y, z = vec
            x = max(.01, x)
            y = max(.01, y)
            z = max(.01, z)

            if vec.length_squared() < .000001:
                zoom = None
            else:
                zoom = (x / size_h) if x / z > size_h / size_v else (z / size_v)
                zoom *= cam.target.get_scale()[0]
                zoom = min(100000., max(.0004, zoom))

            if transition:
                if zoom is None:
                    interval1 = None
                else:
                    interval1 = LerpScaleInterval(cam.target, .3, zoom, blendType="easeInOut")
            else:
                set_zoom = lambda: None if zoom is None else cam.target.set_scale(zoom)

        if transition:

            interval2 = LerpPosInterval(cam.pivot, .3, center_pos, blendType="easeInOut")
            lerp_interval = Parallel(interval2)

            if interval1 is not None:
                lerp_interval.append(interval1)

            if obj_to_align_to:
                quat = obj_to_align_to.get_pivot().get_quat(self.world)
                interval3 = LerpQuatInterval(cam.pivot, .3, quat, blendType="easeInOut")
                interval4 = LerpQuatInterval(cam.target, .3, Quat(), blendType="easeInOut")
                interval5 = LerpQuatInterval(Mgr.get("view_gizmo_root"), .5,
                                             quat, blendType="easeInOut")
                lerp_interval.append(interval3)
                lerp_interval.append(interval4)
                lerp_interval.append(interval5)

            self._lerp_interval = lerp_interval
            lerp_interval.start()
            Mgr.add_task(self.__transition_view, "transition_view", sort=30)
            Mgr.do("start_view_gizmo_transition")
            self._dest_view = "obj_extents"
            self._transition_done = False

        else:

            cam.pivot.set_pos(center_pos)
            set_zoom()
            Mgr.do("update_transf_gizmo")
            Mgr.do("update_coord_sys")
            Mgr.do("update_zoom_indicator")

            if obj_to_align_to:
                Mgr.do("update_view_gizmo", False, True)

        if obj_to_align_to:
            self.is_front_custom = True
            quat = Quat()
            zoom = cam.zoom if zoom is None else zoom
            self.custom_home_default_pos = center_pos
            self.custom_home_default_quat = quat
            self.custom_home_default_zoom = zoom
            self.home_pos = center_pos
            self.home_quat = quat
            self.home_zoom = zoom

    def __enable_view_tiles(self, enable=True):

        self._view_tiles_icon_region.set_active(enable)
        self._view_tiles_region.set_active(enable)

        if self._view_tiles_shown:
            for region in self._view_tile_region_group:
                region.set_active(enable)

    def __exit_view_tiles_region(self):

        Mgr.remove_task("check_view")

        if self._view_tile_entered:

            current_view = Mgr.get_global("view")
            self._view_tiles[current_view].set_color_scale(1., 1., 1., 1.)
            self._view_label.set_color_scale(1., 1., 1., 1.)
            view = self._view_before_preview

            if view and view != current_view:

                current_lens_type = self.cam.lens_type
                Mgr.set_global("view", view)
                self.cam.update()
                lens_type = self.cam.lens_type
                name = self._view_names[view]

                if view in self._user_views:
                    name = "User %s - %s" % (lens_type, name)

                self._view_label_node.set_text(name)
                Mgr.update_app("active_grid_plane", self.grid_plane)
                Mgr.set_global("render_mode", self.render_mode)
                Mgr.update_app("render_mode")

                if current_lens_type != lens_type:
                    Mgr.do("adjust_grid_to_lens")
                    Mgr.do("adjust_picking_cam_to_lens")
                    Mgr.do("adjust_transform_gizmo_to_lens", current_lens_type, lens_type)

                Mgr.do("update_zoom_indicator")
                Mgr.do("update_view_gizmo", cube=False, hpr=True)
                Mgr.do("update_transf_gizmo")
                Mgr.do("update_coord_sys")

            self._view_tile_entered = ""
            self._view_before_preview = ""

    def __on_region_enter(self, *args):

        name = args[0].get_name()

        if self._quick_view_select:
            if name == "view_tiles_icon_region":
                self._view_tiles_icon_entered = True
            return

        if name == "view_tiles_icon_region":
            self._view_tiles_icon_entered = True
            self._view_tiles_icon.set_color_scale(1., 1., 0., 1.)
            Mgr.get("core").suppress_mouse_events()
            self._listener.accept("mouse1", self.__on_left_down)
            self._listener.accept("mouse1-up", self.__on_left_up)
            self._listener.accept("mouse3", self.__on_right_down)
        elif name == "view_tiles_region":
            Mgr.get("core").suppress_mouse_events()
            self._listener.accept("mouse1", self.__on_left_down)
            self._listener.accept("mouse1-up", self.__on_left_up)
            self._listener.accept("mouse3", self.__on_right_down)

    def __on_region_leave(self, *args):

        name = args[0].get_name()

        if self._quick_view_select:
            if name == "view_tiles_icon_region":
                self._view_tiles_icon_entered = False
            return

        if name == "view_tiles_icon_region":
            self._view_tiles_icon_entered = False
            self._view_tiles_icon.set_color_scale(1., 1., 1., 1.)
            self._listener.ignore("mouse1")
            self._listener.ignore("mouse1-up")
            Mgr.get("core").suppress_mouse_events(False)
        elif name == "view_tiles_region":
            self._listener.ignore("mouse1")
            self._listener.ignore("mouse1-up")
            Mgr.get("core").suppress_mouse_events(False)
            self.__exit_view_tiles_region()

    def __do_preview(self, view):

        self._view_tile_entered = view
        current_view = Mgr.get_global("view")
        self._view_tiles[current_view].set_color_scale(1., 1., 1., 1.)
        self._view_tiles[view].set_color_scale(1., 1., 0., 1.)
        self._view_label.set_color_scale(1., 1., 0., 1.)

        if not self._view_before_preview:
            self._view_before_preview = current_view

        if view != current_view:

            current_lens_type = self.cam.lens_type
            Mgr.set_global("view", view)
            self.cam.update()
            lens_type = self.cam.lens_type
            name = self._view_names[view]

            if view in self._user_views:
                name = "User %s - %s" % (lens_type, name)

            self._view_label_node.set_text(name)
            Mgr.update_app("active_grid_plane", self.grid_plane)
            Mgr.set_global("render_mode", self.render_mode)
            Mgr.update_app("render_mode")

            if current_lens_type != lens_type:
                Mgr.do("adjust_grid_to_lens")
                Mgr.do("adjust_picking_cam_to_lens")
                Mgr.do("adjust_transform_gizmo_to_lens", current_lens_type, lens_type)

            Mgr.do("update_zoom_indicator")
            Mgr.do("update_view_gizmo", cube=False, hpr=True)
            Mgr.do("update_transf_gizmo")
            Mgr.do("update_coord_sys")

    def __check_view(self, view, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        mouse_pos = self.mouse_watcher.get_mouse()

        if mouse_pos == self._mouse_prev:

            if not self._checking_view:
                self._checking_view = True
                self._clock.reset()
            elif not self._previewing and self._clock.get_real_time() >= .02:
                self.__do_preview(view)
                self._previewing = True
                self._clock.reset()
                return

        else:

            self._mouse_prev = Point2(mouse_pos)

            if self._checking_view:
                self._checking_view = False
                self._previewing = False

        return task.cont

    def __on_region_within(self, *args):

        name = args[0].get_name()

        if name.startswith("view_tile_region_"):
            view = name.replace("view_tile_region_", "")
            Mgr.remove_task("check_view")
            Mgr.add_task(self.__check_view, "check_view", extraArgs=[view], appendTask=True)

    def __on_region_without(self, *args):

        name = args[0].get_name()

        if name == "view_tiles_region":
            self.__exit_view_tiles_region()

    def __toggle_view_tiles(self):

        self._view_tiles_shown = not self._view_tiles_shown
        color = (0., 1., 1., 1.) if self._view_tiles_shown else (1., 1., 1., 1.)
        self._view_tiles_icon.set_color(color)

        if self._view_tiles_shown:

            self._view_tile_root.show()
            self._view_tiles_region.set_active(True)

            for region in self._view_tile_region_group:
                region.set_active(True)

        else:

            Mgr.remove_task("check_view")
            current_view = Mgr.get_global("view")
            self._view_tiles[current_view].set_color_scale(1., 1., 1., 1.)
            self._view_label.set_color_scale(1., 1., 1., 1.)
            self._view_tile_root.hide()
            self._view_tile_entered = ""
            self._view_before_preview = ""
            self._view_tiles_region.set_active(False)

            for region in self._view_tile_region_group:
                region.set_active(False)

    def __check_mouse_offset(self, task):
        """
        Delay showing view tiles until user has moved mouse at least 3 pixels
        in any direction, in case of unintended clicks on view tile icon.

        """

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = mouse_pointer.get_y()
        mouse_start_x, mouse_start_y = self._mouse_start_pos

        if max(abs(mouse_x - mouse_start_x), abs(mouse_y - mouse_start_y)) > 3:
            self._quick_view_select = True
            self.__toggle_view_tiles()
            return task.done

        return task.cont

    def __on_left_down(self):

        self._is_clicked = True

        if self._view_tiles_icon_entered and not self._view_tiles_shown:
            mouse_pointer = Mgr.get("mouse_pointer", 0)
            self._mouse_start_pos = (mouse_pointer.get_x(), mouse_pointer.get_y())
            Mgr.add_task(self.__check_mouse_offset, "check_mouse_offset")

    def __on_left_up(self):

        if not self._is_clicked:
            return

        self._is_clicked = False

        if self._view_tile_entered:
            Mgr.set_global("view", self._view_tile_entered)
            self.__set_view(self._view_tile_entered)

        if self._quick_view_select:

            Mgr.remove_task("check_mouse_offset")
            self.__toggle_view_tiles()
            self._quick_view_select = False

            if not self._view_tiles_icon_entered:
                self._view_tiles_icon.set_color_scale(1., 1., 1., 1.)
                self._listener.ignore("mouse1")
                self._listener.ignore("mouse1-up")
                Mgr.get("core").suppress_mouse_events(False)

        elif self._view_tiles_icon_entered:

            Mgr.remove_task("check_mouse_offset")
            self.__toggle_view_tiles()

    def __on_right_down(self):

        self._is_clicked = True
        tile_entered = self._view_tile_entered

        if tile_entered:
            if tile_entered in self._user_views:
                Mgr.update_remotely("view", "menu", "user")
            else:
                Mgr.update_remotely("view", "menu", "std")


MainObjects.add_class(ViewManager)
