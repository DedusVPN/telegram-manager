const TOKEN_KEY = "tam_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const isAuthRequest = path.startsWith("/api/auth/login");
  const token = getToken();
  if (token && !isAuthRequest) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(path, { ...options, headers });

  if (!response.ok) {
    let detail = "Ошибка запроса";
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch {
        /* ignore */
      }
    } else {
      detail = `Сервер вернул некорректный ответ (${response.status}). Перезапустите backend.`;
    }

    if (response.status === 401 && !isAuthRequest) {
      clearToken();
      window.location.href = "/login";
    }

    throw new Error(typeof detail === "string" ? detail : "Ошибка запроса");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error("Сервер вернул некорректный ответ. Перезапустите backend.");
  }

  return response.json() as Promise<T>;
}

export async function fetchChatAvatarUrl(accountId: number, chatId: string): Promise<string | null> {
  const cacheKey = `${accountId}:${chatId}`;
  if (avatarUrlCache.has(cacheKey)) {
    return avatarUrlCache.get(cacheKey)!;
  }

  const token = getToken();
  if (!token) return null;

  const response = await fetch(`/api/accounts/${accountId}/chats/${encodeURIComponent(chatId)}/avatar`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    avatarUrlCache.set(cacheKey, null);
    return null;
  }

  const blob = await response.blob();
  if (!blob.size) {
    avatarUrlCache.set(cacheKey, null);
    return null;
  }

  const url = URL.createObjectURL(blob);
  avatarUrlCache.set(cacheKey, url);
  return url;
}

const avatarUrlCache = new Map<string, string | null>();

export interface Account {
  id: number;
  phone: string;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Dialog {
  id: string;
  title: string;
  unread_count: number;
  is_user: boolean;
  is_group: boolean;
  is_channel: boolean;
  is_bot?: boolean;
  has_avatar?: boolean;
  username: string | null;
  last_message: {
    id: number;
    text: string;
    date: string | null;
    out: boolean;
  } | null;
}

export interface BotCommand {
  command: string;
  description: string;
}

export interface MessageButton {
  text: string;
  url?: string | null;
  callback_data?: string | null;
  switch_inline_query?: string | null;
  copy_text?: string | null;
}

export interface MessageKeyboard {
  type: "inline" | "reply";
  rows: MessageButton[][];
  resize?: boolean | null;
  one_time?: boolean | null;
  persistent?: boolean | null;
}

export interface ChatMessage {
  id: number;
  text: string;
  text_html: string;
  date: string | null;
  out: boolean;
  sender_id: number | null;
  sender_name: string | null;
  reply_markup: MessageKeyboard | null;
  edit_date: string | null;
}

export interface Stats {
  success: number;
  pending: number;
  error: number;
  flood_wait: number;
  forbidden: number;
}

export interface HistoryMessage {
  id: number;
  account_id: number;
  target_chat: string;
  text: string;
  status: string;
  sent_at: string | null;
  error: string | null;
  created_at: string;
}

export interface TaskItem {
  id: number;
  target_chat: string;
  message_text: string;
  account_ids: string;
  repeat_count: number;
  interval: number;
  account_delay: number;
  status: string;
  created_at: string;
}

export const api = {
  login(password: string) {
    return request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
  },

  getAccounts(search?: string) {
    const params = search ? `?search=${encodeURIComponent(search)}` : "";
    return request<Account[]>(`/api/accounts${params}`);
  },

  deleteAccount(id: number) {
    return request<{ status: string }>(`/api/accounts/${id}`, { method: "DELETE" });
  },

  startAccountAuth(phone: string) {
    return request<{ session_id: string; status: string }>("/api/accounts/auth/start", {
      method: "POST",
      body: JSON.stringify({ phone }),
    });
  },

  verifyAccountAuth(sessionId: string, code: string) {
    return request<{ status: string; account?: Account; message?: string }>(
      "/api/accounts/auth/verify",
      {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, code }),
      },
    );
  },

  verifyAccount2FA(sessionId: string, password: string) {
    return request<{ status: string; account?: Account }>("/api/accounts/auth/2fa", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, password }),
    });
  },

  getDialogs(accountId: number, search?: string) {
    const params = new URLSearchParams({ limit: "50" });
    if (search) params.set("search", search);
    return request<Dialog[]>(`/api/accounts/${accountId}/dialogs?${params.toString()}`);
  },

  searchByUsername(accountId: number, username: string) {
    const normalized = username.trim().replace(/^@/, "");
    const params = new URLSearchParams({ username: normalized });
    return request<Dialog>(`/api/accounts/${accountId}/lookup?${params.toString()}`);
  },

  getMessages(accountId: number, chatId: string, offsetId = 0) {
    const params = new URLSearchParams({ limit: "100" });
    if (offsetId) params.set("offset_id", String(offsetId));
    return request<ChatMessage[]>(
      `/api/accounts/${accountId}/chats/${chatId}/messages?${params.toString()}`,
    );
  },

  getActiveKeyboard(accountId: number, chatId: string) {
    return request<MessageKeyboard | null>(
      `/api/accounts/${accountId}/chats/${chatId}/keyboard`,
    );
  },

  getBotCommands(accountId: number, chatId: string) {
    return request<BotCommand[]>(`/api/accounts/${accountId}/chats/${chatId}/commands`);
  },

  markChatRead(accountId: number, chatId: string) {
    return request<{ status: string }>(`/api/accounts/${accountId}/chats/${chatId}/read`, {
      method: "POST",
    });
  },

  sendMessage(accountId: number, chatId: string, text: string) {
    return request<{ status: string; message_id: number | null; error: string | null }>(
      `/api/accounts/${accountId}/chats/${chatId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ text }),
      },
    );
  },

  clickMessageButton(
    accountId: number,
    chatId: string,
    messageId: number,
    payload: { row?: number; col?: number; text?: string },
  ) {
    return request<{ status: string }>(
      `/api/accounts/${accountId}/chats/${chatId}/messages/${messageId}/click`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },

  getStats() {
    return request<Stats>("/api/stats");
  },

  getHistory() {
    return request<HistoryMessage[]>("/api/messages/history");
  },

  getTasks() {
    return request<TaskItem[]>("/api/tasks");
  },

  createTask(payload: {
    target_chat: string;
    message_text: string;
    account_ids: number[];
    repeat_count: number;
    interval: number;
    account_delay: number;
  }) {
    return request<TaskItem>("/api/tasks", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
