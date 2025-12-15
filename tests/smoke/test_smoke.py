#!/usr/bin/env python3
"""
Smoke и приёмочные тесты для проверки работоспособности контейнеров.

Эти тесты проверяют:
1. Доступность API endpoints веб-интерфейса и бота
2. Соответствие версий в контейнерах версиям в коде
3. Health check для БД
"""

import os
import json
import pytest
import requests
from pathlib import Path


# Конфигурация тестов
# Используем порт 5434 для прямого доступа к web контейнеру через docker network
# или localhost:80 через nginx (может редиректить на HTTPS)
WEB_BASE_URL = os.getenv('WEB_BASE_URL', 'http://localhost:80')
BOT_API_URL = os.getenv('BOT_API_URL', 'http://localhost:8080')
TIMEOUT = 10  # секунд
# Отключаем проверку SSL для localhost тестов
VERIFY_SSL = os.getenv('VERIFY_SSL', 'false').lower() == 'true'

# Подавляем warnings о небезопасных запросах при verify=False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_local_version(filename):
    """Получить версию из локального файла"""
    try:
        path = Path(__file__).parent.parent / filename
        return path.read_text().strip()
    except FileNotFoundError:
        return None


def make_request(url, **kwargs):
    """Делает HTTP запрос с обработкой редиректа на HTTPS"""
    kwargs.setdefault('timeout', TIMEOUT)
    kwargs.setdefault('verify', VERIFY_SSL)

    try:
        response = requests.get(url, **kwargs)
        # Если nginx редиректит на HTTPS, следуем за редиректом без проверки SSL
        if response.status_code in [301, 302] and 'https://' in response.headers.get('Location', ''):
            https_url = response.headers['Location']
            return requests.get(https_url, timeout=TIMEOUT, verify=False)
        return response
    except requests.exceptions.SSLError:
        # Пробуем без SSL верификации
        return requests.get(url.replace('http://', 'https://'), timeout=TIMEOUT, verify=False)


class TestWebSmoke:
    """Smoke тесты для веб-интерфейса"""

    def test_web_version_endpoint(self):
        """Проверка доступности /api/version"""
        response = make_request(f'{WEB_BASE_URL}/api/version')
        assert response.status_code == 200, f"Web /api/version returned {response.status_code}"

        data = response.json()
        assert 'web_version' in data
        assert 'bot_version' in data
        assert data.get('status') == 'ok'

    def test_web_health_endpoint(self):
        """Проверка доступности /api/health"""
        response = make_request(f'{WEB_BASE_URL}/api/health')
        assert response.status_code == 200, f"Web /api/health returned {response.status_code}"

        data = response.json()
        assert data.get('status') == 'healthy'
        assert data.get('database') == 'connected'

    def test_web_login_page(self):
        """Проверка доступности страницы логина"""
        response = make_request(f'{WEB_BASE_URL}/login', allow_redirects=False)
        # Может быть 200 (страница логина), 301/302 (редирект на HTTPS или другую страницу)
        assert response.status_code in [200, 301, 302], f"Login page returned {response.status_code}"

    def test_web_root_redirect(self):
        """Проверка редиректа с главной страницы"""
        response = make_request(f'{WEB_BASE_URL}/', allow_redirects=False)
        # Должен редиректить на логин или показать страницу (или редирект на HTTPS)
        assert response.status_code in [200, 301, 302], f"Root returned {response.status_code}"


class TestBotSmoke:
    """Smoke тесты для API бота"""

    def test_bot_version_endpoint(self):
        """Проверка доступности /api/version на боте"""
        response = requests.get(f'{BOT_API_URL}/api/version', timeout=TIMEOUT)
        assert response.status_code == 200, f"Bot /api/version returned {response.status_code}"

        data = response.json()
        assert 'bot_version' in data
        assert 'web_version' in data
        assert data.get('status') == 'ok'

    def test_bot_health_endpoint(self):
        """Проверка доступности /api/health на боте"""
        response = requests.get(f'{BOT_API_URL}/api/health', timeout=TIMEOUT)
        assert response.status_code == 200, f"Bot /api/health returned {response.status_code}"

        data = response.json()
        assert data.get('status') == 'healthy'


class TestVersionMatch:
    """Приёмочные тесты для проверки соответствия версий"""

    def test_web_version_matches_local(self):
        """Проверка что версия веб-интерфейса в контейнере совпадает с локальной"""
        local_version = get_local_version('WEB_VERSION')
        if local_version is None:
            pytest.skip("WEB_VERSION file not found locally")

        response = make_request(f'{WEB_BASE_URL}/api/version')
        assert response.status_code == 200

        data = response.json()
        container_version = data.get('web_version')

        assert container_version == local_version, \
            f"Web version mismatch: container={container_version}, local={local_version}"

    def test_bot_version_matches_local(self):
        """Проверка что версия бота в контейнере совпадает с локальной"""
        local_version = get_local_version('VERSION')
        if local_version is None:
            pytest.skip("VERSION file not found locally")

        response = requests.get(f'{BOT_API_URL}/api/version', timeout=TIMEOUT)
        assert response.status_code == 200

        data = response.json()
        container_version = data.get('bot_version')

        assert container_version == local_version, \
            f"Bot version mismatch: container={container_version}, local={local_version}"

    def test_versions_consistent_across_services(self):
        """Проверка что версии согласованы между сервисами"""
        web_response = make_request(f'{WEB_BASE_URL}/api/version')
        bot_response = requests.get(f'{BOT_API_URL}/api/version', timeout=TIMEOUT)

        assert web_response.status_code == 200
        assert bot_response.status_code == 200

        web_data = web_response.json()
        bot_data = bot_response.json()

        # Версии бота должны совпадать
        assert web_data.get('bot_version') == bot_data.get('bot_version'), \
            f"Bot version inconsistent: web reports {web_data.get('bot_version')}, bot reports {bot_data.get('bot_version')}"


def run_smoke_tests():
    """Запуск smoke тестов для использования в pre-push хуке"""
    import sys

    # Запускаем только smoke тесты (без приёмочных)
    exit_code = pytest.main([
        __file__,
        '-v',
        '-k', 'TestWebSmoke or TestBotSmoke',
        '--tb=short',
        '-x'  # Остановиться при первой ошибке
    ])

    return exit_code == 0


def run_acceptance_tests():
    """Запуск всех тестов включая проверку версий"""
    import sys

    exit_code = pytest.main([
        __file__,
        '-v',
        '--tb=short'
    ])

    return exit_code == 0


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--acceptance':
        success = run_acceptance_tests()
    else:
        success = run_smoke_tests()

    sys.exit(0 if success else 1)
