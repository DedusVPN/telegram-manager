import { FormEvent, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  Bot,
  ChevronDown,
  Keyboard,
  Loader2,
  Menu,
  MessageSquare,
  Radio,
  RefreshCw,
  Search,
  Send,
  Smartphone,
  User,
  Users,
} from "lucide-react";
import { Account, BotCommand, ChatMessage, Dialog, MessageButton, MessageKeyboard, api } from "../api/client";
import { Icon } from "../components/Icon";
import { ChatAvatar } from "../components/telegram/ChatAvatar";
import { formatDialogPreview, formatDialogTime } from "../components/telegram/chatUtils";
import { MessageList } from "../components/telegram/MessageBubble";
import { ReplyKeyboard } from "../components/telegram/MessageKeyboard";
import { findActiveReplyKeyboard, mergeReplyKeyboard } from "../components/telegram/types";

function isUsernameQuery(value: string): boolean {
  const normalized = value.trim().replace(/^@/, "");
  return /^[a-zA-Z][a-zA-Z0-9_]{4,31}$/.test(normalized);
}

function getDialogIcon(dialog: Dialog) {
  if (dialog.is_bot) return Bot;
  if (dialog.is_channel) return Radio;
  if (dialog.is_group) return Users;
  return User;
}

export function ChatsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [dialogs, setDialogs] = useState<Dialog[]>([]);
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [replyKeyboard, setReplyKeyboard] = useState<MessageKeyboard | null>(null);
  const [botCommands, setBotCommands] = useState<BotCommand[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [keyboardVisible, setKeyboardVisible] = useState(true);
  const [text, setText] = useState("");
  const [filterQuery, setFilterQuery] = useState("");
  const [loadingDialogs, setLoadingDialogs] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [searchingUsername, setSearchingUsername] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const filteredDialogs = useMemo(() => {
    const query = filterQuery.trim().toLowerCase().replace(/^@/, "");
    if (!query) {
      return dialogs;
    }
    return dialogs.filter(
      (dialog) =>
        dialog.title.toLowerCase().includes(query) ||
        (dialog.username && dialog.username.toLowerCase().includes(query)),
    );
  }, [dialogs, filterQuery]);

  const activeReplyKeyboard = useMemo(
    () => mergeReplyKeyboard(findActiveReplyKeyboard(messages), replyKeyboard),
    [messages, replyKeyboard],
  );

  const reloadMessages = useCallback(async () => {
    if (!selectedAccountId || !selectedChatId) return;
    const [data, keyboard, commands] = await Promise.all([
      api.getMessages(selectedAccountId, selectedChatId),
      api.getActiveKeyboard(selectedAccountId, selectedChatId),
      api.getBotCommands(selectedAccountId, selectedChatId).catch(() => [] as BotCommand[]),
    ]);
    setMessages([...data].reverse());
    setReplyKeyboard(keyboard);
    setBotCommands(commands);
    if (keyboard?.rows?.length) {
      setKeyboardVisible(true);
    }
    await api.markChatRead(selectedAccountId, selectedChatId).catch(() => null);
    setDialogs((current) =>
      current.map((dialog) =>
        dialog.id === selectedChatId ? { ...dialog, unread_count: 0 } : dialog,
      ),
    );
  }, [selectedAccountId, selectedChatId]);

  const reloadDialogs = useCallback(async () => {
    if (!selectedAccountId) return;
    setLoadingDialogs(true);
    setError("");
    try {
      const data = await api.getDialogs(selectedAccountId);
      setDialogs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки чатов");
    } finally {
      setLoadingDialogs(false);
    }
  }, [selectedAccountId]);

  const scrollMessagesToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
    const pane = messagesRef.current;
    if (!pane) return;
    pane.scrollTo({ top: pane.scrollHeight, behavior });
  }, []);

  useEffect(() => {
    api.getAccounts()
      .then((data) => {
        const active = data.filter((account) => account.is_active);
        setAccounts(active);
        if (active.length > 0) {
          setSelectedAccountId(active[0].id);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Ошибка"));
  }, []);

  useEffect(() => {
    if (!selectedAccountId) return;
    setSelectedChatId(null);
    setMessages([]);
    setReplyKeyboard(null);
    setBotCommands([]);
    setMenuOpen(false);
    setKeyboardVisible(true);
    setFilterQuery("");
    void reloadDialogs();
  }, [selectedAccountId, reloadDialogs]);

  useEffect(() => {
    if (!selectedAccountId || !selectedChatId) return;
    setLoadingMessages(true);
    setMenuOpen(false);
    reloadMessages()
      .catch((err) => setError(err instanceof Error ? err.message : "Ошибка загрузки сообщений"))
      .finally(() => setLoadingMessages(false));
  }, [selectedAccountId, selectedChatId, reloadMessages]);

  useLayoutEffect(() => {
    if (loadingMessages || messages.length === 0) return;

    scrollMessagesToBottom("auto");

    // Повтор после отрисовки (аватарки, клавиатура, inline-кнопки)
    const frame = requestAnimationFrame(() => {
      scrollMessagesToBottom("auto");
    });
    const timer = window.setTimeout(() => scrollMessagesToBottom("auto"), 100);

    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(timer);
    };
  }, [messages, loadingMessages, keyboardVisible, replyKeyboard, scrollMessagesToBottom]);

  useEffect(() => {
    if (!menuOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [menuOpen]);

  function openDialog(dialog: Dialog) {
    setDialogs((current) => {
      if (current.some((item) => item.id === dialog.id)) {
        return current.map((item) => (item.id === dialog.id ? { ...item, ...dialog } : item));
      }
      return [dialog, ...current];
    });
    setSelectedChatId(dialog.id);
    setError("");
  }

  async function handleUsernameSearch(event: FormEvent) {
    event.preventDefault();
    if (!selectedAccountId || !filterQuery.trim()) return;

    setSearchingUsername(true);
    setError("");
    try {
      const dialog = await api.searchByUsername(selectedAccountId, filterQuery.trim());
      openDialog(dialog);
      setFilterQuery("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Username не найден");
    } finally {
      setSearchingUsername(false);
    }
  }

  async function handleSendMessage(messageText: string) {
    if (!selectedAccountId || !selectedChatId || !messageText.trim()) return;

    setActionLoading(true);
    setError("");
    try {
      const result = await api.sendMessage(selectedAccountId, selectedChatId, messageText.trim());
      if (result.status !== "success") {
        throw new Error(result.error || "Не удалось отправить сообщение");
      }
      await reloadMessages();
      void reloadDialogs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка отправки");
      throw err;
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSend(event: FormEvent) {
    event.preventDefault();
    const messageText = text.trim();
    if (!messageText) return;
    setText("");
    try {
      await handleSendMessage(messageText);
    } catch {
      setText(messageText);
    }
  }

  function handleComposeKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!actionLoading && text.trim()) {
        void handleSend(event as unknown as FormEvent);
      }
    }
  }

  async function handleInlineClick(
    messageId: number,
    row: number,
    col: number,
    button: MessageButton,
  ) {
    if (!selectedAccountId || !selectedChatId) return;

    if (button.url) {
      window.open(button.url, "_blank", "noopener,noreferrer");
      return;
    }

    if (button.copy_text) {
      await navigator.clipboard.writeText(button.copy_text);
      return;
    }

    setActionLoading(true);
    setError("");
    try {
      await api.clickMessageButton(selectedAccountId, selectedChatId, messageId, { row, col });
      await new Promise((resolve) => setTimeout(resolve, 700));
      await reloadMessages();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка нажатия кнопки");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReplyKeyboardClick(buttonText: string) {
    try {
      await handleSendMessage(buttonText);
    } catch {
      /* error already shown */
    }
  }

  const selectedDialog =
    dialogs.find((dialog) => dialog.id === selectedChatId) ||
    filteredDialogs.find((dialog) => dialog.id === selectedChatId);
  const canSearchUsername = isUsernameQuery(filterQuery);
  const isGroupChat = Boolean(selectedDialog?.is_group || selectedDialog?.is_channel);
  const isBotChat = Boolean(selectedDialog?.is_bot);
  const showReplyKeyboard = Boolean(activeReplyKeyboard?.rows?.length && keyboardVisible);
  const selectedAccount = accounts.find((account) => account.id === selectedAccountId) ?? null;

  return (
    <div className={`chats-page${selectedChatId ? " chats-page--chat-open" : ""}`}>
      {error ? <div className="error-banner">{error}</div> : null}

      <div className="chat-layout card tg-chat-shell">
        <aside className="dialog-list">
          <div className="dialog-list-header">
            <div className="dialog-list-title">
              <h2>Диалоги</h2>
              <span>{filteredDialogs.length}</span>
            </div>
            <div className="dialog-list-toolbar">
              <label className="account-select-wrap">
                <Icon icon={Smartphone} size="sm" className="account-select-icon" />
                <select
                  className="account-select"
                  value={selectedAccountId ?? ""}
                  onChange={(event) => setSelectedAccountId(Number(event.target.value))}
                >
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.first_name || account.phone}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="icon-btn"
                title="Обновить список"
                disabled={loadingDialogs || !selectedAccountId}
                onClick={() => void reloadDialogs()}
              >
                <Icon icon={RefreshCw} size="sm" className={loadingDialogs ? "spin" : undefined} />
              </button>
            </div>
          </div>

          <form className="dialog-search" onSubmit={handleUsernameSearch}>
            <div className="input-with-icon dialog-search-input">
              <Icon icon={Search} size="sm" className="input-icon" />
              <input
                value={filterQuery}
                onChange={(event) => setFilterQuery(event.target.value)}
                placeholder="Поиск или @username"
              />
            </div>
            {canSearchUsername ? (
              <button
                className="btn btn-with-icon dialog-search-btn"
                type="submit"
                disabled={searchingUsername}
                title="Искать в Telegram"
              >
                {searchingUsername ? (
                  <Icon icon={Loader2} size="sm" className="spin" />
                ) : (
                  <Icon icon={Search} size="sm" />
                )}
              </button>
            ) : null}
          </form>

          <div className="dialog-list-scroll">
            {loadingDialogs ? (
              <div className="empty-state">
                <Icon icon={Loader2} size="lg" className="empty-state-icon spin" />
                Загрузка чатов...
              </div>
            ) : filteredDialogs.length === 0 ? (
              <div className="empty-state">
                <Icon icon={MessageSquare} size="xl" className="empty-state-icon" />
                {filterQuery
                  ? canSearchUsername
                    ? "В списке нет совпадений. Нажмите поиск для глобального поиска."
                    : "Ничего не найдено"
                  : "Чаты не найдены"}
              </div>
            ) : (
              filteredDialogs.map((dialog) => (
                <button
                  key={dialog.id}
                  type="button"
                  className={`dialog-item ${selectedChatId === dialog.id ? "active" : ""}`}
                  onClick={() => {
                    setSelectedChatId(dialog.id);
                    setDialogs((current) =>
                      current.map((item) =>
                        item.id === dialog.id ? { ...item, unread_count: 0 } : item,
                      ),
                    );
                  }}
                >
                  <ChatAvatar
                    accountId={selectedAccountId}
                    chatId={dialog.id}
                    title={dialog.title}
                    hasAvatar={dialog.has_avatar}
                    fallbackIcon={getDialogIcon(dialog)}
                    size="md"
                  />
                  <span className="dialog-item-content">
                    <span className="dialog-item-top">
                      <strong>{dialog.title}</strong>
                      <span className="dialog-item-meta">
                        {formatDialogTime(dialog.last_message?.date)}
                      </span>
                    </span>
                    <span className="dialog-item-bottom">
                      <small>{formatDialogPreview(dialog)}</small>
                      {dialog.unread_count > 0 ? (
                        <span className="dialog-unread">{dialog.unread_count}</span>
                      ) : null}
                    </span>
                  </span>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="chat-panel tg-chat-panel">
          {selectedChatId && selectedDialog ? (
            <>
              <div className="chat-panel-header tg-chat-header">
                <button
                  type="button"
                  className="chat-back-btn"
                  title="К списку чатов"
                  onClick={() => setSelectedChatId(null)}
                >
                  <Icon icon={ArrowLeft} size="md" />
                </button>
                <ChatAvatar
                  accountId={selectedAccountId}
                  chatId={selectedDialog.id}
                  title={selectedDialog.title}
                  hasAvatar={selectedDialog.has_avatar}
                  fallbackIcon={getDialogIcon(selectedDialog)}
                  size="lg"
                  className="tg-chat-header-avatar"
                />
                <div className="tg-chat-header-info">
                  <strong>{selectedDialog.title}</strong>
                  <div className="tg-chat-header-subtitle">
                    {selectedDialog.username
                      ? `@${selectedDialog.username}`
                      : selectedDialog.is_bot
                        ? "бот"
                        : selectedDialog.is_group
                          ? "группа"
                          : selectedDialog.is_channel
                            ? "канал"
                            : "личный чат"}
                    {selectedAccount ? ` · ${selectedAccount.phone}` : ""}
                  </div>
                </div>
                <button
                  type="button"
                  className="icon-btn"
                  title="Обновить сообщения"
                  disabled={loadingMessages || actionLoading}
                  onClick={() => void reloadMessages()}
                >
                  <Icon icon={RefreshCw} size="sm" className={loadingMessages ? "spin" : undefined} />
                </button>
              </div>

              <div className="messages-pane tg-messages-pane" ref={messagesRef}>
                {loadingMessages ? (
                  <div className="empty-state">
                    <Icon icon={Loader2} size="lg" className="empty-state-icon spin" />
                    Загрузка сообщений...
                  </div>
                ) : (
                  <MessageList
                    messages={messages}
                    isGroup={isGroupChat}
                    peerAvatar={
                      selectedDialog
                        ? {
                            accountId: selectedAccountId,
                            chatId: selectedDialog.id,
                            title: selectedDialog.title,
                            hasAvatar: selectedDialog.has_avatar,
                            fallbackIcon: getDialogIcon(selectedDialog),
                          }
                        : undefined
                    }
                    disabled={actionLoading}
                    onInlineClick={handleInlineClick}
                  />
                )}
              </div>

              {activeReplyKeyboard?.rows?.length && !keyboardVisible ? (
                <button
                  type="button"
                  className="tg-keyboard-restore"
                  onClick={() => setKeyboardVisible(true)}
                  title="Показать клавиатуру"
                >
                  <Icon icon={Keyboard} size="md" />
                </button>
              ) : null}

              <form className="compose-bar tg-compose-bar" onSubmit={handleSend}>
                {isBotChat && botCommands.length > 0 ? (
                  <div className="tg-menu-wrap" ref={menuRef}>
                    <button
                      type="button"
                      className="tg-menu-btn btn-with-icon"
                      onClick={() => setMenuOpen((open) => !open)}
                      disabled={actionLoading}
                    >
                      <Icon icon={Menu} size="sm" />
                      Меню
                    </button>
                    {menuOpen ? (
                      <div className="tg-menu-dropdown">
                        {botCommands.map((command) => (
                          <button
                            key={command.command}
                            type="button"
                            onClick={() => {
                              setMenuOpen(false);
                              void handleSendMessage(`/${command.command}`);
                            }}
                          >
                            <span>/{command.command}</span>
                            <small>{command.description}</small>
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
                <textarea
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  onKeyDown={handleComposeKeyDown}
                  placeholder="Сообщение… Enter — отправить"
                  rows={1}
                  disabled={actionLoading}
                />
                {showReplyKeyboard ? (
                  <button
                    type="button"
                    className="tg-keyboard-toggle"
                    onClick={() => setKeyboardVisible(false)}
                    title="Скрыть клавиатуру"
                    disabled={actionLoading}
                  >
                    <Icon icon={ChevronDown} size="md" />
                  </button>
                ) : null}
                <button
                  className="btn tg-send-btn"
                  type="submit"
                  disabled={actionLoading || !text.trim()}
                  title="Отправить"
                >
                  <Icon icon={Send} size="md" />
                </button>
              </form>

              {showReplyKeyboard && activeReplyKeyboard ? (
                <ReplyKeyboard
                  keyboard={activeReplyKeyboard}
                  disabled={actionLoading}
                  onClick={handleReplyKeyboardClick}
                />
              ) : null}
            </>
          ) : (
            <div className="chat-empty-pane">
              <Icon icon={MessageSquare} size="xl" className="empty-state-icon" />
              <strong>Выберите чат</strong>
              <p>Найдите диалог слева или введите @username для глобального поиска</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
