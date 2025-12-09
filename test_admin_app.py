#!/usr/bin/env python3
"""
Интеграционные тесты для веб-интерфейса
"""

import pytest
import os
import json
import tempfile
import zipfile
from decimal import Decimal
from admin_app import app, db
from db.models import Unit


@pytest.fixture
def client():
    """Создать тестовый клиент Flask"""
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

    with app.test_client() as client:
        yield client

    # Очистка после тестов
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for file in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(app.config['UPLOAD_FOLDER'])


@pytest.fixture
def test_unit():
    """Создать тестового юнита в БД"""
    with db.get_session() as session:
        # Очистить существующие юниты
        session.query(Unit).delete()
        session.flush()

        unit = Unit(
            name="Тестовый воин",
            icon="⚔️",
            price=Decimal("100.00"),
            damage=10,
            defense=5,
            health=100,
            range=1,
            speed=2,
            luck=Decimal("0.1"),
            crit_chance=Decimal("0.15")
        )
        session.add(unit)
        session.flush()
        unit_id = unit.id

    yield unit_id

    # Очистка после теста
    with db.get_session() as session:
        session.query(Unit).filter_by(id=unit_id).delete()
        session.flush()


class TestAdminPages:
    """Тесты страниц веб-интерфейса"""

    def test_index_page(self, client):
        """Тест главной страницы (управление картинками)"""
        response = client.get('/')
        assert response.status_code == 200
        assert 'Управление картинками юнитов' in response.data.decode('utf-8')

    def test_units_list_page(self, client):
        """Тест страницы списка юнитов"""
        response = client.get('/units')
        assert response.status_code == 200
        assert 'Управление юнитами' in response.data.decode('utf-8')

    def test_help_page(self, client):
        """Тест страницы справки"""
        response = client.get('/help')
        assert response.status_code == 200
        assert 'Справка по параметрам юнитов' in response.data.decode('utf-8')
        assert 'Базовые параметры' in response.data.decode('utf-8')
        assert 'Полная формула расчета урона' in response.data.decode('utf-8')


class TestUnitManagement:
    """Тесты управления юнитами"""

    def test_create_unit_get(self, client):
        """Тест отображения формы создания юнита"""
        response = client.get('/units/create')
        assert response.status_code == 200
        assert 'Создание юнита' in response.data.decode('utf-8')

    def test_create_unit_post(self, client):
        """Тест создания нового юнита"""
        # Очистить базу
        with db.get_session() as session:
            session.query(Unit).delete()
            session.flush()

        response = client.post('/units/create', data={
            'name': 'Новый юнит',
            'icon': '🛡️',
            'price': '150.50',
            'damage': '15',
            'defense': '8',
            'health': '120',
            'range': '2',
            'speed': '3',
            'luck': '0.2',
            'crit_chance': '0.25'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert 'успешно создан' in response.data.decode('utf-8')

        # Проверить, что юнит действительно создан в БД
        with db.get_session() as session:
            unit = session.query(Unit).filter_by(name='Новый юнит').first()
            assert unit is not None
            assert unit.icon == '🛡️'
            assert float(unit.price) == 150.50
            assert unit.damage == 15
            assert unit.defense == 8
            assert unit.health == 120
            assert unit.range == 2
            assert unit.speed == 3
            assert float(unit.luck) == 0.2
            assert float(unit.crit_chance) == 0.25

    def test_edit_unit_get(self, client, test_unit):
        """Тест отображения формы редактирования юнита"""
        response = client.get(f'/units/edit/{test_unit}')
        assert response.status_code == 200
        assert 'Редактирование юнита' in response.data.decode('utf-8')
        assert 'Тестовый воин' in response.data.decode('utf-8')

    def test_edit_unit_post(self, client, test_unit):
        """Тест редактирования юнита"""
        response = client.post(f'/units/edit/{test_unit}', data={
            'name': 'Измененный воин',
            'icon': '⚔️',
            'price': '200.00',
            'damage': '20',
            'defense': '10',
            'health': '150',
            'range': '2',
            'speed': '3',
            'luck': '0.15',
            'crit_chance': '0.2'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert 'успешно обновлен' in response.data.decode('utf-8')

        # Проверить, что юнит действительно обновлен в БД
        with db.get_session() as session:
            unit = session.query(Unit).filter_by(id=test_unit).first()
            assert unit.name == 'Измененный воин'
            assert float(unit.price) == 200.00
            assert unit.damage == 20
            assert unit.defense == 10

    def test_delete_unit(self, client, test_unit):
        """Тест удаления юнита"""
        response = client.post(f'/units/delete/{test_unit}', follow_redirects=True)
        assert response.status_code == 200
        assert 'удален' in response.data.decode('utf-8')

        # Проверить, что юнит действительно удален из БД
        with db.get_session() as session:
            unit = session.query(Unit).filter_by(id=test_unit).first()
            assert unit is None


class TestExportImport:
    """Тесты экспорта/импорта юнитов"""

    def test_export_units(self, client, test_unit):
        """Тест экспорта юнитов в ZIP"""
        response = client.get('/export')
        assert response.status_code == 200
        assert response.content_type == 'application/zip'

        # Проверить содержимое ZIP
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            tmp.write(response.data)
            tmp_path = tmp.name

        try:
            with zipfile.ZipFile(tmp_path, 'r') as zipf:
                # Проверить наличие units.json
                assert 'units.json' in zipf.namelist()

                # Прочитать и проверить JSON
                with zipf.open('units.json') as f:
                    units_data = json.load(f)
                    assert len(units_data) >= 1

                    # Найти тестового юнита
                    test_unit_data = next((u for u in units_data if u['name'] == 'Тестовый воин'), None)
                    assert test_unit_data is not None
                    assert test_unit_data['icon'] == '⚔️'
                    assert test_unit_data['damage'] == 10
        finally:
            os.remove(tmp_path)

    def test_import_units(self, client):
        """Тест импорта юнитов из ZIP"""
        # Создать тестовый ZIP архив
        units_data = [
            {
                'name': 'Импортированный маг',
                'icon': '🧙',
                'price': 250.0,
                'damage': 30,
                'defense': 5,
                'health': 80,
                'range': 5,
                'speed': 2,
                'luck': 0.3,
                'crit_chance': 0.4,
                'image_filename': None
            },
            {
                'name': 'Импортированный лучник',
                'icon': '🏹',
                'price': 180.0,
                'damage': 25,
                'defense': 3,
                'health': 70,
                'range': 4,
                'speed': 3,
                'luck': 0.2,
                'crit_chance': 0.3,
                'image_filename': None
            }
        ]

        # Создать временный ZIP
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            with zipfile.ZipFile(tmp, 'w') as zipf:
                zipf.writestr('units.json', json.dumps(units_data, ensure_ascii=False, indent=2))
            tmp_path = tmp.name

        try:
            # Отправить запрос на импорт
            with open(tmp_path, 'rb') as f:
                response = client.post('/import', data={
                    'archive': (f, 'test_units.zip')
                }, content_type='multipart/form-data', follow_redirects=True)

            assert response.status_code == 200
            assert 'Успешно импортировано' in response.data.decode('utf-8')

            # Проверить, что юниты импортированы
            with db.get_session() as session:
                mage = session.query(Unit).filter_by(name='Импортированный маг').first()
                assert mage is not None
                assert mage.icon == '🧙'
                assert mage.damage == 30

                archer = session.query(Unit).filter_by(name='Импортированный лучник').first()
                assert archer is not None
                assert archer.icon == '🏹'
                assert archer.damage == 25
        finally:
            os.remove(tmp_path)

    def test_import_invalid_archive(self, client):
        """Тест импорта некорректного архива"""
        # Создать ZIP без units.json
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            with zipfile.ZipFile(tmp, 'w') as zipf:
                zipf.writestr('invalid.txt', 'test')
            tmp_path = tmp.name

        try:
            with open(tmp_path, 'rb') as f:
                response = client.post('/import', data={
                    'archive': (f, 'invalid.zip')
                }, content_type='multipart/form-data', follow_redirects=True)

            assert response.status_code == 200
            assert 'Некорректный архив' in response.data.decode('utf-8')
        finally:
            os.remove(tmp_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
