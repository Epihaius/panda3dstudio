from .base import *
from .mgr import CoreManager as Mgr


class CreationPhaseManager(object):

    _id_generator = id_generator()

    def __init__(self, obj_type, has_color=False, add_to_hist=False):

        self._obj = None
        self._obj_type = obj_type
        self._has_color = has_color
        self._add_to_hist = add_to_hist
        self._custom_obj_name = ""

        self._origin_pos = Point3()
        self._creation_handlers = []
        self._current_creation_phase = 0

        if has_color:
            self.set_next_object_color()
        else:
            GlobalData["next_%s_color" % obj_type] = None

        Mgr.expose("custom_%s_name" % obj_type, lambda: self._custom_obj_name)
        Mgr.accept("set_custom_%s_name" % obj_type, self.__set_custom_object_name)

    def setup(self, creation_phases, status_text):

        creation_status = {}
        mode_text = "Create %s" % status_text["obj_type"]
        info_text = "LMB-drag to start creation"
        creation_status["idle"] = {"mode": mode_text, "info": info_text}

        add_state = Mgr.add_state
        bind = Mgr.bind_state
        state_persistence = -12

        for i, phase_data in enumerate(creation_phases):

            main_starter, main_handler = phase_data

            if i == 0:
                creation_starter = self.__get_creation_starter(main_starter)
                Mgr.accept("start_%s_creation" % self._obj_type, creation_starter)
                on_enter_state = None
            else:
                on_enter_state = self.__get_creation_phase_starter(main_starter)

            state_id = "%s_creation_phase_%s" % (self._obj_type, i + 1)
            add_state(state_id, state_persistence, on_enter_state)

            self._creation_handlers.append(self.__get_creation_phase_handler(main_handler))

            binding_id = "quit %s creation" % self._obj_type
            bind(state_id, binding_id, "escape", self.__end_creation)
            binding_id = "cancel %s creation" % self._obj_type
            bind(state_id, binding_id, "mouse3-up", self.__end_creation)

            info_text = "move mouse to %s;" % status_text["phase%s" % (i + 1)]
            get_command = lambda state_id: lambda: Mgr.enter_state(state_id)

            if i == len(creation_phases) - 1:
                binding_id = "finalize %s creation" % self._obj_type
                bind(state_id, binding_id, "mouse1-up",
                     lambda: self.__end_creation(cancel=False))
                info_text += " release LMB to finalize;"
            else:
                binding_id = "start %s creation phase %s" % (self._obj_type, i + 2)
                next_state_id = "%s_creation_phase_%s" % (self._obj_type, i + 2)
                bind(state_id, binding_id, "mouse1-up", get_command(next_state_id))
                info_text += " release LMB to set;"

            info_text += " RMB to cancel"
            creation_status["phase%s" % (i + 1)] = {"mode": mode_text, "info": info_text}

        status_data = GlobalData["status_data"]["create"]
        status_data[self._obj_type] = creation_status

        return True

    def __get_creation_starter(self, main_creation_func):

        def start_creation(origin_pos):

            self._origin_pos = origin_pos
            main_creation_func()

            Mgr.enter_state("%s_creation_phase_1" % self._obj_type)
            Mgr.add_task(self._creation_handlers[0], "draw_object", sort=3)
            Mgr.update_app("status", "create", self._obj_type, "phase1")

        return start_creation

    def __get_creation_phase_starter(self, main_start_func):

        def start_creation_phase(prev_state_id, is_active):

            Mgr.remove_task("draw_object")
            main_start_func()
            self._current_creation_phase += 1
            creation_handler = self._creation_handlers[self._current_creation_phase]
            Mgr.add_task(creation_handler, "draw_object", sort=3)
            phase_id = self._current_creation_phase + 1
            Mgr.update_app("status", "create", self._obj_type, "phase%s" % phase_id)

        return start_creation_phase

    def __get_creation_phase_handler(self, main_handler_func):

        def handle_creation_phase(task):

            main_handler_func()

            return task.cont

        return handle_creation_phase

    def __set_custom_object_name(self, custom_name):

        self._custom_obj_name = custom_name

    def init_object(self, obj):

        self._obj = obj

    def get_object(self):

        return self._obj

    def get_object_type(self):

        return self._obj_type

    def generate_object_id(self):

        obj_id = (self._obj_type,) + self._id_generator.next()

        return obj_id

    def set_next_object_color(self):

        color_values = tuple(random.random() * .4 + .5 for i in range(3))
        GlobalData["next_%s_color" % self._obj_type] = color_values

    def get_next_object_color(self):

        r, g, b = GlobalData["next_%s_color" % self._obj_type]
        color = VBase4(r, g, b, 1.)

        return color

    def get_origin_pos(self):

        return self._origin_pos

    def add_history(self, toplevel_obj):

        Mgr.do("update_history_time")
        name = toplevel_obj.get_name()
        event_descr = 'Create "%s"' % name
        obj_id = toplevel_obj.get_id()
        obj_data = {obj_id: toplevel_obj.get_data_to_store("creation")}
        event_data = {"objects": obj_data}
        event_data["object_ids"] = set(Mgr.get("object_ids"))
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __end_creation(self, cancel=True):

        Mgr.remove_task("draw_object")
        process = None

        if cancel or not self._obj.is_valid():

            self._obj.destroy()

        else:

            finalization = self._obj.finalize()

            if finalization:

                def finalize():

                    finalization.next()

                    for step in finalization:
                        yield True

                    obj_type = self._obj_type
                    name = Mgr.get("next_obj_name", obj_type)
                    Mgr.update_remotely("next_obj_name", name)

                    if self._add_to_hist:
                        self.add_history(self._obj.get_toplevel_object())

                    yield False

                process = finalize()

            else:

                obj_type = self._obj_type
                name = Mgr.get("next_obj_name", obj_type)
                Mgr.update_remotely("next_obj_name", name)

                if self._has_color:
                    self.set_next_object_color()

                if self._add_to_hist:
                    self.add_history(self._obj.get_toplevel_object())

        self._obj = None
        self._current_creation_phase = 0

        Mgr.notify("creation_ended")
        Mgr.enter_state("creation_mode")

        if process and process.next():
            Mgr.show_screenshot()
            descr = "Creating %s..." % self._obj_type
            Mgr.do_gradually(process, "creation", descr, cancellable=True)
