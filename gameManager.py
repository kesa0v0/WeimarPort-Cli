import logging


from cliView import CliView
from utils.dataLoader import DataLoader


logger = logging.getLogger(__name__) 


class GameManager:
    def __init__(self):
        self.cli = CliView()
        self.loader = DataLoader()

        logger.info("WeimarPort-Cli 시작")
        logger.info("정적 데이터 로드 중...")

        party_data = self.loader.load("data/parties.json")
        city_data = self.loader.load("data/cities.json")
        unit_data = self.loader.load("data/units.json")
    