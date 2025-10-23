from colorama import init as init_colorama, Fore, Style

init_colorama(autoreset=True)

class CliView:
    def tag_print(self, message, tag, tag_color=Fore.WHITE):
        print(f"{tag_color}[{tag}]{Style.RESET_ALL} {message}")

    def colorprint(self, message, color=Fore.WHITE):
        print(f"{color}{message}{Style.RESET_ALL}")

    def print(self, message):
        print(message)

    def get_input(self, prompt):
        return input(prompt)