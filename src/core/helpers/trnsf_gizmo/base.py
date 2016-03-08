from ...base import *


class TransformationGizmo(BaseObject):

    _picking_col_id_generator = lambda: None

    @classmethod
    def set_picking_col_id_generator(cls, col_id_generator):

        cls._picking_col_id_generator = col_id_generator

    def __init__(self):

        BaseObject.__init__(self)

        self._origin = None
        self._render_mask = Mgr.get("gizmo_render_mask")
        self._picking_mask = Mgr.get("gizmo_picking_mask")
        self._handles = {"axes": {}, "planes": {}, "quads": {}}
        self._handle_names = {}
        self._hilited_handles = []
        self._axis_colors = {}
        self._selected_axes = ""

        self._create_handles()

    def get_next_picking_color_id(self):

        return self._picking_col_id_generator()

    def _create_handles(self): pass

    def set_active_axes(self, axes): pass

    def hilite_handle(self, color_id): pass

    def remove_hilite(self): pass

    def select_handle(self, color_id): pass

    def set_shear(self, shear): pass

    def get_point_at_screen_pos(self, screen_pos): pass

    def show(self):

        self._origin.show()

    def hide(self):

        self._origin.hide()


class DisabledGizmo(TransformationGizmo):

    def _create_handles(self):

        root = Mgr.get("transf_gizmo_root")
        self._origin = root.attach_new_node("disabled_gizmo")
        self._origin.hide(self._picking_mask)

        for i, axis in enumerate("xyz"):
            pos = Point3()
            pos[i] = .2
            handle = self.__create_axis_handle(self._origin, pos, axis + "_axis_handle")
            color = VBase4(0., 0., 0., 1.)
            color[i] = .3
            handle.set_color(color)
            self._handles["axes"][axis] = handle

    def __create_axis_handle(self, origin, pos, node_name):

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("axis_line_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.add_data3f(0., 0., 0.)
        pos_writer.add_data3f(*pos)
        axis_line = GeomLines(Geom.UH_static)
        axis_line.add_vertices(0, 1)
        axis_line_geom = Geom(vertex_data)
        axis_line_geom.add_primitive(axis_line)
        axis_line_node = GeomNode(node_name)
        axis_line_node.add_geom(axis_line_geom)

        return origin.attach_new_node(axis_line_node)

    def set_shear(self, shear):

        self._origin.set_shear(shear)
