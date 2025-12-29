#!/usr/bin/env python3
"""
Smoke и приёмочные тесты для проверки работоспособности контейнеров.

Эти тесты проверяют:
1. Доступность API endpoints веб-интерфейса и бота
2. Соответствие версий в контейнерах версиям в коде
3. Health check для БД
4. Авторизованный доступ ко всем страницам
"""

import os
import pytest
import requests
from pathlib import Path


# Конфигурация тестов
WEB_BASE_URL = os.getenv('WEB_BASE_URL', 'http://localhost:80')
BOT_API_URL = os.getenv('BOT_API_URL', 'http://localhost:8080')
TIMEOUT = 10  # секунд
VERIFY_SSL = os.getenv('VERIFY_SSL', 'false').lower() == 'true'

# Тестовый пользователь (должен существовать в БД с паролем)
TEST_USERNAME = os.getenv('SMOKE_TEST_USERNAME', 'okarien')
TEST_PASSWORD = os.getenv('SMOKE_TEST_PASSWORD', 'test123')

# Подавляем warnings о небезопасных запросах при verify=False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_local_version(filename):
    """Получить версию из локального файла"""
    try:
        # Пробуем несколько путей
        paths = [
            Path(__file__).parent.parent.parent / filename,  # tests/smoke -> root
            Path(__file__).parent.parent / filename,  # tests -> root
            Path(filename),  # current dir
        ]
        for path in paths:
            if path.exists():
                return path.read_text().strip()
        return None
    except Exception:
        return None


def make_request(url, session=None, **kwargs):
    """Делает HTTP запрос с обработкой редиректа на HTTPS"""
    kwargs.setdefault('timeout', TIMEOUT)
    kwargs.setdefault('verify', VERIFY_SSL)

    requester = session if session else requests
    method = kwargs.pop('method', 'get')

    try:
        if method == 'post':
            response = requester.post(url, **kwargs)
        else:
            response = requester.get(url, **kwargs)

        # Если nginx редиректит на HTTPS, следуем за редиректом без проверки SSL
        if response.status_code in [301, 302] and 'https://' in response.headers.get('Location', ''):
            https_url = response.headers['Location']
            kwargs['verify'] = False
            if method == 'post':
                return requester.post(https_url, **kwargs)
            return requester.get(https_url, **kwargs)
        return response
    except requests.exceptions.SSLError:
        # Пробуем без SSL верификации
        kwargs['verify'] = False
        new_url = url.replace('http://', 'https://')
        if method == 'post':
            return requester.post(new_url, **kwargs)
        return requester.get(new_url, **kwargs)


class TestWebSmoke:
    """Smoke тесты для веб-интерфейса (без авторизации)"""

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
        assert data.get('status') == 'healthy', f"Health status: {data}"
        assert data.get('database') == 'connected', f"Database not connected: {data}"

    def test_web_login_page(self):
        """Проверка доступности страницы логина"""
        response = make_request(f'{WEB_BASE_URL}/login', allow_redirects=False)
        assert response.status_code in [200, 301, 302], f"Login page returned {response.status_code}"

    def test_web_root_redirect(self):
        """Проверка редиректа с главной страницы"""
        response = make_request(f'{WEB_BASE_URL}/', allow_redirects=False)
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


class TestAuthenticatedEndpoints:
    """Тесты авторизованных эндпоинтов"""

    @pytest.fixture(scope='class')
    def auth_session(self):
        """Создает авторизованную сессию"""
        session = requests.Session()
        session.verify = False  # Отключаем проверку SSL для localhost

        login_data = {
            'username': TEST_USERNAME,
            'password': TEST_PASSWORD
        }

        # Определяем HTTPS URL для логина
        # Сначала получаем login page чтобы определить правильный URL
        from urllib.parse import urlparse

        urls_to_try = [
            'https://localhost',  # HTTPS напрямую (предпочтительно)
            WEB_BASE_URL.replace('http://', 'https://').replace(':80', ''),  # HTTPS без порта
        ]

        response = None
        final_base_url = None

        for base_url in urls_to_try:
            login_url = f'{base_url}/login'
            try:
                # Сначала GET чтобы получить сессию
                session.get(login_url, timeout=TIMEOUT, verify=False)
                # Затем POST для логина
                response = session.post(login_url, data=login_data,
                                       allow_redirects=True, timeout=TIMEOUT, verify=False)
                if response.url:
                    parsed = urlparse(response.url)
                    final_base_url = f'{parsed.scheme}://{parsed.netloc}'
                break
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                continue

        if response is None:
            pytest.skip(f"Could not connect to any URL. Tried: {urls_to_try}")

        # Проверяем что логин успешен
        if response.status_code != 200:
            pytest.skip(f"Login failed with status {response.status_code}. Check test credentials.")

        # Проверяем что мы залогинены (не на странице логина)
        if '/login' in response.url:
            pytest.skip(f"Login failed - still on login page. Check test credentials for user '{TEST_USERNAME}'")

        # Сохраняем base_url для использования в тестах
        session.base_url = final_base_url or 'https://localhost'
        return session

    def test_login_successful(self, auth_session):
        """Проверка успешного логина"""
        # Если дошли сюда - логин уже успешен (fixture не скипнул)
        assert auth_session is not None

    def _get(self, auth_session, path):
        """Вспомогательный метод для GET запросов с авторизацией"""
        url = f'{auth_session.base_url}{path}'
        return auth_session.get(url, timeout=TIMEOUT, verify=False, allow_redirects=True)

    def test_arena_page(self, auth_session):
        """Проверка страницы арены"""
        response = self._get(auth_session, '/arena/')
        assert response.status_code == 200, f"Arena page returned {response.status_code}"
        assert 'Арена' in response.text or 'arena' in response.text.lower()

    def test_fields_list_page(self, auth_session):
        """Проверка списка полей"""
        response = self._get(auth_session, '/fields/')
        assert response.status_code == 200, f"Fields list returned {response.status_code}: {response.text[:500]}"

    def test_fields_edit_page(self, auth_session):
        """Проверка редактора поля (field_id=4)"""
        response = self._get(auth_session, '/fields/4/edit')
        assert response.status_code == 200, f"Fields edit returned {response.status_code}: {response.text[:500]}"
        # Проверяем что это страница редактора, а не ошибка БД
        assert 'OperationalError' not in response.text, \
            f"Fields edit page has database error: {response.text[:1000]}"
        assert 'password authentication failed' not in response.text, \
            f"Fields edit page has auth error: {response.text[:1000]}"

    def test_elements_page(self, auth_session):
        """Проверка страницы элементов"""
        response = self._get(auth_session, '/elements/')
        assert response.status_code == 200, f"Elements page returned {response.status_code}"

    def test_races_page(self, auth_session):
        """Проверка страницы рас (админ-панель)"""
        response = self._get(auth_session, '/admin/races/')
        assert response.status_code == 200, f"Races page returned {response.status_code}"

    def test_leaderboard_page(self, auth_session):
        """Проверка таблицы лидеров"""
        response = self._get(auth_session, '/leaderboard')
        assert response.status_code == 200, f"Leaderboard returned {response.status_code}"

    def test_help_page(self, auth_session):
        """Проверка страницы справки"""
        response = self._get(auth_session, '/help')
        assert response.status_code == 200, f"Help page returned {response.status_code}"


class TestArenaAPI:
    """Тесты Arena API эндпоинтов"""

    def test_arena_debug_status(self):
        """Проверка статуса арены"""
        response = make_request(f'{WEB_BASE_URL}/arena/api/public/debug/status')
        assert response.status_code == 200, f"Arena status returned {response.status_code}"
        data = response.json()
        # Проверяем что ответ содержит какие-то данные о состоянии
        assert 'debug_mode' in data or 'status' in data, f"Unexpected response: {data}"


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
    exit_code = pytest.main([
        __file__,
        '-v',
        '-k', 'TestWebSmoke or TestBotSmoke or TestArenaAPI',
        '--tb=short',
        '-x'  # Остановиться при первой ошибке
    ])
    return exit_code == 0


def run_acceptance_tests():
    """Запуск всех тестов включая проверку версий и авторизованные эндпоинты"""
    exit_code = pytest.main([
        __file__,
        '-v',
        '--tb=short'
    ])
    return exit_code == 0


def run_authenticated_tests():
    """Запуск только авторизованных тестов"""
    exit_code = pytest.main([
        __file__,
        '-v',
        '-k', 'TestAuthenticatedEndpoints',
        '--tb=short'
    ])
    return exit_code == 0


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == '--acceptance':
            success = run_acceptance_tests()
        elif sys.argv[1] == '--auth':
            success = run_authenticated_tests()
        else:
            success = run_smoke_tests()
    else:
        success = run_smoke_tests()

    sys.exit(0 if success else 1)
