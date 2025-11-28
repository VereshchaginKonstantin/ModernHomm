#!/usr/bin/env python3
"""
Модуль для генерации PNG изображения игрового поля
"""

import os
import io
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session
from db.models import Game, BattleUnit, Unit


class FieldRenderer:
    """Класс для генерации изображения игрового поля"""

    # Настройки отображения
    CELL_SIZE = 100  # Размер одной клетки в пикселях
    UNIT_ICON_SIZE = 80  # Размер иконки юнита (меньше чем клетка)
    BORDER_WIDTH = 2  # Ширина границы клеток
    COLOR_LIGHT = (240, 217, 181)  # Светлая клетка (бежевый)
    COLOR_DARK = (181, 136, 99)   # Темная клетка (коричневый)
    COLOR_BORDER = (0, 0, 0)      # Цвет границ
    COLOR_TEXT = (0, 0, 0)        # Цвет текста
    LABEL_HEIGHT = 30             # Высота области для меток (A, B, C и 1, 2, 3)

    def __init__(self, db_session: Session):
        self.db = db_session

    def render_field(self, game_id: int) -> Optional[bytes]:
        """
        Генерирует PNG изображение игрового поля

        Args:
            game_id: ID игры

        Returns:
            bytes: PNG изображение в виде байтов или None если игра не найдена
        """
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return None

        field = game.field
        width, height = field.width, field.height

        # Вычислить размеры изображения
        img_width = width * self.CELL_SIZE + self.LABEL_HEIGHT
        img_height = height * self.CELL_SIZE + self.LABEL_HEIGHT

        # Создать новое изображение
        img = Image.new('RGB', (img_width, img_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Попытаться загрузить шрифт
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            font = ImageFont.load_default()
            label_font = ImageFont.load_default()

        # Нарисовать метки столбцов (A, B, C...)
        for x in range(width):
            label = chr(ord('A') + x)
            bbox = draw.textbbox((0, 0), label, font=label_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = self.LABEL_HEIGHT + x * self.CELL_SIZE + (self.CELL_SIZE - text_width) // 2
            text_y = (self.LABEL_HEIGHT - text_height) // 2
            draw.text((text_x, text_y), label, fill=self.COLOR_TEXT, font=label_font)

        # Нарисовать метки строк (1, 2, 3...)
        for y in range(height):
            label = str(y + 1)
            bbox = draw.textbbox((0, 0), label, font=label_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (self.LABEL_HEIGHT - text_width) // 2
            text_y = self.LABEL_HEIGHT + y * self.CELL_SIZE + (self.CELL_SIZE - text_height) // 2
            draw.text((text_x, text_y), label, fill=self.COLOR_TEXT, font=label_font)

        # Нарисовать шахматную доску
        for y in range(height):
            for x in range(width):
                # Определить цвет клетки (шахматный порядок)
                is_light = (x + y) % 2 == 0
                color = self.COLOR_LIGHT if is_light else self.COLOR_DARK

                # Координаты клетки на изображении
                cell_x = self.LABEL_HEIGHT + x * self.CELL_SIZE
                cell_y = self.LABEL_HEIGHT + y * self.CELL_SIZE

                # Нарисовать клетку
                draw.rectangle(
                    [cell_x, cell_y, cell_x + self.CELL_SIZE, cell_y + self.CELL_SIZE],
                    fill=color,
                    outline=self.COLOR_BORDER,
                    width=self.BORDER_WIDTH
                )

        # Разместить юниты на поле
        for battle_unit in game.battle_units:
            x, y = battle_unit.position_x, battle_unit.position_y
            unit = battle_unit.user_unit.unit

            # Подсчитать живых юнитов
            alive_count = self._count_alive_units(battle_unit)

            if alive_count > 0:
                # Координаты клетки
                cell_x = self.LABEL_HEIGHT + x * self.CELL_SIZE
                cell_y = self.LABEL_HEIGHT + y * self.CELL_SIZE

                # Проверить, есть ли изображение юнита
                if unit.image_path and os.path.exists(unit.image_path):
                    # Загрузить и отобразить изображение юнита
                    unit_img = Image.open(unit.image_path)

                    # Определить, нужно ли зеркалить (для противника)
                    if battle_unit.player_id == game.player2_id:
                        unit_img = unit_img.transpose(Image.FLIP_LEFT_RIGHT)

                    # Изменить размер изображения
                    unit_img = unit_img.resize((self.UNIT_ICON_SIZE, self.UNIT_ICON_SIZE), Image.LANCZOS)

                    # Вычислить позицию для центрирования
                    icon_x = cell_x + (self.CELL_SIZE - self.UNIT_ICON_SIZE) // 2
                    icon_y = cell_y + (self.CELL_SIZE - self.UNIT_ICON_SIZE) // 2 - 10  # Сдвиг вверх для текста

                    # Вставить изображение
                    if unit_img.mode == 'RGBA':
                        img.paste(unit_img, (icon_x, icon_y), unit_img)
                    else:
                        img.paste(unit_img, (icon_x, icon_y))
                else:
                    # Если нет изображения, показать иконку и имя юнита
                    # Получить иконку (из custom_icon или стандартную)
                    icon = unit.icon
                    if unit.custom_icon:
                        icon = unit.custom_icon.custom_icon

                    # Нарисовать текст с иконкой и именем
                    text = f"{icon}\n{unit.name[:6]}"
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    text_x = cell_x + (self.CELL_SIZE - text_width) // 2
                    text_y = cell_y + (self.CELL_SIZE - text_height) // 2 - 10
                    draw.text((text_x, text_y), text, fill=self.COLOR_TEXT, font=font)

                # Нарисовать количество юнитов внизу клетки
                count_text = f"x{alive_count}"
                bbox = draw.textbbox((0, 0), count_text, font=font)
                count_width = bbox[2] - bbox[0]
                count_x = cell_x + (self.CELL_SIZE - count_width) // 2
                count_y = cell_y + self.CELL_SIZE - 25

                # Фон для текста
                draw.rectangle(
                    [count_x - 5, count_y - 2, count_x + count_width + 5, count_y + 20],
                    fill=(255, 255, 255, 200)
                )
                draw.text((count_x, count_y), count_text, fill=self.COLOR_TEXT, font=font)

        # Конвертировать изображение в байты
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)

        return output.getvalue()

    def _count_alive_units(self, battle_unit: BattleUnit) -> int:
        """
        Подсчитать живых юнитов в группе

        Args:
            battle_unit: Юнит в бою

        Returns:
            int: Количество живых юнитов
        """
        if battle_unit.total_count == 0:
            return 0

        # Если есть юниты и у последнего есть HP
        if battle_unit.total_count > 0 and battle_unit.remaining_hp > 0:
            return battle_unit.total_count

        return 0

    def check_all_units_have_images(self) -> Tuple[bool, List[str]]:
        """
        Проверить, что у всех юнитов загружены изображения

        Returns:
            Tuple[bool, List[str]]: (все_загружены, список_юнитов_без_изображений)
        """
        units = self.db.query(Unit).all()
        missing_images = []

        for unit in units:
            if not unit.image_path or not os.path.exists(unit.image_path):
                missing_images.append(unit.name)

        return len(missing_images) == 0, missing_images
