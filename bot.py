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
from database import Database


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
            "Доступные команды:\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n"
            "/search <username> - Поиск сообщений пользователя"
        )
        await update.message.reply_text(help_text, parse_mode=self.parse_mode)
        logger.info(f"Команда /help от пользователя {update.effective_user.id}")

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

            # Формируем ответ с упоминанием username
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

        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("search", self.search_command))
        application.add_handler(CallbackQueryHandler(self.search_pagination_callback))
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
