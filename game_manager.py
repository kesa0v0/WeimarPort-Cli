import logging
import json


from presenter import GamePresenter
from utils.data_loader import DataLoader
from datas import GameKnowledge, PartyData
from models import GameModel
from cli_view import CliView
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

    def start_game(self, scenario_file="data/scenarios/main_scenario.json"):
        logger.info("Setting up game...")
        self.model = GameModel(self.bus, knowledge=self.game_knowledge)
        
        try:
            with open(scenario_file, "r", encoding="utf-8") as f:
                scenario_data = json.load(f)
            logger.info(f"Loaded scenario: {scenario_data['name']}")
        except Exception as e:
            logger.error(f"Failed to load scenario file {scenario_file}: {e}")
            return None

        self.view = CliView(self.bus)
        
        self.presenter = GamePresenter(self.bus, self.model)

        logger.info("Game setup complete.")

        return self.model, self.view, self.presenter

    def load_scenario(self, filepath: str):
        scenario_model = load_and_validate_scenario(filepath)
        if not scenario_model:
            logger.error("Scenario validation failed. Cannot load scenario.")
            return False

        self.presenter.handle_load_scenario(scenario_model)
        return True

            