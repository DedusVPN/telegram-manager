import type { Dialog } from "../../api/client";

export function formatDialogTime(date: string | null | undefined): string {
  if (!date) return "";
  const value = new Date(date);
  const now = new Date();
  const sameDay = value.toDateString() === now.toDateString();
  if (sameDay) {
    return value.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  }
  const yesterday = new Date();
  yesterday.setDate(now.getDate() - 1);
  if (value.toDateString() === yesterday.toDateString()) {
    return "вчера";
  }
  return value.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

export function formatDialogPreview(dialog: Dialog): string {
  const text = dialog.last_message?.text?.replace(/\s+/g, " ").trim();
  if (!text) return "Нет сообщений";
  const prefix = dialog.last_message?.out ? "Вы: " : "";
  const preview = `${prefix}${text}`;
  return preview.length > 72 ? `${preview.slice(0, 72)}…` : preview;
}
