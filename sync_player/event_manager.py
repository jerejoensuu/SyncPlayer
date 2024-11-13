class EventManager:
    def __init__(self):
        self._handlers = {}

    def register_event(self, event_name):
        """Registers a new event."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []

    def subscribe(self, event_name, handler):
        """Subscribes a handler to an event."""
        if event_name not in self._handlers:
            self.register_event(event_name)
        self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name, handler):
        """Unsubscribes a handler from an event."""
        if event_name in self._handlers:
            self._handlers[event_name].remove(handler)

    def trigger(self, event_name, *args, **kwargs):
        """Triggers all handlers associated with an event."""
        handlers = self._handlers.get(event_name, [])
        for handler in handlers:
            handler(*args, **kwargs)
