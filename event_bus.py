import logging
import asyncio
import inspect

logger = logging.getLogger(__name__)


class EventBus:
    listeners = {}

    def subscribe(self, event_type, listener):
        if event_type not in EventBus.listeners:
            EventBus.listeners[event_type] = []
        EventBus.listeners[event_type].append(listener)
        logger.debug(f"Listener subscribed to event '{event_type}'")

    def publish(self, event_type, data):
        if event_type in EventBus.listeners:
            for listener in EventBus.listeners[event_type]:
                if inspect.iscoroutinefunction(listener):
                    asyncio.create_task(listener(data))
                else:
                    listener(data)
            logger.debug(f"Event '{event_type}' published to {len(EventBus.listeners[event_type])} listeners")