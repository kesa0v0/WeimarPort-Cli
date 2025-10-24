
from datas import GameKnowledge, ThreatData, UnitData
from typing import Any

from enums import PartyID
from datas import CityData
from event_bus import EventBus

class CityState:
    def __init__(self, city: CityData):
        self.city: CityData = city
        self.id: str = city.id
        self.party_bases: dict[PartyID, int] = {party: 0 for party in PartyID}
        self.units_on_city: list[str] = []  # List of unit IDs
        self.threats_on_city: list[str] = []  # List of threat IDs
                

class UnitOnBoard:
    def __init__(self, unit_data: UnitData, id: str):
        self.unit_data = unit_data
        self.id: str = id


class ThreatOnBoard:
    def __init__(self, threat_type: ThreatData, id: str):
        self.threat_data = threat_type
        self.id: str = id


class PartyState:
    def __init__(self):
        self.party_id: str

        self.current_vp: int = 0
        self.reserved_ap: int = 0

        self.units_in_supply: list[str] = []  # List of unit IDs
        
        self.hand_timeline: list[str] = []
        self.hand_party: list[str] = []
        self.party_deck: list[str] = []
        self.party_discard_pile: list[str] = []

        self.agenda = None
        
        self.controlling_minor_parties: list[str] = []

        

class GameModel:
    def __init__(self, bus: EventBus, knowledge: GameKnowledge):
        self.bus = bus
        self.knowledge = knowledge

        self.round = 1
        self.turn: PartyID = PartyID.SPD

        self.party_states: dict[PartyID, PartyState] = {
            party: PartyState() for party in PartyID
        }

        self.threats_on_board: dict[str, ThreatOnBoard] = {}
        self.units_on_board: dict[str, UnitOnBoard] = {}
        self.cities_state: dict[str, CityState] = {}
        
    def setup_game_from_scenario(self, scenario_data: dict[str, Any]):
        pass

    def get_status_data(self) -> dict[str, Any]:
        status = {
            "round": self.round,
            "turn": self.turn,
            "parties": self.party_states,
            "cities": self.cities_state
        }
        return status
