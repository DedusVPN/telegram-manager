from telethon.extensions import html
from telethon.tl.types import ReplyInlineMarkup, ReplyKeyboardHide, ReplyKeyboardMarkup


def _button_from_dict(button: dict) -> dict:
    payload = {"text": button.get("text") or ""}

    if button.get("url"):
        payload["url"] = button["url"]

    data = button.get("data")
    if data is not None:
        payload["callback_data"] = (
            data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
        )

    if button.get("query") is not None:
        payload["switch_inline_query"] = button["query"]

    if button.get("copy_text"):
        payload["copy_text"] = button["copy_text"]

    return payload


def serialize_reply_markup(markup) -> dict | None:
    if not markup:
        return None

    if isinstance(markup, ReplyKeyboardHide):
        return None

    if hasattr(markup, "to_dict"):
        raw = markup.to_dict()
        markup_type = raw.get("_")
        if markup_type == "ReplyKeyboardHide":
            return None
        if markup_type == "ReplyInlineMarkup":
            return {
                "type": "inline",
                "rows": [
                    [_button_from_dict(button) for button in row.get("buttons", [])]
                    for row in raw.get("rows", [])
                ],
            }
        if markup_type == "ReplyKeyboardMarkup":
            return {
                "type": "reply",
                "rows": [
                    [_button_from_dict(button) for button in row.get("buttons", [])]
                    for row in raw.get("rows", [])
                ],
                "resize": bool(raw.get("resize")),
                "one_time": bool(raw.get("single_use")),
                "persistent": bool(raw.get("persistent")),
            }

    if isinstance(markup, ReplyInlineMarkup):
        return {
            "type": "inline",
            "rows": [
                [_button_from_dict(button.to_dict()) for button in row.buttons]
                for row in markup.rows
            ],
        }

    if isinstance(markup, ReplyKeyboardMarkup):
        return {
            "type": "reply",
            "rows": [
                [_button_from_dict(button.to_dict()) for button in row.buttons]
                for row in markup.rows
            ],
            "resize": bool(markup.resize),
            "one_time": bool(markup.single_use),
            "persistent": bool(getattr(markup, "persistent", False)),
        }

    return None


def message_to_dict(message) -> dict:
    text = message.message or ""
    entities = message.entities or []
    sender_name = None
    if message.sender:
        sender_name = getattr(message.sender, "first_name", None) or getattr(
            message.sender, "title", None
        )

    reply_markup = serialize_reply_markup(message.reply_markup)

    return {
        "id": message.id,
        "text": text,
        "text_html": html.unparse(text, entities) if text else "",
        "date": message.date.isoformat() if message.date else None,
        "out": message.out,
        "sender_id": message.sender_id,
        "sender_name": sender_name,
        "reply_markup": reply_markup,
        "edit_date": message.edit_date.isoformat() if message.edit_date else None,
    }


def pick_active_reply_keyboard(messages: list[dict]) -> dict | None:
    best: dict | None = None
    best_id = 0

    for message in messages:
        markup = message.get("reply_markup")
        if not markup or markup.get("type") != "reply":
            continue
        if not markup.get("rows"):
            continue
        if message["id"] > best_id:
            best = markup
            best_id = message["id"]

    return best
