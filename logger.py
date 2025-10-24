import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style


def init_logger():
    # 로그 폴더 생성
    LOG_DIR = "logs"
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 오래된 날짜 기반 로그 파일 삭제
    def cleanup_old_logs():
        log_files = [f for f in os.listdir(LOG_DIR) if f.endswith(".log") and f != "latest.log"]
        log_files.sort()  # 파일 이름 기준 정렬 (날짜 순서)
        if len(log_files) > 5:  # 최대 5개까지만 유지
            for old_file in log_files[:len(log_files) - 4]:
                os.remove(os.path.join(LOG_DIR, old_file))

    cleanup_old_logs()  # 초기화 시 오래된 로그 정리

    # 로그 레벨별 색상 정의
    LOG_COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Style.BRIGHT,
    }

    class ColorFormatter(logging.Formatter):
        def format(self, record):
            log_color = LOG_COLORS.get(record.levelname, Fore.WHITE)
            # 전체 메시지 포맷 생성
            s = super().format(record)
            # 레벨명 부분만 색상 적용
            s = s.replace(f"[{record.levelname}]", f"{log_color}[{record.levelname}]{Style.RESET_ALL}")
            return s

    # 콘솔 핸들러 (색상 출력)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColorFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))

    # 파일 핸들러 (latest.log)
    latest_log_path = os.path.join(LOG_DIR, "latest.log")
    file_handler = RotatingFileHandler(latest_log_path, maxBytes=5 * 1024 * 1024, backupCount=0)  # 백업 없음
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))

    # 실행 시점의 날짜-시간으로 로그 파일 생성
    start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    timestamped_log_path = os.path.join(LOG_DIR, f"{start_time}.log")
    timestamped_file_handler = logging.FileHandler(timestamped_log_path, encoding="utf-8")
    timestamped_file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))

    # 로거 설정
    logging.basicConfig(level=logging.DEBUG, handlers=[console_handler, file_handler, timestamped_file_handler])
