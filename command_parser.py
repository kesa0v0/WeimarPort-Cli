



class CommandParser:
    def __init__(self, presenter):
        self.presenter = presenter

    def parse_command(self, command, current_player_id):
        command = command.strip().lower()
        if command == 'status':
            self.presenter.handle_show_status()
            