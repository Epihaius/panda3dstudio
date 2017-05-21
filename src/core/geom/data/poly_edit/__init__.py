from ....base import *
from .create import CreationBase, CreationManager
from .triangulate import TriangulationBase, TriangulationManager
from .smooth import SmoothingBase, SmoothingManager, SmoothingGroup
from .region import RegionBase, RegionManager


class PolygonEditBase(CreationBase, TriangulationBase, SmoothingBase, RegionBase):

    def __init__(self):

        TriangulationBase.__init__(self)
        SmoothingBase.__init__(self)

    def update_poly_centers(self):

        for poly in self._ordered_polys:
            poly.update_center_pos()

    def update_poly_normals(self):

        for poly in self._ordered_polys:
            poly.update_normal()

    def detach_polygons(self):

        selected_poly_ids = self._selected_subobj_ids["poly"]

        if not selected_poly_ids:
            return False

        merged_edges = self._merged_edges
        polys = self._subobjs["poly"]
        selected_polys = (polys[i] for i in selected_poly_ids)
        border_edges = []

        for poly in selected_polys:

            for edge_id in poly.get_edge_ids():

                merged_edge = merged_edges[edge_id]

                if merged_edge in border_edges:
                    border_edges.remove(merged_edge)
                else:
                    border_edges.append(merged_edge)

        edge_ids = set(e_id for merged_edge in border_edges for e_id in merged_edge)

        return self.split_edges(edge_ids)


class PolygonEditManager(CreationManager, TriangulationManager, SmoothingManager, RegionManager):

    def __init__(self):

        CreationManager.__init__(self)
        TriangulationManager.__init__(self)
        SmoothingManager.__init__(self)
        RegionManager.__init__(self)

        self._pixel_under_mouse = VBase4()

        Mgr.add_app_updater("poly_detach", self.__detach_polygons)

    def __detach_polygons(self):

        selection = Mgr.get("selection", "top")
        changed_objs = {}

        for model in selection:

            geom_data_obj = model.get_geom_object().get_geom_data_object()

            if geom_data_obj.detach_polygons():
                changed_objs[model.get_id()] = geom_data_obj

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.iteritems():
            obj_data[obj_id] = geom_data_obj.get_data_to_store("prop_change", "subobj_merge")

        event_descr = "Detach polygon selection"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def _update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont


MainObjects.add_class(PolygonEditManager)
