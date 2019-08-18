from .base import *


class ExportManager:

    def __init__(self):

        self._exporters = {}
        self._exporters["bam"] = exporters.bam.BamExporter()
        self._exporters["obj"] = exporters.obj.ObjExporter()

        Mgr.add_app_updater("export", self.__update_export)

    def __prepare_export(self):

        if Mgr.get("selection_top"):
            Mgr.update_remotely("export", "export")
        elif Mgr.get("objects"):
            Mgr.update_remotely("export", "confirm_entire_scene")
        else:
            Mgr.update_remotely("export", "empty_scene")

    def __export(self, filename):

        ext = os.path.splitext(filename)[1].lstrip(".")
        self._exporters[ext].export(filename)

    def __update_export(self, update_type, *args):

        if update_type == "prepare":
            self.__prepare_export()
        elif update_type == "export":
            self.__export(*args)


MainObjects.add_class(ExportManager)
