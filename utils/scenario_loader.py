# utils/scenarioLoader.py (신규 생성)
import json
import logging
from typing import Optional
from pydantic import ValidationError

# ⭐️ 위에서 정의한 ScenarioModel 임포트
from datas import GameKnowledge
from scenario_model import ScenarioModel 

logger = logging.getLogger(__name__)

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
        # ⭐️ Pydantic 모델로 파싱 및 유효성 검사 실행!
        ScenarioModel.game_knowledge = game_knowledge  # GameKnowledge 인스턴스 설정
        scenario = ScenarioModel.model_validate(raw_data)
        logger.info(f"Scenario '{scenario.name}' validated successfully.")
        return scenario
    except ValidationError as e:
        # ⭐️ 유효성 검사 실패 시 상세 오류 로깅
        logger.error(f"Scenario validation failed for '{filepath}'. Errors:\n{e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating scenario '{filepath}': {e}")
        return None