#!/usr/bin/env python3
"""
Простой Telegram бот, который отвечает на все сообщения стандартной фразой из конфига.
Сохраняет все сообщения и пользователей в PostgreSQL.
"""

import json
import logging
import os
import html
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from db import Database
from db.models import GameUser, Unit, UnitCustomIcon, BattleUnit, Game
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


def format_coins(amount):
    """Форматирование монет с правильным склонением"""
    # Получаем последнюю цифру и две последние цифры
    amount_int = int(amount) if isinstance(amount, (int, float, Decimal)) else int(float(amount))
    last_digit = amount_int % 10
    last_two_digits = amount_int % 100

    # Определяем правильное склонение
    if last_two_digits >= 11 and last_two_digits <= 19:
        word = "монет"
    elif last_digit == 1:
        word = "монета"
    elif last_digit >= 2 and last_digit <= 4:
        word = "монеты"
    else:
        word = "монет"

    return f"{amount} {word}"


class SimpleBot:
    def __init__(self, config_path='config.json', db=None):
        """Инициализация бота с загрузкой конфигурации"""
        self.config = self.load_config(config_path)
        self.default_response = self.config['bot']['default_response']
        self.bot_token = self.config['telegram']['bot_token']
        self.parse_mode = self.config['telegram'].get('parse_mode', 'HTML')
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

    def get_latest_commit_message(self):
        """Получение сообщения последнего коммита из git"""
        import subprocess
        try:
            # Получаем сообщение последнего коммита без тегов и футеров
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=%B'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                full_message = result.stdout.strip()
                # Убираем строки с 🤖 Generated и Co-Authored-By
                lines = []
                for line in full_message.split('\n'):
                    if '🤖 Generated with' not in line and 'Co-Authored-By:' not in line:
                        lines.append(line)
                # Убираем пустые строки в конце
                while lines and not lines[-1].strip():
                    lines.pop()
                return '\n'.join(lines).strip()
            else:
                logger.warning("Не удалось получить сообщение коммита из git")
                return None
        except Exception as e:
            logger.warning(f"Ошибка при получении сообщения коммита: {e}")
            return None

    def get_initial_balance(self):
        """Получение стартовой суммы из конфигурации в базе данных"""
        try:
            value = self.db.get_config('start_registration_amount', '1000')
            return float(value)
        except (ValueError, TypeError):
            logger.warning("Ошибка при получении start_registration_amount из БД, используется 1000")
            return 1000.0

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

            # Получаем сообщение последнего коммита
            commit_message = self.get_latest_commit_message()

            if commit_message:
                # Если есть сообщение коммита, используем его
                notification_text = (
                    f"🔄 <b>Бот обновлен!</b>\n\n"
                    f"🤖 Новая версия: <code>{self.version}</code>\n\n"
                    f"✨ <b>Что нового:</b>\n"
                    f"{html.escape(commit_message)}\n\n"
                    f"Используйте /help для просмотра доступных команд."
                )
            else:
                # Если не удалось получить коммит, используем общий текст
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
        """Обработчик команды /start - начало работы с ботом и инициализация профиля"""
        user = update.effective_user
        logger.info(f"Команда /start от пользователя {user.id}")

        try:
            # Проверяем наличие username
            if not user.username:
                await update.message.reply_text(
                    "❌ Для игры необходим username в Telegram.\n\n"
                    "Пожалуйста, установите username в настройках Telegram:\n"
                    "Настройки → Имя пользователя\n\n"
                    "После этого используйте /start снова.",
                    parse_mode=self.parse_mode
                )
                logger.warning(f"Попытка создания профиля без username от пользователя {user.id}")
                return

            # Получаем или создаем игрового пользователя (используем username как имя)
            game_user, created = self.db.get_or_create_game_user(
                telegram_id=user.id,
                name=user.username,
                initial_balance=self.get_initial_balance()
            )

            if created:
                response = (
                    f"🎮 Добро пожаловать в игру, {game_user.name}!\n\n"
                    f"💰 Ваш начальный баланс: {format_coins(game_user.balance)}\n"
                    f"🏆 Побед: {game_user.wins}\n"
                    f"💔 Поражений: {game_user.losses}\n\n"
                    "Используйте /help для просмотра команд."
                )
            else:
                response = (
                    f"👋 С возвращением, {game_user.name}!\n\n"
                    f"💰 Текущий баланс: {format_coins(game_user.balance)}\n"
                    f"🏆 Побед: {game_user.wins}\n"
                    f"💔 Поражений: {game_user.losses}\n\n"
                    "Используйте /help для просмотра команд."
                )

            await update.message.reply_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при инициализации профиля: {e}")
            await update.message.reply_text(
                "Произошла ошибка при создании профиля. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "<b>Основные команды:</b>\n"
            "/start - Начать работу с ботом и инициализировать игровой профиль\n"
            "/help - Показать это сообщение\n"
            "/version - Показать версию бота\n"
            "/password - Установить пароль для админки\n"
            "/profile - Посмотреть свой игровой профиль\n"
            "/top - Рейтинг игроков\n"
            "/shop - Магазин юнитов (покупка армии)\n"
            "/transfer - Перевести деньги другому игроку\n\n"
            "<b>Игровые команды:</b>\n"
            "/challenge &lt;username&gt; - Вызвать игрока на бой\n"
            "/accept - Принять вызов на бой\n"
            "/game - Показать текущую игру\n"
            "/mygames - История игр"
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

    async def password_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /password - установка пароля для админки"""
        user = update.effective_user
        logger.info(f"Команда /password от пользователя {user.id}")

        try:
            # Проверяем наличие username
            if not user.username:
                await update.message.reply_text(
                    "❌ Для установки пароля необходим username в Telegram.",
                    parse_mode=self.parse_mode
                )
                return

            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await update.message.reply_text(
                    "❌ У вас еще нет игрового профиля.\n"
                    "Используйте /start для создания профиля.",
                    parse_mode=self.parse_mode
                )
                return

            # Устанавливаем флаг ожидания пароля
            context.user_data['waiting_for_password'] = True

            await update.message.reply_text(
                "🔐 <b>Установка пароля для админки</b>\n\n"
                "Введите пароль (минимум 6 символов):\n\n"
                "⚠️ <i>Пароль будет сохранен в зашифрованном виде и потребуется для входа в админку.</i>",
                parse_mode=self.parse_mode
            )

        except Exception as e:
            logger.error(f"Ошибка при обработке команды /password: {e}")
            await update.message.reply_text(
                "Произошла ошибка. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def handle_password_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода пароля"""
        user = update.effective_user

        # Проверяем, что мы ждем ввода пароля
        if not context.user_data.get('waiting_for_password'):
            return

        try:
            password = update.message.text.strip()

            # Валидация пароля
            if len(password) < 6:
                await update.message.reply_text(
                    "❌ Пароль должен быть не менее 6 символов. Попробуйте еще раз:",
                    parse_mode=self.parse_mode
                )
                return

            # Хешируем пароль
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            # Сохраняем хеш в базу
            with self.db.get_session() as session:
                game_user = session.query(GameUser).filter_by(telegram_id=user.id).first()
                if game_user:
                    game_user.password_hash = password_hash
                    session.commit()

                    # Удаляем сообщение с паролем для безопасности
                    try:
                        await update.message.delete()
                    except Exception as e:
                        logger.warning(f"Не удалось удалить сообщение с паролем: {e}")

                    # Очищаем флаг ожидания
                    context.user_data['waiting_for_password'] = False

                    await update.message.reply_text(
                        "✅ <b>Пароль успешно установлен!</b>\n\n"
                        f"Теперь вы можете войти в админку:\n"
                        f"Username: <code>{user.username}</code>\n\n"
                        f"🌐 Админка: http://modernhomm.ru",
                        parse_mode=self.parse_mode
                    )
                    logger.info(f"Пользователь {user.username} ({user.id}) установил пароль")
                else:
                    await update.message.reply_text(
                        "❌ Профиль не найден.",
                        parse_mode=self.parse_mode
                    )
                    context.user_data['waiting_for_password'] = False

        except Exception as e:
            logger.error(f"Ошибка при установке пароля: {e}")
            await update.message.reply_text(
                "Произошла ошибка при установке пароля. Попробуйте позже.",
                parse_mode=self.parse_mode
            )
            context.user_data['waiting_for_password'] = False

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /profile - просмотр игрового профиля"""
        user = update.effective_user
        logger.info(f"Команда /profile от пользователя {user.id}")

        try:
            game_user = self.db.get_game_user(user.id)

            if not game_user:
                await update.message.reply_text(
                    "❌ У вас еще нет игрового профиля.\n"
                    "Используйте /start для создания профиля.",
                    parse_mode=self.parse_mode
                )
                return

            # Получаем юнитов пользователя
            user_units = self.db.get_user_units(user.id)

            units_text = ""
            keyboard = []
            if user_units:
                # Фильтруем юнитов с количеством > 0
                active_units = [u for u in user_units if u.count > 0]
                if active_units:
                    units_text = "\n\n🔰 Ваши юниты:\n"
                    for user_unit in active_units:
                        # Получаем детали юнита
                        unit = self.db.get_unit_by_id(user_unit.unit_type_id)
                        if unit:
                            total_price = unit.price * user_unit.count
                            sell_price = total_price * Decimal('0.7')
                            units_text += (
                                f"\n{unit.name} x{user_unit.count}\n"
                                f"  ⚔️ Урон: {unit.damage} | 🛡️ Защита: {unit.defense} | 🎯 Дальность: {unit.range}\n"
                                f"  ❤️ HP: {unit.health} | 🏃 Скорость: {unit.speed} | 🌀 Уклонение: {float(unit.dodge_chance)*100:.0f}%\n"
                                f"  💵 Цена продажи: {format_coins(sell_price)}\n"
                            )
                            # Добавляем кнопку продажи для этого юнита
                            keyboard.append([
                                InlineKeyboardButton(
                                    f"💰 Продать {unit.name} ({user_unit.count} шт.)",
                                    callback_data=f"sell_unit_{user_unit.unit_type_id}"
                                )
                            ])
                else:
                    units_text = "\n\n🔰 У вас пока нет юнитов. Посетите /shop для покупки!"
            else:
                units_text = "\n\n🔰 У вас пока нет юнитов. Посетите /shop для покупки!"

            response = (
                f"👤 Профиль игрока {game_user.name}\n\n"
                f"💰 Баланс: {format_coins(game_user.balance)}\n"
                f"🏆 Побед: {game_user.wins}\n"
                f"💔 Поражений: {game_user.losses}"
                f"{units_text}"
            )

            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            await update.message.reply_text(response, parse_mode=self.parse_mode, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Ошибка при получении профиля: {e}")
            await update.message.reply_text(
                "Произошла ошибка при получении профиля. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def sell_unit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для продажи юнита"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: sell_unit_unit_type_id)
        data = query.data
        if not data.startswith('sell_unit_'):
            return

        unit_type_id = int(data.split('_')[2])
        user = update.effective_user

        try:
            # Получаем информацию о юните
            unit = self.db.get_unit_by_id(unit_type_id)
            if not unit:
                await query.edit_message_text(
                    "❌ Юнит не найден.",
                    parse_mode=self.parse_mode
                )
                return

            # Продаем юниты
            count, money = self.db.sell_units(user.id, unit_type_id)

            if count == 0:
                await query.edit_message_text(
                    "❌ У вас нет этих юнитов для продажи.",
                    parse_mode=self.parse_mode
                )
                return

            # Успешная продажа
            response = (
                f"✅ Успешно продано!\n\n"
                f"🔰 Юнит: {unit.name}\n"
                f"📦 Количество: {count} шт.\n"
                f"💰 Получено: {format_coins(money)}\n\n"
                f"Используйте /profile чтобы увидеть обновленный профиль."
            )

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode
            )

        except Exception as e:
            logger.error(f"Ошибка при продаже юнита: {e}")
            await query.edit_message_text(
                "Произошла ошибка при продаже. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def transfer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для перевода денег другому игроку"""
        user = update.effective_user
        logger.info(f"Команда /transfer от пользователя {user.id}")

        try:
            # Проверяем что у пользователя есть игровой профиль
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await update.message.reply_text(
                    "❌ У вас нет игрового профиля.\nИспользуйте /start для создания профиля.",
                    parse_mode=self.parse_mode
                )
                return

            # Показать список всех пользователей для выбора
            with self.db.get_session() as session:
                from db.models import GameUser

                # Получить всех пользователей кроме текущего
                all_users = session.query(GameUser).filter(
                    GameUser.telegram_id != user.id
                ).order_by(GameUser.name).all()

                if not all_users:
                    await update.message.reply_text(
                        "❌ Нет других игроков для перевода.",
                        parse_mode=self.parse_mode
                    )
                    return

                # Формируем сообщение со списком пользователей
                response = (
                    f"💰 <b>Перевод денег</b>\n\n"
                    f"Ваш баланс: {format_coins(game_user.balance)}\n\n"
                    f"Выберите получателя:\n\n"
                )

                # Создаем кнопки для каждого пользователя
                keyboard = []
                for i, player in enumerate(all_users[:20], 1):  # Показываем первых 20
                    safe_name = html.escape(player.name)

                    keyboard.append([
                        InlineKeyboardButton(
                            f"👤 {player.name}",
                            callback_data=f"transfer_user:{player.telegram_id}"
                        )
                    ])

                await update.message.reply_text(
                    response,
                    parse_mode=self.parse_mode,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        except Exception as e:
            logger.error(f"Ошибка при выполнении команды /transfer: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def transfer_select_user_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора пользователя для перевода денег"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: transfer_user:telegram_id)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'transfer_user':
            return

        target_telegram_id = int(data[1])
        user = update.effective_user

        # Получить информацию о текущем пользователе
        game_user = self.db.get_game_user(user.id)
        if not game_user:
            await query.edit_message_text("❌ Ваш профиль не найден.")
            return

        # Получить информацию о получателе
        with self.db.get_session() as session:
            from db.models import GameUser

            target_user = session.query(GameUser).filter_by(telegram_id=target_telegram_id).first()

            if not target_user:
                await query.edit_message_text("❌ Получатель не найден.")
                return

            # Экранируем имя
            safe_name = html.escape(target_user.name)

            # Показать выбор суммы
            response = (
                f"💰 <b>Перевод денег для {safe_name}</b>\n\n"
                f"Ваш баланс: {format_coins(game_user.balance)}\n\n"
                f"Выберите сумму перевода:"
            )

            keyboard = [
                [InlineKeyboardButton("💵 100 монет", callback_data=f"transfer_amount:{target_telegram_id}:100")],
                [InlineKeyboardButton("💵 1000 монет", callback_data=f"transfer_amount:{target_telegram_id}:1000")],
                [InlineKeyboardButton("💵 10000 монет", callback_data=f"transfer_amount:{target_telegram_id}:10000")],
                [InlineKeyboardButton("◀️ Назад", callback_data="transfer_back")]
            ]

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def transfer_confirm_amount_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик подтверждения суммы перевода"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: transfer_amount:telegram_id:amount)
        data = query.data.split(':')
        if len(data) != 3 or data[0] != 'transfer_amount':
            return

        target_telegram_id = int(data[1])
        amount = float(data[2])
        user = update.effective_user

        try:
            # Выполнить перевод
            success, message = self.db.transfer_money(user.id, target_telegram_id, amount)

            if success:
                await query.edit_message_text(
                    message,
                    parse_mode=self.parse_mode
                )

                # Уведомить получателя (если возможно)
                try:
                    game_user = self.db.get_game_user(user.id)
                    if game_user:
                        from telegram import Bot
                        bot = context.bot
                        notification = (
                            f"💰 <b>Вам перевели деньги!</b>\n\n"
                            f"От: {game_user.name}\n"
                            f"Сумма: {format_coins(amount)}\n\n"
                            f"Используйте /profile чтобы увидеть обновленный баланс."
                        )
                        await bot.send_message(
                            chat_id=target_telegram_id,
                            text=notification,
                            parse_mode=self.parse_mode
                        )
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление получателю: {e}")
            else:
                await query.edit_message_text(
                    f"❌ {message}",
                    parse_mode=self.parse_mode
                )

        except Exception as e:
            logger.error(f"Ошибка при переводе денег: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при переводе. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def transfer_back_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки 'Назад' в меню перевода"""
        query = update.callback_query
        await query.answer()

        # Возвращаемся к команде /transfer
        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await query.edit_message_text("❌ Ваш профиль не найден.")
                return

            with self.db.get_session() as session:
                from db.models import GameUser

                all_users = session.query(GameUser).filter(
                    GameUser.telegram_id != user.id
                ).order_by(GameUser.name).all()

                if not all_users:
                    await query.edit_message_text("❌ Нет других игроков для перевода.")
                    return

                response = (
                    f"💰 <b>Перевод денег</b>\n\n"
                    f"Ваш баланс: {format_coins(game_user.balance)}\n\n"
                    f"Выберите получателя:\n\n"
                )

                keyboard = []
                for i, player in enumerate(all_users[:20], 1):
                    keyboard.append([
                        InlineKeyboardButton(
                            f"👤 {player.name}",
                            callback_data=f"transfer_user:{player.telegram_id}"
                        )
                    ])

                await query.edit_message_text(
                    response,
                    parse_mode=self.parse_mode,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        except Exception as e:
            logger.error(f"Ошибка при возврате в меню перевода: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка.",
                parse_mode=self.parse_mode
            )

    async def top_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /top - рейтинг игроков"""
        logger.info(f"Команда /top от пользователя {update.effective_user.id}")

        try:
            # Получаем всех игроков
            all_users = self.db.get_all_game_users()

            if not all_users:
                await update.message.reply_text(
                    "📊 Рейтинг пока пуст. Станьте первым игроком!",
                    parse_mode=self.parse_mode
                )
                return

            # Подготовка данных для рейтинга
            player_stats = []
            for game_user in all_users:
                # Получаем юнитов игрока
                user_units = self.db.get_user_units(game_user.telegram_id)

                # Вычисляем стоимость армии
                army_cost = Decimal('0')
                for user_unit in user_units:
                    if user_unit.count > 0:
                        unit = self.db.get_unit_by_id(user_unit.unit_type_id)
                        if unit:
                            army_cost += unit.price * user_unit.count

                player_stats.append({
                    'name': game_user.name,
                    'wins': game_user.wins,
                    'losses': game_user.losses,
                    'army_cost': army_cost
                })

            # Сортируем по победам (по убыванию), затем по стоимости армии (по убыванию)
            player_stats.sort(key=lambda x: (x['wins'], x['army_cost']), reverse=True)

            # Формируем текст рейтинга
            response = "🏆 <b>Рейтинг игроков</b>\n\n"

            for idx, player in enumerate(player_stats[:10], 1):  # Топ-10
                medal = ""
                if idx == 1:
                    medal = "🥇 "
                elif idx == 2:
                    medal = "🥈 "
                elif idx == 3:
                    medal = "🥉 "
                else:
                    medal = f"{idx}. "

                response += (
                    f"{medal}<b>{html.escape(player['name'])}</b>\n"
                    f"  🏆 Побед: {player['wins']} | 💔 Поражений: {player['losses']}\n"
                    f"  ⚔️ Стоимость армии: {format_coins(player['army_cost'])}\n\n"
                )

            await update.message.reply_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при получении рейтинга: {e}")
            await update.message.reply_text(
                "Произошла ошибка при получении рейтинга. Попробуйте позже.",
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
                    "Используйте /start для создания профиля.",
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
            response = f"🏪 <b>Магазин юнитов</b>\n\n💰 Ваш баланс: {format_coins(game_user.balance)}\n\n"
            response += "Выберите юнита для покупки:\n"

            # Создаем кнопки для каждого юнита
            keyboard = []
            for unit in units:
                unit_info = (
                    f"{unit.name} - {format_coins(unit.price)}\n"
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
                f"💰 Цена за 1 шт: {format_coins(unit.price)}\n"
                f"💵 Ваш баланс: {format_coins(game_user.balance)}\n\n"
                f"<b>Характеристики:</b>\n"
                f"⚔️ Урон: {unit.damage}\n"
                f"🛡️ Защита: {unit.defense}\n"
                f"🎯 Дальность: {unit.range}\n"
                f"❤️ Здоровье: {unit.health}\n"
                f"🏃 Скорость: {unit.speed}\n"
                f"🍀 Удача: {float(unit.luck)*100:.0f}%\n"
                f"💥 Крит: {float(unit.crit_chance)*100:.0f}%\n"
                f"🌀 Уклонение: {float(unit.dodge_chance)*100:.0f}%\n\n"
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
                        f"{qty} шт ({format_coins(total)})",
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
                    f"💰 Новый баланс: {format_coins(game_user.balance)}"
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
            response = f"🏪 <b>Магазин юнитов</b>\n\n💰 Ваш баланс: {format_coins(game_user.balance)}\n\n"
            response += "Выберите юнита для покупки:\n"

            # Создаем кнопки для каждого юнита
            keyboard = []
            for unit in units:
                unit_info = (
                    f"{unit.name} - {format_coins(unit.price)}\n"
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
                            f"  ❤️ HP: {unit.health} | 🏃 Скорость: {unit.speed} | 🌀 Уклонение: {float(unit.dodge_chance)*100:.0f}%\n"
                        )
            else:
                units_text = "\n\n🔰 У вас пока нет юнитов. Посетите /shop для покупки!"

            response = (
                f"👤 Профиль игрока {game_user.name}\n\n"
                f"💰 Баланс: {format_coins(game_user.balance)}\n"
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

    def _calculate_army_cost(self, telegram_id: int) -> Decimal:
        """
        Вычисление стоимости армии игрока

        Args:
            telegram_id: ID игрока в Telegram

        Returns:
            Decimal: Общая стоимость всех юнитов игрока
        """
        user_units = self.db.get_user_units(telegram_id)
        army_cost = Decimal('0')

        for user_unit in user_units:
            if user_unit.count > 0:
                unit = self.db.get_unit_by_id(user_unit.unit_type_id)
                if unit:
                    army_cost += unit.price * user_unit.count

        return army_cost

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
                "❌ У вас еще нет игрового профиля. Используйте /start",
                parse_mode=self.parse_mode
            )
            return

        # Если не указан username, показываем список игроков с близкой стоимостью армии
        if not context.args:
            try:
                # Получаем 3 игроков с близкой стоимостью армии
                players_with_value = self.db.get_players_by_army_value(user.id, limit=3, variance=0.3)

                if not players_with_value:
                    await update.message.reply_text(
                        "❌ Нет доступных игроков для вызова.\n"
                        "Или используйте: /challenge username",
                        parse_mode=self.parse_mode
                    )
                    return

                # Формируем сообщение со списком пользователей
                response = "⚔️ <b>Выберите противника для боя:</b>\n"
                response += "<i>Игроки с близкой стоимостью армии (±30%)</i>\n\n"

                # Создаем кнопки для каждого пользователя
                keyboard = []
                for i, (opponent, army_value) in enumerate(players_with_value, 1):
                    win_rate = 0
                    if opponent.wins + opponent.losses > 0:
                        win_rate = (opponent.wins / (opponent.wins + opponent.losses)) * 100

                    # Экранируем HTML-символы в имени
                    safe_name = html.escape(opponent.name)

                    response += (
                        f"{i}. {safe_name}\n"
                        f"   💰 Армия: {format_coins(army_value)}\n"
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

            # Получаем противника для проверки стоимости армий
            opponent_user = None
            with self.db.get_session() as session:
                from db.models import GameUser as GU
                opponent_user = session.query(GU).filter_by(name=opponent_username).first()

            if not opponent_user:
                await update.message.reply_text(
                    f"❌ Игрок {opponent_username} не найден.",
                    parse_mode=self.parse_mode
                )
                return

            # Проверка разницы в стоимости армий (±50%)
            challenger_army_cost = self._calculate_army_cost(user.id)
            opponent_army_cost = self._calculate_army_cost(opponent_user.telegram_id)

            # Если хотя бы у одного игрока есть армия, проверяем разницу
            if challenger_army_cost > 0 or opponent_army_cost > 0:
                # Вычисляем максимальную допустимую разницу (50%)
                max_cost = max(challenger_army_cost, opponent_army_cost)
                min_cost = min(challenger_army_cost, opponent_army_cost)

                # Если одна из армий нулевая, считаем разницу 100%
                if min_cost == 0:
                    difference_percent = 100
                else:
                    difference_percent = ((max_cost - min_cost) / min_cost) * 100

                if difference_percent > 50:
                    await update.message.reply_text(
                        f"❌ <b>Невозможно начать бой!</b>\n\n"
                        f"Разница в стоимости армий слишком большая ({difference_percent:.0f}%).\n\n"
                        f"💰 Ваша армия: <code>{format_coins(challenger_army_cost)}</code>\n"
                        f"💰 Армия противника: <code>{format_coins(opponent_army_cost)}</code>\n\n"
                        f"Максимально допустимая разница: 50%\n"
                        f"Купите или продайте юнитов, чтобы уравнять армии.",
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
                    "❌ У вас еще нет игрового профиля. Используйте /start",
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
                    "❌ У вас еще нет игрового профиля. Используйте /start",
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
                    "❌ У вас еще нет игрового профиля. Используйте /start",
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

            # Отправить результаты противнику и убрать у него поле
            current_player_game_user = self.db.get_game_user(query.from_user.id)
            if current_player_game_user:
                opponent_id = loser_id if current_player_game_user.id == game.winner_id else game.winner_id
                opponent = self.db.get_game_user_by_id(opponent_id)

                if opponent and opponent.telegram_id:
                    try:
                        # Отправляем поле без кнопок противнику
                        await self._send_field_image(
                            chat_id=opponent.telegram_id,
                            game_id=game.id,
                            caption=result_message,
                            context=context,
                            keyboard=[]
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
        result += f"   💰 Баланс: {format_coins(winner.balance)}\n"
        result += f"   🏆 Побед: {winner.wins}\n"
        result += f"   💔 Поражений: {winner.losses}\n\n"

        # Статистика проигравшего
        result += f"📊 <b>Статистика {html.escape(loser.name)}:</b>\n"
        result += f"   💰 Баланс: {format_coins(loser.balance)}\n"
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

        # Добавляем кнопку просмотра лога (всегда доступна)
        keyboard.append([InlineKeyboardButton("📜 Показать лог игры", callback_data=f"game_log:{game_id}")])

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

            if image_bytes:
                if has_photo:
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
                    # Было текстовое сообщение, но теперь есть изображение
                    # Удаляем старое сообщение и отправляем новое с фото
                    try:
                        chat_id = query.message.chat_id
                        await query.message.delete()
                        await query.message.get_bot().send_photo(
                            chat_id=chat_id,
                            photo=io.BytesIO(image_bytes),
                            caption=caption,
                            parse_mode=self.parse_mode,
                            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при замене текста на фото: {e}")
                        # Fallback: оставляем текстовое сообщение
                        with self.db.get_session() as session:
                            engine = GameEngine(session)
                            field_display = engine.render_field(game_id)
                            await query.edit_message_text(
                                text=f"{caption}\n\n{field_display}",
                                parse_mode=self.parse_mode,
                                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                            )
            else:
                # Нет изображения - текстовое отображение
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

            # Проверка: если юнит не может ни двигаться, ни атаковать - автоматически пропускаем ход
            can_move = unit_data.get("can_move", False)
            targets = unit_data.get("targets", [])

            if not can_move and not targets:
                # Автоматически пропускаем ход
                with self.db.get_session() as session:
                    engine = GameEngine(session)
                    success, message = engine.skip_turn(game_id, game_user.id)

                    if success:
                        await self._edit_message_universal(
                            query,
                            f"⏭️ {unit_data['unit_name']} не может ходить и атаковать.\nХод пропущен автоматически.\n\n{message}",
                            parse_mode=self.parse_mode
                        )
                    else:
                        await self._edit_message_universal(query, f"❌ {message}", parse_mode=self.parse_mode)
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

            # Кнопка пропуска хода
            if unit_data.get("can_move") or targets:
                keyboard.append([InlineKeyboardButton("⏭️ Пропустить ход", callback_data=f"game_skip:{game_id}:{unit_id}")])

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

                        # Получаем информацию о перемещенном юните
                        battle_unit = session.query(BattleUnit).filter_by(id=unit_id).first()
                        unit_name = battle_unit.user_unit.unit.name if battle_unit and battle_unit.user_unit else "Юнит"

                        # Вычисляем старую позицию (берем из message, который содержит старую позицию)
                        # message имеет формат: "Юнит перемещен с (x1, y1) на (x2, y2)"
                        match = re.search(r'\((\d+),\s*(\d+)\)\s+на\s+\((\d+),\s*(\d+)\)', message)
                        if match:
                            old_x, old_y = int(match.group(1)), int(match.group(2))
                            new_x, new_y = int(match.group(3)), int(match.group(4))
                            from_cell = coords_to_chess(old_x, old_y)
                            to_cell = coords_to_chess(new_x, new_y)
                            movement_message = f"📍 {unit_name} переместился с {from_cell} на {to_cell}"
                        else:
                            from_cell = coords_to_chess(target_x - 1, target_y)  # Приблизительно
                            to_cell = coords_to_chess(target_x, target_y)
                            movement_message = f"📍 {unit_name} переместился на {to_cell}"

                        actions = engine.get_available_actions(game_id, game_user.id)
                        keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

                        # Используем _edit_field для обновления поля с PNG
                        await self._edit_field(query, game_id, f"✅ {movement_message}", keyboard)

                        # Отправить уведомление о перемещении противнику
                        game = session.query(Game).filter_by(id=game_id).first()
                        if game:
                            opponent_id = game.player2_id if game.player1_id == game_user.id else game.player1_id
                            opponent = session.query(GameUser).filter_by(id=opponent_id).first()

                            if opponent and opponent.telegram_id:
                                try:
                                    # Создаем кнопку "Текущая игра"
                                    current_game_keyboard = InlineKeyboardMarkup([
                                        [InlineKeyboardButton("🎮 Текущая игра", callback_data=f"show_game:{game_id}")]
                                    ])

                                    # Отправляем уведомление о перемещении противнику
                                    await context.bot.send_message(
                                        chat_id=opponent.telegram_id,
                                        text=f"👁️ Противник: {movement_message}",
                                        parse_mode=self.parse_mode,
                                        reply_markup=current_game_keyboard
                                    )
                                    logger.info(f"Уведомление о перемещении отправлено противнику {opponent.telegram_id}")
                                except Exception as e:
                                    logger.error(f"Ошибка при отправке уведомления о перемещении противнику: {e}")

                        # Если ход сменился, отправить уведомление противнику с полем
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

                    # Сохранить контекст для текстового ввода
                    context.user_data['waiting_for_cell_input'] = {
                        'game_id': game_id,
                        'unit_id': unit_id,
                        'available_cells': available_cells
                    }

                    # Используем _edit_field для показа поля с доступными позициями
                    caption = f"🏃 Выберите позицию для перемещения\n\nДоступно позиций: {len(available_cells)}\n\n💬 Вы можете отправить название ячейки текстом (например: A1, B3)"
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
                        await self._edit_field(query, game_id, "✅ Атака выполнена!", keyboard)

                        # Создаем кнопку "Текущая игра"
                        current_game_keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🎮 Текущая игра", callback_data=f"show_game:{game_id}")]
                        ])

                        # Отправить лог боя отдельным сообщением атакующему
                        try:
                            await context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text=message,
                                parse_mode='HTML',
                                reply_markup=current_game_keyboard
                            )
                        except Exception as e:
                            logger.error(f"Ошибка при отправке лога боя атакующему: {e}")

                        # Отправить лог боя защищающемуся игроку
                        opponent_id = game.player2_id if game.player1_id == game_user.id else game.player1_id
                        opponent = self.db.get_game_user_by_id(opponent_id)

                        if opponent and opponent.telegram_id:
                            try:
                                await context.bot.send_message(
                                    chat_id=opponent.telegram_id,
                                    text=message,
                                    parse_mode='HTML',
                                    reply_markup=current_game_keyboard
                                )
                            except Exception as e:
                                logger.error(f"Ошибка при отправке лога боя противнику: {e}")

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

    async def game_skip_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для пропуска хода юнита"""
        query = update.callback_query
        await query.answer()

        data = query.data.split(':')
        if len(data) != 3 or data[0] != 'game_skip':
            return

        game_id = int(data[1])
        unit_id = int(data[2])
        user = update.effective_user

        try:
            game_user = self.db.get_game_user(user.id)
            with self.db.get_session() as session:
                engine = GameEngine(session)
                success, message, turn_switched = engine.skip_unit_turn(game_id, game_user.id, unit_id)

                if success:
                    # Обновить поле
                    actions = engine.get_available_actions(game_id, game_user.id)
                    keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

                    await self._edit_field(query, game_id, "⏭️ Ход пропущен", keyboard)

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
                    await query.answer(f"❌ {message}", show_alert=True)

        except Exception as e:
            logger.error(f"Ошибка при пропуске хода: {e}")
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

            # Проверка разницы в стоимости армий (±50%)
            challenger_army_cost = self._calculate_army_cost(user.id)
            opponent_army_cost = self._calculate_army_cost(opponent.telegram_id)

            # Если хотя бы у одного игрока есть армия, проверяем разницу
            if challenger_army_cost > 0 or opponent_army_cost > 0:
                # Вычисляем максимальную допустимую разницу (50%)
                max_cost = max(challenger_army_cost, opponent_army_cost)
                min_cost = min(challenger_army_cost, opponent_army_cost)

                # Если одна из армий нулевая, считаем разницу 100%
                if min_cost == 0:
                    difference_percent = 100
                else:
                    difference_percent = ((max_cost - min_cost) / min_cost) * 100

                if difference_percent > 50:
                    safe_opponent_name = html.escape(opponent.name)
                    await query.edit_message_text(
                        f"❌ <b>Невозможно начать бой с {safe_opponent_name}!</b>\n\n"
                        f"Разница в стоимости армий слишком большая ({difference_percent:.0f}%).\n\n"
                        f"💰 Ваша армия: <code>{format_coins(challenger_army_cost)}</code>\n"
                        f"💰 Армия противника: <code>{format_coins(opponent_army_cost)}</code>\n\n"
                        f"Максимально допустимая разница: 50%\n"
                        f"Купите или продайте юнитов, чтобы уравнять армии.",
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
                        [InlineKeyboardButton("📊 Показать детали", callback_data=f"show_opponent_details:{game_id}")],
                        [InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_challenge:{game_id}")]
                    ])

                    await context.bot.send_message(
                        chat_id=opponent.telegram_id,
                        text=(
                            f"⚔️ <b>Вызов на бой!</b>\n\n"
                            f"Игрок {safe_challenger_name} вызывает вас на бой!\n"
                            f"Игра #{game_id}\n\n"
                            f"💰 Стоимость вашей армии: {format_coins(opponent_army_cost)}\n"
                            f"💰 Стоимость армии противника: {format_coins(challenger_army_cost)}\n\n"
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
                        # Получить обновленную игру после surrender (может быть None если игра была удалена)
                        updated_game = self.db.get_game_by_id(game_id)

                        if updated_game and updated_game.status == GameStatus.COMPLETED:
                            # Игра завершена (сдача в процессе игры) - отправляем поле с результатами
                            notification = (
                                f"🏃 Игрок {game_user.name} сдался в игре #{game_id}!\n\n"
                                f"🏆 Вы победили!\n\n"
                                f"{message.split('Урон юнитов зафиксирован. ')[1] if 'Урон юнитов зафиксирован. ' in message else ''}"
                            )

                            # Отправляем поле с результатами победителю
                            await self._send_field_image(
                                chat_id=opponent_telegram_id,
                                game_id=game_id,
                                caption=notification,
                                context=context,
                                keyboard=[]
                            )
                        else:
                            # Игра была удалена (отклонение вызова) - просто текстовое уведомление
                            notification = f"❌ Игрок {game_user.name} отклонил ваш вызов на бой (Игра #{game_id})"
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

    async def game_log_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для показа лога игры"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: game_log:game_id)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'game_log':
            return

        game_id = int(data[1])

        try:
            # Получить лог игры из базы данных
            from db.models import GameLog
            with self.db.get_session() as session:
                logs = session.query(GameLog).filter_by(game_id=game_id).order_by(GameLog.created_at).all()

                if not logs:
                    await query.answer("📜 Лог игры пуст", show_alert=True)
                    return

                # Формируем текст лога
                log_text = f"📜 <b>Лог игры #{game_id}</b>\n\n"
                for log in logs:
                    timestamp = log.created_at.strftime("%H:%M:%S")
                    log_text += f"[{timestamp}] {log.message}\n\n"

                # Отправляем лог отдельным сообщением
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=log_text,
                    parse_mode=self.parse_mode
                )
                await query.answer("📜 Лог отправлен")

        except Exception as e:
            logger.error(f"Ошибка при получении лога игры: {e}")
            await query.answer(f"❌ Ошибка: {e}", show_alert=True)

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
                        opponent_keyboard = self._create_game_keyboard(game_id, opponent_id, opponent_actions)

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

    async def show_opponent_details_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для показа деталей армии противника"""
        query = update.callback_query
        await query.answer()

        # Парсим данные из callback (формат: show_opponent_details:game_id)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'show_opponent_details':
            return

        game_id = int(data[1])
        user = update.effective_user

        try:
            game = self.db.get_game_by_id(game_id)
            if not game:
                await query.answer("❌ Игра не найдена", show_alert=True)
                return

            game_user = self.db.get_game_user(user.id)
            if not game_user:
                await query.answer("❌ Игровой профиль не найден", show_alert=True)
                return

            # Определяем, кто противник
            if game.player2_id == game_user.id:
                opponent_id = game.player1_id
            else:
                await query.answer("❌ Вы не участник этой игры", show_alert=True)
                return

            opponent = self.db.get_game_user_by_id(opponent_id)
            if not opponent:
                await query.answer("❌ Противник не найден", show_alert=True)
                return

            # Получаем юниты противника
            opponent_units = self.db.get_user_units_by_game_user_id(opponent_id)

            if not opponent_units or len(opponent_units) == 0:
                details_text = f"📊 <b>Армия {html.escape(opponent.name)}</b>\n\nУ противника нет юнитов!"
            else:
                details_text = f"📊 <b>Армия {html.escape(opponent.name)}</b>\n\n"
                total_cost = Decimal('0')

                for user_unit in opponent_units:
                    if user_unit.count > 0:
                        unit = self.db.get_unit_by_id(user_unit.unit_type_id)
                        if unit:
                            unit_total = unit.price * user_unit.count
                            total_cost += unit_total
                            details_text += (
                                f"{unit.icon} <b>{unit.name}</b> x{user_unit.count}\n"
                                f"  ⚔️ Урон: {unit.damage} | 🛡️ Защита: {unit.defense} | 🎯 Дальность: {unit.range}\n"
                                f"  ❤️ HP: {unit.health} | 🏃 Скорость: {unit.speed}\n"
                                f"  🍀 Удача: {float(unit.luck)*100:.0f}% | 💥 Крит: {float(unit.crit_chance)*100:.0f}% | 🌀 Уклонение: {float(unit.dodge_chance)*100:.0f}%\n"
                                f"  💰 Стоимость: {format_coins(unit_total)}\n\n"
                            )

                details_text += f"💵 <b>Общая стоимость армии:</b> {format_coins(total_cost)}"

            # Возвращаем клавиатуру с исходными кнопками
            challenge_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Принять бой", callback_data=f"accept_challenge:{game_id}")],
                [InlineKeyboardButton("📊 Показать детали", callback_data=f"show_opponent_details:{game_id}")],
                [InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_challenge:{game_id}")]
            ])

            await query.edit_message_text(
                details_text,
                parse_mode=self.parse_mode,
                reply_markup=challenge_keyboard
            )

        except Exception as e:
            logger.error(f"Ошибка при показе деталей противника: {e}")
            await query.answer(f"❌ Ошибка: {e}", show_alert=True)

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
            # Обработка ввода стартовой суммы
            if context.user_data.get('waiting_for_start_amount') and self.is_admin(user.username):
                await self.handle_start_amount_input(update, context)
                return

            # Обработка ввода пароля
            if context.user_data.get('waiting_for_password'):
                await self.handle_password_input(update, context)
                return

            # === GAME FUNCTIONS ===
            # Обработка ввода ячейки при перемещении
            if 'waiting_for_cell_input' in context.user_data:
                cell_data = context.user_data['waiting_for_cell_input']
                game_id = cell_data['game_id']
                unit_id = cell_data['unit_id']
                available_cells = cell_data['available_cells']

                # Парсим ввод пользователя (например A1, B3)
                cell_input = user_message.strip().upper()
                try:
                    # Преобразуем шахматную нотацию в координаты
                    target_x, target_y = chess_to_coords(cell_input)

                    # Проверяем что эта ячейка доступна
                    if (target_x, target_y) not in available_cells:
                        await update.message.reply_text(
                            f"❌ Ячейка {cell_input} недоступна для перемещения!\n"
                            f"Доступные ячейки: {', '.join([coords_to_chess(x, y) for x, y in available_cells[:10]])}",
                            parse_mode=self.parse_mode
                        )
                        return

                    # Очищаем контекст
                    del context.user_data['waiting_for_cell_input']

                    # Выполняем перемещение
                    game_user = self.db.get_game_user(user.id)
                    with self.db.get_session() as session:
                        engine = GameEngine(session)
                        success, message, turn_switched = engine.move_unit(game_id, game_user.id, unit_id, target_x, target_y)

                        if success:
                            # Получаем информацию о перемещенном юните
                            battle_unit = session.query(BattleUnit).filter_by(id=unit_id).first()
                            unit_name = battle_unit.user_unit.unit.name if battle_unit and battle_unit.user_unit else "Юнит"

                            # Вычисляем старую и новую позицию
                            match = re.search(r'\((\d+),\s*(\d+)\)\s+на\s+\((\d+),\s*(\d+)\)', message)
                            if match:
                                old_x, old_y = int(match.group(1)), int(match.group(2))
                                new_x, new_y = int(match.group(3)), int(match.group(4))
                                from_cell = coords_to_chess(old_x, old_y)
                                to_cell = coords_to_chess(new_x, new_y)
                                movement_message = f"📍 {unit_name} переместился с {from_cell} на {to_cell}"
                            else:
                                to_cell = cell_input
                                movement_message = f"📍 {unit_name} переместился на {to_cell}"

                            # Отправляем PNG поле
                            actions = engine.get_available_actions(game_id, game_user.id)
                            keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

                            await self._send_field_image(
                                chat_id=update.effective_chat.id,
                                game_id=game_id,
                                caption=f"✅ {movement_message}",
                                context=context,
                                keyboard=keyboard
                            )
                        else:
                            await update.message.reply_text(
                                f"❌ {message}",
                                parse_mode=self.parse_mode
                            )
                    return

                except (ValueError, IndexError) as e:
                    await update.message.reply_text(
                        f"❌ Неверный формат ячейки!\n"
                        f"Используйте формат: БукваЦифра (например: A1, B3)\n"
                        f"Доступные ячейки: {', '.join([coords_to_chess(x, y) for x, y in available_cells[:10]])}",
                        parse_mode=self.parse_mode
                    )
                    return

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
                            f"Цена: {format_coins(unit_data['price'])}\n"
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
                    initial_balance=self.get_initial_balance()
                )
                logger.info(f"Создан игровой профиль для пользователя {user.id}")

            # Обработка специальных текстовых команд
            if user_message.lower() in ['играть', 'play', 'start game']:
                # Пользователь написал "Играть" вместо команды /play
                response = (
                    f"🎮 Добро пожаловать в игру, {game_user.name}!\n\n"
                    f"💰 Ваш баланс: {format_coins(game_user.balance)}\n"
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

    async def addmoney_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для добавления денег игроку (только для okarien)"""
        user = update.effective_user
        username = user.username

        # Проверить права доступа
        if not self.is_admin(username):
            await update.message.reply_text(
                "❌ У вас нет доступа к этой команде.",
                parse_mode=self.parse_mode
            )
            return

        # Если аргументов нет - показать список всех пользователей
        if len(context.args) == 0:
            try:
                with self.db.get_session() as session:
                    from db.models import GameUser

                    # Получить всех пользователей
                    all_users = session.query(GameUser).order_by(GameUser.name).all()

                    if not all_users:
                        await update.message.reply_text(
                            "❌ В базе данных нет игроков.",
                            parse_mode=self.parse_mode
                        )
                        return

                    # Формируем сообщение со списком пользователей
                    response = "💰 <b>Выберите игрока для добавления средств:</b>\n\n"

                    # Создаем кнопки для каждого пользователя
                    keyboard = []
                    for i, player in enumerate(all_users, 1):
                        safe_name = html.escape(player.name)

                        response += (
                            f"{i}. {safe_name}\n"
                            f"   💵 Баланс: {format_coins(player.balance)}\n"
                            f"   🏆 {player.wins}W / 💔 {player.losses}L\n\n"
                        )

                        keyboard.append([
                            InlineKeyboardButton(
                                f"💰 {player.name} ({format_coins(player.balance)})",
                                callback_data=f"addmoney_user:{player.telegram_id}"
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

        # Проверить аргументы команды (старый формат)
        if len(context.args) != 2:
            await update.message.reply_text(
                "❌ Неверный формат команды.\n"
                "Использование: /addmoney <логин> <сумма>\n"
                "Пример: /addmoney Player1 1000\n\n"
                "Или используйте /addmoney без параметров для выбора из списка.",
                parse_mode=self.parse_mode
            )
            return

        target_name = context.args[0]
        try:
            amount = float(context.args[1])
            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть положительным числом.",
                    parse_mode=self.parse_mode
                )
                return
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат суммы. Используйте число.",
                parse_mode=self.parse_mode
            )
            return

        # Найти пользователя по имени
        with self.db.get_session() as session:
            from db.models import GameUser
            from decimal import Decimal

            target_user = session.query(GameUser).filter(GameUser.name == target_name).first()

            if not target_user:
                await update.message.reply_text(
                    f"❌ Игрок с логином '{target_name}' не найден.",
                    parse_mode=self.parse_mode
                )
                return

            # Добавить деньги
            old_balance = float(target_user.balance)
            target_user.balance += Decimal(str(amount))
            new_balance = float(target_user.balance)

            session.commit()

            # Отправить подтверждение
            await update.message.reply_text(
                f"✅ Успешно добавлено {format_coins(amount)} игроку {target_name}.\n"
                f"Баланс: {format_coins(old_balance)} → {format_coins(new_balance)}",
                parse_mode=self.parse_mode
            )

            logger.info(f"Администратор {username} добавил {amount} монет игроку {target_name} (ID: {target_user.telegram_id})")

    async def addmoney_select_user_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора пользователя для добавления денег"""
        query = update.callback_query
        await query.answer()

        username = update.effective_user.username
        if not self.is_admin(username):
            await query.edit_message_text("❌ У вас нет доступа к этой функции.")
            return

        # Парсим данные из callback (формат: addmoney_user:telegram_id)
        data = query.data.split(':')
        if len(data) != 2 or data[0] != 'addmoney_user':
            return

        target_telegram_id = int(data[1])

        # Получить информацию о пользователе
        with self.db.get_session() as session:
            from db.models import GameUser

            target_user = session.query(GameUser).filter_by(telegram_id=target_telegram_id).first()

            if not target_user:
                await query.edit_message_text("❌ Игрок не найден.")
                return

            # Экранируем имя
            safe_name = html.escape(target_user.name)

            # Формируем кнопки с суммами
            keyboard = [
                [InlineKeyboardButton(
                    "💵 +1,000",
                    callback_data=f"addmoney_amount:{target_telegram_id}:1000"
                )],
                [InlineKeyboardButton(
                    "💰 +5,000",
                    callback_data=f"addmoney_amount:{target_telegram_id}:5000"
                )],
                [InlineKeyboardButton(
                    "💎 +10,000",
                    callback_data=f"addmoney_amount:{target_telegram_id}:10000"
                )],
                [InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data="addmoney_back"
                )]
            ]

            await query.edit_message_text(
                f"💰 <b>Добавление средств игроку</b>\n\n"
                f"Игрок: {safe_name}\n"
                f"Текущий баланс: {format_coins(target_user.balance)}\n\n"
                f"Выберите сумму для добавления:",
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def addmoney_confirm_amount_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик подтверждения суммы и добавления денег"""
        query = update.callback_query
        await query.answer()

        username = update.effective_user.username
        if not self.is_admin(username):
            await query.edit_message_text("❌ У вас нет доступа к этой функции.")
            return

        # Парсим данные из callback (формат: addmoney_amount:telegram_id:amount)
        data = query.data.split(':')
        if len(data) != 3 or data[0] != 'addmoney_amount':
            return

        target_telegram_id = int(data[1])
        amount = float(data[2])

        # Добавить деньги
        with self.db.get_session() as session:
            from db.models import GameUser
            from decimal import Decimal

            target_user = session.query(GameUser).filter_by(telegram_id=target_telegram_id).first()

            if not target_user:
                await query.edit_message_text("❌ Игрок не найден.")
                return

            # Добавить деньги
            old_balance = float(target_user.balance)
            target_user.balance += Decimal(str(amount))
            new_balance = float(target_user.balance)

            session.commit()

            # Экранируем имя
            safe_name = html.escape(target_user.name)

            # Отправить подтверждение
            await query.edit_message_text(
                f"✅ <b>Средства успешно добавлены!</b>\n\n"
                f"Игрок: {safe_name}\n"
                f"Сумма: +{format_coins(amount)}\n"
                f"Баланс: {format_coins(old_balance)} → {format_coins(new_balance)}",
                parse_mode=self.parse_mode
            )

            logger.info(f"Администратор {username} добавил {amount} монет игроку {target_user.name} (ID: {target_telegram_id})")

    async def addmoney_back_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки 'Назад' в addmoney"""
        query = update.callback_query
        await query.answer()

        username = update.effective_user.username
        if not self.is_admin(username):
            await query.edit_message_text("❌ У вас нет доступа к этой функции.")
            return

        # Показать список пользователей снова
        with self.db.get_session() as session:
            from db.models import GameUser

            all_users = session.query(GameUser).order_by(GameUser.name).all()

            if not all_users:
                await query.edit_message_text("❌ В базе данных нет игроков.")
                return

            response = "💰 <b>Выберите игрока для добавления средств:</b>\n\n"

            keyboard = []
            for i, player in enumerate(all_users, 1):
                safe_name = html.escape(player.name)

                response += (
                    f"{i}. {safe_name}\n"
                    f"   💵 Баланс: {format_coins(player.balance)}\n"
                    f"   🏆 {player.wins}W / 💔 {player.losses}L\n\n"
                )

                keyboard.append([
                    InlineKeyboardButton(
                        f"💰 {player.name} ({format_coins(player.balance)})",
                        callback_data=f"addmoney_user:{player.telegram_id}"
                    )
                ])

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def start_registration_amount_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для настройки стартовой суммы при регистрации (только для okarien)"""
        user = update.effective_user
        username = user.username

        # Проверить права доступа
        if not self.is_admin(username):
            await update.message.reply_text(
                "❌ У вас нет доступа к этой команде.",
                parse_mode=self.parse_mode
            )
            return

        # Получить текущее значение из базы данных
        current_amount = self.get_initial_balance()

        # Сохранить состояние для ожидания ввода
        context.user_data['waiting_for_start_amount'] = True

        await update.message.reply_text(
            f"💰 <b>Настройка стартовой суммы при регистрации</b>\n\n"
            f"Текущая стартовая сумма: <b>{format_coins(current_amount)}</b>\n\n"
            f"Введите новую сумму (число):",
            parse_mode=self.parse_mode
        )

    async def handle_start_amount_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода новой стартовой суммы"""
        user = update.effective_user
        username = user.username

        # Проверить, что мы ждем ввода суммы
        if not context.user_data.get('waiting_for_start_amount'):
            return

        # Проверить права доступа
        if not self.is_admin(username):
            context.user_data['waiting_for_start_amount'] = False
            return

        # Получить введенное значение
        try:
            new_amount = float(update.message.text.strip())

            if new_amount < 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть положительным числом. Попробуйте еще раз:",
                    parse_mode=self.parse_mode
                )
                return

        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат. Введите число (например, 1000):",
                parse_mode=self.parse_mode
            )
            return

        # Сохранить новое значение в базу данных
        old_amount = self.get_initial_balance()
        self.db.set_config(
            key='start_registration_amount',
            value=str(new_amount),
            description='Стартовая сумма денег при регистрации нового пользователя'
        )

        # Очистить состояние ожидания
        context.user_data['waiting_for_start_amount'] = False

        # Отправить подтверждение
        await update.message.reply_text(
            f"✅ <b>Стартовая сумма обновлена!</b>\n\n"
            f"Старое значение: {format_coins(old_amount)}\n"
            f"Новое значение: {format_coins(new_amount)}\n\n"
            f"Новые пользователи будут получать {format_coins(new_amount)} при регистрации.",
            parse_mode=self.parse_mode
        )

        logger.info(f"Администратор {username} изменил стартовую сумму с {old_amount} на {new_amount} монет")

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
        application.add_handler(CommandHandler("password", self.password_command))
        application.add_handler(CommandHandler("profile", self.profile_command))
        application.add_handler(CommandHandler("top", self.top_command))
        application.add_handler(CommandHandler("shop", self.shop_command))
        application.add_handler(CommandHandler("transfer", self.transfer_command))
        application.add_handler(CommandHandler("search", self.search_command))
        application.add_handler(CommandHandler("users", self.users_command))

        # Игровые команды
        application.add_handler(CommandHandler("challenge", self.challenge_command))
        application.add_handler(CommandHandler("accept", self.accept_command))
        application.add_handler(CommandHandler("game", self.game_command))
        application.add_handler(CommandHandler("mygames", self.mygames_command))

        # Админские команды
        application.add_handler(CommandHandler("admin", self.admin_command))
        application.add_handler(CommandHandler("addmoney", self.addmoney_command))
        application.add_handler(CommandHandler("startRegistrationAmount", self.start_registration_amount_command))

        # Регистрация обработчиков callback (порядок важен для правильной маршрутизации)
        # Админские callback обработчики
        application.add_handler(CallbackQueryHandler(self.admin_unit_icons_callback, pattern=r'^admin_unit_icons$'))
        application.add_handler(CallbackQueryHandler(self.admin_edit_icon_callback, pattern=r'^admin_edit_icon:'))
        application.add_handler(CallbackQueryHandler(self.admin_create_unit_callback, pattern=r'^admin_create_unit$'))
        application.add_handler(CallbackQueryHandler(self.admin_back_callback, pattern=r'^admin_back$'))

        # AddMoney callback обработчики
        application.add_handler(CallbackQueryHandler(self.addmoney_select_user_callback, pattern=r'^addmoney_user:'))
        application.add_handler(CallbackQueryHandler(self.addmoney_confirm_amount_callback, pattern=r'^addmoney_amount:'))
        application.add_handler(CallbackQueryHandler(self.addmoney_back_callback, pattern=r'^addmoney_back$'))

        # Transfer callback обработчики
        application.add_handler(CallbackQueryHandler(self.transfer_select_user_callback, pattern=r'^transfer_user:'))
        application.add_handler(CallbackQueryHandler(self.transfer_confirm_amount_callback, pattern=r'^transfer_amount:'))
        application.add_handler(CallbackQueryHandler(self.transfer_back_callback, pattern=r'^transfer_back$'))

        # Регистрация обработчиков callback (порядок важен для правильной маршрутизации)
        application.add_handler(CallbackQueryHandler(self.buy_unit_callback, pattern=r'^buy_unit:'))
        application.add_handler(CallbackQueryHandler(self.confirm_buy_callback, pattern=r'^confirm_buy:'))
        application.add_handler(CallbackQueryHandler(self.back_to_shop_callback, pattern=r'^back_to_shop$'))
        application.add_handler(CallbackQueryHandler(self.sell_unit_callback, pattern=r'^sell_unit_'))
        application.add_handler(CallbackQueryHandler(self.show_profile_callback, pattern=r'^show_profile$'))
        application.add_handler(CallbackQueryHandler(self.search_pagination_callback, pattern=r'^search:'))
        application.add_handler(CallbackQueryHandler(self.users_pagination_callback, pattern=r'^users:'))
        application.add_handler(CallbackQueryHandler(self.user_messages_callback, pattern=r'^user_msgs:'))

        # Игровые callback обработчики
        application.add_handler(CallbackQueryHandler(self.challenge_user_callback, pattern=r'^challenge_user:'))
        application.add_handler(CallbackQueryHandler(self.accept_challenge_callback, pattern=r'^accept_challenge:'))
        application.add_handler(CallbackQueryHandler(self.show_opponent_details_callback, pattern=r'^show_opponent_details:'))
        application.add_handler(CallbackQueryHandler(self.decline_challenge_callback, pattern=r'^decline_challenge:'))
        application.add_handler(CallbackQueryHandler(self.show_game_callback, pattern=r'^show_game:'))
        application.add_handler(CallbackQueryHandler(self.surrender_callback, pattern=r'^surrender:'))
        application.add_handler(CallbackQueryHandler(self.game_log_callback, pattern=r'^game_log:'))
        application.add_handler(CallbackQueryHandler(self.back_to_activegames_callback, pattern=r'^back_to_activegames$'))
        application.add_handler(CallbackQueryHandler(self.game_unit_callback, pattern=r'^game_unit:'))
        application.add_handler(CallbackQueryHandler(self.game_move_callback, pattern=r'^game_move:'))
        application.add_handler(CallbackQueryHandler(self.game_attack_callback, pattern=r'^game_attack:'))
        application.add_handler(CallbackQueryHandler(self.game_skip_callback, pattern=r'^game_skip:'))
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
