#!/usr/bin/env python3
"""
Простой Telegram бот, который отвечает на все сообщения стандартной фразой из конфига.
Сохраняет все сообщения и пользователей в PostgreSQL.
"""

import json
import logging
import os
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from db import Database
from db.models import GameUser, Unit, UnitCustomIcon
from decimal import Decimal
from game_engine import GameEngine, coords_to_chess, chess_to_coords
from field_renderer import FieldRenderer
import io


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
        self.version = self.load_version()

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

    def load_version(self):
        """Загрузка версии из файла VERSION"""
        try:
            with open('VERSION', 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("Файл VERSION не найден, используется версия по умолчанию")
            return "unknown"

    def check_version_changed(self):
        """Проверка, изменилась ли версия с прошлого запуска"""
        try:
            with open('.last_version', 'r', encoding='utf-8') as f:
                last_version = f.read().strip()
                return last_version != self.version
        except FileNotFoundError:
            # Первый запуск - версия "изменилась"
            return True

    def save_current_version(self):
        """Сохранение текущей версии"""
        try:
            with open('.last_version', 'w', encoding='utf-8') as f:
                f.write(self.version)
            logger.info(f"Версия {self.version} сохранена")
        except Exception as e:
            logger.error(f"Ошибка при сохранении версии: {e}")

    async def notify_all_users_about_update(self, application):
        """Отправка уведомления всем пользователям о новой версии"""
        try:
            # Получаем всех игровых пользователей
            game_users = self.db.get_all_game_users()

            if not game_users:
                logger.info("Нет зарегистрированных пользователей для уведомления")
                return

            notification_text = (
                f"🔄 <b>Бот обновлен!</b>\n\n"
                f"🤖 Новая версия: <code>{self.version}</code>\n\n"
                f"✨ Что нового:\n"
                f"• Исправления ошибок\n"
                f"• Улучшения производительности\n"
                f"• Новые функции\n\n"
                f"Используйте /help для просмотра доступных команд."
            )

            success_count = 0
            fail_count = 0

            for user in game_users:
                if user.telegram_id:
                    try:
                        await application.bot.send_message(
                            chat_id=user.telegram_id,
                            text=notification_text,
                            parse_mode=self.parse_mode
                        )
                        success_count += 1
                        logger.info(f"Уведомление отправлено пользователю {user.telegram_id}")
                    except Exception as e:
                        fail_count += 1
                        logger.warning(f"Не удалось отправить уведомление пользователю {user.telegram_id}: {e}")

            logger.info(f"Уведомления отправлены: успешно={success_count}, ошибок={fail_count}")

        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений: {e}")

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
            "/version - Показать версию бота\n"
            "/play - Начать игру (инициализация игрового профиля)\n"
            "/profile - Посмотреть свой игровой профиль\n"
            "/shop - Магазин юнитов (покупка армии)\n\n"
            "<b>Игровые команды:</b>\n"
            "/challenge &lt;username&gt; - Вызвать игрока на бой\n"
            "/accept - Принять вызов на бой\n"
            "/game - Показать текущую игру\n"
            "/activegames - Просмотр активных игр\n"
            "/mygames - История игр\n\n"
            "<b>Другое:</b>\n"
            "/search &lt;username&gt; - Поиск сообщений пользователя\n"
            "/users - Просмотр всех пользователей"
        )
        await update.message.reply_text(help_text, parse_mode=self.parse_mode)
        logger.info(f"Команда /help от пользователя {update.effective_user.id}")

    async def version_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /version"""
        version_text = (
            f"🤖 <b>Версия бота:</b> {self.version}\n\n"
            f"Эта версия была собрана: {self.version}"
        )
        await update.message.reply_text(version_text, parse_mode=self.parse_mode)
        logger.info(f"Команда /version от пользователя {update.effective_user.id}")

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
                # Фильтруем юнитов с количеством > 0
                active_units = [u for u in user_units if u.count > 0]
                if active_units:
                    units_text = "\n\n🔰 Ваши юниты:\n"
                    for user_unit in active_units:
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

        # Проверка игрового профиля
        game_user = self.db.get_game_user(user.id)
        if not game_user:
            await update.message.reply_text(
                "❌ У вас еще нет игрового профиля. Используйте /play",
                parse_mode=self.parse_mode
            )
            return

        # Если не указан username, показываем список случайных пользователей
        if not context.args:
            try:
                # Получаем случайных пользователей (исключая текущего)
                random_users = self.db.get_random_game_users(limit=10, exclude_telegram_id=user.id)

                if not random_users:
                    await update.message.reply_text(
                        "❌ Нет доступных игроков для вызова.\n"
                        "Или используйте: /challenge username",
                        parse_mode=self.parse_mode
                    )
                    return

                # Формируем сообщение со списком пользователей
                response = "⚔️ <b>Выберите противника для боя:</b>\n\n"

                # Создаем кнопки для каждого пользователя
                keyboard = []
                for i, opponent in enumerate(random_users, 1):
                    win_rate = 0
                    if opponent.wins + opponent.losses > 0:
                        win_rate = (opponent.wins / (opponent.wins + opponent.losses)) * 100

                    # Экранируем HTML-символы в имени
                    safe_name = html.escape(opponent.name)

                    response += (
                        f"{i}. {safe_name}\n"
                        f"   🏆 {opponent.wins} | 💔 {opponent.losses} | "
                        f"📊 {win_rate:.0f}% побед\n\n"
                    )

                    keyboard.append([
                        InlineKeyboardButton(
                            f"⚔️ Вызвать {opponent.name}",
                            callback_data=f"challenge_user:{opponent.telegram_id}"
                        )
                    ])

                await update.message.reply_text(
                    response,
                    parse_mode=self.parse_mode,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            except Exception as e:
                logger.error(f"Ошибка при получении списка игроков: {e}")
                await update.message.reply_text(
                    "❌ Произошла ошибка при получении списка игроков",
                    parse_mode=self.parse_mode
                )
                return

        opponent_username = context.args[0].lstrip('@')

        try:
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
                # Показать поле обоим игрокам
                with self.db.get_session() as session:
                    engine = GameEngine(session)
                    actions = engine.get_available_actions(active_game.id, game_user.id)

                # Отправить уведомление и поле player2 (тому, кто принял)
                keyboard = self._create_game_keyboard(active_game.id, game_user.id, actions)
                await self._send_field_image(
                    chat_id=update.effective_chat.id,
                    game_id=active_game.id,
                    caption=f"✅ {message}",
                    context=context,
                    keyboard=keyboard
                )

                # Отправить уведомление и поле player1 (тому, кто создал игру)
                player1_id = active_game.player1_id if active_game.player2_id == game_user.id else active_game.player2_id
                player1 = self.db.query(GameUser).filter_by(id=player1_id).first()

                if player1 and player1.telegram_id:
                    try:
                        player1_actions = engine.get_available_actions(active_game.id, player1_id)
                        player1_keyboard = self._create_game_keyboard(active_game.id, player1_id, player1_actions)

                        await self._send_field_image(
                            chat_id=player1.telegram_id,
                            game_id=active_game.id,
                            caption="🎮 Игра началась!",
                            context=context,
                            keyboard=player1_keyboard
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления player1: {e}")
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
                actions = engine.get_available_actions(active_game.id, game_user.id)

            logger.info(f"Actions для игрока {game_user.id}: {actions}")
            keyboard = self._create_game_keyboard(active_game.id, game_user.id, actions)
            logger.info(f"Клавиатура после _create_game_keyboard: {len(keyboard)} кнопок")

            await self._send_field_image(
                chat_id=update.effective_chat.id,
                game_id=active_game.id,
                caption="",
                context=context,
                keyboard=keyboard
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
                opponent = self.db.get_game_user_by_id(opponent_id) if opponent_id else None
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

    async def activegames_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /activegames - просмотр активных игр"""
        user = update.effective_user
        logger.info(f"Команда /activegames от пользователя {user.id}")

        try:
            # Проверка игрового профиля
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await update.message.reply_text(
                    "❌ У вас еще нет игрового профиля. Используйте /play",
                    parse_mode=self.parse_mode
                )
                return

            # Получение активных игр
            active_games = self.db.get_active_games(user.id)

            if not active_games:
                await update.message.reply_text(
                    "🎮 У вас нет активных игр.\nИспользуйте /challenge для вызова на бой!",
                    parse_mode=self.parse_mode
                )
                return

            response = "🎮 <b>Ваши активные игры:</b>\n\n"
            keyboard = []

            for game in active_games:
                opponent_id = game.player2_id if game.player1_id == game_user.id else game.player1_id
                opponent = self.db.get_game_user_by_id(opponent_id) if opponent_id else None
                opponent_name = opponent.name if opponent else "Unknown"

                status_emoji = {"waiting": "⏳", "in_progress": "⚔️"}
                status_text = status_emoji.get(game.status.value, "❓")

                # Определить статус игры
                turn_info = ""
                if game.status.value == "waiting":
                    # Определяем, кто создал игру (player1) и кто должен принять (player2)
                    if game.player1_id == game_user.id:
                        turn_info = " - Ожидание принятия"
                    else:
                        turn_info = " - Нужно принять вызов"
                elif game.status.value == "in_progress":
                    if game.current_player_id == game_user.id:
                        turn_info = " - 🟢 Ваш ход"
                    else:
                        turn_info = " - 🔴 Ход противника"

                response += f"{status_text} Игра #{game.id} vs {opponent_name}{turn_info}\n"

                # Создать кнопку для каждой игры
                keyboard.append([
                    InlineKeyboardButton(
                        f"📋 Игра #{game.id} vs {opponent_name}",
                        callback_data=f"show_game:{game.id}"
                    )
                ])

            await update.message.reply_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Ошибка при получении активных игр: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка: {e}",
                parse_mode=self.parse_mode
            )

    async def _send_field_image(self, chat_id: int, game_id: int, caption: str, context: ContextTypes.DEFAULT_TYPE, keyboard=None):
        """
        Отправить изображение игрового поля

        Args:
            chat_id: ID чата
            game_id: ID игры
            caption: Подпись к изображению
            context: Контекст бота
            keyboard: Клавиатура (опционально)
        """
        with self.db.get_session() as session:
            renderer = FieldRenderer(session)
            image_bytes = renderer.render_field(game_id)

            if image_bytes:
                # Отправить изображение
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=io.BytesIO(image_bytes),
                    caption=caption,
                    parse_mode=self.parse_mode,
                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                )
            else:
                # Fallback на текстовое отображение если не удалось создать изображение
                with self.db.get_session() as session:
                    engine = GameEngine(session)
                    field_display = engine.render_field(game_id)
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"{caption}\n\n{field_display}",
                        parse_mode=self.parse_mode,
                        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                    )

    async def _handle_game_completion(self, query, game, attack_message: str, context):
        """
        Обработка завершения игры - отправка результатов обоим игрокам и очистка кнопок

        Args:
            query: CallbackQuery объект
            game: Объект игры
            attack_message: Сообщение об атаке
            context: Контекст бота
        """
        try:
            # Получить информацию об игроках
            winner = self.db.get_game_user_by_id(game.winner_id)
            loser_id = game.player1_id if game.winner_id == game.player2_id else game.player2_id
            loser = self.db.get_game_user_by_id(loser_id)

            # Собрать детальную информацию о результатах
            result_message = self._build_game_result_message(game, winner, loser, attack_message)

            # Обновить поле атакующего (убрать кнопки)
            await self._edit_field(query, game.id, result_message, keyboard=[])

            # Отправить результаты противнику
            opponent_id = loser_id if query.from_user.id == winner.telegram_id else winner.telegram_id
            opponent = self.db.get_game_user_by_id(loser_id if opponent_id == loser.telegram_id else game.winner_id)

            if opponent and opponent.telegram_id:
                try:
                    await context.bot.send_message(
                        chat_id=opponent.telegram_id,
                        text=result_message,
                        parse_mode=self.parse_mode
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке результатов противнику: {e}")

        except Exception as e:
            logger.error(f"Ошибка при обработке завершения игры: {e}")
            raise

    def _build_game_result_message(self, game, winner, loser, attack_message: str) -> str:
        """
        Формирование сообщения с результатами игры

        Args:
            game: Объект игры
            winner: Победитель
            loser: Проигравший
            attack_message: Сообщение об атаке

        Returns:
            str: Форматированное сообщение с результатами
        """
        # Основное сообщение
        result = f"{attack_message}\n\n"
        result += "🏆 " + "=" * 30 + "\n"
        result += f"          ИГРА ЗАВЕРШЕНА!\n"
        result += "=" * 30 + "\n\n"

        # Информация о победителе и проигравшем
        result += f"👑 <b>Победитель:</b> {html.escape(winner.name)}\n"
        result += f"💔 <b>Проигравший:</b> {html.escape(loser.name)}\n\n"

        # Статистика победителя
        result += f"📊 <b>Статистика {html.escape(winner.name)}:</b>\n"
        result += f"   💰 Баланс: ${winner.balance}\n"
        result += f"   🏆 Побед: {winner.wins}\n"
        result += f"   💔 Поражений: {winner.losses}\n\n"

        # Статистика проигравшего
        result += f"📊 <b>Статистика {html.escape(loser.name)}:</b>\n"
        result += f"   💰 Баланс: ${loser.balance}\n"
        result += f"   🏆 Побед: {loser.wins}\n"
        result += f"   💔 Поражений: {loser.losses}\n\n"

        # Информация об игре
        if game.started_at and game.completed_at:
            duration = game.completed_at - game.started_at
            minutes = int(duration.total_seconds() / 60)
            result += f"⏱️ <b>Длительность игры:</b> {minutes} мин.\n"

        result += f"🎮 <b>ID игры:</b> #{game.id}\n"

        return result

    def _create_game_keyboard(self, game_id: int, player_id: int, actions: dict) -> list:
        """Создание клавиатуры для игровых действий"""
        keyboard = []

        if actions.get("action") == "accept":
            keyboard.append([InlineKeyboardButton("✅ Принять игру", callback_data=f"game_accept:{game_id}")])
        elif actions.get("action") == "wait":
            # Не возвращаем пустой список, просто не добавляем кнопки действий
            pass
        elif actions.get("action") == "play":
            # Кнопки для выбора юнита
            units = actions.get("units", [])
            for unit in units[:5]:  # Показываем первые 5 юнитов
                unit_name = unit.get("unit_name", "Unit")
                unit_id = unit.get("unit_id")
                pos = unit.get("position", (0, 0))
                chess_pos = coords_to_chess(pos[0], pos[1])
                keyboard.append([
                    InlineKeyboardButton(
                        f"⚔️ {unit_name} {chess_pos}",
                        callback_data=f"game_unit:{game_id}:{unit_id}"
                    )
                ])

        # Не добавляем кнопки "Обновить" и "Выйти из схватки" когда игра завершена
        if actions.get("action") != "none":
            keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data=f"game_refresh:{game_id}")])
            keyboard.append([InlineKeyboardButton("🏃 Выйти из схватки", callback_data=f"surrender:{game_id}")])
        return keyboard

    async def _edit_message_universal(self, query, text: str, reply_markup=None, parse_mode=None):
        """
        Универсальное редактирование сообщения (текст или caption для фото)

        Args:
            query: CallbackQuery объект
            text: Текст или caption для редактирования
            reply_markup: Клавиатура
            parse_mode: Режим парсинга (HTML/Markdown)
        """
        try:
            # Проверяем, есть ли фото в сообщении
            if query.message.photo:
                # Если есть фото, редактируем caption
                await query.edit_message_caption(
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                # Если нет фото, редактируем текст
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            raise

    async def _edit_field(self, query, game_id: int, caption: str, keyboard: list = None):
        """
        Редактировать сообщение с игровым полем (PNG или текст)

        Args:
            query: CallbackQuery объект
            game_id: ID игры
            caption: Подпись/текст для поля
            keyboard: Клавиатура (опционально)
        """
        from telegram import InputMediaPhoto

        with self.db.get_session() as session:
            renderer = FieldRenderer(session)
            image_bytes = renderer.render_field(game_id)

            # Проверяем, было ли сообщение с фото
            has_photo = bool(query.message.photo)

            if image_bytes and has_photo:
                # Редактируем фото и caption
                try:
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=io.BytesIO(image_bytes), caption=caption, parse_mode=self.parse_mode),
                        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                    )
                except Exception as e:
                    logger.error(f"Ошибка при редактировании медиа: {e}")
                    # Fallback: редактируем только caption
                    await query.edit_message_caption(
                        caption=caption,
                        parse_mode=self.parse_mode,
                        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                    )
            else:
                # Текстовое отображение
                with self.db.get_session() as session:
                    engine = GameEngine(session)
                    field_display = engine.render_field(game_id)
                    await query.edit_message_text(
                        text=f"{caption}\n\n{field_display}",
                        parse_mode=self.parse_mode,
                        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                    )


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
                await self._edit_message_universal(query, "❌ Игровой профиль не найден", parse_mode=self.parse_mode)
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
                await self._edit_message_universal(query, "❌ Юнит не найден", parse_mode=self.parse_mode)
                return

            # Получаем позицию в шахматной нотации
            pos = unit_data['position']
            chess_pos = coords_to_chess(pos[0], pos[1])

            response = f"⚔️ <b>{unit_data['unit_name']}</b>\n"
            response += f"Позиция: {chess_pos}\n\n"

            keyboard = []

            # Кнопки для движения
            if unit_data.get("can_move"):
                keyboard.append([InlineKeyboardButton("🏃 Переместить", callback_data=f"game_move:{game_id}:{unit_id}")])

            # Кнопки для атаки
            targets = unit_data.get("targets", [])
            if targets:
                response += "🎯 <b>Доступные цели:</b>\n"
                for target in targets[:3]:  # Показываем первые 3 цели
                    target_pos = coords_to_chess(target['position'][0], target['position'][1])
                    response += f"- {target['unit_name']} {target_pos}\n"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"⚔️ Атаковать {target['unit_name']}",
                            callback_data=f"game_attack:{game_id}:{unit_id}:{target['unit_id']}"
                        )
                    ])

            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=f"game_refresh:{game_id}")])
            keyboard.append([InlineKeyboardButton("🏃 Выйти из схватки", callback_data=f"surrender:{game_id}")])

            await self._edit_message_universal(
                query,
                response,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=self.parse_mode
            )

        except Exception as e:
            logger.error(f"Ошибка при выборе юнита: {e}")
            await self._edit_message_universal(query, f"❌ Ошибка: {e}", parse_mode=self.parse_mode)

    async def game_move_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для перемещения юнита"""
        query = update.callback_query
        await query.answer()

        data = query.data.split(':')
        logger.info(f"game_move_callback: data={query.data}, len={len(data)}")

        if len(data) < 3:
            logger.warning(f"game_move_callback: недостаточно данных, data={data}")
            return

        game_id = int(data[1])
        unit_id = int(data[2])

        # Если есть координаты
        if len(data) == 5:
            logger.info(f"game_move_callback: перемещение юнита {unit_id} в игре {game_id}")
            target_x = int(data[3])
            target_y = int(data[4])
            user = update.effective_user

            try:
                game_user = self.db.get_game_user(user.id)
                logger.info(f"game_move: game_user={game_user.id if game_user else None}, target=({target_x}, {target_y})")
                with self.db.get_session() as session:
                    engine = GameEngine(session)
                    success, message, turn_switched = engine.move_unit(game_id, game_user.id, unit_id, target_x, target_y)
                    logger.info(f"game_move: success={success}, message={message}, turn_switched={turn_switched}")

                    if success:
                        logger.info(f"game_move: перемещение успешно, обновляем поле")
                        actions = engine.get_available_actions(game_id, game_user.id)
                        keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

                        # Используем _edit_field для обновления поля с PNG
                        await self._edit_field(query, game_id, f"✅ {message}", keyboard)

                        # Если ход сменился, отправить уведомление противнику
                        if turn_switched:
                            game = self.db.get_game_by_id(game_id)
                            opponent_id = game.player2_id if game.player1_id == game_user.id else game.player1_id
                            opponent = self.db.get_game_user_by_id(opponent_id)

                            if opponent and opponent.telegram_id:
                                try:
                                    opponent_actions = engine.get_available_actions(game_id, opponent_id)
                                    opponent_keyboard = self._create_game_keyboard(game_id, opponent_id, opponent_actions)

                                    # Отправляем PNG поле противнику
                                    await self._send_field_image(
                                        chat_id=opponent.telegram_id,
                                        game_id=game_id,
                                        caption="🎮 Теперь ваш ход!",
                                        context=context,
                                        keyboard=opponent_keyboard
                                    )
                                except Exception as e:
                                    logger.error(f"Ошибка при отправке уведомления противнику: {e}")
                    else:
                        logger.warning(f"game_move: перемещение не удалось: {message}")
                        await query.answer(f"❌ {message}", show_alert=True)

            except Exception as e:
                logger.error(f"Ошибка при перемещении: {e}", exc_info=True)
                await query.answer(f"❌ Ошибка: {e}", show_alert=True)
        else:
            # Показать доступные позиции для перемещения
            try:
                user = update.effective_user
                game_user = self.db.get_game_user(user.id)

                with self.db.get_session() as session:
                    engine = GameEngine(session)

                    # Получить доступные клетки для перемещения
                    available_cells = engine.get_available_movement_cells(game_id, unit_id)

                    if not available_cells:
                        await self._edit_message_universal(
                            query,
                            "❌ Нет доступных позиций для перемещения!\n"
                            "Юнит заблокирован или уже походил.",
                            parse_mode=self.parse_mode
                        )
                        return

                    # Создать кнопки для каждой доступной позиции
                    keyboard = []
                    for x, y in available_cells:
                        chess_notation = coords_to_chess(x, y)
                        keyboard.append([
                            InlineKeyboardButton(
                                f"📍 {chess_notation}",
                                callback_data=f"game_move:{game_id}:{unit_id}:{x}:{y}"
                            )
                        ])

                    # Добавить кнопку "Назад"
                    keyboard.append([
                        InlineKeyboardButton("◀️ Назад", callback_data=f"game_unit:{game_id}:{unit_id}")
                    ])
                    keyboard.append([
                        InlineKeyboardButton("🏃 Выйти из схватки", callback_data=f"surrender:{game_id}")
                    ])

                    # Используем _edit_field для показа поля с доступными позициями
                    caption = f"🏃 Выберите позицию для перемещения\n\nДоступно позиций: {len(available_cells)}"
                    await self._edit_field(query, game_id, caption, keyboard)

            except Exception as e:
                logger.error(f"Ошибка при показе доступных позиций: {e}")
                await self._edit_message_universal(
                    query,
                    f"❌ Ошибка при получении доступных позиций: {e}",
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
                success, message, turn_switched = engine.attack(game_id, game_user.id, attacker_id, target_id)

                if success:
                    # Проверить, завершилась ли игра
                    game = self.db.get_game_by_id(game_id)
                    from db.models import GameStatus

                    if game.status == GameStatus.COMPLETED:
                        # Игра завершена - отправить результаты обоим игрокам
                        await self._handle_game_completion(query, game, message, context)
                    else:
                        # Игра продолжается - обновить поле
                        actions = engine.get_available_actions(game_id, game_user.id)
                        keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

                        # Используем _edit_field для обновления поля с PNG
                        await self._edit_field(query, game_id, message, keyboard)

                        # Если ход сменился, отправить уведомление противнику
                        if turn_switched:
                            opponent_id = game.player2_id if game.player1_id == game_user.id else game.player1_id
                            opponent = self.db.get_game_user_by_id(opponent_id)

                            if opponent and opponent.telegram_id:
                                try:
                                    opponent_actions = engine.get_available_actions(game_id, opponent_id)
                                    opponent_keyboard = self._create_game_keyboard(game_id, opponent_id, opponent_actions)

                                    # Отправляем PNG поле противнику
                                    await self._send_field_image(
                                        chat_id=opponent.telegram_id,
                                        game_id=game_id,
                                        caption="🎮 Теперь ваш ход!",
                                        context=context,
                                        keyboard=opponent_keyboard
                                    )
                                except Exception as e:
                                    logger.error(f"Ошибка при отправке уведомления противнику: {e}")
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
                actions = engine.get_available_actions(game_id, game_user.id)

            keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

            # Используем _edit_field для обновления поля (с поддержкой PNG)
            await self._edit_field(query, game_id, "🎮 Игровое поле", keyboard)

        except Exception as e:
            logger.error(f"Ошибка при обновлении игры: {e}")
            await query.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def challenge_user_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для вызова пользователя на бой из списка"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: challenge_user:telegram_id)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'challenge_user':
            return

        opponent_telegram_id = int(data[1])
        user = update.effective_user

        try:
            # Получаем игрового пользователя
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await query.edit_message_text(
                    "❌ Игровой профиль не найден.",
                    parse_mode=self.parse_mode
                )
                return

            # Получаем информацию о противнике
            opponent = self.db.get_game_user(opponent_telegram_id)
            if not opponent:
                await query.edit_message_text(
                    "❌ Игрок не найден.",
                    parse_mode=self.parse_mode
                )
                return

            # Проверка активной игры
            active_game = self.db.get_active_game(user.id)
            if active_game:
                await query.edit_message_text(
                    "❌ У вас уже есть активная игра. Завершите её сначала.",
                    parse_mode=self.parse_mode
                )
                return

            # Создание игры через игровой движок (по имени)
            with self.db.get_session() as session:
                engine = GameEngine(session)
                game, message = engine.create_game(game_user.id, opponent.name)

                # Сохраняем ID игры внутри сессии
                game_id = game.id if game else None

            if game_id:
                safe_opponent_name = html.escape(opponent.name)
                safe_challenger_name = html.escape(game_user.name)
                safe_message = html.escape(message)

                response = (
                    f"✅ {safe_message}\n\n"
                    f"Игра #{game_id} создана!\n"
                    f"Ожидание принятия игроком {safe_opponent_name}"
                )
                await query.edit_message_text(response, parse_mode=self.parse_mode)

                # Отправить уведомление противнику
                try:
                    challenge_keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Принять бой", callback_data=f"accept_challenge:{game_id}")],
                        [InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_challenge:{game_id}")]
                    ])

                    await context.bot.send_message(
                        chat_id=opponent.telegram_id,
                        text=(
                            f"⚔️ <b>Вызов на бой!</b>\n\n"
                            f"Игрок {safe_challenger_name} вызывает вас на бой!\n"
                            f"Игра #{game_id}\n\n"
                            f"Будете сражаться?"
                        ),
                        parse_mode=self.parse_mode,
                        reply_markup=challenge_keyboard
                    )
                    logger.info(f"Уведомление о вызове отправлено игроку {opponent.telegram_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления противнику: {e}")
            else:
                safe_message = html.escape(message)
                response = f"❌ {safe_message}"
                await query.edit_message_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при вызове игрока: {e}")
            await query.edit_message_text(
                f"❌ Произошла ошибка: {e}",
                parse_mode=self.parse_mode
            )

    async def show_game_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для показа деталей игры"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: show_game:game_id)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'show_game':
            return

        game_id = int(data[1])
        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await self._edit_message_universal(query, "❌ Игровой профиль не найден", parse_mode=self.parse_mode)
                return

            game = self.db.get_game_by_id(game_id)
            if not game:
                await self._edit_message_universal(query, "❌ Игра не найдена", parse_mode=self.parse_mode)
                return

            # Проверить, что игрок участвует в игре
            if game.player1_id != game_user.id and game.player2_id != game_user.id:
                await self._edit_message_universal(query, "❌ Вы не участвуете в этой игре", parse_mode=self.parse_mode)
                return

            # Получить информацию об игре
            opponent_id = game.player2_id if game.player1_id == game_user.id else game.player1_id
            opponent = self.db.get_game_user_by_id(opponent_id)
            opponent_name = opponent.name if opponent else "Unknown"

            # Отобразить поле
            with self.db.get_session() as session:
                engine = GameEngine(session)
                actions = engine.get_available_actions(game_id, game_user.id)

            # Создать клавиатуру
            keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

            # Добавить кнопку "Назад к списку игр"
            keyboard.append([
                InlineKeyboardButton("🔙 К списку игр", callback_data="back_to_activegames")
            ])

            # Используем _edit_field для показа поля
            await self._edit_field(query, game_id, "🎮 Игровое поле", keyboard)

        except Exception as e:
            logger.error(f"Ошибка при показе игры: {e}")
            await self._edit_message_universal(query, f"❌ Ошибка: {e}", parse_mode=self.parse_mode)

    async def surrender_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для выхода из игры"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: surrender:game_id)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'surrender':
            return

        game_id = int(data[1])
        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await self._edit_message_universal(query, "❌ Игровой профиль не найден", parse_mode=self.parse_mode)
                return

            # Получить информацию об игре для уведомления
            game = self.db.get_game_by_id(game_id)
            if not game:
                await self._edit_message_universal(query, "❌ Игра не найдена", parse_mode=self.parse_mode)
                return

            opponent_id = game.player2_id if game.player1_id == game_user.id else game.player1_id
            opponent = self.db.get_game_user_by_id(opponent_id)

            # Выполнить surrender через игровой движок
            with self.db.get_session() as session:
                engine = GameEngine(session)
                success, message, opponent_telegram_id = engine.surrender_game(game_id, game_user.id)

            if success:
                response = f"✅ {message}"
                await self._edit_message_universal(query, response, parse_mode=self.parse_mode)

                # Отправить уведомление противнику
                if opponent_telegram_id:
                    try:
                        notification = (
                            f"🏃 Игрок {game_user.name} сбежал из игры #{game_id}!\n"
                            f"Вы победили в этой игре!"
                        )
                        await context.bot.send_message(
                            chat_id=opponent_telegram_id,
                            text=notification,
                            parse_mode=self.parse_mode
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления противнику: {e}")
            else:
                await self._edit_message_universal(query, f"❌ {message}", parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при выходе из игры: {e}")
            await self._edit_message_universal(query, f"❌ Ошибка: {e}", parse_mode=self.parse_mode)

    async def back_to_activegames_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для возврата к списку активных игр"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await query.edit_message_text("❌ Игровой профиль не найден")
                return

            # Получение активных игр
            active_games = self.db.get_active_games(user.id)

            if not active_games:
                await query.edit_message_text(
                    "🎮 У вас нет активных игр.\nИспользуйте /challenge для вызова на бой!",
                    parse_mode=self.parse_mode
                )
                return

            response = "🎮 <b>Ваши активные игры:</b>\n\n"
            keyboard = []

            for game in active_games:
                opponent_id = game.player2_id if game.player1_id == game_user.id else game.player1_id
                opponent = self.db.get_game_user_by_id(opponent_id) if opponent_id else None
                opponent_name = opponent.name if opponent else "Unknown"

                status_emoji = {"waiting": "⏳", "in_progress": "⚔️"}
                status_text = status_emoji.get(game.status.value, "❓")

                # Определить статус игры
                turn_info = ""
                if game.status.value == "waiting":
                    # Определяем, кто создал игру (player1) и кто должен принять (player2)
                    if game.player1_id == game_user.id:
                        turn_info = " - Ожидание принятия"
                    else:
                        turn_info = " - Нужно принять вызов"
                elif game.status.value == "in_progress":
                    if game.current_player_id == game_user.id:
                        turn_info = " - 🟢 Ваш ход"
                    else:
                        turn_info = " - 🔴 Ход противника"

                response += f"{status_text} Игра #{game.id} vs {opponent_name}{turn_info}\n"

                # Создать кнопку для каждой игры
                keyboard.append([
                    InlineKeyboardButton(
                        f"📋 Игра #{game.id} vs {opponent_name}",
                        callback_data=f"show_game:{game.id}"
                    )
                ])

            await self._edit_message_universal(
                query,
                response,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=self.parse_mode
            )

        except Exception as e:
            logger.error(f"Ошибка при возврате к списку игр: {e}")
            await self._edit_message_universal(query, f"❌ Ошибка: {e}", parse_mode=self.parse_mode)

    async def accept_challenge_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для принятия вызова на бой"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: accept_challenge:game_id)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'accept_challenge':
            return

        game_id = int(data[1])
        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await self._edit_message_universal(query, "❌ Игровой профиль не найден", parse_mode=self.parse_mode)
                return

            game = self.db.get_game_by_id(game_id)
            if not game:
                await self._edit_message_universal(query, "❌ Игра не найдена", parse_mode=self.parse_mode)
                return

            # Принятие игры через игровой движок
            with self.db.get_session() as session:
                engine = GameEngine(session)
                success, message = engine.accept_game(game_id, game_user.id)

            if success:
                # Показать поле принявшему игрок
                with self.db.get_session() as session:
                    engine = GameEngine(session)
                    actions = engine.get_available_actions(game_id, game_user.id)

                keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

                # Используем _edit_field для показа поля
                await self._edit_field(query, game_id, f"✅ {message}", keyboard)

                # Отправить уведомление и поле игроку, создавшему вызов
                opponent_id = game.player1_id if game.player2_id == game_user.id else game.player2_id
                opponent = self.db.get_game_user_by_id(opponent_id)

                if opponent and opponent.telegram_id:
                    try:
                        opponent_actions = engine.get_available_actions(game_id, opponent_id)
                        opponent_keyboard = self._create_game_keyboard(game_id, opponent_id, opponent_answers)

                        # Отправляем PNG поле противнику
                        await self._send_field_image(
                            chat_id=opponent.telegram_id,
                            game_id=game_id,
                            caption="🎮 Игра началась!",
                            context=context,
                            keyboard=opponent_keyboard
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления о начале игры: {e}")
            else:
                await self._edit_message_universal(query, f"❌ {message}", parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при принятии вызова: {e}")
            await self._edit_message_universal(query, f"❌ Ошибка: {e}", parse_mode=self.parse_mode)

    async def decline_challenge_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для отклонения вызова на бой"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: decline_challenge:game_id)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'decline_challenge':
            return

        game_id = int(data[1])
        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await self._edit_message_universal(query, "❌ Игровой профиль не найден", parse_mode=self.parse_mode)
                return

            game = self.db.get_game_by_id(game_id)
            if not game:
                await self._edit_message_universal(query, "❌ Игра не найдена", parse_mode=self.parse_mode)
                return

            # Отклонение вызова - удаляем игру
            with self.db.get_session() as session:
                engine = GameEngine(session)
                success, msg, opponent_telegram_id = engine.surrender_game(game_id, game_user.id)

            if success:
                await self._edit_message_universal(
                    query,
                    "❌ Вы отклонили вызов на бой",
                    parse_mode=self.parse_mode
                )

                # Уведомить вызывавшего игрока
                opponent_id = game.player1_id if game.player2_id == game_user.id else game.player2_id
                opponent = self.db.get_game_user_by_id(opponent_id)

                if opponent and opponent.telegram_id:
                    try:
                        await context.bot.send_message(
                            chat_id=opponent.telegram_id,
                            text=f"❌ Игрок {html.escape(game_user.name)} отклонил ваш вызов на бой (Игра #{game_id})",
                            parse_mode=self.parse_mode
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления об отклонении: {e}")
            else:
                await self._edit_message_universal(query, f"❌ Ошибка: {msg}", parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при отклонении вызова: {e}")
            await self._edit_message_universal(query, f"❌ Ошибка: {e}", parse_mode=self.parse_mode)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех текстовых сообщений"""
        user_message = update.message.text
        user = update.effective_user

        logger.info(f"Сообщение от {user.id} (@{user.username}): {user_message}")

        try:
            # === ADMIN FUNCTIONS ===
            # Обработка изменения эмодзи юнита
            if 'editing_icon_unit_id' in context.user_data and self.is_admin(user.username):
                unit_id = context.user_data['editing_icon_unit_id']
                unit_name = context.user_data.get('editing_icon_unit_name', 'Юнит')
                new_icon = user_message.strip()

                logger.info(f"Получен новый эмодзи '{new_icon}' для юнита {unit_name} (ID: {unit_id})")

                with self.db.get_session() as session:
                    unit = session.query(Unit).filter_by(id=unit_id).first()
                    if not unit:
                        await update.message.reply_text("❌ Юнит не найден.")
                        del context.user_data['editing_icon_unit_id']
                        if 'editing_icon_unit_name' in context.user_data:
                            del context.user_data['editing_icon_unit_name']
                        return

                    # Проверяем, существует ли уже кастомная иконка
                    custom_icon = session.query(UnitCustomIcon).filter_by(unit_id=unit.id).first()

                    old_icon = custom_icon.custom_icon if custom_icon else unit.icon

                    if custom_icon:
                        # Обновляем существующую иконку
                        custom_icon.custom_icon = new_icon
                        logger.info(f"Обновлена кастомная иконка для {unit.name}: {old_icon} → {new_icon}")
                    else:
                        # Создаем новую кастомную иконку
                        custom_icon = UnitCustomIcon(
                            unit_id=unit.id,
                            custom_icon=new_icon
                        )
                        session.add(custom_icon)
                        logger.info(f"Создана новая кастомная иконка для {unit.name}: {unit.icon} → {new_icon}")

                    session.commit()

                await update.message.reply_text(
                    f"✅ <b>Эмодзи обновлен!</b>\n\n"
                    f"🎮 Юнит: <b>{unit.name}</b>\n"
                    f"Старый эмодзи: {old_icon}\n"
                    f"Новый эмодзи: {new_icon}\n\n"
                    f"Изменения вступят в силу в новых играх.",
                    parse_mode='HTML'
                )

                del context.user_data['editing_icon_unit_id']
                if 'editing_icon_unit_name' in context.user_data:
                    del context.user_data['editing_icon_unit_name']

                logger.info(f"Эмодзи для {unit.name} успешно обновлен на {new_icon}")
                return

            # Обработка создания нового юнита
            if 'creating_unit' in context.user_data and self.is_admin(user.username):
                unit_data = context.user_data['creating_unit']
                step = unit_data['step']

                steps_info = {
                    'name': ('icon', 'Шаг 2/10: Введите эмодзи для юнита:'),
                    'icon': ('price', 'Шаг 3/10: Введите цену юнита:'),
                    'price': ('damage', 'Шаг 4/10: Введите урон юнита:'),
                    'damage': ('defense', 'Шаг 5/10: Введите защиту юнита:'),
                    'defense': ('range', 'Шаг 6/10: Введите дальность атаки:'),
                    'range': ('health', 'Шаг 7/10: Введите здоровье юнита:'),
                    'health': ('speed', 'Шаг 8/10: Введите скорость юнита:'),
                    'speed': ('luck', 'Шаг 9/10: Введите удачу (0.0-1.0):'),
                    'luck': ('crit_chance', 'Шаг 10/10: Введите шанс крита (0.0-1.0):'),
                    'crit_chance': ('complete', None)
                }

                # Сохраняем текущее значение
                unit_data[step] = user_message.strip()

                # Переходим к следующему шагу
                next_step, next_message = steps_info.get(step, ('complete', None))

                if next_step == 'complete':
                    # Создаем юнита
                    try:
                        with self.db.get_session() as session:
                            new_unit = Unit(
                                name=unit_data['name'],
                                icon=unit_data['icon'],
                                price=Decimal(unit_data['price']),
                                damage=int(unit_data['damage']),
                                defense=int(unit_data['defense']),
                                range=int(unit_data['range']),
                                health=int(unit_data['health']),
                                speed=int(unit_data['speed']),
                                luck=Decimal(unit_data['luck']),
                                crit_chance=Decimal(unit_data['crit_chance'])
                            )
                            session.add(new_unit)
                            session.commit()

                        await update.message.reply_text(
                            f"Новый тип юнита '{unit_data['name']}' успешно создан!\n\n"
                            f"Характеристики:\n"
                            f"Эмодзи: {unit_data['icon']}\n"
                            f"Цена: ${unit_data['price']}\n"
                            f"Урон: {unit_data['damage']}\n"
                            f"Защита: {unit_data['defense']}\n"
                            f"Дальность: {unit_data['range']}\n"
                            f"Здоровье: {unit_data['health']}\n"
                            f"Скорость: {unit_data['speed']}\n"
                            f"Удача: {unit_data['luck']}\n"
                            f"Шанс крита: {unit_data['crit_chance']}"
                        )
                        del context.user_data['creating_unit']
                        return
                    except Exception as e:
                        await update.message.reply_text(
                            f"Ошибка при создании юнита: {e}\n"
                            "Проверьте правильность введенных данных."
                        )
                        del context.user_data['creating_unit']
                        return
                else:
                    unit_data['step'] = next_step
                    await update.message.reply_text(next_message)
                    return

            # === REGULAR USER PROCESSING ===
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
                await update.message.reply_text(
                    response,
                    parse_mode=self.parse_mode
                )
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")

    # === ADMIN COMMANDS ===

    def is_admin(self, username: str) -> bool:
        """Проверка, является ли пользователь администратором"""
        ADMIN_USERNAMES = ['okarien']
        # Убираем @ если есть
        clean_username = username.lstrip('@') if username else None
        return clean_username in ADMIN_USERNAMES

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Панель администратора"""
        username = update.effective_user.username

        if not self.is_admin(username):
            await update.message.reply_text("У вас нет доступа к этой команде.")
            return

        keyboard = [
            [InlineKeyboardButton("Настроить эмодзи юнитов", callback_data='admin_unit_icons')],
            [InlineKeyboardButton("Создать новый тип юнита", callback_data='admin_create_unit')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Панель администратора:",
            reply_markup=reply_markup
        )

    async def admin_unit_icons_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список юнитов для настройки эмодзи"""
        query = update.callback_query
        await query.answer()

        username = update.effective_user.username
        if not self.is_admin(username):
            await query.edit_message_text("У вас нет доступа к этой функции.")
            return

        with self.db.get_session() as session:
            units = session.query(Unit).all()

            if not units:
                await query.edit_message_text("Нет доступных юнитов.")
                return

            keyboard = []
            for unit in units:
                custom_icon = session.query(UnitCustomIcon).filter_by(unit_id=unit.id).first()
                current_icon = custom_icon.custom_icon if custom_icon else unit.icon
                keyboard.append([
                    InlineKeyboardButton(
                        f"{current_icon} {unit.name}",
                        callback_data=f'admin_edit_icon:{unit.id}'
                    )
                ])

            keyboard.append([InlineKeyboardButton("Назад", callback_data='admin_back')])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "Выберите юнита для изменения эмодзи:",
                reply_markup=reply_markup
            )

    async def admin_edit_icon_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запросить новый эмодзи для юнита"""
        query = update.callback_query
        await query.answer()

        username = update.effective_user.username
        logger.info(f"Admin edit icon callback от {username}")

        if not self.is_admin(username):
            await query.edit_message_text("У вас нет доступа к этой функции.")
            return

        unit_id = int(query.data.split(':')[1])
        logger.info(f"Редактирование иконки для юнита ID: {unit_id}")

        unit_name = None
        current_icon = None

        with self.db.get_session() as session:
            unit = session.query(Unit).filter_by(id=unit_id).first()
            if not unit:
                await query.edit_message_text("Юнит не найден.")
                return

            unit_name = unit.name
            custom_icon = session.query(UnitCustomIcon).filter_by(unit_id=unit.id).first()
            current_icon = custom_icon.custom_icon if custom_icon else unit.icon

        # Сохраняем unit_id и unit_name в user_data для последующего использования
        context.user_data['editing_icon_unit_id'] = unit_id
        context.user_data['editing_icon_unit_name'] = unit_name

        logger.info(f"Запрос на ввод нового эмодзи для {unit_name}, текущий: {current_icon}")

        await query.edit_message_text(
            f"📝 Изменение эмодзи для юнита\n\n"
            f"🎮 Юнит: <b>{unit_name}</b>\n"
            f"Текущий эмодзи: {current_icon}\n\n"
            f"👉 Отправьте новый эмодзи в чат:",
            parse_mode='HTML'
        )

    async def admin_create_unit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс создания нового юнита"""
        query = update.callback_query
        await query.answer()

        username = update.effective_user.username
        if not self.is_admin(username):
            await query.edit_message_text("У вас нет доступа к этой функции.")
            return

        # Инициализируем данные для создания юнита
        context.user_data['creating_unit'] = {
            'step': 'name'
        }

        await query.edit_message_text(
            "Создание нового типа юнита\n\n"
            "Шаг 1/10: Введите название юнита:"
        )

    async def admin_back_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться в панель администратора"""
        query = update.callback_query
        await query.answer()

        username = update.effective_user.username
        if not self.is_admin(username):
            await query.edit_message_text("У вас нет доступа к этой функции.")
            return

        keyboard = [
            [InlineKeyboardButton("Настроить эмодзи юнитов", callback_data='admin_unit_icons')],
            [InlineKeyboardButton("Создать новый тип юнита", callback_data='admin_create_unit')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Панель администратора:",
            reply_markup=reply_markup
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
        application.add_handler(CommandHandler("version", self.version_command))
        application.add_handler(CommandHandler("play", self.play_command))
        application.add_handler(CommandHandler("profile", self.profile_command))
        application.add_handler(CommandHandler("shop", self.shop_command))
        application.add_handler(CommandHandler("search", self.search_command))
        application.add_handler(CommandHandler("users", self.users_command))

        # Игровые команды
        application.add_handler(CommandHandler("challenge", self.challenge_command))
        application.add_handler(CommandHandler("accept", self.accept_command))
        application.add_handler(CommandHandler("game", self.game_command))
        application.add_handler(CommandHandler("activegames", self.activegames_command))
        application.add_handler(CommandHandler("mygames", self.mygames_command))

        # Админские команды
        application.add_handler(CommandHandler("admin", self.admin_command))

        # Регистрация обработчиков callback (порядок важен для правильной маршрутизации)
        # Админские callback обработчики
        application.add_handler(CallbackQueryHandler(self.admin_unit_icons_callback, pattern=r'^admin_unit_icons$'))
        application.add_handler(CallbackQueryHandler(self.admin_edit_icon_callback, pattern=r'^admin_edit_icon:'))
        application.add_handler(CallbackQueryHandler(self.admin_create_unit_callback, pattern=r'^admin_create_unit$'))
        application.add_handler(CallbackQueryHandler(self.admin_back_callback, pattern=r'^admin_back$'))

        # Регистрация обработчиков callback (порядок важен для правильной маршрутизации)
        application.add_handler(CallbackQueryHandler(self.buy_unit_callback, pattern=r'^buy_unit:'))
        application.add_handler(CallbackQueryHandler(self.confirm_buy_callback, pattern=r'^confirm_buy:'))
        application.add_handler(CallbackQueryHandler(self.back_to_shop_callback, pattern=r'^back_to_shop$'))
        application.add_handler(CallbackQueryHandler(self.show_profile_callback, pattern=r'^show_profile$'))
        application.add_handler(CallbackQueryHandler(self.search_pagination_callback, pattern=r'^search:'))
        application.add_handler(CallbackQueryHandler(self.users_pagination_callback, pattern=r'^users:'))
        application.add_handler(CallbackQueryHandler(self.user_messages_callback, pattern=r'^user_msgs:'))

        # Игровые callback обработчики
        application.add_handler(CallbackQueryHandler(self.challenge_user_callback, pattern=r'^challenge_user:'))
        application.add_handler(CallbackQueryHandler(self.accept_challenge_callback, pattern=r'^accept_challenge:'))
        application.add_handler(CallbackQueryHandler(self.decline_challenge_callback, pattern=r'^decline_challenge:'))
        application.add_handler(CallbackQueryHandler(self.show_game_callback, pattern=r'^show_game:'))
        application.add_handler(CallbackQueryHandler(self.surrender_callback, pattern=r'^surrender:'))
        application.add_handler(CallbackQueryHandler(self.back_to_activegames_callback, pattern=r'^back_to_activegames$'))
        application.add_handler(CallbackQueryHandler(self.game_unit_callback, pattern=r'^game_unit:'))
        application.add_handler(CallbackQueryHandler(self.game_move_callback, pattern=r'^game_move:'))
        application.add_handler(CallbackQueryHandler(self.game_attack_callback, pattern=r'^game_attack:'))
        application.add_handler(CallbackQueryHandler(self.game_refresh_callback, pattern=r'^game_refresh:'))

        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Регистрация обработчика ошибок
        application.add_error_handler(self.error_handler)

        # Проверка версии и отправка уведомлений
        async def post_init(app):
            """Callback после инициализации приложения"""
            if self.check_version_changed():
                logger.info(f"Обнаружена новая версия: {self.version}")
                await self.notify_all_users_about_update(app)
                self.save_current_version()
            else:
                logger.info(f"Версия не изменилась: {self.version}")

        application.post_init = post_init

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
