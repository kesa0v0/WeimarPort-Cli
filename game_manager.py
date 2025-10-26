import logging
import json


from enums import PartyID
from player_agent import IPlayerAgent
from presenter import GamePresenter
from utils.data_loader import DataLoader
from datas import GameKnowledge, PartyData
from models import GameModel
from event_bus import EventBus
from utils.scenario_loader import load_and_validate_scenario


logger = logging.getLogger(__name__) 


class GameManager:
    def __init__(self):
        logger.info("Starting WeimarPort-Cli")
        logger.info("Loading static data...")
        self.loader = DataLoader()

        party_data = self.loader.load("data/parties.json")
        city_data = self.loader.load("data/cities.json")
        unit_data = self.loader.load("data/units.json")
        threat_data = self.loader.load("data/threats.json")

        self.game_knowledge = GameKnowledge(party=party_data, cities=city_data, units=unit_data, threat=threat_data # type: ignore
                                       
                                       )
        self.bus = EventBus()

    def start_game(self, agents: dict[PartyID, IPlayerAgent]):
        logger.info("Setting up game...")
        self.model = GameModel(self.bus, knowledge=self.game_knowledge)
        
        self.presenter = GamePresenter(self.bus, self.model, agents)

        logger.info("Game setup complete.")

        return self.model, self.presenter

    async def load_scenario(self, filepath: str):
        scenario_model = load_and_validate_scenario(filepath, self.game_knowledge)
        if not scenario_model:
            logger.error("Scenario validation failed. Cannot load scenario.")
            return False

        await self.presenter.handle_load_scenario(scenario_model)
        return True

            