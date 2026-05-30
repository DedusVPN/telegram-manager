import type { ChatMessage, MessageKeyboard } from "../../api/client";

export type { ChatMessage, MessageButton, MessageKeyboard } from "../../api/client";

export function formatMessageTime(date: string | null): string {
  if (!date) return "";
  return new Date(date).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

export function formatDateLabel(date: string | null): string {
  if (!date) return "";
  const value = new Date(date);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  if (value.toDateString() === today.toDateString()) return "Сегодня";
  if (value.toDateString() === yesterday.toDateString()) return "Вчера";
  return value.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
}

export function findActiveReplyKeyboard(messages: ChatMessage[]): MessageKeyboard | null {
  let best: MessageKeyboard | null = null;
  let bestId = 0;

  for (const message of messages) {
    const markup = message.reply_markup;
    if (!markup || markup.type !== "reply" || !markup.rows?.length) {
      continue;
    }
    if (message.id > bestId) {
      best = markup;
      bestId = message.id;
    }
  }

  return best;
}

export function shouldGroupMessages(current: ChatMessage, previous: ChatMessage | null): boolean {
  if (!previous) return false;
  if (current.out !== previous.out) return false;
  if (current.sender_id !== previous.sender_id) return false;
  if (!current.date || !previous.date) return false;
  return Math.abs(new Date(current.date).getTime() - new Date(previous.date).getTime()) < 5 * 60 * 1000;
}

export function mergeReplyKeyboard(
  fromMessages: MessageKeyboard | null,
  fromApi: MessageKeyboard | null,
): MessageKeyboard | null {
  return fromApi || fromMessages;
}
