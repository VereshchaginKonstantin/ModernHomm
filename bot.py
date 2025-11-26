#!/usr/bin/env python3
"""
Простой Telegram бот, который отвечает на все сообщения стандартной фразой из конфига.
Сохраняет все сообщения и пользователей в PostgreSQL.
"""

import json
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from db import Database
from game_engine import GameEngine


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class SimpleBot:
    def __init__(self, config_path='config.json', db=None):
        """Инициализация бота с загрузкой конфигурации"""
        self.config = self.load_config(config_path)
        self.default_response = self.config['bot']['default_response']
        self.bot_token = self.config['telegram']['bot_token']
        self.parse_mode = self.config['telegram'].get('parse_mode', 'HTML')
        self.initial_balance = self.config.get('game', {}).get('initial_balance', 1000)

        # Инициализация базы данных
        if db is None:
            db_url = os.getenv('DATABASE_URL', self.config.get('database', {}).get('url'))
            self.db = Database(db_url)
            self.db.create_tables()
            # Инициализация базовых юнитов
            self.db.initialize_base_units()
            logger.info("Базовые юниты инициализированы")
        else:
            self.db = db

        logger.info("База данных инициализирована")

    def load_config(self, config_path):
        """Загрузка конфигурации из JSON файла"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Файл конфигурации {config_path} не найден!")
            raise
        except json.JSONDecodeError:
            logger.error(f"Ошибка при парсинге файла конфигурации {config_path}")
            raise

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        await update.message.reply_text(
            f"Привет! Я простой бот.\n\n{self.default_response}",
            parse_mode=self.parse_mode
        )
        logger.info(f"Команда /start от пользователя {update.effective_user.id}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "Я простой бот, который отвечает на все сообщения одинаково.\n\n"
            "<b>Основные команды:</b>\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n"
            "/play - Начать игру (инициализация игрового профиля)\n"
            "/profile - Посмотреть свой игровой профиль\n"
            "/shop - Магазин юнитов (покупка армии)\n\n"
            "<b>Игровые команды:</b>\n"
            "/challenge &lt;username&gt; - Вызвать игрока на бой\n"
            "/accept - Принять вызов на бой\n"
            "/game - Показать текущую игру\n"
            "/mygames - История игр\n\n"
            "<b>Другое:</b>\n"
            "/search &lt;username&gt; - Поиск сообщений пользователя\n"
            "/users - Просмотр всех пользователей"
        )
        await update.message.reply_text(help_text, parse_mode=self.parse_mode)
        logger.info(f"Команда /help от пользователя {update.effective_user.id}")

    async def play_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /play - инициализация игрового профиля"""
        user = update.effective_user
        logger.info(f"Команда /play от пользователя {user.id}")

        try:
            # Получаем или создаем игрового пользователя
            game_user, created = self.db.get_or_create_game_user(
                telegram_id=user.id,
                name=user.first_name or user.username or f"User_{user.id}",
                initial_balance=self.initial_balance
            )

            if created:
                response = (
                    f"🎮 Добро пожаловать в игру, {game_user.name}!\n\n"
                    f"💰 Ваш начальный баланс: ${game_user.balance}\n"
                    f"🏆 Побед: {game_user.wins}\n"
                    f"💔 Поражений: {game_user.losses}\n\n"
                    "Удачи в игре!"
                )
            else:
                response = (
                    f"👋 С возвращением, {game_user.name}!\n\n"
                    f"💰 Текущий баланс: ${game_user.balance}\n"
                    f"🏆 Побед: {game_user.wins}\n"
                    f"💔 Поражений: {game_user.losses}\n\n"
                    "Вы уже зарегистрированы в игре!"
                )

            await update.message.reply_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при инициализации игрового профиля: {e}")
            await update.message.reply_text(
                "Произошла ошибка при создании игрового профиля. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /profile - просмотр игрового профиля"""
        user = update.effective_user
        logger.info(f"Команда /profile от пользователя {user.id}")

        try:
            game_user = self.db.get_game_user(user.id)

            if not game_user:
                await update.message.reply_text(
                    "❌ У вас еще нет игрового профиля.\n"
                    "Используйте /play для создания профиля.",
                    parse_mode=self.parse_mode
                )
                return

            # Получаем юнитов пользователя
            user_units = self.db.get_user_units(user.id)

            units_text = ""
            if user_units:
                units_text = "\n\n🔰 Ваши юниты:\n"
                for user_unit in user_units:
                    # Получаем детали юнита
                    unit = self.db.get_unit_by_id(user_unit.unit_type_id)
                    if unit:
                        units_text += (
                            f"\n{unit.name} x{user_unit.count}\n"
                            f"  ⚔️ Урон: {unit.damage} | 🛡️ Защита: {unit.defense} | 🎯 Дальность: {unit.range}\n"
                            f"  ❤️ HP: {unit.health} | 🏃 Скорость: {unit.speed}\n"
                        )
            else:
                units_text = "\n\n🔰 У вас пока нет юнитов. Посетите /shop для покупки!"

            response = (
                f"👤 Профиль игрока {game_user.name}\n\n"
                f"💰 Баланс: ${game_user.balance}\n"
                f"🏆 Побед: {game_user.wins}\n"
                f"💔 Поражений: {game_user.losses}"
                f"{units_text}"
            )

            await update.message.reply_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при получении профиля: {e}")
            await update.message.reply_text(
                "Произошла ошибка при получении профиля. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def shop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /shop - магазин юнитов"""
        user = update.effective_user
        logger.info(f"Команда /shop от пользователя {user.id}")

        try:
            # Проверяем наличие игрового профиля
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await update.message.reply_text(
                    "❌ У вас еще нет игрового профиля.\n"
                    "Используйте /play для создания профиля.",
                    parse_mode=self.parse_mode
                )
                return

            # Получаем все доступные юниты
            units = self.db.get_all_units()

            if not units:
                await update.message.reply_text(
                    "Магазин пуст. Юниты временно недоступны.",
                    parse_mode=self.parse_mode
                )
                return

            # Формируем сообщение с магазином
            response = f"🏪 <b>Магазин юнитов</b>\n\n💰 Ваш баланс: ${game_user.balance}\n\n"
            response += "Выберите юнита для покупки:\n"

            # Создаем кнопки для каждого юнита
            keyboard = []
            for unit in units:
                unit_info = (
                    f"{unit.name} - ${unit.price}\n"
                    f"⚔️ {unit.damage} | 🛡️ {unit.defense} | 🎯 {unit.range} | ❤️ {unit.health} | 🏃 {unit.speed}\n"
                    f"🍀 {float(unit.luck)*100:.0f}% | 💥 {float(unit.crit_chance)*100:.0f}%"
                )
                response += f"\n{unit_info}\n"

                keyboard.append([
                    InlineKeyboardButton(
                        f"Купить {unit.name}",
                        callback_data=f"buy_unit:{unit.id}"
                    )
                ])

            await update.message.reply_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Ошибка при открытии магазина: {e}")
            await update.message.reply_text(
                "Произошла ошибка при открытии магазина. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def buy_unit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для выбора юнита в магазине"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: buy_unit:unit_id)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'buy_unit':
            return

        unit_id = int(data[1])
        user = update.effective_user

        try:
            # Получаем информацию о юните
            unit = self.db.get_unit_by_id(unit_id)
            if not unit:
                await query.edit_message_text(
                    "❌ Юнит не найден.",
                    parse_mode=self.parse_mode
                )
                return

            # Получаем баланс пользователя
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await query.edit_message_text(
                    "❌ Игровой профиль не найден.",
                    parse_mode=self.parse_mode
                )
                return

            # Показываем информацию о юните и кнопки для выбора количества
            response = (
                f"🛒 <b>Покупка: {unit.name}</b>\n\n"
                f"💰 Цена за 1 шт: ${unit.price}\n"
                f"💵 Ваш баланс: ${game_user.balance}\n\n"
                f"<b>Характеристики:</b>\n"
                f"⚔️ Урон: {unit.damage}\n"
                f"🛡️ Защита: {unit.defense}\n"
                f"🎯 Дальность: {unit.range}\n"
                f"❤️ Здоровье: {unit.health}\n"
                f"🏃 Скорость: {unit.speed}\n"
                f"🍀 Удача: {float(unit.luck)*100:.0f}%\n"
                f"💥 Крит: {float(unit.crit_chance)*100:.0f}%\n\n"
                f"Выберите количество:"
            )

            # Создаем кнопки для выбора количества
            keyboard = []
            quantities = [1, 5, 10]
            row = []
            for qty in quantities:
                total = float(unit.price) * qty
                if total <= float(game_user.balance):
                    row.append(InlineKeyboardButton(
                        f"{qty} шт (${total:.0f})",
                        callback_data=f"confirm_buy:{unit_id}:{qty}"
                    ))
            if row:
                keyboard.append(row)

            keyboard.append([
                InlineKeyboardButton("◀️ Назад в магазин", callback_data="back_to_shop")
            ])

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Ошибка при выборе юнита: {e}")
            await query.edit_message_text(
                "Произошла ошибка. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def confirm_buy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для подтверждения покупки"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: confirm_buy:unit_id:quantity)
        data = query.data.split(':')
        if len(data) != 3 or data[0] != 'confirm_buy':
            return

        unit_id = int(data[1])
        quantity = int(data[2])
        user = update.effective_user

        try:
            # Выполняем покупку
            success, message = self.db.purchase_units(user.id, unit_id, quantity)

            if success:
                # Получаем обновленный профиль
                game_user = self.db.get_game_user(user.id)
                response = (
                    f"✅ {message}\n\n"
                    f"💰 Новый баланс: ${game_user.balance}"
                )
            else:
                response = f"❌ {message}"

            # Кнопки для дальнейших действий
            keyboard = [
                [
                    InlineKeyboardButton("🏪 Продолжить покупки", callback_data="back_to_shop"),
                    InlineKeyboardButton("👤 Профиль", callback_data="show_profile")
                ]
            ]

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Ошибка при покупке юнита: {e}")
            await query.edit_message_text(
                f"❌ Произошла ошибка при покупке: {e}",
                parse_mode=self.parse_mode
            )

    async def back_to_shop_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для возврата в магазин"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user

        try:
            # Получаем игрового пользователя
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await query.edit_message_text("❌ Игровой профиль не найден.", parse_mode=self.parse_mode)
                return

            # Получаем все доступные юниты
            units = self.db.get_all_units()

            # Формируем сообщение с магазином
            response = f"🏪 <b>Магазин юнитов</b>\n\n💰 Ваш баланс: ${game_user.balance}\n\n"
            response += "Выберите юнита для покупки:\n"

            # Создаем кнопки для каждого юнита
            keyboard = []
            for unit in units:
                unit_info = (
                    f"{unit.name} - ${unit.price}\n"
                    f"⚔️ {unit.damage} | 🛡️ {unit.defense} | 🎯 {unit.range} | ❤️ {unit.health} | 🏃 {unit.speed}\n"
                    f"🍀 {float(unit.luck)*100:.0f}% | 💥 {float(unit.crit_chance)*100:.0f}%"
                )
                response += f"\n{unit_info}\n"

                keyboard.append([
                    InlineKeyboardButton(
                        f"Купить {unit.name}",
                        callback_data=f"buy_unit:{unit.id}"
                    )
                ])

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Ошибка при возврате в магазин: {e}")
            await query.edit_message_text(
                "Произошла ошибка. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def show_profile_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для показа профиля"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await query.edit_message_text("❌ Игровой профиль не найден.", parse_mode=self.parse_mode)
                return

            # Получаем юнитов пользователя
            user_units = self.db.get_user_units(user.id)

            units_text = ""
            if user_units:
                units_text = "\n\n🔰 Ваши юниты:\n"
                for user_unit in user_units:
                    unit = self.db.get_unit_by_id(user_unit.unit_type_id)
                    if unit:
                        units_text += (
                            f"\n{unit.name} x{user_unit.count}\n"
                            f"  ⚔️ Урон: {unit.damage} | 🛡️ Защита: {unit.defense} | 🎯 Дальность: {unit.range}\n"
                            f"  ❤️ HP: {unit.health} | 🏃 Скорость: {unit.speed}\n"
                        )
            else:
                units_text = "\n\n🔰 У вас пока нет юнитов. Посетите /shop для покупки!"

            response = (
                f"👤 Профиль игрока {game_user.name}\n\n"
                f"💰 Баланс: ${game_user.balance}\n"
                f"🏆 Побед: {game_user.wins}\n"
                f"💔 Поражений: {game_user.losses}"
                f"{units_text}"
            )

            keyboard = [[InlineKeyboardButton("🏪 Магазин", callback_data="back_to_shop")]]

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Ошибка при показе профиля: {e}")
            await query.edit_message_text(
                "Произошла ошибка. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /search для поиска сообщений по username"""
        if not context.args:
            await update.message.reply_text(
                "Использование: /search <username>\n\n"
                "Например: /search john или /search @john",
                parse_mode=self.parse_mode
            )
            return

        username = context.args[0]
        logger.info(f"Команда /search от пользователя {update.effective_user.id} для username: {username}")

        try:
            messages, total_count = self.db.search_messages_by_username(username, offset=0, limit=10)

            if not messages:
                await update.message.reply_text(
                    f"Сообщения от пользователя {username} не найдены.",
                    parse_mode=self.parse_mode
                )
                return

            # Формируем текст с результатами
            response = self._format_search_results(username, messages, total_count, page=0)

            # Создаем кнопки пагинации если сообщений больше 10
            keyboard = self._create_pagination_keyboard(username, page=0, total_count=total_count)

            if keyboard:
                await update.message.reply_text(
                    response,
                    parse_mode=self.parse_mode,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при поиске сообщений: {e}")
            await update.message.reply_text(
                "Произошла ошибка при поиске сообщений. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def search_pagination_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для пагинации результатов поиска"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: search:username:page)
        data = query.data.split(':')
        if len(data) != 3 or data[0] != 'search':
            return

        username = data[1]
        page = int(data[2])
        offset = page * 10

        try:
            messages, total_count = self.db.search_messages_by_username(username, offset=offset, limit=10)

            if not messages:
                await query.edit_message_text(
                    f"Больше сообщений от пользователя {username} не найдено.",
                    parse_mode=self.parse_mode
                )
                return

            # Формируем текст с результатами
            response = self._format_search_results(username, messages, total_count, page)

            # Создаем кнопки пагинации
            keyboard = self._create_pagination_keyboard(username, page, total_count)

            if keyboard:
                await query.edit_message_text(
                    response,
                    parse_mode=self.parse_mode,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при пагинации результатов поиска: {e}")
            await query.edit_message_text(
                "Произошла ошибка при загрузке следующей страницы.",
                parse_mode=self.parse_mode
            )

    def _format_search_results(self, username: str, messages: list, total_count: int, page: int) -> str:
        """Форматирование результатов поиска"""
        start_num = page * 10 + 1
        end_num = min(start_num + len(messages) - 1, total_count)

        response = f"🔍 Результаты поиска для @{username}\n"
        response += f"Показаны {start_num}-{end_num} из {total_count} сообщений\n\n"

        for i, msg in enumerate(messages, start=start_num):
            # Форматируем дату
            date_str = msg.message_date.strftime("%d.%m.%Y %H:%M")
            # Ограничиваем длину сообщения
            text_preview = msg.message_text[:100] + "..." if len(msg.message_text) > 100 else msg.message_text
            response += f"{i}. [{date_str}]\n{text_preview}\n\n"

        return response

    def _create_pagination_keyboard(self, username: str, page: int, total_count: int) -> list:
        """Создание клавиатуры для пагинации"""
        total_pages = (total_count + 9) // 10  # Округление вверх

        if total_pages <= 1:
            return None

        keyboard = []
        buttons = []

        # Кнопка "Предыдущая"
        if page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"search:{username}:{page-1}"))

        # Показываем текущую страницу
        buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))

        # Кнопка "Следующая"
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"search:{username}:{page+1}"))

        if buttons:
            keyboard.append(buttons)

        return keyboard

    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /users для просмотра всех пользователей"""
        logger.info(f"Команда /users от пользователя {update.effective_user.id}")

        try:
            users, total_count = self.db.get_users_paginated(offset=0, limit=10)

            if not users:
                await update.message.reply_text(
                    "Пользователи не найдены.",
                    parse_mode=self.parse_mode
                )
                return

            # Формируем текст с результатами
            response = self._format_users_list(users, total_count, page=0)

            # Создаем кнопки с пользователями и пагинацией
            keyboard = self._create_users_keyboard(users, page=0, total_count=total_count)

            await update.message.reply_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            await update.message.reply_text(
                "Произошла ошибка при получении списка пользователей. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def users_pagination_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для пагинации списка пользователей"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: users:page)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'users':
            return

        page = int(data[1])
        offset = page * 10

        try:
            users, total_count = self.db.get_users_paginated(offset=offset, limit=10)

            if not users:
                await query.edit_message_text(
                    "Больше пользователей не найдено.",
                    parse_mode=self.parse_mode
                )
                return

            # Формируем текст с результатами
            response = self._format_users_list(users, total_count, page)

            # Создаем кнопки с пользователями и пагинацией
            keyboard = self._create_users_keyboard(users, page, total_count)

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Ошибка при пагинации списка пользователей: {e}")
            await query.edit_message_text(
                "Произошла ошибка при загрузке следующей страницы.",
                parse_mode=self.parse_mode
            )

    async def user_messages_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для просмотра сообщений пользователя"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: user_msgs:telegram_id:page или user_msgs:telegram_id:page:back_page)
        data = query.data.split(':')
        if len(data) < 3 or data[0] != 'user_msgs':
            return

        telegram_id = int(data[1])
        page = int(data[2])
        back_page = int(data[3]) if len(data) > 3 else 0
        offset = page * 10

        try:
            messages, total_count = self.db.get_user_messages_paginated(telegram_id, offset=offset, limit=10)

            if not messages:
                await query.edit_message_text(
                    "Сообщения не найдены.",
                    parse_mode=self.parse_mode
                )
                return

            # Формируем текст с результатами
            response = self._format_user_messages(messages, total_count, page, telegram_id)

            # Создаем кнопки пагинации и кнопку "Назад"
            keyboard = self._create_user_messages_keyboard(telegram_id, page, total_count, back_page)

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Ошибка при получении сообщений пользователя: {e}")
            await query.edit_message_text(
                "Произошла ошибка при загрузке сообщений.",
                parse_mode=self.parse_mode
            )

    def _format_users_list(self, users: list, total_count: int, page: int) -> str:
        """Форматирование списка пользователей"""
        start_num = page * 10 + 1
        end_num = min(start_num + len(users) - 1, total_count)

        response = f"👥 Список пользователей\n"
        response += f"Показаны {start_num}-{end_num} из {total_count} пользователей\n\n"
        response += "Выберите пользователя, чтобы посмотреть его сообщения:"

        return response

    def _format_user_messages(self, messages: list, total_count: int, page: int, telegram_id: int) -> str:
        """Форматирование сообщений пользователя"""
        start_num = page * 10 + 1
        end_num = min(start_num + len(messages) - 1, total_count)

        # Получаем информацию о пользователе из первого сообщения
        username = messages[0].username if messages and messages[0].username else f"ID: {telegram_id}"
        user_display = f"@{username}" if messages[0].username else username

        response = f"💬 Сообщения пользователя {user_display}\n"
        response += f"Показаны {start_num}-{end_num} из {total_count} сообщений\n\n"

        for i, msg in enumerate(messages, start=start_num):
            # Форматируем дату
            date_str = msg.message_date.strftime("%d.%m.%Y %H:%M")
            # Ограничиваем длину сообщения
            text_preview = msg.message_text[:100] + "..." if len(msg.message_text) > 100 else msg.message_text
            response += f"{i}. [{date_str}]\n{text_preview}\n\n"

        return response

    def _create_users_keyboard(self, users: list, page: int, total_count: int) -> list:
        """Создание клавиатуры со списком пользователей и пагинацией"""
        keyboard = []

        # Кнопки с пользователями (по 1 в строке)
        for user in users:
            user_display = f"@{user.username}" if user.username else f"{user.first_name or 'User'} (ID: {user.telegram_id})"
            # Формат callback: user_msgs:telegram_id:page:back_page
            keyboard.append([
                InlineKeyboardButton(
                    user_display,
                    callback_data=f"user_msgs:{user.telegram_id}:0:{page}"
                )
            ])

        # Кнопки пагинации
        total_pages = (total_count + 9) // 10
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"users:{page-1}"))
            nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"users:{page+1}"))
            keyboard.append(nav_buttons)

        return keyboard

    def _create_user_messages_keyboard(self, telegram_id: int, page: int, total_count: int, back_page: int) -> list:
        """Создание клавиатуры для пагинации сообщений пользователя"""
        keyboard = []
        total_pages = (total_count + 9) // 10

        # Кнопки пагинации сообщений
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"user_msgs:{telegram_id}:{page-1}:{back_page}"))
            nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"user_msgs:{telegram_id}:{page+1}:{back_page}"))
            keyboard.append(nav_buttons)

        # Кнопка "Вернуться к списку пользователей"
        keyboard.append([
            InlineKeyboardButton("🔙 К списку пользователей", callback_data=f"users:{back_page}")
        ])

        return keyboard

    # ===== Игровые команды =====

    async def challenge_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /challenge - вызов игрока на бой"""
        user = update.effective_user
        logger.info(f"Команда /challenge от пользователя {user.id}")

        if not context.args:
            await update.message.reply_text(
                "Использование: /challenge <username>\n\n"
                "Например: /challenge john",
                parse_mode=self.parse_mode
            )
            return

        opponent_username = context.args[0].lstrip('@')

        try:
            # Проверка игрового профиля
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await update.message.reply_text(
                    "❌ У вас еще нет игрового профиля. Используйте /play",
                    parse_mode=self.parse_mode
                )
                return

            # Проверка активной игры
            active_game = self.db.get_active_game(user.id)
            if active_game:
                await update.message.reply_text(
                    "❌ У вас уже есть активная игра. Завершите её сначала.",
                    parse_mode=self.parse_mode
                )
                return

            # Создание игры через игровой движок
            with self.db.get_session() as session:
                engine = GameEngine(session)
                game, message = engine.create_game(game_user.id, opponent_username)

            if game:
                response = (
                    f"✅ {message}\n\n"
                    f"Игра #{game.id} создана!\n"
                    f"Ожидание принятия игроком {opponent_username}"
                )
            else:
                response = f"❌ {message}"

            await update.message.reply_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при создании игры: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка: {e}",
                parse_mode=self.parse_mode
            )

    async def accept_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /accept - принятие вызова"""
        user = update.effective_user
        logger.info(f"Команда /accept от пользователя {user.id}")

        try:
            # Проверка игрового профиля
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await update.message.reply_text(
                    "❌ У вас еще нет игрового профиля. Используйте /play",
                    parse_mode=self.parse_mode
                )
                return

            # Поиск игры в ожидании
            active_game = self.db.get_active_game(user.id)
            if not active_game:
                await update.message.reply_text(
                    "❌ У вас нет ожидающих игр",
                    parse_mode=self.parse_mode
                )
                return

            if active_game.status.value != 'waiting':
                await update.message.reply_text(
                    "❌ Игра уже начата",
                    parse_mode=self.parse_mode
                )
                return

            # Принятие игры через игровой движок
            with self.db.get_session() as session:
                engine = GameEngine(session)
                success, message = engine.accept_game(active_game.id, game_user.id)

            if success:
                # Показать поле
                with self.db.get_session() as session:
                    engine = GameEngine(session)
                    field_display = engine.render_field(active_game.id)

                response = f"✅ {message}\n\n{field_display}"

                # Получить доступные действия
                actions = engine.get_available_actions(active_game.id, game_user.id)
                keyboard = self._create_game_keyboard(active_game.id, game_user.id, actions)

                await update.message.reply_text(
                    response,
                    parse_mode=self.parse_mode,
                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                )
            else:
                await update.message.reply_text(
                    f"❌ {message}",
                    parse_mode=self.parse_mode
                )

        except Exception as e:
            logger.error(f"Ошибка при принятии игры: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка: {e}",
                parse_mode=self.parse_mode
            )

    async def game_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /game - показать текущую игру"""
        user = update.effective_user
        logger.info(f"Команда /game от пользователя {user.id}")

        try:
            # Проверка игрового профиля
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await update.message.reply_text(
                    "❌ У вас еще нет игрового профиля. Используйте /play",
                    parse_mode=self.parse_mode
                )
                return

            # Поиск активной игры
            active_game = self.db.get_active_game(user.id)
            if not active_game:
                await update.message.reply_text(
                    "❌ У вас нет активных игр. Используйте /challenge для вызова",
                    parse_mode=self.parse_mode
                )
                return

            # Отображение игры
            with self.db.get_session() as session:
                engine = GameEngine(session)
                field_display = engine.render_field(active_game.id)
                actions = engine.get_available_actions(active_game.id, game_user.id)

            keyboard = self._create_game_keyboard(active_game.id, game_user.id, actions)

            await update.message.reply_text(
                field_display,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )

        except Exception as e:
            logger.error(f"Ошибка при отображении игры: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка: {e}",
                parse_mode=self.parse_mode
            )

    async def mygames_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /mygames - история игр"""
        user = update.effective_user
        logger.info(f"Команда /mygames от пользователя {user.id}")

        try:
            # Проверка игрового профиля
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await update.message.reply_text(
                    "❌ У вас еще нет игрового профиля. Используйте /play",
                    parse_mode=self.parse_mode
                )
                return

            # Получение игр
            games = self.db.get_user_games(user.id)

            if not games:
                await update.message.reply_text(
                    "📋 У вас пока нет игр",
                    parse_mode=self.parse_mode
                )
                return

            response = "📋 <b>Ваши игры:</b>\n\n"
            for game in games[:10]:  # Показываем последние 10
                opponent_id = game.player2_id if game.player1_id == game_user.id else game.player1_id
                opponent = self.db.get_game_user(opponent_id) if opponent_id else None
                opponent_name = opponent.name if opponent else "Unknown"

                status_emoji = {"waiting": "⏳", "in_progress": "⚔️", "completed": "✅"}
                status_text = status_emoji.get(game.status.value, "❓")

                result = ""
                if game.status.value == "completed":
                    if game.winner_id == game_user.id:
                        result = " - 🏆 Победа"
                    else:
                        result = " - 💔 Поражение"

                response += f"{status_text} Игра #{game.id} vs {opponent_name}{result}\n"

            await update.message.reply_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при получении истории игр: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка: {e}",
                parse_mode=self.parse_mode
            )

    def _create_game_keyboard(self, game_id: int, player_id: int, actions: dict) -> list:
        """Создание клавиатуры для игровых действий"""
        keyboard = []

        if actions.get("action") == "accept":
            keyboard.append([InlineKeyboardButton("✅ Принять игру", callback_data=f"game_accept:{game_id}")])
        elif actions.get("action") == "wait":
            return []
        elif actions.get("action") == "play":
            # Кнопки для выбора юнита
            units = actions.get("units", [])
            for unit in units[:5]:  # Показываем первые 5 юнитов
                unit_name = unit.get("unit_name", "Unit")
                unit_id = unit.get("unit_id")
                pos = unit.get("position", (0, 0))
                keyboard.append([
                    InlineKeyboardButton(
                        f"⚔️ {unit_name} [{pos[0]},{pos[1]}]",
                        callback_data=f"game_unit:{game_id}:{unit_id}"
                    )
                ])

        keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data=f"game_refresh:{game_id}")])
        return keyboard

    async def game_unit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для выбора юнита"""
        query = update.callback_query
        await query.answer()

        data = query.data.split(':')
        if len(data) != 3 or data[0] != 'game_unit':
            return

        game_id = int(data[1])
        unit_id = int(data[2])
        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await query.edit_message_text("❌ Игровой профиль не найден")
                return

            # Показать действия для юнита
            with self.db.get_session() as session:
                engine = GameEngine(session)
                actions = engine.get_available_actions(game_id, game_user.id)

            # Найти выбранного юнита
            unit_data = None
            for unit in actions.get("units", []):
                if unit.get("unit_id") == unit_id:
                    unit_data = unit
                    break

            if not unit_data:
                await query.edit_message_text("❌ Юнит не найден")
                return

            response = f"⚔️ <b>{unit_data['unit_name']}</b>\n"
            response += f"Позиция: [{unit_data['position'][0]}, {unit_data['position'][1]}]\n\n"

            keyboard = []

            # Кнопки для движения
            if unit_data.get("can_move"):
                keyboard.append([InlineKeyboardButton("🏃 Переместить", callback_data=f"game_move:{game_id}:{unit_id}")])

            # Кнопки для атаки
            targets = unit_data.get("targets", [])
            if targets:
                response += "🎯 <b>Доступные цели:</b>\n"
                for target in targets[:3]:  # Показываем первые 3 цели
                    response += f"- {target['unit_name']} [{target['position'][0]},{target['position'][1]}]\n"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"⚔️ Атаковать {target['unit_name']}",
                            callback_data=f"game_attack:{game_id}:{unit_id}:{target['unit_id']}"
                        )
                    ])

            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=f"game_refresh:{game_id}")])

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Ошибка при выборе юнита: {e}")
            await query.edit_message_text(f"❌ Ошибка: {e}")

    async def game_move_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для перемещения юнита"""
        query = update.callback_query
        await query.answer()

        data = query.data.split(':')
        if len(data) < 3:
            return

        game_id = int(data[1])
        unit_id = int(data[2])

        # Если есть координаты
        if len(data) == 5:
            target_x = int(data[3])
            target_y = int(data[4])
            user = update.effective_user

            try:
                game_user = self.db.get_game_user(user.id)
                with self.db.get_session() as session:
                    engine = GameEngine(session)
                    success, message = engine.move_unit(game_id, game_user.id, unit_id, target_x, target_y)

                if success:
                    field_display = engine.render_field(game_id)
                    actions = engine.get_available_actions(game_id, game_user.id)
                    keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

                    await query.edit_message_text(
                        f"✅ {message}\n\n{field_display}",
                        parse_mode=self.parse_mode,
                        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                    )
                else:
                    await query.answer(f"❌ {message}", show_alert=True)

            except Exception as e:
                logger.error(f"Ошибка при перемещении: {e}")
                await query.answer(f"❌ Ошибка: {e}", show_alert=True)
        else:
            # Показать доступные позиции
            await query.edit_message_text(
                "🏃 Выберите позицию для перемещения\n\n"
                "Используйте команду: /move <unit_id> <x> <y>",
                parse_mode=self.parse_mode
            )

    async def game_attack_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для атаки"""
        query = update.callback_query
        await query.answer()

        data = query.data.split(':')
        if len(data) != 4 or data[0] != 'game_attack':
            return

        game_id = int(data[1])
        attacker_id = int(data[2])
        target_id = int(data[3])
        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            with self.db.get_session() as session:
                engine = GameEngine(session)
                success, message = engine.attack(game_id, game_user.id, attacker_id, target_id)

            if success:
                field_display = engine.render_field(game_id)
                actions = engine.get_available_actions(game_id, game_user.id)
                keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

                await query.edit_message_text(
                    f"{message}\n\n{field_display}",
                    parse_mode=self.parse_mode,
                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                )
            else:
                await query.answer(f"❌ {message}", show_alert=True)

        except Exception as e:
            logger.error(f"Ошибка при атаке: {e}")
            await query.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def game_refresh_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для обновления игры"""
        query = update.callback_query
        await query.answer()

        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'game_refresh':
            return

        game_id = int(data[1])
        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            with self.db.get_session() as session:
                engine = GameEngine(session)
                field_display = engine.render_field(game_id)
                actions = engine.get_available_actions(game_id, game_user.id)

            keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

            await query.edit_message_text(
                field_display,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )

        except Exception as e:
            logger.error(f"Ошибка при обновлении игры: {e}")
            await query.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех текстовых сообщений"""
        user_message = update.message.text
        user = update.effective_user

        logger.info(f"Сообщение от {user.id} (@{user.username}): {user_message}")

        try:
            # Сохраняем пользователя в базу данных
            self.db.save_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )

            # Сохраняем сообщение в базу данных
            self.db.save_message(
                telegram_user_id=user.id,
                message_text=user_message,
                username=user.username
            )

            logger.info(f"Сообщение от пользователя {user.id} сохранено в БД")

            # Проверяем, есть ли у пользователя игровой профиль, и создаем его при необходимости
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                # Автоматически создаем игровой профиль при первом сообщении
                game_user, created = self.db.get_or_create_game_user(
                    telegram_id=user.id,
                    name=user.first_name or user.username or f"User_{user.id}",
                    initial_balance=self.initial_balance
                )
                logger.info(f"Создан игровой профиль для пользователя {user.id}")

            # Обработка специальных текстовых команд
            if user_message.lower() in ['играть', 'play', 'start game']:
                # Пользователь написал "Играть" вместо команды /play
                response = (
                    f"🎮 Добро пожаловать в игру, {game_user.name}!\n\n"
                    f"💰 Ваш баланс: ${game_user.balance}\n"
                    f"🏆 Побед: {game_user.wins}\n"
                    f"💔 Поражений: {game_user.losses}\n\n"
                    "Используйте /profile для просмотра профиля!"
                )
            else:
                # Формируем стандартный ответ с упоминанием username
                username_display = f"@{user.username}" if user.username else user.first_name or "пользователь"
                response = f"{username_display}, я сохранила твое сообщение!\n\n{self.default_response}"

            await update.message.reply_text(
                response,
                parse_mode=self.parse_mode
            )
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения: {e}")
            # Отправляем стандартный ответ даже если не удалось сохранить
            await update.message.reply_text(
                self.default_response,
                parse_mode=self.parse_mode
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка при обработке обновления: {context.error}")

    def run(self):
        """Запуск бота"""
        logger.info("Запуск бота...")

        # Создание приложения
        application = Application.builder().token(self.bot_token).build()

        # Регистрация обработчиков команд
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("play", self.play_command))
        application.add_handler(CommandHandler("profile", self.profile_command))
        application.add_handler(CommandHandler("shop", self.shop_command))
        application.add_handler(CommandHandler("search", self.search_command))
        application.add_handler(CommandHandler("users", self.users_command))

        # Игровые команды
        application.add_handler(CommandHandler("challenge", self.challenge_command))
        application.add_handler(CommandHandler("accept", self.accept_command))
        application.add_handler(CommandHandler("game", self.game_command))
        application.add_handler(CommandHandler("mygames", self.mygames_command))

        # Регистрация обработчиков callback (порядок важен для правильной маршрутизации)
        application.add_handler(CallbackQueryHandler(self.buy_unit_callback, pattern=r'^buy_unit:'))
        application.add_handler(CallbackQueryHandler(self.confirm_buy_callback, pattern=r'^confirm_buy:'))
        application.add_handler(CallbackQueryHandler(self.back_to_shop_callback, pattern=r'^back_to_shop$'))
        application.add_handler(CallbackQueryHandler(self.show_profile_callback, pattern=r'^show_profile$'))
        application.add_handler(CallbackQueryHandler(self.search_pagination_callback, pattern=r'^search:'))
        application.add_handler(CallbackQueryHandler(self.users_pagination_callback, pattern=r'^users:'))
        application.add_handler(CallbackQueryHandler(self.user_messages_callback, pattern=r'^user_msgs:'))

        # Игровые callback обработчики
        application.add_handler(CallbackQueryHandler(self.game_unit_callback, pattern=r'^game_unit:'))
        application.add_handler(CallbackQueryHandler(self.game_move_callback, pattern=r'^game_move:'))
        application.add_handler(CallbackQueryHandler(self.game_attack_callback, pattern=r'^game_attack:'))
        application.add_handler(CallbackQueryHandler(self.game_refresh_callback, pattern=r'^game_refresh:'))

        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Регистрация обработчика ошибок
        application.add_error_handler(self.error_handler)

        # Запуск бота
        logger.info("Бот запущен и ожидает сообщения...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Главная функция"""
    try:
        bot = SimpleBot()
        bot.run()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise


if __name__ == '__main__':
    main()
