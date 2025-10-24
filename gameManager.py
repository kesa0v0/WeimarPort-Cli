import logging


from presenter import GamePresenter
from utils.dataLoader import DataLoader
from datas import GameKnowledge
from models import GameModel
from cliView import CliView
from eventBus import EventBus


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
        self.model = GameModel(self.bus, knowledge=self.game_knowledge)
        # scenario_data = self.loader.load(scenario_file)
        # self.model.setup_game_from_scenario(scenario_data)

        self.view = CliView(self.bus)
        
        self.presenter = GamePresenter(self.bus, self.model)

        logger.info("Entering main game loop...")
        self.main_loop()


    def main_loop(self):
        while True:
            user_input = self.view.get_input("Enter command (or 'quit' to exit): ")
            if user_input.lower() == 'quit':
                logger.info("Exiting game.")
                break
            elif user_input.lower() == 'status':
                self.presenter.handle_show_status()
            # Here you would handle other commands and game logic
            