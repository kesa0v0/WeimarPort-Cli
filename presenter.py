

from typing import Any
from event_bus import EventBus
import game_events
from models import GameModel


class GamePresenter:
    def __init__(self, bus: EventBus, model: GameModel):
        self.bus = bus
        self.model = model

    def handle_show_status(self):
        data = self.model.get_status_data()
        self.bus.publish(game_events.UI_SHOW_STATUS, data)