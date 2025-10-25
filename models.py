
import logging
import random
from datas import GameKnowledge, ThreatData, UnitData
from typing import Any, Dict, Optional

from enums import PartyID
from datas import CityData
from event_bus import EventBus
import game_events
from scenario_model import ScenarioModel


logger = logging.getLogger(__name__)

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
    def __init__(self, party_id: PartyID):
        self.party_id: PartyID = party_id

        self.current_vp: int = 0
        self.reserved_ap: int = 0

        self.units_in_supply: list[str] = []  # List of unit IDs
        
        self.hand_timeline: list[str] = []
        self.hand_party: list[str] = []
        self.party_deck: list[str] = []
        self.party_discard_pile: list[str] = []

        self.agenda = None
        
        self.controlling_minor_parties: list[str] = []


class ParliamentState:
    def __init__(self):
        self.seats: dict[PartyID, int] = {party: 0 for party in PartyID}
        

class GameModel:
    def __init__(self, bus: EventBus, knowledge: GameKnowledge):
        self.bus = bus
        self.knowledge = knowledge

        self.round = 0
        self.turn: Optional[PartyID] = None

        self.dr_box_threats: list[str] = []

        self.governing_parties: list[PartyID] = []
        self.chancellor: Optional[PartyID] = None

        self.party_states: dict[PartyID, PartyState] = {
            party: PartyState(party) for party in PartyID
        }

        self.parliament_state = ParliamentState()
        
        self.cities_state: dict[str, CityState] = {}
        for city_id, city_data in self.knowledge.cities.items():
            self.cities_state[city_id] = CityState(city_data)

        self.threats_on_board: dict[str, ThreatOnBoard] = {}
        self.units_on_board: dict[str, UnitOnBoard] = {}

    def get_current_player(self) -> Optional[PartyID]:
        return self.turn

    def get_status_data(self) -> dict[str, Any]:
        status = {
            "round": self.round,
            "turn": self.turn,
            "parties": self.party_states,
            "cities": self.cities_state
        }
        return status

    def setup_game_from_scenario(self, scenario: ScenarioModel):
        """Pydantic ScenarioModel 객체를 기반으로 게임의 초기 상태를 설정합니다."""
        logger.info(f"Setting up game from scenario: {scenario.name}")

        # --- 1. 기본 상태 설정 ---
        try:
            trackers = scenario.starting_trackers
            self.round = trackers.round
            # self.foreign_affairs_track_position = trackers.foreign_affairs_track
            # self.economy_track_position = trackers.economy_track
            logger.debug(f"Trackers set: Round={self.round}, FA={trackers.foreign_affairs_track}, Eco={trackers.economy_track}")

            # --- 2. 정부 및 마이너 정당 설정 ---
            gov_info = scenario.starting_government
            self.governing_parties = gov_info.parties
            self.chancellor = gov_info.chancellor
            logger.debug(f"Government set: Chancellor={self.chancellor}, Parties={self.governing_parties}")

            minor_parties_control = scenario.starting_minor_parties
            for minor_party_id, controlling_party_id in minor_parties_control.items():
                if controlling_party_id in self.party_states:
                    self.party_states[controlling_party_id].controlling_minor_parties.append(minor_party_id)
            logger.debug(f"Minor parties assigned: {minor_parties_control}")


            # --- 3. 위협 마커 배치 ---
            threats_setup = scenario.initial_threats

            # DR Box
            for threat_id in threats_setup.dr_box:
                self._place_threat("DR_BOX", threat_id)

            # 특정 도시
            for city_id, threat_list in threats_setup.specific_cities.items():
                if city_id not in self.cities_state:
                    logger.warning(f"Scenario tries to place threat in unknown city '{city_id}'. Skipping.")
                    continue
                for threat_id in threat_list:
                    self._place_threat(city_id, threat_id)

            # 랜덤 도시
            all_city_ids = list(self.cities_state.keys())
            for task in threats_setup.random_cities:
                # task는 이제 RandomThreatTask 객체임
                threat_id_to_place = task.threat_id
                count = task.count
                unique = task.unique_cities

                # ... (랜덤 도시 선택 로직 동일) ...
                chosen_cities = []
                if count > len(all_city_ids):
                     chosen_cities = all_city_ids
                elif unique:
                     if count <= len(all_city_ids):
                          chosen_cities = random.sample(all_city_ids, count)
                     else: # 요청 수가 도시 수보다 많으면 가능한 모든 도시 선택
                          chosen_cities = all_city_ids
                          logger.warning(f"Requested {count} unique cities for threat {threat_id_to_place}, but only {len(all_city_ids)} exist. Placing in all.")
                else: # 중복 허용 (룰북 규칙 확인 필요)
                     chosen_cities = random.choices(all_city_ids, k=count)


                for city_id in chosen_cities:
                     self._place_threat(city_id, threat_id_to_place)

            # --- 4. 정당 초기 설정 (피규어 배치) ---
            party_setup = scenario.initial_party_setup # Key가 PartyID Enum임 (Pydantic 덕분)
            for party_id, setup_details in party_setup.items():
                # party_id는 이미 PartyID Enum 객체임
                if party_id not in self.party_states:
                    # Pydantic 모델에서 이미 검증되었으므로 이 경우는 거의 없음
                    logger.warning(f"Scenario contains setup for unknown party '{party_id}'. Skipping.")
                    continue
                 
                # 의석 설정
                self.parliament_state.seats[party_id] = setup_details.parliament_seats

                # 도시 기반 배치 (랜덤 도시 선택)
                city_bases_count = setup_details.city_bases
                # ... (도시 선택 로직 동일) ...
                available_cities = list(self.cities_state.keys())
                chosen_cities = [] # 실제 선택 로직 필요
                if city_bases_count > len(available_cities):
                    chosen_cities = available_cities
                else:
                    chosen_cities = random.sample(available_cities, city_bases_count)

                for city_id in chosen_cities:
                    self._place_party_base(party_id, city_id)

            # --- 5. 초기 턴 설정 ---
            # ⭐️ 시나리오에 정의되어 있지 않다면 기본값 사용
            self.turn = PartyID.SPD # 예시 기본값

            # --- 6. 완료 알림 ---
            logger.info("Game setup from scenario complete.")
            self.bus.publish(game_events.UI_SHOW_STATUS, self.get_status_data())

        except Exception as e:
            logger.exception(f"CRITICAL ERROR during scenario setup: {e}")
            raise RuntimeError(f"Failed to setup game from scenario: {e}")

    def _place_threat_in_dr_box(self, threat_id: str):
        """헬퍼 메서드: DR 박스에 위협 마커를 배치하고 상태를 업데이트합니다."""
        if threat_id not in self.knowledge.threat:
            logger.warning(f"Attempted to place unknown threat '{threat_id}' in DR Box. Skipping.")
            return
        
        # 빈곤 - 번영 상쇄
        if threat_id == "POVERTY" and "PROSPERITY" in self.dr_box_threats:
            self.dr_box_threats.remove("PROSPERITY")
            logger.debug("Removed 'PROSPERITY' from DR Box due to 'POVERTY' placement.")
            return
        elif threat_id == "PROSPERITY" and "POVERTY" in self.dr_box_threats:
            self.dr_box_threats.remove("POVERTY")
            logger.debug("Removed 'POVERTY' from DR Box due to 'PROSPERITY' placement.")
            return

        self.dr_box_threats.append(threat_id)
        logger.debug(f"Placed threat '{threat_id}' in DR Box.")

    def _place_threat(self, location_id: str, threat_id: str):
        """헬퍼 메서드: 위협 마커를 배치하고 상태를 업데이트합니다."""
        if threat_id not in self.knowledge.threat:
            logger.warning(f"Attempted to place unknown threat '{threat_id}'. Skipping.")
            return

        new_threat = ThreatOnBoard(self.knowledge.threat[threat_id], f"threat_{threat_id}_{len(self.threats_on_board)}")
        self.threats_on_board[new_threat.id] = new_threat
        
        if location_id == "DR_BOX":
            self._place_threat_in_dr_box(threat_id)
        elif location_id in self.cities_state:
            # TODO: CityState 업데이트 로직 (예: self.cities_state[location_id].threats_on_city.append(new_threat.id))
            # TODO: 룰북 규칙 적용 (예: 빈곤/번영 상쇄, 도시에 동일 위협 중복 불가)
            
            # 번영-빈곤 상쇄
            if threat_id == "POVERTY" and "PROSPERITY" in self.cities_state[location_id].threats_on_city:
                self.cities_state[location_id].threats_on_city.remove("PROSPERITY")
                logger.debug(f"Removed 'PROSPERITY' from city '{location_id}' due to 'POVERTY' placement.")
            elif threat_id == "PROSPERITY" and "POVERTY" in self.cities_state[location_id].threats_on_city:
                self.cities_state[location_id].threats_on_city.remove("POVERTY")
                logger.debug(f"Removed 'POVERTY' from city '{location_id}' due to 'PROSPERITY' placement.")
            
            # 빈곤 중복 시 DR박스에 빈곤 위협 추가
            if threat_id == "POVERTY" and "POVERTY" in self.cities_state[location_id].threats_on_city:
                self._place_threat_in_dr_box(threat_id)
                return
            # 번영 중복 시 DR박스에 번영 추가
            elif threat_id == "PROSPERITY" and "PROSPERITY" in self.cities_state[location_id].threats_on_city:
                self._place_threat_in_dr_box(threat_id)
                return
            # 기타 위협 중복 시 무시
            elif threat_id in self.cities_state[location_id].threats_on_city:
                logger.debug(f"Threat '{threat_id}' already present in city '{location_id}'. Skipping duplicate placement.")
                return
            # 도시 위협 개수 제한(threat)
            elif 

            self.cities_state[location_id].threats_on_city.append(threat_id)
            logger.debug(f"Placed threat '{threat_id}' in city '{location_id}'.")
        else:
            logger.warning(f"Attempted to place threat in unknown location '{location_id}'. Skipping.")

    def _place_party_base(self, party_id: PartyID, city_id: str):
        """헬퍼 메서드: 정당 기반을 배치하고 상태를 업데이트합니다."""
        if city_id not in self.cities_state:
            logger.warning(f"Attempted to place base in unknown city '{city_id}'. Skipping.")
            return
        if party_id not in self.party_states:
             logger.warning(f"Attempted to place base for unknown party '{party_id}'. Skipping.")
             return

        # TODO: 룰북 규칙 적용 (예: 도시의 최대 기반 수 확인)
        # city_capacity = self.knowledge.cities[city_id].max_party_bases
        # current_bases = sum(self.cities_state[city_id].party_bases.values())
        # if current_bases >= city_capacity: ...

        self.cities_state[city_id].party_bases[party_id] += 1
        logger.debug(f"Placed base for {party_id} in city '{city_id}'.")