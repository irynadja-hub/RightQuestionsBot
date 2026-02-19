import asyncio
import json
import os
import random
from typing import Dict, List
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ---------- Налаштування ----------
QUESTIONS_FILE = "questions.json"
QUESTIONS_PER_TEST = 20
FUN_EMOJIS = ["🔥", "🚀", "🎯", "💪", "🏆", "😎", "✨", "🥳", "🤟"]
BUTTON_TEXT_LIMIT = 60  # щоб точно влізло (Telegram має ліміт на текст кнопки)

# ---------- Завантаження питань ----------
def load_questions() -> List[dict]:
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # базова валідація (щоб не зламалося посеред тесту)
    for q in data:
        if "situation" not in q or "answers" not in q or "correct_idx" not in q:
            raise ValueError("Кожне питання має містити: situation, answers, correct_idx")
        if not isinstance(q["answers"], list) or len(q["answers"]) != 4:
            raise ValueError("Кожне питання має містити рівно 4 answers")
        if int(q["correct_idx"]) not in (0, 1, 2, 3):
            raise ValueError("correct_idx має бути 0..3")

    return data

ALL_QUESTIONS = load_questions()

# ---------- Сесії ----------
class Session:
    def __init__(self, questions: List[dict]):
        self.questions = questions
        self.current_index = 0
        self.score = 0

    def current_question(self):
        if self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

SESSIONS: Dict[int, Session] = {}

# ---------- UI helpers ----------
def _truncate_for_button(text: str, limit: int = BUTTON_TEXT_LIMIT) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"

def build_answers_keyboard(answers: List[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=_truncate_for_button(ans), callback_data=f"ans:{i}")]
        for i, ans in enumerate(answers)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_restart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Пройти ще раз", callback_data="restart")]
        ]
async def start_health_server() -> None:
    app = web.Application()

    async def root(request: web.Request) -> web.Response:
        return web.Response(text="RightQuestionsBot is alive ✅")

    async def health(request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app.router.add_get("/", root)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()


    )

# ---------- Логіка ----------
async def send_question(message: Message, session: Session):
    q = session.current_question()

    if not q:
        await message.answer(
            f"✅ Тест завершено!\n\n"
            f"Твій результат: {session.score}/{QUESTIONS_PER_TEST}\n\n"
            f"Хочеш спробувати ще раз?",
            reply_markup=build_restart_keyboard(),
        )
        return

    num = session.current_index + 1
    total = len(session.questions)

    await message.answer(
        f"Питання {num}/{total}\n\n<b>{q['situation']}</b>",
    reply_markup=build_answers_keyboard(q["answers"]),
    parse_mode="HTML",
    )

def start_new_session(user_id: int) -> Session:
    selected = random.sample(ALL_QUESTIONS, QUESTIONS_PER_TEST)
    session = Session(selected)
    SESSIONS[user_id] = session
    return session

async def main():
    if not TOKEN:
        raise RuntimeError("Нема BOT_TOKEN у .env")

    bot = Bot(token=TOKEN)
    dp = Dispatcher()
await start_health_server()
await dp.start_polling(bot)

    @dp.message(Command("start"))
    async def start_handler(message: Message):
        user_name = message.from_user.first_name or "друже/подруго"

        session = start_new_session(message.from_user.id)

        await message.answer(
            f"Привіт, {user_name} 👋\n\n"
            f"Перевір свої знання відповівши на 20 питань.\n"
            f"Обирай відповідь на кнопці.\n\n"
            f"Готов(а)? 🚀"
        )

        await send_question(message, session)

    @dp.callback_query(F.data == "restart")
    async def restart_handler(callback: CallbackQuery):
        # прибираємо кнопку з попереднього повідомлення (щоб не тицяли 100 разів)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        session = start_new_session(callback.from_user.id)
        await callback.answer("Поїхали! 🚀")

        # Відправляємо перше питання
        await send_question(callback.message, session)

    @dp.callback_query(F.data.startswith("ans:"))
    async def answer_handler(callback: CallbackQuery):
        user_id = callback.from_user.id
        session = SESSIONS.get(user_id)

        if not session:
            await callback.answer("Натисни /start", show_alert=True)
            return

        q = session.current_question()
        if not q:
            await callback.answer()
            return

        chosen_index = int(callback.data.split(":")[1])

        correct_index = int(q["correct_idx"])
        correct_answer = q["answers"][correct_index]

        # прибираємо кнопки з питання
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        # фідбек
        if chosen_index == correct_index:
            session.score += 1
            emoji = random.choice(FUN_EMOJIS)
            await callback.message.answer(f"{emoji} Вірно!")
        else:
            await callback.message.answer(
                f"Не вірно.\nПравильна відповідь – {correct_answer}"
            )

        # наступне питання
        session.current_index += 1
        await callback.answer()
        await send_question(callback.message, session)

   await start_health_server()
await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
