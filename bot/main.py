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
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from db import Database
from db.models import GameUser, BattleUnit, Game, GameLog, RaceUnit, GameStatus
from decimal import Decimal
from core.game_engine import GameEngine, coords_to_chess, chess_to_coords
# Field rendering removed - battles now in Godot arena only
import io


# HTTP API сервер для health check и получения версии
class BotAPIHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для API бота"""
    bot_instance = None  # Будет установлен при запуске

    def log_message(self, format, *args):
        """Логирование запросов"""
        logger.debug(f"API: {args[0]}")

    def do_GET(self):
        """Обработка GET запросов"""
        if self.path == '/api/version':
            self._send_json({
                'bot_version': self._get_version('VERSION'),
                'web_version': self._get_version('WEB_VERSION'),
                'status': 'ok'
            })
        elif self.path == '/api/health':
            try:
                if self.bot_instance and self.bot_instance.db:
                    from sqlalchemy import text
                    with self.bot_instance.db.get_session() as session:
                        session.execute(text('SELECT 1'))
                self._send_json({'status': 'healthy', 'database': 'connected'})
            except Exception as e:
                self._send_json({'status': 'unhealthy', 'error': str(e)}, 500)
        else:
            self._send_json({'error': 'Not found'}, 404)

    def _get_version(self, filename):
        """Получить версию из файла"""
        try:
            with open(filename, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return 'unknown'

    def _send_json(self, data, status=200):
        """Отправить JSON ответ"""
        import json
        response = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response)


def start_api_server(bot_instance, port=8080):
    """Запустить HTTP API сервер в отдельном потоке"""
    BotAPIHandler.bot_instance = bot_instance
    server = HTTPServer(('0.0.0.0', port), BotAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"API сервер запущен на порту {port}")
    return server


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

    def load_web_version(self):
        """Загрузка версии веб-интерфейса из файла WEB_VERSION"""
        try:
            with open('WEB_VERSION', 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("Файл WEB_VERSION не найден")
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
        """Проверка, изменилась ли версия бота или веб-интерфейса с прошлого запуска"""
        try:
            with open('.last_version', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                # Формат: bot_version|web_version
                if '|' in content:
                    last_bot_version, last_web_version = content.split('|', 1)
                else:
                    last_bot_version = content
                    last_web_version = ""

                current_web_version = self.load_web_version()
                bot_changed = last_bot_version != self.version
                web_changed = last_web_version != current_web_version

                return bot_changed, web_changed
        except FileNotFoundError:
            # Первый запуск - версии "изменились"
            return True, True

    def save_current_version(self):
        """Сохранение текущих версий бота и веб-интерфейса"""
        try:
            web_version = self.load_web_version()
            with open('.last_version', 'w', encoding='utf-8') as f:
                f.write(f"{self.version}|{web_version}")
            logger.info(f"Версии сохранены: бот={self.version}, веб-интерфейс={web_version}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении версий: {e}")

    async def notify_all_users_about_update(self, application, bot_changed=True, web_changed=False):
        """Отправка уведомления всем пользователям о новой версии"""
        try:
            # Получаем всех игровых пользователей
            game_users = self.db.get_all_game_users()

            if not game_users:
                logger.info("Нет зарегистрированных пользователей для уведомления")
                return

            # Получаем сообщение последнего коммита
            commit_message = self.get_latest_commit_message()
            web_version = self.load_web_version()

            # Формируем заголовок в зависимости от того, что обновилось
            if bot_changed and web_changed:
                title = "🔄 <b>Система обновлена!</b>"
                versions_info = (
                    f"🤖 Бот: <code>{self.version}</code>\n"
                    f"🖥️ Веб-интерфейс: <code>{web_version}</code>"
                )
            elif web_changed:
                title = "🔄 <b>Веб-интерфейс обновлена!</b>"
                versions_info = f"🖥️ Новая версия: <code>{web_version}</code>"
            else:
                title = "🔄 <b>Бот обновлен!</b>"
                versions_info = f"🤖 Новая версия: <code>{self.version}</code>"

            if commit_message:
                # Если есть сообщение коммита, используем его
                notification_text = (
                    f"{title}\n\n"
                    f"{versions_info}\n\n"
                    f"✨ <b>Что нового:</b>\n"
                    f"{html.escape(commit_message)}\n\n"
                    f"Используйте /help для просмотра доступных команд."
                )
            else:
                # Если не удалось получить коммит, используем общий текст
                notification_text = (
                    f"{title}\n\n"
                    f"{versions_info}\n\n"
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

            # Получаем или создаем игрового пользователя
            game_user, created = self.db.get_or_create_game_user(
                telegram_id=user.id,
                username=user.username or f"User_{user.id}",
                initial_balance=self.get_initial_balance()
            )

            if created:
                response = (
                    f"🎮 Добро пожаловать в игру, @{game_user.username}!\n\n"
                    f"💰 Ваш начальный баланс: {format_coins(game_user.balance)}\n"
                    f"🏆 Побед: {game_user.wins}\n"
                    f"💔 Поражений: {game_user.losses}\n\n"
                    "Используйте /help для просмотра команд."
                )
            else:
                response = (
                    f"👋 С возвращением, @{game_user.username}!\n\n"
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
            "/password - Установить пароль для веб-интерфейса\n"
            "/profile - Посмотреть свой игровой профиль\n"
            "/top - Рейтинг игроков\n\n"
            "<b>Игровые команды:</b>\n"
            "/history - История ваших боёв\n"
            "/gamelog &lt;game_id&gt; - Лог конкретного боя\n\n"
            "⚔️ <i>Бои проводятся в <a href=\"https://modernhomm.ru/\">Godot Arena</a></i>"
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
        """Обработчик команды /password - установка пароля для веб-интерфейса"""
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
                "🔐 <b>Установка пароля для веб-интерфейса</b>\n\n"
                "Введите пароль (минимум 6 символов):\n\n"
                "⚠️ <i>Пароль будет сохранен в зашифрованном виде и потребуется для входа в веб-интерфейс.</i>",
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
                        f"Теперь вы можете войти в веб-интерфейс:\n"
                        f"Username: <code>{user.username}</code>\n\n"
                        f"🌐 Веб-интерфейс: http://modernhomm.ru",
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

            # Получаем армии пользователя через расу
            armies_text = ""
            with self.db.get_session() as session:
                from db.models import UserRace, Army, ArmyUnit
                user_races = session.query(UserRace).filter_by(user_id=game_user.id).all()

                if user_races:
                    armies_text = "\n\n⚔️ Ваши армии:\n"
                    for user_race in user_races:
                        race_name = user_race.race.name if user_race.race else "Неизвестная раса"
                        armies = session.query(Army).filter_by(user_race_id=user_race.id).all()
                        if armies:
                            for army in armies:
                                army_type = "Рейтинговая" if army.army_type == "rated" else "Наемная"
                                armies_text += f"\n🏰 <b>{army.name}</b> ({army_type})\n"
                                armies_text += f"  Раса: {race_name}\n"
                                # Показываем состав армии
                                army_units = session.query(ArmyUnit).filter_by(army_id=army.id).all()
                                if army_units:
                                    armies_text += "  Состав:\n"
                                    for unit in army_units:
                                        unit_name = unit.race_unit.name if unit.race_unit else "Неизвестный юнит"
                                        level_icon = unit.unit_level.icon if unit.unit_level else ""
                                        armies_text += f"    {level_icon} {unit_name} x{unit.count}\n"
                                else:
                                    armies_text += "  <i>Армия пуста</i>\n"
                        else:
                            armies_text += f"\n{race_name}: нет армий\n"
                else:
                    armies_text = "\n\n⚔️ У вас пока нет армий. Создайте армию на веб-сайте!"

            response = (
                f"👤 Профиль игрока @{game_user.username}\n\n"
                f"💰 Баланс: {format_coins(game_user.balance)}\n"
                f"🏆 Побед: {game_user.wins}\n"
                f"💔 Поражений: {game_user.losses}"
                f"{armies_text}"
            )

            await update.message.reply_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при получении профиля: {e}")
            await update.message.reply_text(
                "Произошла ошибка при получении профиля. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def sell_unit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для продажи юнита - УСТАРЕВШИЙ"""
        query = update.callback_query
        await query.answer("Эта функция больше недоступна. Управляйте армиями на веб-сайте.", show_alert=True)

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
                player_stats.append({
                    'name': f"@{game_user.username}",
                    'wins': game_user.wins,
                    'losses': game_user.losses,
                    'glory': game_user.glory
                })

            # Сортируем по победам (по убыванию), затем по славе (по убыванию)
            player_stats.sort(key=lambda x: (x['wins'], x['glory']), reverse=True)

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
                    f"  ⭐ Слава: {player['glory']}\n\n"
                )

            await update.message.reply_text(response, parse_mode=self.parse_mode)

        except Exception as e:
            logger.error(f"Ошибка при получении рейтинга: {e}")
            await update.message.reply_text(
                "Произошла ошибка при получении рейтинга. Попробуйте позже.",
                parse_mode=self.parse_mode
            )

    async def shop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /shop - УСТАРЕВШИЙ, команда удалена"""
        user = update.effective_user
        logger.info(f"Команда /shop (устаревшая) от пользователя {user.id}")

        await update.message.reply_text(
            "❌ <b>Команда /shop удалена</b>\n\n"
            "Управление армиями теперь доступно только на веб-сайте.\n\n"
            "Используйте /profile для просмотра профиля.",
            parse_mode=self.parse_mode
        )

    async def buy_unit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для покупки юнита - УСТАРЕВШИЙ"""
        query = update.callback_query
        await query.answer("Эта функция больше недоступна. Управляйте армиями на веб-сайте.", show_alert=True)

    async def confirm_buy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для подтверждения покупки - УСТАРЕВШИЙ"""
        query = update.callback_query
        await query.answer("Эта функция больше недоступна. Управляйте армиями на веб-сайте.", show_alert=True)

    async def back_to_shop_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для возврата в магазин - УСТАРЕВШИЙ"""
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            "🏪 <b>Управление армиями</b>\n\n"
            "Покупка юнитов и создание армий теперь доступны на веб-сайте.\n\n"
            "Используйте /profile для просмотра ваших армий.",
            parse_mode='HTML'
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

            # Получаем армии пользователя через расу
            armies_text = ""
            with self.db.get_session() as session:
                from db.models import UserRace, Army, ArmyUnit
                user_races = session.query(UserRace).filter_by(user_id=game_user.id).all()

                if user_races:
                    armies_text = "\n\n⚔️ Ваши армии:\n"
                    for user_race in user_races:
                        race_name = user_race.race.name if user_race.race else "Неизвестная раса"
                        armies = session.query(Army).filter_by(user_race_id=user_race.id).all()
                        if armies:
                            for army in armies:
                                army_type = "Рейтинговая" if army.army_type == "rated" else "Наемная"
                                armies_text += f"\n🏰 <b>{army.name}</b> ({army_type})\n"
                                armies_text += f"  Раса: {race_name}\n"
                                # Показываем состав армии
                                army_units = session.query(ArmyUnit).filter_by(army_id=army.id).all()
                                if army_units:
                                    armies_text += "  Состав:\n"
                                    for unit in army_units:
                                        unit_name = unit.race_unit.name if unit.race_unit else "Неизвестный юнит"
                                        level_icon = unit.unit_level.icon if unit.unit_level else ""
                                        armies_text += f"    {level_icon} {unit_name} x{unit.count}\n"
                                else:
                                    armies_text += "  <i>Армия пуста</i>\n"
                        else:
                            armies_text += f"\n{race_name}: нет армий\n"
                else:
                    armies_text = "\n\n⚔️ У вас пока нет армий. Создайте армию на веб-сайте!"

            response = (
                f"👤 Профиль игрока @{game_user.username}\n\n"
                f"💰 Баланс: {format_coins(game_user.balance)}\n"
                f"🏆 Побед: {game_user.wins}\n"
                f"💔 Поражений: {game_user.losses}"
                f"{armies_text}"
            )

            await query.edit_message_text(
                response,
                parse_mode=self.parse_mode
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
        Вычисление стоимости армии игрока - УСТАРЕВШИЙ МЕТОД

        Args:
            telegram_id: ID игрока в Telegram

        Returns:
            Decimal: Всегда 0 - стоимость армии теперь рассчитывается по армиям
        """
        # Старая система юнитов удалена, армии управляются через веб-интерфейс
        return Decimal('0')

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
            user_display = f"@{user.username}" if user.username else f"User (ID: {user.telegram_id})"
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

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех текстовых сообщений"""
        user_message = update.message.text
        user = update.effective_user

        logger.info(f"Сообщение от {user.id} (@{user.username}): {user_message}")

        try:
            # Проверка что context доступен
            has_user_data = context and hasattr(context, 'user_data') and context.user_data is not None

            # === ADMIN FUNCTIONS ===
            # Обработка ввода стартовой суммы
            if has_user_data and context.user_data.get('waiting_for_start_amount') and self.is_admin(user.username):
                await self.handle_start_amount_input(update, context)
                return

            # Обработка ввода пароля
            if has_user_data and context.user_data.get('waiting_for_password'):
                await self.handle_password_input(update, context)
                return

            # === GAME FUNCTIONS ===
            # Обработка ввода ячейки при перемещении
            if has_user_data and 'waiting_for_cell_input' in context.user_data:
                cell_data = context.user_data['waiting_for_cell_input']
                game_id = cell_data['game_id']
                unit_id = cell_data['unit_id']
                available_cells = cell_data['available_cells']

                # Проверяем, что игра всё ещё активна
                game = self.db.get_game_by_id(game_id)
                if not game or game.status != GameStatus.IN_PROGRESS:
                    # Игра завершена или не найдена - очищаем контекст
                    del context.user_data['waiting_for_cell_input']
                    # Не return - продолжаем обработку как обычное сообщение
                else:
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
                                unit_name = battle_unit.army_unit.race_unit.name if battle_unit and battle_unit.army_unit and battle_unit.army_unit.race_unit else "Юнит"

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

                                # Отправляем статус без поля
                                actions = engine.get_available_actions(game_id, game_user.id)
                                keyboard = self._create_game_keyboard(game_id, game_user.id, actions)

                                await context.bot.send_message(
                                    chat_id=update.effective_chat.id,
                                    text=f"✅ {movement_message}",
                                    parse_mode=self.parse_mode,
                                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                                )
                            else:
                                await update.message.reply_text(
                                    f"❌ {message}",
                                    parse_mode=self.parse_mode
                                )
                        return

                    except (ValueError, IndexError) as e:
                        # Неверный формат - но игра активна, показываем ошибку
                        await update.message.reply_text(
                            f"❌ Неверный формат ячейки!\n"
                            f"Используйте формат: БукваЦифра (например: A1, B3)\n"
                            f"Доступные ячейки: {', '.join([coords_to_chess(x, y) for x, y in available_cells[:10]])}",
                            parse_mode=self.parse_mode
                        )
                        return

            # === REGULAR USER PROCESSING ===
            # Проверяем, есть ли у пользователя игровой профиль, и создаем его при необходимости
            game_user = self.db.get_game_user(user.id)
            if not game_user:
                # Проверяем наличие username
                if not user.username:
                    await update.message.reply_text(
                        "❌ Для игры необходим username в Telegram.\n\n"
                        "Пожалуйста, установите username в настройках Telegram:\n"
                        "Настройки → Имя пользователя\n\n"
                        "После этого используйте /start для начала игры.",
                        parse_mode=self.parse_mode
                    )
                    logger.warning(f"Попытка создания профиля без username от пользователя {user.id}")
                    return

                # Автоматически создаем игровой профиль при первом сообщении
                game_user, created = self.db.get_or_create_game_user(
                    telegram_id=user.id,
                    username=user.username or f"User_{user.id}",
                    initial_balance=self.get_initial_balance()
                )
                logger.info(f"Создан игровой профиль для пользователя {user.id}")

            # Обработка специальных текстовых команд
            if user_message.lower() in ['играть', 'play', 'start game']:
                # Пользователь написал "Играть" вместо команды /play
                response = (
                    f"🎮 Добро пожаловать в игру, @{game_user.username}!\n\n"
                    f"💰 Ваш баланс: {format_coins(game_user.balance)}\n"
                    f"🏆 Побед: {game_user.wins}\n"
                    f"💔 Поражений: {game_user.losses}\n\n"
                    "Используйте /profile для просмотра профиля!"
                )
                await update.message.reply_text(
                    response,
                    parse_mode=self.parse_mode
                )
                return

            # Fallback для нераспознанных сообщений
            await update.message.reply_text(
                "❓ Команда не распознана.\n\n"
                "Используйте /help для просмотра доступных команд.",
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

        await update.message.reply_text(
            "Панель администратора:\n\n"
            "Управление юнитами и расами теперь осуществляется через веб-интерфейс.\n\n"
            "Доступные команды:\n"
            "/addmoney - Добавить монеты игроку\n"
            "/startRegistrationAmount - Изменить стартовую сумму",
            parse_mode=self.parse_mode
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
                    all_users = session.query(GameUser).order_by(GameUser.username).all()

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
                        safe_name = html.escape(player.username)

                        response += (
                            f"{i}. {safe_name}\n"
                            f"   💵 Баланс: {format_coins(player.balance)}\n"
                            f"   🏆 {player.wins}W / 💔 {player.losses}L\n\n"
                        )

                        keyboard.append([
                            InlineKeyboardButton(
                                f"💰 {player.username} ({format_coins(player.balance)})",
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

            target_user = session.query(GameUser).filter(GameUser.username == target_name).first()

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
            safe_name = html.escape(target_user.username)

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
            safe_name = html.escape(target_user.username)

            # Отправить подтверждение
            await query.edit_message_text(
                f"✅ <b>Средства успешно добавлены!</b>\n\n"
                f"Игрок: {safe_name}\n"
                f"Сумма: +{format_coins(amount)}\n"
                f"Баланс: {format_coins(old_balance)} → {format_coins(new_balance)}",
                parse_mode=self.parse_mode
            )

            logger.info(f"Администратор {username} добавил {amount} монет игроку {target_user.username} (ID: {target_telegram_id})")

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

            all_users = session.query(GameUser).order_by(GameUser.username).all()

            if not all_users:
                await query.edit_message_text("❌ В базе данных нет игроков.")
                return

            response = "💰 <b>Выберите игрока для добавления средств:</b>\n\n"

            keyboard = []
            for i, player in enumerate(all_users, 1):
                safe_name = html.escape(player.username)

                response += (
                    f"{i}. {safe_name}\n"
                    f"   💵 Баланс: {format_coins(player.balance)}\n"
                    f"   🏆 {player.wins}W / 💔 {player.losses}L\n\n"
                )

                keyboard.append([
                    InlineKeyboardButton(
                        f"💰 {player.username} ({format_coins(player.balance)})",
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
        """УСТАРЕВШИЙ - Настройка эмодзи теперь через веб-интерфейс"""
        query = update.callback_query
        await query.answer("Эта функция перенесена в веб-интерфейс.", show_alert=True)

    async def admin_edit_icon_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """УСТАРЕВШИЙ - Настройка эмодзи теперь через веб-интерфейс"""
        query = update.callback_query
        await query.answer("Эта функция перенесена в веб-интерфейс.", show_alert=True)

    async def admin_create_unit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """УСТАРЕВШИЙ - Создание юнитов теперь через веб-интерфейс"""
        query = update.callback_query
        await query.answer("Эта функция перенесена в веб-интерфейс.", show_alert=True)

    async def admin_back_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """УСТАРЕВШИЙ - Админ-панель упрощена"""
        query = update.callback_query
        await query.answer("Используйте /admin для панели администратора.", show_alert=True)

    # ================ История боёв ================

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать историю боёв пользователя"""
        user = update.effective_user
        telegram_id = str(user.id)

        with self.db.get_session() as session:
            game_user = session.query(GameUser).filter(GameUser.telegram_id == telegram_id).first()
            if not game_user:
                await update.message.reply_text(
                    "Вы не зарегистрированы в системе. Используйте /start для регистрации."
                )
                return

            await self._show_history_page(update.message, session, game_user.id, 0)

    async def _show_history_page(self, message, session, player_id: int, page: int, edit: bool = False):
        """Показать страницу истории боёв"""
        from sqlalchemy import or_, desc

        per_page = 5
        offset = page * per_page

        # Получаем завершённые игры пользователя
        games_query = session.query(Game).filter(
            Game.status == GameStatus.COMPLETED,
            or_(Game.player1_id == player_id, Game.player2_id == player_id)
        ).order_by(desc(Game.completed_at))

        total_count = games_query.count()
        games = games_query.offset(offset).limit(per_page).all()

        if not games and page == 0:
            text = "У вас пока нет завершённых боёв."
            if edit:
                await message.edit_text(text)
            else:
                await message.reply_text(text)
            return

        lines = ["<b>История ваших боёв:</b>\n"]
        keyboard = []

        for game in games:
            # Определяем результат
            is_player1 = game.player1_id == player_id
            opponent = game.player2 if is_player1 else game.player1
            opponent_name = opponent.username if opponent else "Неизвестный"
            won = game.winner_id == player_id

            result_emoji = "🏆" if won else "💀"
            result_text = "Победа" if won else "Поражение"

            date_str = game.completed_at.strftime("%d.%m.%Y %H:%M") if game.completed_at else "?"
            lines.append(f"{result_emoji} vs <b>{html.escape(opponent_name)}</b> - {result_text}")
            lines.append(f"   Поле: {game.field.name}, {date_str}")
            lines.append("")

            # Кнопка для просмотра лога
            keyboard.append([InlineKeyboardButton(
                f"📜 Лог боя #{game.id} vs {opponent_name[:10]}",
                callback_data=f"gamelog:{game.id}"
            )])

        # Пагинация
        nav_buttons = []
        total_pages = (total_count + per_page - 1) // per_page
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"history:{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"history:{page + 1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)

        lines.append(f"Страница {page + 1} из {total_pages}")

        text = "\n".join(lines)
        markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        if edit:
            await message.edit_text(text, reply_markup=markup, parse_mode='HTML')
        else:
            await message.reply_text(text, reply_markup=markup, parse_mode='HTML')

    async def history_pagination_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик пагинации истории боёв"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        telegram_id = str(user.id)
        page = int(query.data.split(":")[1])

        with self.db.get_session() as session:
            game_user = session.query(GameUser).filter(GameUser.telegram_id == telegram_id).first()
            if not game_user:
                await query.edit_message_text("Вы не зарегистрированы в системе.")
                return

            await self._show_history_page(query.message, session, game_user.id, page, edit=True)

    async def gamelog_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать лог конкретного боя: /gamelog <game_id>"""
        user = update.effective_user
        telegram_id = str(user.id)

        if not context.args:
            await update.message.reply_text(
                "Использование: /gamelog &lt;game_id&gt;\n"
                "Например: /gamelog 42\n\n"
                "Используйте /history для списка ваших боёв.",
                parse_mode='HTML'
            )
            return

        try:
            game_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Некорректный ID игры. Используйте число.")
            return

        with self.db.get_session() as session:
            game_user = session.query(GameUser).filter(GameUser.telegram_id == telegram_id).first()
            if not game_user:
                await update.message.reply_text(
                    "Вы не зарегистрированы в системе. Используйте /start для регистрации."
                )
                return

            await self._show_game_log(update.message, session, game_id, game_user.id)

    async def _show_game_log(self, message, session, game_id: int, player_id: int, edit: bool = False):
        """Показать лог боя"""
        from sqlalchemy import or_

        game = session.query(Game).filter(Game.id == game_id).first()
        if not game:
            text = f"Игра #{game_id} не найдена."
            if edit:
                await message.edit_text(text)
            else:
                await message.reply_text(text)
            return

        # Проверяем что пользователь участник этого боя
        if game.player1_id != player_id and game.player2_id != player_id:
            text = "Вы не являетесь участником этого боя."
            if edit:
                await message.edit_text(text)
            else:
                await message.reply_text(text)
            return

        # Получаем логи
        logs = session.query(GameLog).filter(
            GameLog.game_id == game_id
        ).order_by(GameLog.created_at).all()

        p1_name = game.player1.username if game.player1 else "Игрок 1"
        p2_name = game.player2.username if game.player2 else "Игрок 2"

        lines = [f"<b>Лог боя #{game_id}</b>"]
        lines.append(f"<b>{html.escape(p1_name)}</b> vs <b>{html.escape(p2_name)}</b>")
        lines.append(f"Поле: {game.field.name}")

        if game.winner_id:
            winner_name = p1_name if game.winner_id == game.player1_id else p2_name
            lines.append(f"Победитель: <b>{html.escape(winner_name)}</b>")
        lines.append("")

        if logs:
            # Показываем последние 30 событий
            recent_logs = logs[-30:] if len(logs) > 30 else logs
            if len(logs) > 30:
                lines.append(f"<i>... пропущено {len(logs) - 30} событий ...</i>\n")

            for log in recent_logs:
                time_str = log.created_at.strftime("%H:%M:%S") if log.created_at else ""
                # Иконки для типов событий
                event_icons = {
                    'game_start': '🎮',
                    'game_end': '🏁',
                    'move': '🚶',
                    'attack': '⚔️',
                    'damage': '💥',
                    'dodge': '💨',
                    'crit': '🎯',
                    'death': '💀',
                    'end_turn': '🔄',
                    'skip': '⏭️',
                    'defer': '⏸️',
                }
                icon = event_icons.get(log.event_type, '📝')
                lines.append(f"{icon} [{time_str}] {log.message}")
        else:
            lines.append("<i>Лог боя пуст.</i>")

        text = "\n".join(lines)

        # Ограничиваем длину сообщения
        if len(text) > 4000:
            text = text[:4000] + "\n... (сообщение обрезано)"

        keyboard = [[InlineKeyboardButton("« Назад к истории", callback_data="history:0")]]
        markup = InlineKeyboardMarkup(keyboard)

        if edit:
            await message.edit_text(text, reply_markup=markup, parse_mode='HTML')
        else:
            await message.reply_text(text, reply_markup=markup, parse_mode='HTML')

    async def gamelog_detail_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик просмотра лога боя по кнопке"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        telegram_id = str(user.id)
        game_id = int(query.data.split(":")[1])

        with self.db.get_session() as session:
            game_user = session.query(GameUser).filter(GameUser.telegram_id == telegram_id).first()
            if not game_user:
                await query.edit_message_text("Вы не зарегистрированы в системе.")
                return

            await self._show_game_log(query.message, session, game_id, game_user.id, edit=True)

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
        # /shop command removed - управление армиями только на веб-сайте
        application.add_handler(CommandHandler("search", self.search_command))
        application.add_handler(CommandHandler("users", self.users_command))

        # Игровые команды (бои в Godot Arena)
        application.add_handler(CommandHandler("history", self.history_command))
        application.add_handler(CommandHandler("gamelog", self.gamelog_command))

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


        # Регистрация обработчиков callback (порядок важен для правильной маршрутизации)
        application.add_handler(CallbackQueryHandler(self.buy_unit_callback, pattern=r'^buy_unit:'))
        application.add_handler(CallbackQueryHandler(self.confirm_buy_callback, pattern=r'^confirm_buy:'))
        application.add_handler(CallbackQueryHandler(self.back_to_shop_callback, pattern=r'^back_to_shop$'))
        application.add_handler(CallbackQueryHandler(self.sell_unit_callback, pattern=r'^sell_unit_'))
        application.add_handler(CallbackQueryHandler(self.show_profile_callback, pattern=r'^show_profile$'))
        application.add_handler(CallbackQueryHandler(self.search_pagination_callback, pattern=r'^search:'))
        application.add_handler(CallbackQueryHandler(self.users_pagination_callback, pattern=r'^users:'))
        application.add_handler(CallbackQueryHandler(self.user_messages_callback, pattern=r'^user_msgs:'))

        # История боёв callback обработчики
        application.add_handler(CallbackQueryHandler(self.history_pagination_callback, pattern=r'^history:'))
        application.add_handler(CallbackQueryHandler(self.gamelog_detail_callback, pattern=r'^gamelog:'))

        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Регистрация обработчика ошибок
        application.add_error_handler(self.error_handler)

        # Проверка версии и отправка уведомлений
        async def post_init(app):
            """Callback после инициализации приложения"""
            bot_changed, web_changed = self.check_version_changed()
            web_version = self.load_web_version()

            if bot_changed or web_changed:
                changes = []
                if bot_changed:
                    changes.append(f"бот={self.version}")
                if web_changed:
                    changes.append(f"веб-интерфейс={web_version}")
                logger.info(f"Обнаружены обновления: {', '.join(changes)}")
                await self.notify_all_users_about_update(app, bot_changed, web_changed)
                self.save_current_version()
            else:
                logger.info(f"Версии не изменились: бот={self.version}, веб-интерфейс={web_version}")

        application.post_init = post_init

        # Запуск бота
        logger.info("Бот запущен и ожидает сообщения...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Главная функция"""
    try:
        bot = SimpleBot()
        # Запускаем API сервер для health check и версии
        api_port = int(os.getenv('BOT_API_PORT', 8080))
        start_api_server(bot, port=api_port)
        bot.run()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise


if __name__ == '__main__':
    main()
