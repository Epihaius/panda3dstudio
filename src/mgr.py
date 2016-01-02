# the AppManager is responsible for unifying the two main components of the
# application: the Core and the GUI


class AppManager(object):

    def __init__(self, verbose=False):

        self._verbose = verbose
        self._updaters = {}
        self._globals = {}
        self._global_inits = {}
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

        self._key_handlers[""] = {
            "CORE": core_key_handlers, "GUI": gui_key_handlers}

        self._keymap["CORE"] = dict((v, core_key_evt_ids[k])
                                    for k, v in gui_key_evt_ids.iteritems())
        self._keymap["GUI"] = dict((v, gui_key_evt_ids[k])
                                   for k, v in core_key_evt_ids.iteritems())

        self._mod_key_codes = gui_mod_key_codes

        core_to_gui = gui_color_max / core_color_max
        converter = lambda rgb: None if rgb is None else [
            x / core_to_gui for x in rgb]
        self._format_converters["CORE"] = {"color": converter}
        converter = lambda rgb: None if rgb is None else [
            x * core_to_gui for x in rgb]
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

        self._key_handlers.setdefault(interface_id, {})[
            component_id] = key_handlers

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
        local_updaters = self._updaters.get("", {}).get(
            component_id, {}).get(update_id, [])
        remote_updaters = self._updaters.get(
            "", {}).get(dest, {}).get(update_id, [])

        if locally:
            for updater, param_ids in local_updaters:
                _kwargs = dict((k, v)
                               for k, v in kwargs.iteritems() if k in param_ids)
                updater(*args, **_kwargs)

        if remotely:
            for updater, param_ids in remote_updaters:
                _kwargs = dict((k, v)
                               for k, v in kwargs.iteritems() if k in param_ids)
                updater(*args, **_kwargs)

    def add_interface_updater(self, interface_id, component_id, update_id, updater, param_ids=None):
        """
        Same as add_updater(), but for a specific interface.

        """

        data = (updater, param_ids if param_ids else [])
        self._updaters.setdefault(interface_id, {}).setdefault(
            component_id, {}).setdefault(update_id, []).append(data)

    def update_interface(self, interface_id, component_id, locally, remotely, update_id, *args, **kwargs):
        """
        Same as update(), but for a specific interface.

        """

        dest = "GUI" if component_id == "CORE" else "CORE"
        local_updaters = self._updaters.get(interface_id, {}).get(
            component_id, {}).get(update_id, [])
        remote_updaters = self._updaters.get(
            interface_id, {}).get(dest, {}).get(update_id, [])

        if locally:
            for updater, param_ids in local_updaters:
                _kwargs = dict((k, v)
                               for k, v in kwargs.iteritems() if k in param_ids)
                updater(*args, **_kwargs)

        if remotely:
            for updater, param_ids in remote_updaters:
                _kwargs = dict((k, v)
                               for k, v in kwargs.iteritems() if k in param_ids)
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

            if self._verbose:
                print "The pressed key is not defined:", key_code

            return

        return self._key_handlers[interface_id][dest]["down"](self._keymap[dest][key_code])

    def remotely_handle_key_up(self, interface_id, component_id, key_code):

        dest = "GUI" if component_id == "CORE" else "CORE"

        if key_code not in self._keymap[dest]:

            if self._verbose:
                print "The released key is not defined:", key_code

            return

        return self._key_handlers[interface_id][dest]["up"](self._keymap[dest][key_code])

    def set_global(self, global_id, value):
        """
        Set a certain global value.
        This can be done from *any* object in the Core or the GUI, while a value
        obtained through manager.get() can only be set by the object that initially
        exposed it.

        """

        self._globals[global_id] = value

        if global_id not in self._global_inits:
            self._global_inits[global_id] = value

    def get_global(self, global_id):
        """
        Get the current value of a certain global.
        This value is accessible from both the Core *and* the GUI.
        Also see set_global().

        """

        if self._verbose and global_id not in self._globals:
            print 'ValueError: global "%s" is not defined.' % global_id

        return self._globals.get(global_id)

    def reset_globals(self):
        """ Reset all globals to their initial values """

        for global_id, value in self._global_inits.iteritems():
            self._globals[global_id] = value


# The following class allows predefining specific bindings of events to their
# handlers.
# Multiple bindings can be set active at once, with the option to stop listening
# for all other events.
class EventBinder(object):

    def __init__(self, listener):

        self._listener = listener
        self._bindings = {}
        self._active_bindings = {}

    def bind(self, binding_id, event_props, handler, arg_list=None, once=False):
        """
        Predefine a specific binding of an event to a handler by id.
        The event in this binding can be set to be listened for later on by simply
        using this id instead of having to set the details of the binding every
        single time.

        """

        args = (arg_list,) if arg_list else ()
        self._bindings[binding_id] = (once, event_props, handler) + args

    def unbind(self, binding_id):
        """
        Remove the given binding.
        Note that, if the binding is currently active, this also stops the event in
        that binding being listened for!

        Returns True if successful or False if binding_id was not found.

        """

        if binding_id not in self._bindings:
            return False

        event_props = self._bindings[binding_id][1]
        del self._bindings[binding_id]

        if event_props in self._active_bindings:
            self.ignore(event_props)

        return True

    def accept(self, binding_ids, exclusive=False):
        """
        Listen for the events in the bindings whose ids are given.

        If "exclusive" is True, the events in all of the predefined bindings other
        than the ones given will be ignored.

        Returns True if successful or False if not all binding_ids were found.

        """

        if exclusive:
            self.ignore_all()

        binding_ids_found = True

        for binding_id in binding_ids:

            if binding_id not in self._bindings:
                binding_ids_found = False
                continue

            binding = self._bindings[binding_id]
            event_props = binding[1]
            self._active_bindings[event_props] = binding_id
            method = self._listener.accept_once if binding[
                0] else self._listener.accept
            method(*binding[1:])

        return binding_ids_found

    def ignore(self, *event_data):
        """
        Stop listening for the events whose ids are given.

        """

        for event_props in event_data:

            self._listener.ignore(event_props)

            if event_props in self._active_bindings:
                del self._active_bindings[event_props]

    def ignore_all(self):
        """
        Stop listening for all events.

        """

        self._listener.ignore_all()
        self._active_bindings = {}

    def get_active_bindings(self):
        """
        Return a list of the ids of the bindings of the events currently being
        listened for.

        """

        return self._active_bindings.values()


class StateObject(object):

    def __init__(self, state_id, persistence, on_enter=None, on_exit=None):

        self._id = state_id
        self._persistence = persistence
        self._enter_command = on_enter if on_enter else lambda prev_state_id, is_active: None
        self._exit_command = on_exit if on_exit else lambda next_state_id, is_active: None
        self._is_active = False
        self._prev_state = None

    def get_id(self):

        return self._id

    def get_persistence(self):

        return self._persistence

    def set_active(self, is_active=True):

        self._is_active = is_active

    def is_active(self):

        return self._is_active

    def set_enter_command(self, on_enter):

        self._enter_command = on_enter

    def set_exit_command(self, on_exit):

        self._exit_command = on_exit

    def set_previous_state(self, prev_state):

        while prev_state and prev_state.get_persistence() <= self._persistence:
            prev_state = prev_state.get_previous_state()

        self._prev_state = prev_state

    def get_previous_state(self):

        prev_state = self._prev_state

        while prev_state and not prev_state.is_active():
            prev_state = prev_state.get_previous_state()

        return prev_state

    def enter(self, prev_state_id):

        self._enter_command(prev_state_id, self._is_active)
        self._is_active = True

    def exit(self, next_state_id):

        self._exit_command(next_state_id, self._is_active)


# The following class manages the different states that the application
# can be in.
class StateManager(object):

    def __init__(self):

        self._states = {}
        self._current_state_id = ""
        self._is_state_binder = False

    def add_state(self, state_id, persistence, on_enter=None, on_exit=None):
        """
        Define a new state, optionally with commands to be called on entering and/or
        exiting that state.

        """

        self._states[state_id] = StateObject(
            state_id, persistence, on_enter, on_exit)

    def set_state_enter_command(self, state_id, on_enter):

        self._states[state_id].set_enter_command(on_enter)

    def set_state_exit_command(self, state_id, on_exit):

        self._states[state_id].set_exit_command(on_exit)

    def has_state(self, state_id):
        """ Check if the state with the given id has been previously defined """

        return state_id in self._states

    def is_state_binder(self):
        """ Check if this object is a StateBinder instance """

        return self._is_state_binder

    def set_initial_state(self, state_id):
        """
        Set the current state at the start of the application.

        Returns True if successful or False if the state with the given id has not
        been previously defined or is already the current state.

        """

        if state_id not in self._states:
            return False

        current_state_id = self._current_state_id

        if state_id == current_state_id:
            return False

        state = self._states[state_id]
        state.enter(current_state_id)

        if self._is_state_binder:
            self._set_state_bindings(state_id)

        self._current_state_id = state_id

        return True

    def enter_state(self, state_id):
        """
        Change from the current state to the one with the given id.

        Returns True if successful or False if the state with the given id has not
        been previously defined or is already the current state.

        """

        if state_id not in self._states:
            return False

        current_state_id = self._current_state_id

        if state_id == current_state_id:
            return False

        current_state = self._states[current_state_id]
        state = self._states[state_id]
        state.set_previous_state(current_state)
        persistence = state.get_persistence()

        if current_state.get_persistence() <= persistence:
            current_state.set_active(False)

        current_state.exit(state_id)
        prev_state = current_state.get_previous_state()

        while prev_state and prev_state is not state and prev_state.get_persistence() <= persistence:
            prev_state.set_active(False)
            prev_state.exit(state_id)
            prev_state = prev_state.get_previous_state()

        state.enter(self._current_state_id)

        if self._is_state_binder:
            self._set_state_bindings(state_id)

        self._current_state_id = state_id

        return True

    def exit_state(self, state_id):
        """
        Exit the state with the given id. If it is not the current state, it will
        merely get deactivated (its exit command will still be called and it will
        be marked as inactive, but its previous state will not be restored).

        Returns True if successful or False if the state with the given id has not
        been previously defined, is inactive or is the default state.

        """

        if state_id not in self._states:
            return False

        state = self._states[state_id]

        if not state.is_active():
            return False

        prev_state = state.get_previous_state()

        if not prev_state:
            # only the default state has no previous state
            return False

        current_state_id = self._current_state_id
        state.set_active(False)

        if state_id == current_state_id:

            prev_state_id = prev_state.get_id()
            state.exit(prev_state_id)
            prev_state.enter(state_id)

            if self._is_state_binder:
                self._set_state_bindings(prev_state_id)

            self._current_state_id = prev_state_id

        else:

            state.exit(current_state_id)

        return True

    def get_current_state_id(self):
        """ Return the id of the current state """

        return self._current_state_id

    def get_state_persistence(self, state_id):

        return self._states[state_id].get_persistence()


# The following class associates a particular state with a selection of event
# bindings.
class StateBinder(StateManager):

    def __init__(self, event_binder):

        StateManager.__init__(self)

        self._state_bindings = {}
        self._evt_binder = event_binder
        self._is_state_binder = True

    def add_state(self, state_id, persistence, on_enter=None, on_exit=None):
        """
        Define a new state, optionally with commands to be called on entering and/or
        exiting that state.

        """

        StateManager.add_state(self, state_id, persistence, on_enter, on_exit)

        self._state_bindings[state_id] = []

    def bind(self, state_id, binding_id, event_props, event_handler):
        """
        Define an event binding and associate it with a state.

        """

        self._evt_binder.bind(binding_id, event_props, event_handler)
        self._state_bindings[state_id].append(binding_id)

    def accept(self, binding_ids, exclusive=False):
        """
        Listen for the events in the bindings whose ids are given.

        If "exclusive" is True, the events in all of the predefined bindings other
        than the ones given will be ignored.

        Returns True if successful or False if not all binding_ids were found.

        """

        return self._evt_binder.accept(binding_ids, exclusive)

    def _set_state_bindings(self, state_id):
        """
        Change from the current state to the one with the given id.

        """

        self._evt_binder.accept(self._state_bindings[state_id], exclusive=True)

    def get_event_binder(self):
        """ Get the event binder used by this StateBinder """

        return self._evt_binder
