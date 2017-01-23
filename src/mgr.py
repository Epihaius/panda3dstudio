from .base import logging, EventBinder, StateManager, StateBinder


# the AppManager is responsible for unifying the two main components of the
# application: the Core and the GUI
class AppManager(object):

    def __init__(self, verbose=False):

        self._verbose = verbose
        self._updaters = {}
        self._state_mgrs = {}
        self._key_handlers = {}
        self._keymap = {}
        self._mod_key_codes = {}
        self._format_converters = {}

    def setup(self, core_listener, core_key_handlers, core_key_evt_ids,
              gui_key_handlers, gui_key_evt_ids, gui_mod_key_codes,
              core_color_max, gui_color_max):

        self._state_mgrs[""] = {"CORE": StateBinder(EventBinder(core_listener)),
                                "GUI": StateManager()}

        self._key_handlers[""] = {"CORE": core_key_handlers, "GUI": gui_key_handlers}

        self._keymap["CORE"] = dict((v, core_key_evt_ids[k]) for k, v in gui_key_evt_ids.iteritems())
        self._keymap["GUI"] = dict((v, gui_key_evt_ids[k]) for k, v in core_key_evt_ids.iteritems())

        self._mod_key_codes = gui_mod_key_codes

        core_to_gui = gui_color_max / core_color_max
        converter = lambda color: None if color is None else tuple(x / core_to_gui for x in color)
        self._format_converters["CORE"] = {"color": converter}
        converter = lambda color: None if color is None else tuple(x * core_to_gui for x in color)
        self._format_converters["GUI"] = {"color": converter}

    def remove_interface(self, interface_id):

        self.remove_state_managers(interface_id)
        self.remove_key_handlers(interface_id)
        self.remove_updaters(interface_id)

    def add_state_manager(self, interface_id, component_id, listener=None):

        if listener:
            state_mgr = StateBinder(EventBinder(listener))
        else:
            state_mgr = StateManager()

        self._state_mgrs.setdefault(interface_id, {})[component_id] = state_mgr

    def remove_state_managers(self, interface_id):

        if interface_id not in self._state_mgrs:
            return

        state_mgrs = self._state_mgrs[interface_id]

        for component_id in state_mgrs:

            state_mgr = state_mgrs[component_id]

            if state_mgr.is_state_binder():
                event_binder = state_mgr.get_event_binder()
                event_binder.ignore_all()

        del self._state_mgrs[interface_id]

    def add_key_handlers(self, interface_id, component_id, key_handlers):

        self._key_handlers.setdefault(interface_id, {})[component_id] = key_handlers

    def remove_key_handlers(self, interface_id):

        handlers = self._key_handlers

        if interface_id in handlers:
            del handlers[interface_id]

    def get_mod_key_code(self, mod_key_id):

        return self._mod_key_codes[mod_key_id]

    def add_state(self, interface_id, component_id, state_id, persistence,
                  on_enter=None, on_exit=None):

        self._state_mgrs[interface_id][component_id].add_state(state_id, persistence,
                                                               on_enter, on_exit)

    def set_initial_state(self, interface_id, state_id):
        """
        Set the initial state of a particular application interface.

        """

        state_mgrs = self._state_mgrs[interface_id]
        state_mgrs["CORE"].set_initial_state(state_id)
        state_mgrs["GUI"].set_initial_state(state_id)

    def enter_state(self, interface_id, state_id):

        state_mgrs = self._state_mgrs[interface_id]
        state_mgrs["CORE"].enter_state(state_id)
        state_mgrs["GUI"].enter_state(state_id)

    def exit_state(self, interface_id, state_id):

        state_mgrs = self._state_mgrs[interface_id]
        state_mgrs["CORE"].exit_state(state_id)
        state_mgrs["GUI"].exit_state(state_id)

    def get_state_id(self, interface_id, component_id):

        return self._state_mgrs[interface_id][component_id].get_current_state_id()

    def get_state_persistence(self, interface_id, component_id, state_id):

        return self._state_mgrs[interface_id][component_id].get_state_persistence(state_id)

    def bind_state(self, interface_id, state_id, binding_id, event_props, event_handler):

        self._state_mgrs[interface_id]["CORE"].bind(state_id, binding_id, event_props,
                                                    event_handler)

    def activate_bindings(self, interface_id, binding_ids, exclusive=False):

        self._state_mgrs[interface_id]["CORE"].accept(binding_ids, exclusive)

    def add_updater(self, component_id, update_id, updater, param_ids=None):
        """
        Add an updater for the property with the given update_id, in either the core
        or the GUI.
        The optional param_ids is a list of parameter names that are defined for
        this updater, but not necessarily for other updaters for the same property.
        This list includes names of parameters for which values will be passed as
        keyword arguments, especially parameters that are not defined for at least
        one of the other updaters.
        When calling all updaters for the property with the given update_id, only
        arguments with keywords that are in this list will be passed along to this
        updater.

        """

        data = (updater, param_ids if param_ids else [])
        self._updaters.setdefault("", {}).setdefault(
            component_id, {}).setdefault(update_id, []).append(data)

    def update(self, component_id, locally, remotely, update_id, *args, **kwargs):
        """
        Call all updaters defined for the property with the given update_id.
        Each updater will handle the update in either the core or the GUI, so both
        components can be updated simultaneously using this method, which can be
        called from either component.
        This unifies the updating of both components, while allowing data to be
        passed on selectively to each updater by passing along the given keyword
        arguments to only those updaters that accept them.

        """

        dest = "GUI" if component_id == "CORE" else "CORE"
        local_updaters = self._updaters.get("", {}).get(component_id, {}).get(update_id, [])
        remote_updaters = self._updaters.get("", {}).get(dest, {}).get(update_id, [])

        if locally:
            for updater, param_ids in local_updaters:
                _kwargs = dict((k, v) for k, v in kwargs.iteritems() if k in param_ids)
                updater(*args, **_kwargs)

        if remotely:
            for updater, param_ids in remote_updaters:
                _kwargs = dict((k, v) for k, v in kwargs.iteritems() if k in param_ids)
                updater(*args, **_kwargs)

    def add_interface_updater(self, interface_id, component_id, update_id, updater,
                              param_ids=None):
        """
        Same as add_updater(), but for a specific interface.

        """

        data = (updater, param_ids if param_ids else [])
        self._updaters.setdefault(interface_id, {}).setdefault(
            component_id, {}).setdefault(update_id, []).append(data)

    def update_interface(self, interface_id, component_id, locally, remotely,
                         update_id, *args, **kwargs):
        """
        Same as update(), but for a specific interface.

        """

        dest = "GUI" if component_id == "CORE" else "CORE"
        local_updaters = self._updaters.get(interface_id, {}).get(component_id, {}).get(update_id, [])
        remote_updaters = self._updaters.get(interface_id, {}).get(dest, {}).get(update_id, [])

        if locally:
            for updater, param_ids in local_updaters:
                _kwargs = dict((k, v) for k, v in kwargs.iteritems() if k in param_ids)
                updater(*args, **_kwargs)

        if remotely:
            for updater, param_ids in remote_updaters:
                _kwargs = dict((k, v) for k, v in kwargs.iteritems() if k in param_ids)
                updater(*args, **_kwargs)

    def remove_updaters(self, interface_id):
        """
        Remove all updaters defined for a specific interface.

        """

        if interface_id in self._updaters:
            del self._updaters[interface_id]

    def convert_to_format(self, component_id, format_type, data):

        dest = "GUI" if component_id == "CORE" else "CORE"

        return self._format_converters[dest][format_type](data)

    def convert_from_format(self, component_id, format_type, data):

        return self._format_converters[component_id][format_type](data)

    def remotely_handle_key_down(self, interface_id, component_id, key_code):

        dest = "GUI" if component_id == "CORE" else "CORE"

        if key_code not in self._keymap[dest]:

            if "mouse" not in key_code:

                logging.warning('The pressed key "%s" is not defined.', str(key_code))

                if self._verbose:
                    print "The pressed key is not defined:", key_code

            return

        return self._key_handlers[interface_id][dest]["down"](self._keymap[dest][key_code])

    def remotely_handle_key_up(self, interface_id, component_id, key_code):

        dest = "GUI" if component_id == "CORE" else "CORE"

        if key_code not in self._keymap[dest]:

            if "mouse" not in key_code:

                logging.warning('The released key "%s" is not defined.', str(key_code))

                if self._verbose:
                    print "The released key is not defined:", key_code

            return

        return self._key_handlers[interface_id][dest]["up"](self._keymap[dest][key_code])
