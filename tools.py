"""
Logging configuration with sensitive data filtering.

Provides a configured logger with automatic masking of sensitive tokens and credentials
in log output (Google tokens, Telegram bot tokens, OAuth access tokens).
"""

import logging
import os
import re

log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
numeric_level = getattr(logging, log_level, logging.INFO)

VERBOSE = os.getenv('VERBOSE', 'false').lower() in ('true', '1')


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that masks sensitive credentials in log output.

    Automatically detects and masks:
    - Telegram bot tokens (shows first 10 digits)
    - Google master tokens (shows first 6 chars)
    - OAuth access tokens (shows first 6 chars)

    Uses regex patterns to find and replace sensitive strings while preserving
    enough context to identify which token is being used.
    """

    def __init__(self):
        super().__init__()
        self.patterns = [
            (re.compile(r'(\d{9,10}):([A-Za-z0-9_-]{25,})'), r'\1:[telegram-bot-token-masked]'),
            (re.compile(r'(/bot)(\d{9,10}):([A-Za-z0-9_-]{25,})'), r'\1\2:[telegram-bot-token-masked]'),
            (re.compile(r'(aas_et/[A-Za-z0-9_-]{6})[A-Za-z0-9_/+=\-]{50,}'), r'\1[google-master-token-masked]'),
            (re.compile(r'([ya]\w{0,3}\.[A-Za-z0-9_-]{6})[A-Za-z0-9_\-\.]{50,}'), r'\1[oauth-access-token-masked]'),
        ]

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in self.patterns:
                record.msg = pattern.sub(replacement, record.msg)

        if record.args:
            new_args = []
            for arg in record.args if isinstance(record.args, tuple) else [record.args]:
                if isinstance(arg, str):
                    for pattern, replacement in self.patterns:
                        arg = pattern.sub(replacement, arg)
                new_args.append(arg)
            record.args = tuple(new_args) if isinstance(record.args, tuple) else new_args[0]

        return True


logging.basicConfig(
    level=numeric_level,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

sensitive_filter = SensitiveDataFilter()
root_logger = logging.getLogger()
root_logger.addFilter(sensitive_filter)

# Add filter to all handlers to catch library loggers
for handler in root_logger.handlers:
    handler.addFilter(sensitive_filter)

logger = logging.getLogger(__name__)
