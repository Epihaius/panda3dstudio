from ....base import *
from .detach import PolygonDetachBase, PolygonDetachManager
from .triangulate import TriangulationBase, TriangulationManager
from .smooth import SmoothingBase, SmoothingManager, SmoothingGroup
from .flip import PolygonFlipBase, PolygonFlipManager


class PolygonEditBase(PolygonDetachBase, TriangulationBase, SmoothingBase,
                      PolygonFlipBase):

    def __init__(self):

        TriangulationBase.__init__(self)
        SmoothingBase.__init__(self)


class PolygonEditManager(PolygonDetachManager, TriangulationManager,
                         SmoothingManager, PolygonFlipManager):

    def __init__(self):

        self._pixel_under_mouse = VBase4()
        self._obj_is_under_mouse = None

        PolygonDetachManager.__init__(self)
        TriangulationManager.__init__(self)
        SmoothingManager.__init__(self)
        PolygonFlipManager.__init__(self)

    def setup(self):

        if not TriangulationManager.setup(self):
            return False
        if not SmoothingManager.setup(self):
            return False

        return True

    def _update_cursor(self, task):

        self._pixel_under_mouse = Mgr.get("pixel_under_mouse")
        obj_is_under_mouse = self._pixel_under_mouse != VBase4()

        if obj_is_under_mouse != self._obj_is_under_mouse:
            self._obj_is_under_mouse = obj_is_under_mouse
            Mgr.set_cursor("select" if obj_is_under_mouse else "main")

        return task.cont


MainObjects.add_class(PolygonEditManager)
