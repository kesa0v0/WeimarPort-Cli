import logging


from presenter import GamePresenter
from utils.data_loader import DataLoader
from datas import GameKnowledge
from models import GameModel
from cli_view import CliView
from event_bus import EventBus


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

        self.game_knowledge = GameKnowledge(party=party_data, cities=city_data, units=unit_data, threat=threat_data
                                       
                                       )

        self.bus = EventBus()

    def start_game(self):
        logger.info("Setting up game...")
        model = GameModel(self.bus, knowledge=self.game_knowledge)
        # scenario_data = self.loader.load(scenario_file)
        # self.model.setup_game_from_scenario(scenario_data)

        view = CliView(self.bus)
        
        presenter = GamePresenter(self.bus, model)

        logger.info("Game setup complete.")

        return model, view, presenter


            