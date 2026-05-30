import type { LucideIcon } from "lucide-react";
import type { ChatMessage } from "../../api/client";
import { ChatAvatar } from "./ChatAvatar";
import { formatMessageTime, shouldGroupMessages, formatDateLabel } from "./types";
import { InlineKeyboard } from "./MessageKeyboard";
import type { MessageButton } from "../../api/client";

interface PeerAvatarInfo {
  accountId: number | null;
  chatId: string;
  title: string;
  hasAvatar?: boolean;
  fallbackIcon?: LucideIcon;
}

interface MessageBubbleProps {
  message: ChatMessage;
  grouped: boolean;
  showSender: boolean;
  showAvatar: boolean;
  peerAvatar?: PeerAvatarInfo;
  disabled?: boolean;
  onInlineClick: (messageId: number, row: number, col: number, button: MessageButton) => void;
}

export function MessageBubble({
  message,
  grouped,
  showSender,
  showAvatar,
  peerAvatar,
  disabled,
  onInlineClick,
}: MessageBubbleProps) {
  const html = message.text_html || message.text.replace(/\n/g, "<br>");

  return (
    <div className={`tg-message-row ${message.out ? "outgoing" : "incoming"} ${grouped ? "grouped" : ""}`}>
      {!message.out && peerAvatar ? (
        <div className={`tg-message-avatar-slot${showAvatar ? "" : " tg-message-avatar-slot-empty"}`}>
          {showAvatar ? (
            <ChatAvatar
              accountId={peerAvatar.accountId}
              chatId={peerAvatar.chatId}
              title={peerAvatar.title}
              hasAvatar={peerAvatar.hasAvatar}
              fallbackIcon={peerAvatar.fallbackIcon}
              size="sm"
            />
          ) : null}
        </div>
      ) : null}
      <div className={`tg-message-bubble ${message.out ? "outgoing" : "incoming"}`}>
        {showSender && message.sender_name ? (
          <div className="tg-message-sender">{message.sender_name}</div>
        ) : null}
        <div className="tg-message-content">
          <div
            className="tg-message-text"
            dangerouslySetInnerHTML={{ __html: html || "—" }}
          />
          <span className="tg-message-time">
            {message.edit_date ? "изм. " : ""}
            {formatMessageTime(message.date)}
          </span>
        </div>
        {message.reply_markup?.type === "inline" && message.reply_markup.rows?.length ? (
          <InlineKeyboard
            keyboard={message.reply_markup}
            disabled={disabled}
            onClick={(row, col, button) => onInlineClick(message.id, row, col, button)}
          />
        ) : null}
      </div>
    </div>
  );
}

interface MessageListProps {
  messages: ChatMessage[];
  isGroup: boolean;
  peerAvatar?: PeerAvatarInfo;
  disabled?: boolean;
  onInlineClick: (messageId: number, row: number, col: number, button: MessageButton) => void;
}

export function MessageList({ messages, isGroup, peerAvatar, disabled, onInlineClick }: MessageListProps) {
  const items: JSX.Element[] = [];
  let previous: ChatMessage | null = null;
  let previousDate = "";

  messages.forEach((message) => {
    const dateLabel = message.date ? new Date(message.date).toDateString() : "";
    if (dateLabel && dateLabel !== previousDate) {
      previousDate = dateLabel;
      items.push(
        <div className="tg-date-separator" key={`date-${dateLabel}-${message.id}`}>
          <span>{formatDateLabel(message.date)}</span>
        </div>,
      );
    }

    const grouped = shouldGroupMessages(message, previous);
    const showAvatar = Boolean(peerAvatar) && !message.out && !grouped && !isGroup;

    items.push(
      <MessageBubble
        key={message.id}
        message={message}
        grouped={grouped}
        showSender={isGroup && !message.out && !grouped}
        showAvatar={showAvatar}
        peerAvatar={peerAvatar}
        disabled={disabled}
        onInlineClick={onInlineClick}
      />,
    );
    previous = message;
  });

  return <>{items}</>;
}
