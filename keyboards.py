from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Аккаунты")],
            [KeyboardButton(text="✉️ Сообщения"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="📜 История")]
        ],
        resize_keyboard=True
    )
    return keyboard

def accounts_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить аккаунт")],
            [KeyboardButton(text="📋 Список аккаунтов")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard

def messages_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Создать сообщение")],
            [KeyboardButton(text="📋 Активные задачи")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard

def account_actions(account_id: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_acc_{account_id}")]
        ]
    )
    return keyboard

def confirm_delete(account_id: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_del_{account_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data="cancel_del")
            ]
        ]
    )
    return keyboard

def account_selection(accounts: list, selected: list = []):
    buttons = []
    for acc in accounts:
        check = "✅" if acc.id in selected else "⬜️"
        buttons.append([InlineKeyboardButton(
            text=f"{check} {acc.first_name or acc.phone}",
            callback_data=f"toggle_acc_{acc.id}"
        )])
    buttons.append([InlineKeyboardButton(text="✔️ Готово", callback_data="accounts_done")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
