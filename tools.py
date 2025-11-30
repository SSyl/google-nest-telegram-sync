import logging
import os
import re

# Get log level from environment variable, default to INFO
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
numeric_level = getattr(logging, log_level, logging.INFO)

# VERBOSE mode for extra detailed logging (XML dumps, etc.)
VERBOSE = os.getenv('VERBOSE', 'false').lower() in ('true', '1')


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs (tokens, API keys, etc.)"""

    def __init__(self):
        super().__init__()
        # Patterns to match sensitive data
        self.patterns = [
            # Telegram bot token format: 1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
            (re.compile(r'(\d{9,10}):([A-Za-z0-9_-]{35})'), r'\1:***MASKED***'),
            # Generic bearer/bot tokens in URLs
            (re.compile(r'(/bot)(\d{9,10}):([A-Za-z0-9_-]{35})'), r'\1\2:***MASKED***'),
        ]

    def filter(self, record):
        # Mask sensitive data in the log message
        if isinstance(record.msg, str):
            for pattern, replacement in self.patterns:
                record.msg = pattern.sub(replacement, record.msg)

        # Also mask in args if present
        if record.args:
            new_args = []
            for arg in record.args if isinstance(record.args, tuple) else [record.args]:
                if isinstance(arg, str):
                    for pattern, replacement in self.patterns:
                        arg = pattern.sub(replacement, arg)
                new_args.append(arg)
            record.args = tuple(new_args) if isinstance(record.args, tuple) else new_args[0]

        return True


# Configure logging
logging.basicConfig(level=numeric_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add sensitive data filter to root logger and all handlers
sensitive_filter = SensitiveDataFilter()
root_logger = logging.getLogger()
root_logger.addFilter(sensitive_filter)

# Also add to all existing handlers to catch library loggers
for handler in root_logger.handlers:
    handler.addFilter(sensitive_filter)

logger = logging.getLogger(__name__)
