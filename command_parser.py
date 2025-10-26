



from game_action import Move, ActionTypeEnum, PlayOptionEnum
from enums import PartyID

class CommandParser:
    def __init__(self, presenter=None):
        self.presenter = presenter

    def parse_command_to_move(self, raw_input: str, player_id: PartyID) -> Move:
        """
        입력 문자열을 분석하여 해당하는 Move 객체를 생성해 반환
        """
        cmd = raw_input.strip().lower()
        # 예시: status -> PASS_TURN (혹은 별도 STATUS 액션)
        if cmd == 'status':
            return Move(player_id=player_id, action_type=ActionTypeEnum.PASS_TURN)
        elif cmd == 'pass':
            return Move(player_id=player_id, action_type=ActionTypeEnum.PASS_TURN)
        elif cmd.startswith('demonstration '):
            # 예시: demonstration berlin
            parts = cmd.split()
            if len(parts) == 2:
                city_id = parts[1]
                return Move(player_id=player_id, action_type=ActionTypeEnum.DEMONSTRATION, target_city=city_id)
        elif cmd.startswith('play '):
            # 예시: play card123
            parts = cmd.split()
            if len(parts) >= 2:
                card_id = parts[1]
                play_option = PlayOptionEnum.ACTION # 기본값
                if len(parts) == 3:
                    try:
                        play_option = PlayOptionEnum(parts[2].upper())
                    except Exception:
                        pass
                return Move(player_id=player_id, action_type=ActionTypeEnum.PLAY_CARD, card_id=card_id, play_option=play_option)
        # TODO: 더 많은 명령어 파싱 추가
        # 기본값: NO_ACTION
        return Move(player_id=player_id, action_type=ActionTypeEnum.NO_ACTION)
            