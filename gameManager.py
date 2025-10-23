
from cliView import CliView
from utils.dataLoader import DataLoader

class GameManager:
    def __init__(self):
        self.cli = CliView()
        self.loader = DataLoader()

        self.cli.tag_print("WeimarPort-Cli 시작", "INFO")
        self.cli.tag_print("정적 데이터 로드 중...", "INIT")

        party_data = self.loader.load("data/parties.json")
        # city_data = loader.load("data/cities.json")
        # unit_data = loader.load("data/units.json")
    