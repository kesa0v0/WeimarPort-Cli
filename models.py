
import logging
import random
from typing import Any, Dict, List, Optional, Set
import uuid

from datas import GameKnowledge, ThreatData, UnitData
from enums import PartyID
from datas import CityData
from event_bus import EventBus
import game_events
from scenario_model import ScenarioModel
from game_action import Move, ActionTypeEnum, PlayOptionEnum


logger = logging.getLogger(__name__)

class CityState:
    def __init__(self, city: CityData):
        self.city: CityData = city
        self.id: str = city.id
        self.party_bases: dict[PartyID, int] = {party: 0 for party in PartyID}
        self.units_on_city: Set[str] = set()  # List of unit IDs
        self.threats_on_city: Set[str] = set()  # List of threat IDs


class UnitOnBoard:
    def __init__(self, unit_data: UnitData, id: str):
        self.unit_data = unit_data
        self.id: str = id
        self.current_location: str = "AVAILABLE_POOL"
        self.is_flipped: bool = False


class ThreatOnBoard:
    def __init__(self, threat_type: ThreatData, id: str):
        self.threat_data = threat_type
        self.id: str = id
        self.current_location: str = "AVAILABLE_POOL"


class PartyState:
    def __init__(self, party_id: PartyID):
        self.party_id: PartyID = party_id

        self.current_vp: int = 0
        self.reserved_ap: int = 0

        self.current_seats: int = 0

        self.unit_supply: Set[str] = set()  # List of unit IDs

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

        self.parliament_state = ParliamentState()
        self.governing_parties: set[PartyID] = set()
        self.chancellor: Optional[PartyID] = None
        self.party_states: dict[str, PartyState] = {}
        self.cities_state: dict[str, CityState] = {}

        # --- Object Pools ---
        self.all_threats: Dict[str, ThreatOnBoard] = {}
        self.all_units: Dict[str, UnitOnBoard] = {}
        self._threat_pool_by_type: Dict[str, List[str]] = {}
        self._unit_pool_by_type: Dict[str, List[str]] = {}
        self.dr_box_threats: Set[str] = set()
        self.dissolved_units: Set[str] = set()

        # --- Setup Phase State ---
        self.setup_phase_active: bool = False
        self.placement_order: List[PartyID] = []
        self.setup_current_party_index: int = 0
        self.setup_bases_placed_count: int = 0
        self.scenario_data: Optional[ScenarioModel] = None


    def initialize_game_objects(self):
        if self.knowledge:
            # Initialize Party States
            if self.knowledge.party:
                self.party_states = {party_id: PartyState(PartyID(party_id)) for party_id in self.knowledge.party.keys()}
            # Initialize City States
            if self.knowledge.cities:
                self.cities_state = {city_id: CityState(city_data) for city_id, city_data in self.knowledge.cities.items()}

            # ⭐️ Initialize Threat Pool
            if self.knowledge.threat:
                logger.debug("Initializing threat pool...")
                for template_id, threat_data in self.knowledge.threat.items():
                    self._threat_pool_by_type[template_id] = []
                    for i in range(threat_data.max_count):
                        instance_id = f"{template_id}_{i+1}"
                        threat_instance = ThreatOnBoard(id=instance_id, threat_type=threat_data)
                        self.all_threats[instance_id] = threat_instance
                        self._threat_pool_by_type[template_id].append(instance_id)
                logger.info(f"Threat pool initialized with {len(self.all_threats)} instances.")

            # ⭐️ Initialize Unit Pool
            if self.knowledge.units:
                logger.debug("Initializing unit pool...")
                for template_id, unit_data in self.knowledge.units.items():
                    self._unit_pool_by_type[template_id] = []
                    for i in range(unit_data.max_count):
                        instance_id = f"{template_id}_{i+1}"
                        unit_instance = UnitOnBoard(id=instance_id, unit_data=unit_data)
                        self.all_units[instance_id] = unit_instance
                        self._unit_pool_by_type[template_id].append(instance_id)
                logger.info(f"Unit pool initialized with {len(self.all_units)} instances.")

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

        try:
            self.initialize_game_objects()
        except Exception as e:
            logger.exception(f"CRITICAL ERROR during game object initialization: {e}")
            raise RuntimeError(f"Failed to initialize game objects: {e}")

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

            # --- 4. 정당 초기 설정 (의석만 설정) ---
            party_setup = scenario.initial_party_setup # Key가 PartyID Enum임 (Pydantic 덕분)
            for party_id, setup_details in party_setup.items():
                # party_id는 이미 PartyID Enum 객체임
                if party_id not in self.party_states:
                    logger.warning(f"Scenario contains setup for unknown party '{party_id}'. Skipping.")
                    continue
                # 의석 설정만 수행
                self.parliament_state.seats[party_id] = setup_details.parliament_seats

            # --- 5. 초기 턴 설정 ---
            # ⭐️ 시나리오에 정의되어 있지 않다면 기본값 사용
            self.turn = PartyID.SPD # 예시 기본값

            # --- 6. 완료 알림 ---
            logger.info("Game setup from scenario complete.")
            self.bus.publish(game_events.UI_SHOW_STATUS, self.get_status_data())

            # --- 7. 초기 기반 배치 단계 시작 ---
            self.scenario_data = scenario
            self.start_initial_setup()

            return True
        except Exception as e:
            logger.exception(f"CRITICAL ERROR during scenario setup: {e}")
            raise RuntimeError(f"Failed to setup game from scenario: {e}")


    def start_initial_setup(self):
        """
        초기 설정(기반 배치 등) 단계를 시작합니다.
        """
        if not self.scenario_data:
            logger.error("Cannot start initial setup without scenario data.")
            return

        # 여기서 플레이 순서 정의 (나중에 시나리오에서 읽어올 수도 있음)
        self.placement_order = [
            PartyID.SPD,
            PartyID.ZENTRUM,
            PartyID.KPD,
            PartyID.DNVP
        ]

        self.setup_phase_active = True
        self.setup_current_party_index = 0
        self.setup_bases_placed_count = 0

        logger.info("Initial base placement phase started.")
        self._request_next_setup_action() # 첫 액션 요청

    def _request_next_setup_action(self):
        """
        설정 단계의 다음 액션을 요청합니다. (기반 배치 요청 등)
        """
        if not self.setup_phase_active:
            return

        # 모든 정당의 배치가 끝났는지 확인
        if self.setup_current_party_index >= len(self.placement_order):
            self.setup_phase_active = False
            logger.info("Initial base placement complete.")
            self.bus.publish(game_events.SETUP_PHASE_COMPLETE, {})
            # TODO: 첫 턴 시작 로직 호출
            # self.start_first_turn()
            return

        current_party_id = self.placement_order[self.setup_current_party_index]
        try:
            bases_to_place = self.scenario_data.initial_party_setup[current_party_id].city_bases
        except (KeyError, AttributeError):
            logger.error(f"Invalid bases_to_place info for party {current_party_id}. Skipping party.")
            self.setup_current_party_index += 1
            self.setup_bases_placed_count = 0
            self._request_next_setup_action() # 다음 정당으로 넘어감
            return

        # 해당 정당이 모든 기반을 배치했는지 확인
        if self.setup_bases_placed_count >= bases_to_place:
            # 다음 정당으로 이동
            self.setup_current_party_index += 1
            self.setup_bases_placed_count = 0
            self._request_next_setup_action() # 다음 액션 요청
            return

        # 기반을 배치해야 함 -> 플레이어에게 선택 요청
        valid_cities = self.get_valid_base_placement_cities(current_party_id)
        if not valid_cities:
            logger.warning(f"No valid cities for {current_party_id} to place base. Skipping party.")
            self.setup_current_party_index += 1
            self.setup_bases_placed_count = 0
            self._request_next_setup_action()
            return

        # Presenter에게 플레이어 선택을 요청하는 이벤트 발행
        self.bus.publish(game_events.REQUEST_PLAYER_CHOICE, {
            "player_id": current_party_id,
            "options": valid_cities,
            "context": {
                "action": "initial_base_placement",
                "party": current_party_id,
                "remaining": bases_to_place - self.setup_bases_placed_count,
                "bases_to_place": bases_to_place,
                "prompt": f"기반을 배치할 도시를 선택하세요 ({self.setup_bases_placed_count + 1}/{bases_to_place})"
            }
        })

    def resolve_initial_base_placement(self, party_id: PartyID, selected_city: str):
        """
        플레이어의 초기 기반 배치 선택을 처리합니다.
        """
        if not self.setup_phase_active or self.placement_order[self.setup_current_party_index] != party_id:
            logger.warning(f"Received unexpected base placement choice from {party_id}.")
            return

        valid_cities = self.get_valid_base_placement_cities(party_id)
        if selected_city in valid_cities:
            success = self._place_party_base(party_id, selected_city)
            if success:
                self.setup_bases_placed_count += 1
                self.bus.publish(game_events.DATA_PARTY_BASE_PLACED, {
                    "party_id": party_id,
                    "city_id": selected_city,
                    "placed_count": self.setup_bases_placed_count
                })
            else:
                logger.error("Internal error: Failed to place base in a city that was considered valid.")
                # 오류 상황, 재요청 또는 다른 처리 필요
        else:
            logger.warning(f"Player {party_id} chose an invalid city '{selected_city}'.")
            # 잘못된 선택, 재요청 또는 다른 처리 필요

        # 다음 액션 요청 (성공/실패와 무관하게 다음 상태로 진행)
        self._request_next_setup_action()


    def _get_unit_instance(self, instance_id: str) -> Optional[UnitOnBoard]:
        return self.all_units.get(instance_id)
    
    def _find_available_unit(self, unit_template_id: str) -> Optional[str]:
        """주어진 유닛 타입의 사용 가능한 인스턴스 ID를 풀에서 찾아 반환합니다."""
        if unit_template_id not in self._unit_pool_by_type:
            return None
        for instance_id in self._unit_pool_by_type[unit_template_id]:
            if self.all_units[instance_id].current_location == "AVAILABLE_POOL":
                return instance_id
        return None
    

    def _get_threat_instance(self, instance_id: str) -> Optional[ThreatOnBoard]:
        return self.all_threats.get(instance_id)

    def _find_available_threat(self, threat_template_id: str) -> Optional[str]:
        """주어진 위협 타입의 사용 가능한 인스턴스 ID를 풀에서 찾아 반환합니다."""
        if threat_template_id not in self._threat_pool_by_type:
            return None
        for instance_id in self._threat_pool_by_type[threat_template_id]:
            if self.all_threats[instance_id].current_location == "AVAILABLE_POOL":
                return instance_id
        return None

    def _move_threat_instance(self, instance_id: str, new_location: str):
        """위협 인스턴스를 이동시키고, 위치 및 관련 리스트를 업데이트합니다."""
        threat = self._get_threat_instance(instance_id)
        if not threat:
            return
        old_location = threat.current_location

        # 이전 위치에서 제거
        if old_location == "DR_BOX":
            self.dr_box_threats.discard(instance_id)
        elif old_location in self.cities_state:
            self.cities_state[old_location].threats_on_city.discard(instance_id)

        # 위치 정보 갱신
        threat.current_location = new_location

        # 새 위치에 추가
        if new_location == "DR_BOX":
            self.dr_box_threats.add(instance_id)
        elif new_location in self.cities_state:
            self.cities_state[new_location].threats_on_city.add(instance_id)
        # AVAILABLE_POOL은 별도 관리 필요 없음

        logger.debug(f"Moved threat '{threat.id}' (ID: {instance_id}) from '{old_location}' to '{new_location}'.")

    def _get_threats_in_location(self, location_id: str, threat_template_id: Optional[str] = None) -> List[str]:
        """특정 위치에 있는 위협 인스턴스 ID 목록을 반환합니다. (template ID로 필터링 가능)"""
        instance_ids = []
        target_set = set()
        if location_id == "DR_BOX":
            target_set = self.dr_box_threats
        elif location_id in self.cities_state:
            target_set = self.cities_state[location_id].threats_on_city
        else:
            return []

        for inst_id in target_set:
            threat = self._get_threat_instance(inst_id)
            if threat:
                if threat_template_id is None or threat.threat_data.id == threat_template_id:
                    instance_ids.append(inst_id)
        return instance_ids

    def _place_threat(self, location_id: str, threat_template_id: str) -> Optional[str]:
        """
        위협 마커를 풀에서 찾아 지정된 위치에 배치하며, 게임 규칙을 적용합니다.
        성공 시 배치된 인스턴스 ID를 반환, 실패 시 None 반환.
        """
        threat_template = self.knowledge.threat.get(threat_template_id)
        if not threat_template:
            logger.warning(f"Attempted to place unknown threat '{threat_template_id}'. Skipping.")
            return None

        # --- DR Box 배치 ---
        if location_id == "DR_BOX":
            max_in_dr = getattr(threat_template, 'max_in_dr_box', float('inf'))
            current_in_dr = len(self._get_threats_in_location("DR_BOX", threat_template_id))
            if current_in_dr >= max_in_dr:
                logger.debug(f"Cannot place '{threat_template_id}' in DR Box: Maximum count ({max_in_dr}) reached.")
                return None

            available_instance_id = self._find_available_threat(threat_template_id)
            if available_instance_id:
                self._move_threat_instance(available_instance_id, "DR_BOX")
                return available_instance_id
            else:
                logger.debug(f"Cannot place threat '{threat_template_id}': No available instances in pool.")
                return None
            
        # --- 도시 배치 ---
        elif location_id in self.cities_state:
            city_state = self.cities_state[location_id]
            max_per_city = getattr(threat_template, 'max_per_city', float('inf'))
            current_in_city = len(self._get_threats_in_location(location_id, threat_template_id))
            if current_in_city >= max_per_city:
                if threat_template_id == "poverty":
                    logger.debug(f"'poverty' already in '{location_id}' at max ({max_per_city}). Attempting DR Box.")
                    return self._place_threat("DR_BOX", threat_template_id)
                elif threat_template_id == "prosperity":
                    logger.debug(f"'prosperity' already in '{location_id}' at max ({max_per_city}). Attempting to remove 'poverty' from DR Box.")
                    dr_poverty_id = self._get_threats_in_location("DR_BOX", "poverty")
                    if dr_poverty_id:
                        self._move_threat_instance(dr_poverty_id[0], "AVAILABLE_POOL")
                    return None
                else:
                    logger.debug(f"Cannot place '{threat_template_id}' in '{location_id}': Max per city ({max_per_city}) reached.")
                    return None

            # 상호작용 규칙 적용
            if threat_template_id == "poverty":
                prosperity_ids = self._get_threats_in_location(location_id, "prosperity")
                if prosperity_ids:
                    self._move_threat_instance(prosperity_ids[0], "AVAILABLE_POOL")
                    logger.debug(f"Removed 'prosperity' from city '{location_id}' due to 'poverty' placement attempt.")
                    return None
            elif threat_template_id == "prosperity":
                poverty_ids = self._get_threats_in_location(location_id, "poverty")
                if poverty_ids:
                    self._move_threat_instance(poverty_ids[0], "AVAILABLE_POOL")
                    logger.debug(f"Removed 'poverty' from city '{location_id}' due to 'prosperity' placement attempt.")
                    return None
            elif threat_template_id == "council":
                regime_ids = self._get_threats_in_location(location_id, "regime")
                if regime_ids:
                    self._move_threat_instance(regime_ids[0], "AVAILABLE_POOL")
                    logger.debug(f"Removed 'regime' from city '{location_id}' to place 'council'.")
            elif threat_template_id == "regime":
                council_ids = self._get_threats_in_location(location_id, "council")
                if council_ids:
                    self._move_threat_instance(council_ids[0], "AVAILABLE_POOL")
                    logger.debug(f"Removed 'council' from city '{location_id}' to place 'regime'.")

            available_instance_id = self._find_available_threat(threat_template_id)
            if available_instance_id:
                self._move_threat_instance(available_instance_id, location_id)
                return available_instance_id
            else:
                logger.debug(f"Cannot place threat '{threat_template_id}': No available instances in pool.")
                return None

        # --- 알 수 없는 위치 ---
        else:
            logger.warning(f"Attempted to place threat in unknown location '{location_id}'. Skipping.")
            return None


    def _place_party_base(self, party_id: PartyID, city_id: str) -> bool:
        """도시에 정당 기반을 배치. 성공 시 True, 실패 시 False 반환."""
        if city_id not in self.cities_state:
            logger.warning(f"Attempted to place base in unknown city '{city_id}'. Skipping.")
            return False
        if party_id not in self.party_states:
            logger.warning(f"Attempted to place base for unknown party '{party_id}'. Skipping.")
            return False
        city_capacity = self.knowledge.cities[city_id].max_party_bases
        current_bases = sum(self.cities_state[city_id].party_bases.values())
        if current_bases >= city_capacity:
            logger.debug(f"Cannot place base for '{party_id}' in '{city_id}': City capacity ({city_capacity}) reached.")
            return False
        self.cities_state[city_id].party_bases[party_id] += 1
        logger.debug(f"Placed base for {party_id} in city '{city_id}'.")
        return True

    def _remove_party_base(self, party_id: PartyID, city_id: str) -> bool:
        """도시에서 정당 기반을 1 감소. 성공 시 True, 실패 시 False 반환."""
        if city_id not in self.cities_state:
            logger.warning(f"Attempted to remove base in unknown city '{city_id}'. Skipping.")
            return False
        if party_id not in self.party_states:
            logger.warning(f"Attempted to remove base for unknown party '{party_id}'. Skipping.")
            return False
        current_bases = self.cities_state[city_id].party_bases.get(party_id, 0)
        if current_bases <= 0:
            logger.debug(f"No base to remove for '{party_id}' in '{city_id}'.")
            return False
        self.cities_state[city_id].party_bases[party_id] -= 1
        logger.debug(f"Removed base for {party_id} in city '{city_id}'.")
        return True
    
    def get_valid_base_placement_cities(self, party_id: PartyID) -> list[str]:
        """
        해당 정당이 아직 기반을 배치하지 않았고, 도시의 최대 기반 수를 넘지 않은 도시 목록 반환
        """
        valid_cities = []
        for city_id, city_state in self.cities_state.items():
            # 도시의 최대 기반 수
            max_bases = self.knowledge.cities[city_id].max_party_bases
            current_total_bases = sum(city_state.party_bases.values())
            # 해당 정당이 아직 기반을 배치하지 않았고, 도시가 꽉 차지 않은 경우
            if city_state.party_bases.get(party_id, 0) == 0 and current_total_bases < max_bases:
                valid_cities.append(city_id)
        return valid_cities

    def execute_demonstration_action(self, player_id: PartyID, city_id: str):
        """Demonstration 액션: 기반 배치 시 자리 있으면 배치, 없으면 Presenter에 선택 요청."""
        if city_id not in self.cities_state:
            logger.warning(f"Invalid city_id '{city_id}' for demonstration action.")
            return
        city_state = self.cities_state[city_id]
        city_capacity = self.knowledge.cities[city_id].max_party_bases
        current_bases = sum(city_state.party_bases.values())
        if current_bases < city_capacity:
            success = self._place_party_base(player_id, city_id)
            if success:
                self.bus.publish("DATA_PARTY_BASE_PLACED", {
                    "player_id": player_id,
                    "city_id": city_id
                })
            return
        # 자리 없으면 제거할 상대 정당 목록 추출
        removable_parties = [party for party, count in city_state.party_bases.items() if count > 0 and party != player_id]
        self.bus.publish("REQUEST_PLAYER_CHOICE", {
            "action": "remove_party_base",
            "city_id": city_id,
            "removable_parties": removable_parties,
            "player_id": player_id
        })
        # 여기서 로직 종료, 응답은 Presenter가 처리


    def get_valid_moves(self, player_id: PartyID) -> list:
        """
        현재 게임 상태에서 해당 플레이어가 할 수 있는 모든 Move 객체를 리스트로 반환
        """
        moves = []
        # 예시: PASS_TURN 항상 가능
        moves.append(Move(player_id=player_id, action_type=ActionTypeEnum.PASS_TURN))

        # 예시: 기반 배치 가능한 도시마다 DEMONSTRATION 액션 추가
        valid_cities = self.get_valid_base_placement_cities(player_id)
        for city_id in valid_cities:
            moves.append(Move(player_id=player_id, action_type=ActionTypeEnum.DEMONSTRATION, target_city=city_id))

        # TODO: 카드 플레이, 쿠데타 등 다른 액션 추가
        # 예시: 플레이어의 손에 카드가 있다면 PLAY_CARD 액션 추가
        party_state = self.party_states.get(player_id)
        if party_state:
            for card_id in party_state.hand_party:
                moves.append(Move(player_id=player_id, action_type=ActionTypeEnum.PLAY_CARD, card_id=card_id, play_option=PlayOptionEnum.ACTION))
        return moves

    def execute_move(self, move):
        """
        전달받은 Move 객체에 따라 게임 상태를 변경하고 관련 이벤트를 발행
        """
        if move.action_type == ActionTypeEnum.NO_ACTION:
            logger.info(f"{move.player_id} takes no action.")
        elif move.action_type == ActionTypeEnum.PASS_TURN:
            logger.info(f"{move.player_id} passes turn.")
            # TODO: 턴 넘기기 로직 구현
            self.bus.publish("DATA_TURN_PASSED", {"player_id": move.player_id})
        elif move.action_type == ActionTypeEnum.DEMONSTRATION:
            logger.info(f"{move.player_id} attempts demonstration in {move.target_city}.")
            self.execute_demonstration_action(move.player_id, move.target_city)
        elif move.action_type == ActionTypeEnum.PLAY_CARD:
            logger.info(f"{move.player_id} plays card {move.card_id} with option {move.play_option}.")
            # TODO: 카드 플레이 로직 구현
            self.bus.publish("DATA_CARD_PLAYED", {"player_id": move.player_id, "card_id": move.card_id, "play_option": move.play_option})
        # TODO: COUP, 기타 액션 등 추가
        else:
            logger.warning(f"Unknown action type: {move.action_type}")