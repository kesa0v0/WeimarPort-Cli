# utils/scenarioLoader.py (신규 생성)
import json
import logging
from typing import Optional
from pydantic import ValidationError

# ⭐️ 위에서 정의한 ScenarioModel 임포트
from datas import GameKnowledge
from scenario_model import ScenarioModel 

logger = logging.getLogger(__name__)

def validate_scenario_references(scenario: ScenarioModel, knowledge: GameKnowledge) -> bool:
    """
    ScenarioModel의 참조 필드(threat_id, city_id 등)가 GameKnowledge에 존재하는지 검증
    """
    # threat_id 유효성 검사
    known_threat_ids = set(knowledge.threat.keys())
    all_threats = scenario.initial_threats.dr_box + \
        [t for threats in scenario.initial_threats.specific_cities.values() for t in threats] + \
        [task.threat_id for task in scenario.initial_threats.random_cities]
    for threat_id in all_threats:
        if threat_id not in known_threat_ids:
            logger.error(f"Scenario validation failed: Unknown threat_id '{threat_id}'")
            return False
    # city_id 유효성 검사
    known_city_ids = set(knowledge.cities.keys())
    for city_id in scenario.initial_threats.specific_cities.keys():
        if city_id not in known_city_ids:
            logger.error(f"Scenario validation failed: Unknown city_id '{city_id}'")
            return False
    # ... 다른 검증 필요시 추가 ...
    return True

def load_and_validate_scenario(filepath: str, game_knowledge: GameKnowledge) -> Optional[ScenarioModel]:
    """
    Loads a scenario JSON file and validates it using the Pydantic model.
    Returns the validated ScenarioModel object or None if validation fails.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            logger.info(f"Scenario file '{filepath}' loaded.")
    except FileNotFoundError:
        logger.error(f"Scenario file not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from {filepath}: {e}")
        return None

    try:
        scenario = ScenarioModel.model_validate(raw_data)
        # ⭐️ Pydantic 검증 후, 참조 유효성 추가 검증
        if not validate_scenario_references(scenario, game_knowledge):
            logger.error(f"Scenario '{filepath}' failed reference validation.")
            return None # 참조 오류 시 실패 처리
        logger.info(f"Scenario '{scenario.name}' validated successfully.")
        return scenario
    except ValidationError as e:
        # ⭐️ 유효성 검사 실패 시 상세 오류 로깅
        logger.error(f"Scenario validation failed for '{filepath}'. Errors:\n{e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating scenario '{filepath}': {e}")
        return None