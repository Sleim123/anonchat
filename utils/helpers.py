from datetime import datetime, timedelta
import re

class TimeHelper:
    @staticmethod
    def parse_timeout(timeout_str: str) -> timedelta:
        if not re.match(r'^\d+[smhd]$', timeout_str):
            raise ValueError("Invalid timeout format")

        amount = int(timeout_str[:-1])
        unit = timeout_str[-1]

        if unit == 's':
            return timedelta(seconds=amount)
        elif unit == 'm':
            return timedelta(minutes=amount)
        elif unit == 'h':
            return timedelta(hours=amount)
        elif unit == 'd':
            return timedelta(days=amount)

    @staticmethod
    def format_timeout(timeout: timedelta) -> str:
        total_seconds = int(timeout.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m"
        elif total_seconds < 86400:
            return f"{total_seconds // 3600}h"
        else:
            return f"{total_seconds // 86400}d"

class MessageHelper:
    @staticmethod
    def extract_command_args(text: str) -> list:
        if not text:
            return []
        parts = text.split()
        return parts[1:] if len(parts) > 1 else []

    @staticmethod
    def is_valid_user_id(user_id: str) -> bool:
        return bool(re.match(r'^\d+$', user_id))