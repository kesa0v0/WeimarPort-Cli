from enum import Enum

class Faction(str, Enum):
    """
    유닛의 영구적인 소속 세력(정체성)을 정의합니다.
    """
    KPD = "KPD"
    SPD = "SPD"
    DNVP = "DNVP"
    GOVERNMENT = "GOVERNMENT"

class PartyID(str, Enum):
    """
    플레이 가능한 정당의 고유 ID.
    parties.json의 'id'와 일치해야 함.
    """
    KPD = "KPD"
    SPD = "SPD"
    DNVP = "DNVP"
    ZENTRUM = "ZENTRUM"