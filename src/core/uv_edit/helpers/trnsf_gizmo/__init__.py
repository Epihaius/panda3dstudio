from ...base import *
from .translate import TranslationComponent
from .rotate import RotationComponent
from .scale import ScalingComponent


class UVTransformGizmo(BaseObject):

    def __init__(self):

        def get_next_id():

            i = 0

            while True:
                i += 1
                yield i

        self._picking_col_id_generator = get_next_id()
        self._pickable_type_id = None
        self._root = root = self.uv_space.attach_new_node("transform_gizmo_root")
        root.hide()
        root.set_light_off()
        root.set_texture_off()
        root.set_material_off()
        root.set_shader_off()

        self._transf_start_mouse = ()

        self._components = {}
        self._active_component_ids = []

        UVMgr.accept("set_transf_gizmo_pos", self.set_pos)
        UVMgr.accept("show_transf_gizmo", self.show)
        UVMgr.accept("hide_transf_gizmo", self.hide)
        UVMgr.accept("enable_transf_gizmo", self.enable)
        UVMgr.accept("disable_transf_gizmo", self.disable)
        UVMgr.accept("set_transf_gizmo_pickable", self.set_pickable)

    def setup(self):

        self._pickable_type_id = PickableTypes.get_id("transf_gizmo")

        if self._pickable_type_id is None:
            return False

        components = {
            "": DefaultAxes(self),
            "translate": TranslationComponent(self),
            "rotate": RotationComponent(self),
            "scale": ScalingComponent(self)
        }
        components["translate"].set_active_axes("uv")
        components["scale"].set_active_axes("uv")
        self._components = components
        self._active_component_ids = ["translate", "rotate", "scale"]

        return True

    def add_interface_updaters(self):

        Mgr.add_interface_updater("uv_window", "active_transform_type", self.__select_component)
        Mgr.add_interface_updater("uv_window", "transform_handles", self.__show_transform_handles)
        Mgr.add_interface_updater("uv_window", "axis_constraints", self.__update_axis_constraints)

    def __update_hilites(self, task):

        comp_ids = self._active_component_ids

        if not comp_ids:
            return task.cont

        pixel_color = UVMgr.get("pixel_under_mouse")
        r, g, b, a = [int(round(c * 255.)) for c in pixel_color]
        color_id = r << 16 | g << 8 | b

        components = self._components

        if color_id and a == self._pickable_type_id:
            for comp_id in comp_ids:
                components[comp_id].hilite_handle(color_id)
        else:
            for comp_id in comp_ids:
                components[comp_id].remove_hilite()

        return task.cont

    def get_root(self):

        return self._root

    def get_next_picking_color_id(self):

        return self._picking_col_id_generator.next()

    def select_handle(self, color_id):

        components = self._components

        for comp_id in self._active_component_ids:

            axes = components[comp_id].select_handle(color_id)

            if axes:

                component_ids = ["translate", "rotate", "scale"]
                component_ids.remove(comp_id)

                for component_id in component_ids:
                    components[component_id].set_active(False)

                component = components[comp_id]
                component.set_active()
                component.set_active_axes(axes)

                return component

    def __select_component(self, component_id):

        components = self._components
        component = components[component_id]
        component_ids = ["translate", "rotate", "scale"]

        if component_id:
            component_ids.remove(component_id)

        for comp_id in component_ids:
            components[comp_id].set_active(False)

        if component_id:
            component.set_active()
            component.set_active_axes(component.get_active_axes())

    def __show_transform_handles(self, transf_type, shown):

        if shown:
            self._components[transf_type].show()
            self._active_component_ids.append(transf_type)
        else:
            self._components[transf_type].hide()
            self._active_component_ids.remove(transf_type)

    def update_transform_handles(self):

        active_component_ids = self._active_component_ids

        for transf_type in ("translate", "rotate", "scale"):
            shown = transf_type in  active_component_ids
            Mgr.update_interface_remotely("uv_window", "transform_handles", transf_type, shown)

    def __update_axis_constraints(self, transf_type, axes):

        GlobalData["uv_axis_constraints_%s" % transf_type] = axes
        self._components[transf_type].set_active_axes(axes)

    def enable(self):

        Mgr.add_task(self.__update_hilites, "update_uv_gizmo", sort=1)

    def disable(self):

        Mgr.remove_task("update_uv_gizmo")

        for comp_id in self._active_component_ids:
            self._components[comp_id].remove_hilite()

    def show(self):

        self._root.show()

        if Mgr.get_state_id("uv_window") == "uv_edit_mode":
            Mgr.add_task(self.__update_hilites, "update_uv_gizmo", sort=1)

    def hide(self):

        Mgr.remove_task("update_uv_gizmo")
        self._root.hide()

    def set_pos(self, pos):

        self._root.set_pos(pos)

    def set_scale(self, scale):

        self._root.set_scale(scale)

    def set_pickable(self, pickable=True):

        picking_mask = UVMgr.get("picking_mask")
        self._root.show(picking_mask) if pickable else self._root.hide(picking_mask)


class DefaultAxes(object):

    def __init__(self, gizmo):

        self._gizmo = gizmo
        self._origin = gizmo.get_root().attach_new_node("uv_gizmo_default_axes")
        self._origin.hide(UVMgr.get("picking_mask"))
        self._origin.set_y(1.)

        for i, axis in enumerate("uv"):
            pos = Point2()
            pos[i] = .1
            handle = self.__create_axis_handle(pos, axis + "_axis_handle")
            color = VBase4(0., 0., 0., 1.)
            color[i] = .3
            handle.set_color(color)

    def __create_axis_handle(self, pos, node_name):

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("axis_line_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.add_data3f(0., 0., 0.)
        u, v = pos
        pos_writer.add_data3f(u, 0., v)
        axis_line = GeomLines(Geom.UH_static)
        axis_line.add_vertices(0, 1)
        axis_line_geom = Geom(vertex_data)
        axis_line_geom.add_primitive(axis_line)
        axis_line_node = GeomNode(node_name)
        axis_line_node.add_geom(axis_line_geom)

        return self._origin.attach_new_node(axis_line_node)
