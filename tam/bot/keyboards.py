from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Аккаунты")],
            [KeyboardButton(text="✉️ Сообщения"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="📜 История")],
        ],
        resize_keyboard=True,
    )


def accounts_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить аккаунт")],
            [KeyboardButton(text="📋 Список аккаунтов")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )


def messages_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Создать сообщение")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )


def account_selection(accounts: list, selected: list | None = None):
    if selected is None:
        selected = []
    buttons = []
    for acc in accounts:
        check = "✅" if acc.id in selected else "⬜️"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{check} {acc.first_name or acc.phone}",
                    callback_data=f"toggle_acc_{acc.id}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="✔️ Готово", callback_data="accounts_done")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
