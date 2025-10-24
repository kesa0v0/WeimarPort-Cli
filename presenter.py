

from typing import Any
from eventBus import EventBus
import gameEvents
from models import GameModel


class GamePresenter:
    def __init__(self, bus: EventBus, model: GameModel):
        self.bus = bus
        self.model = model

    def handle_show_status(self):
        data = self.model.get_status_data()
        self.bus.publish(gameEvents.UI_SHOW_STATUS, data)