
import logging
import random
from typing import Any, Dict, List, Optional, Set
import uuid

from datas import GameKnowledge, ThreatData, UnitData
from enums import GamePhase, PartyID
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
        self.phase = GamePhase.SETUP
        self.current_turn_order: List[PartyID] = []

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
        self.placement_order: List[PartyID] = []
        self.setup_current_party_index: int = 0
        self.setup_bases_placed_count: int = 0
        self.scenario_data: Optional[ScenarioModel] = None

        # --- Agenda Phase State ---
        self._pending_agenda_choices = {} # 아젠다 단계에서 선택을 기록
        self.agenda_choice_player_index = 0


        # --- Reaction State ---
        self._pending_move: Optional[Move] = None # 실행 보류 중인 원본 Move
        self._reaction_chain: List[Any] = [] # "Reaction Stack" (Move 또는 Reaction 객체)
        self._reaction_ask_index: int = 0 # 리액션을 물어볼 다음 플레이어 인덱스


    def initialize_game_objects(self):
        if self.knowledge:
            # Initialize Party States
            if self.knowledge.party:
                self.party_states = {party_id: PartyState(PartyID(party_id)) for party_id in self.knowledge.party.keys()}
            # Initialize City States
            if self.knowledge.cities:
                self.cities_state = {city_id: CityState(city_data) for city_id, city_data in self.knowledge.cities.items()}

            # Initialize Threat Pool
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

            # Initialize Unit Pool
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
        return self.current_turn_order[self.current_player_index]

    def get_status_data(self) -> dict[str, Any]:
        status = {
            "round": self.round,
            "turn": self.current_turn_order[self.current_player_index],
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
            # 시나리오에 정의되어 있지 않다면 기본값 사용
            self.current_turn_order = [PartyID.SPD, PartyID.ZENTRUM, PartyID.KPD, PartyID.DNVP]
            self.current_player_index = 0

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

        self.setup_current_party_index = 0
        self.setup_bases_placed_count = 0

        logger.info("Initial base placement phase started.")
        self._request_next_setup_action() # 첫 액션 요청

    def _request_next_setup_action(self):
        """
        설정 단계의 다음 액션을 요청합니다. (기반 배치 요청 등)
        """
        if self.phase != GamePhase.SETUP:
            return

        # 모든 정당의 배치가 끝났는지 확인
        if self.setup_current_party_index >= len(self.placement_order):
            self.phase = GamePhase.AGENDA_PHASE_START
            logger.info("Initial base placement complete.")
            self.bus.publish(game_events.SETUP_PHASE_COMPLETE, {})
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
        if self.phase != GamePhase.SETUP or self.placement_order[self.setup_current_party_index] != party_id:
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

    def _execute_place_base(self, player_id: PartyID, city_id: str):
        """기반 배치 로직: 자리가 있으면 배치, 없으면 플레이어에게 제거할 기반 선택을 요청."""
        if city_id not in self.cities_state:
            logger.warning(f"Invalid city_id '{city_id}' for place base action.")
            return

        city_state = self.cities_state[city_id]
        city_capacity = self.knowledge.cities[city_id].max_party_bases
        current_bases = sum(city_state.party_bases.values())

        if current_bases < city_capacity:
            # 자리가 있으면 즉시 배치
            success = self._place_party_base(player_id, city_id)
            if success:
                self.bus.publish(game_events.DATA_PARTY_BASE_PLACED, {
                    "party_id": player_id,
                    "city_id": city_id
                })
            return

        # 자리가 없으면 제거할 상대 정당 목록을 플레이어에게 물어봄
        removable_parties = [p for p, count in city_state.party_bases.items() if count > 0 and p != player_id]
        if not removable_parties:
            logger.warning(f"Cannot place base in '{city_id}': City is full and no opponent bases to remove.")
            self.bus.publish(game_events.UI_SHOW_ERROR, {"error": f"{city_id}에 기반을 놓을 수 없습니다: 도시가 가득 찼고 제거할 상대 기반이 없습니다."})
            return

        removable_party_ids = [p.value for p in removable_parties]
        self.bus.publish(game_events.REQUEST_PLAYER_CHOICE, {
            "player_id": player_id,
            "options": removable_party_ids,
            "context": {
                "action": "resolve_place_base",
                "city_id": city_id,
                "player_id": player_id,
                "prompt": f"어떤 정당의 기반을 제거하시겠습니까? ({city_id}에 기반 배치하기 위함)"
            }
        })
        # 여기서 로직 종료, 응답은 Presenter가 처리

    def _resolve_place_base_choice(self, data: dict):
        """도시가 꽉 찼을 때, 플레이어의 기반 제거 선택을 처리하고 액션을 완료합니다."""
        try:
            player_id = data["context"]["player_id"]
            city_id = data["context"]["city_id"]
            selected_party_to_remove = PartyID(data["selected_option"])

            logger.info(f"Resolving place base choice: Player {player_id} chose to remove {selected_party_to_remove}'s base in {city_id}.")

            # 1. 상대 기반 제거
            remove_success = self._remove_party_base(selected_party_to_remove, city_id)
            if not remove_success:
                logger.error(f"Failed to remove base of {selected_party_to_remove} from {city_id}.")
                self.bus.publish(game_events.UI_SHOW_ERROR, {"error": "기반 제거에 실패했습니다."})
                return

            self.bus.publish(game_events.DATA_PARTY_BASE_REMOVED, {
                "remover_id": player_id,
                "removed_party_id": selected_party_to_remove,
                "city_id": city_id
            })

            # 2. 자신의 기반 배치
            place_success = self._place_party_base(player_id, city_id)
            if not place_success:
                logger.error(f"Failed to place base for {player_id} in {city_id} after removal.")
                # 이 경우는 발생하기 매우 어렵지만, 방어적으로 처리
                self.bus.publish(game_events.UI_SHOW_ERROR, {"error": "기반 제거 후, 자신의 기반을 배치하는 데 실패했습니다."})
                return
            
            self.bus.publish(game_events.DATA_PARTY_BASE_PLACED, {
                "party_id": player_id,
                "city_id": city_id
            })
            
            self.bus.publish(game_events.UI_SHOW_STATUS, self.get_status_data())

        except KeyError as e:
            logger.error(f"_resolve_place_base_choice failed due to missing key: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred in _resolve_place_base_choice: {e}")


    def _resolve_agenda_choices(self):
        logger.info("Resolving agenda choices for all players.")
        for party_id, selected_agenda in self._pending_agenda_choices.items():
            logger.debug(f"Party {party_id} selected agenda: {selected_agenda}")
            # 아젠다 카드 적용 로직 구현 필요
            # 예: self.party_states[party_id].agenda = selected_agenda

    def _request_next_agenda_choice(self):
        if self.agenda_choice_player_index < len(self.current_turn_order):
            party_id = self.current_turn_order[self.agenda_choice_player_index]
            agenda_options = ["Agenda1", "Agenda2", "Agenda3", "Agenda4"]
            context = {
                "action": "agenda_selection",
                "party": party_id,
                "prompt": "이번 라운드의 아젠다 카드를 선택하세요."
            }
            self.bus.publish(game_events.REQUEST_PLAYER_CHOICE, {
                "player_id": party_id,
                "options": agenda_options,
                "context": context
            })
        else:
            # 모든 플레이어가 선택 완료
            self._resolve_agenda_choices()
            self.phase = GamePhase.IMPULSE_PHASE_START
            self.current_player_index = 0


    async def advance_game_state(self):
        match self.phase:
            case GamePhase.SETUP:
                raise Exception("Game Started Not Setuped Properly.")

            case GamePhase.AGENDA_PHASE_START:
                # 1. 아젠다 선택 단계 시작
                self._pending_agenda_choices = {}
                self.agenda_choice_player_index = 0
                self.phase = GamePhase.AGENDA_PHASE_AWAIT_CHOICES
                self._request_next_agenda_choice()

            case GamePhase.AGENDA_PHASE_AWAIT_CHOICES:
                # Agent가 'submit_choice'를 호출할 때까지 대기
                pass
                    
            case GamePhase.IMPULSE_PHASE_START:
                # 1. 이번 턴 플레이어 결정
                player_id = self.current_turn_order[self.current_player_index]
                self.turn = player_id # 현재 턴 플레이어 설정
                
                # 2. 상태 변경: 이제 이 플레이어의 'Move'를 기다림
                self.phase = GamePhase.IMPULSE_PHASE_AWAIT_MOVE
                
                # 3. Presenter/Agent에게 'Move'를 요청하라고 알림
                # 'get_next_move'를 호출하라는 신호!
                self.bus.publish("REQUEST_PLAYER_MOVE", {"player_id": player_id})

            case GamePhase.IMPULSE_PHASE_AWAIT_MOVE:
                # 1. 플레이어가 'Move'를 제출할 때까지 아무것도 하지 않고 대기
                # 2. 'Move'가 제출되면 'submit_move' 핸들러가 상태를 변경할 것임
                pass

            case GamePhase.REACTION_WINDOW_GATHERING:
                # 1. 한 바퀴 다 돌았는지 확인 (턴 플레이어에게 돌아왔나?)
                if self._reaction_ask_index == self.current_player_index:
                    logger.debug("Reaction window closed. All players passed.")
                    # 2. 모두 "Pass"함. 스택 실행 단계로 이동
                    self.phase = GamePhase.REACTION_CHAIN_RESOLVING
                    return # 👈 즉시 다음 루프로

                # 3. 현재 물어볼 플레이어
                player_to_ask = self.current_turn_order[self._reaction_ask_index]
                
                # 4. 이 플레이어가 현재 스택의 '마지막' 아이템에 반응할 수 있나?
                # 룰북: "react to... action or reaction"
                last_event_on_stack = self._reaction_chain[-1]
                valid_reactions = self._get_valid_reactions_for_player(player_to_ask, last_event_on_stack)
                
                if not valid_reactions:
                    # 5. 반응할 수단이 없음. 다음 플레이어로
                    self._reaction_ask_index = (self._reaction_ask_index + 1) % len(self.current_turn_order)
                    # (다음 advance_game_state 루프에서 계속)
                else:
                    # 6. 반응할 수단이 있음! "Pass" 옵션 추가
                    valid_reactions.append("PASS")
                    
                    # 7. 응답 대기 상태로 변경
                    self.phase = GamePhase.REACTION_WINDOW_AWAIT_CHOICE
                    
                    # 8. Agent에게 'get_choice' 요청
                    self.bus.publish(game_events.REQUEST_PLAYER_CHOICE, {
                        "player_id": player_to_ask,
                        "options": valid_reactions, # [ "Street Fight (Board)", "Otto Wels (Card)", "PASS" ]
                        "context": {
                            "action": "reaction",
                            "party": player_to_ask,
                            "target_event": str(last_event_on_stack),
                            "prompt": f"'{last_event_on_stack}'에 반응하시겠습니까?"
                        }
                    })

            case GamePhase.REACTION_WINDOW_AWAIT_CHOICE:
                # Agent가 'submit_choice'를 호출할 때까지 대기
                pass

            case GamePhase.REACTION_CHAIN_RESOLVING:
                logger.info(f"Resolving reaction chain (LIFO). Stack size: {len(self._reaction_chain)}")
                
                # 1. 스택이 빌 때까지 역순으로 실행
                while self._reaction_chain:
                    item_to_resolve = self._reaction_chain.pop() # 맨 위(마지막) 아이템
                    
                    if self._is_politician_card(item_to_resolve):
                        self._resolve_politician_card(item_to_resolve)
                    
                    elif self._is_board_reaction(item_to_resolve):
                        self._resolve_board_reaction(item_to_resolve)

                    elif isinstance(item_to_resolve, Move):
                        self._execute_action(item_to_resolve) # 최종 실행

                # 4. 스택 해결 완료. 다음 턴으로.
                self._pending_move = None
                self._advance_to_next_impulse_turn()


    def get_valid_moves(self, player_id: PartyID) -> list:
        """
        현재 게임 상태에서 해당 플레이어가 할 수 있는 모든 Move 객체를 리스트로 반환
        """
        moves = []

        # TODO: 카드 플레이, 쿠데타 등 다른 액션 추가
        # 예시: 플레이어의 손에 카드가 있다면 Event 액션 추가
        party_state = self.party_states.get(player_id)
        if party_state:
            for card_id in party_state.hand_party:
                moves.append(Move(player_id=player_id, card_id=card_id, play_option=PlayOptionEnum.EVENT))

        # 기반 배치 가능한 도시마다 DEMONSTRATION 액션 추가
        valid_cities = self.get_valid_base_placement_cities(player_id)
        for city_id in valid_cities:
            moves.append(Move(player_id=player_id, play_option=PlayOptionEnum.ACTION, card_action_type=ActionTypeEnum.DEMONSTRATION, target=city_id))

        return moves

    def submit_move(self, move: Move):
        """Presenter가 Agent로부터 받은 Move를 실행"""
        
        # 0. 현재 턴 플레이어의 Move가 맞는지 확인
        if move.player_id != self.turn or self.phase != GamePhase.IMPULSE_PHASE_AWAIT_MOVE:
            self.bus.publish(game_events.UI_SHOW_ERROR, {"error": "지금은 당신의 턴이 아닙니다."})
            # 다시 요청
            self.bus.publish("REQUEST_PLAYER_MOVE", {"player_id": self.turn})
            return

        # 1. Reaction이 가능한 Move인지 확인
        if move.card_action_type in (ActionTypeEnum.DEMONSTRATION, ActionTypeEnum.COUP, ActionTypeEnum.COUNTER_COUP, ActionTypeEnum.FIGHT):
            
            # 2. Move를 "보류"하고 스택(체인)의 맨 밑에 둠
            self._pending_move = move
            self._reaction_chain = [move] # 원본 행동이 스택의 0번
            
            # 3. 현재 플레이어의 '다음' 사람부터 물어보기 시작
            self.phase = GamePhase.REACTION_WINDOW_GATHERING
            self.current_player_index = self.current_player_index # 턴 플레이어 인덱스
            self._reaction_ask_index = (self.current_player_index + 1) % len(self.current_turn_order)

            logger.info(f"Action {move} announced. Opening reaction window starting from {self.current_turn_order[self._reaction_ask_index]}.")
            
            # (advance_game_state가 이어서 처리)
        
        else:
            # 4. 리액션 불가능한 행동 (예: Pass, Debate)은 즉시 실행
            self._execute_action(move) # 즉시 실행
            self._advance_to_next_impulse_turn()

    def _execute_move(self, move):
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
            # 나중에 주사위 굴림 등 복잡한 로직이 추가될 수 있음
            # 지금은 요청대로 +2 기반 설치 효과를 위해 _execute_place_base를 두 번 호출
            self._execute_place_base(move.player_id, move.target_city)
            # self._execute_place_base(move.player_id, move.target_city) # 두 번 호출이 필요하다면 이렇게
        elif move.action_type == ActionTypeEnum.PLAY_CARD:
            logger.info(f"{move.player_id} plays card {move.card_id} with option {move.play_option}.")
            # TODO: 카드 플레이 로직 구현
            self.bus.publish("DATA_CARD_PLAYED", {"player_id": move.player_id, "card_id": move.card_id, "play_option": move.play_option})
        # TODO: COUP, 기타 액션 등 추가
        else:
            logger.warning(f"Unknown action type: {move.action_type}")

    def _resolve_reaction_choice(self, player_id: PartyID, choice: Any, context: dict):
        if choice == "PASS":
            # 1. "Pass" 선택. 다음 사람에게 물어봄
            self._reaction_ask_index = (self._reaction_ask_index + 1) % len(self.current_turn_order)
            self.phase = GamePhase.REACTION_WINDOW_GATHERING
            
        else:
            # 2. "React" 선택! (예: "DNVP의 Street Fight")
            logger.info(f"{player_id} reacts with {choice}.")
            self._reaction_chain.append(choice) # 스택(체인)에 추가!
            
            # 3. 룰북: "Only 1 reaction is allowed per trigger"
            # (이것은 "Party Board" 리액션에만 해당)
            # (Politician Card는 리액션에 리액션 가능)
            
            if self._is_board_reaction(choice):
                # 4a. 보드 리액션임. 다른 사람은 더 이상 '보드 리액션' 불가.
                # 하지만 "정치가 카드"는 이 리액션에 반응할 수 있음.
                # 따라서 스택이 쌓였으므로, '다음' 사람부터 다시 물어봄
                self._reaction_ask_index = (self._reaction_ask_index + 1) % len(self.current_turn_order)
                self.phase = GamePhase.REACTION_WINDOW_GATHERING # 루프 리셋

            elif self._is_politician_card(choice):
                # 4b. 정치가 카드임. 이 카드에 또 반응할 수 있음.
                # '다음' 사람부터 다시 물어봄
                self._reaction_ask_index = (self._reaction_ask_index + 1) % len(self.current_turn_order)
                self.phase = GamePhase.REACTION_WINDOW_GATHERING # 루프 리셋

    def submit_choice(self, player_id: PartyID, choice: Any, context: dict):
        """Presenter가 Agent로부터 받은 Choice를 처리"""
        
        action = context.get("action")
        

        if action == "initial_base_placement":
            self.resolve_initial_base_placement(player_id, choice)

        elif action == "agenda_selection":
            self._pending_agenda_choices[player_id] = choice
            self.agenda_choice_player_index += 1
            self._request_next_agenda_choice()

        elif action == "resolve_place_base":
            self._resolve_place_base_choice(choice)
            
        elif action == "reaction":
            self._resolve_reaction_choice(player_id, choice, context)

    def _advance_to_next_impulse_turn(self):
            # TODO: 모든 플레이어가 카드를 다 썼는지 확인 (Impulse Phase 종료)
            # if self._is_impulse_phase_over():
            #    self.phase = GamePhase.POLITICS_PHASE
            # else:
            
            # 아니면 다음 플레이어로 인덱스 이동
            self.current_player_index = (self.current_player_index + 1) % len(self.current_turn_order)
            self.phase = GamePhase.IMPULSE_PHASE_START