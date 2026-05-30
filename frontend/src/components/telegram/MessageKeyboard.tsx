import type { MessageButton, MessageKeyboard } from "../../api/client";

interface InlineKeyboardProps {
  keyboard: MessageKeyboard;
  disabled?: boolean;
  onClick: (row: number, col: number, button: MessageButton) => void;
}

export function InlineKeyboard({ keyboard, disabled, onClick }: InlineKeyboardProps) {
  if (keyboard.type !== "inline") return null;

  return (
    <div className="tg-inline-keyboard">
      {keyboard.rows.map((row, rowIndex) => (
        <div className="tg-keyboard-row" key={`row-${rowIndex}`}>
          {row.map((button, colIndex) => (
            <button
              key={`${rowIndex}-${colIndex}-${button.text}`}
              type="button"
              className="tg-keyboard-btn"
              disabled={disabled}
              onClick={() => onClick(rowIndex, colIndex, button)}
            >
              {button.text}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

interface ReplyKeyboardProps {
  keyboard: MessageKeyboard;
  disabled?: boolean;
  onClick: (text: string) => void;
}

export function ReplyKeyboard({ keyboard, disabled, onClick }: ReplyKeyboardProps) {
  if (keyboard.type !== "reply") return null;

  return (
    <div className="tg-reply-keyboard">
      {keyboard.rows.map((row, rowIndex) => (
        <div className="tg-keyboard-row" key={`reply-row-${rowIndex}`}>
          {row.map((button) => (
            <button
              key={`${rowIndex}-${button.text}`}
              type="button"
              className="tg-reply-keyboard-btn"
              disabled={disabled}
              onClick={() => onClick(button.text)}
            >
              {button.text}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
