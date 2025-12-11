#!/usr/bin/env python3
"""
Веб-модуль приложения
"""

from .app import app
from .templates import get_web_version, get_bot_version

__all__ = ['app', 'get_web_version', 'get_bot_version']
