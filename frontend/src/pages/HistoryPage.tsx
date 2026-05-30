import { useEffect, useState } from "react";
import { History } from "lucide-react";
import { HistoryMessage, api } from "../api/client";
import { Icon } from "../components/Icon";

export function HistoryPage() {
  const [messages, setMessages] = useState<HistoryMessage[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getHistory()
      .then(setMessages)
      .catch((err) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>История</h1>
          <p>Журнал отправленных сообщений и ошибок</p>
        </div>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      <div className="card">
        <div className="card-body">
          {messages.length === 0 ? (
            <div className="empty-state">
              <Icon icon={History} size="xl" className="empty-state-icon" />
              История пуста
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Аккаунт</th>
                  <th>Чат</th>
                  <th>Текст</th>
                  <th>Статус</th>
                  <th>Дата</th>
                </tr>
              </thead>
              <tbody>
                {messages.map((message) => (
                  <tr key={message.id}>
                    <td>{message.account_id}</td>
                    <td>{message.target_chat}</td>
                    <td>{message.text.slice(0, 80)}</td>
                    <td>
                      <span className={`badge ${message.status === "success" ? "success" : "danger"}`}>
                        {message.status}
                      </span>
                    </td>
                    <td>{new Date(message.created_at).toLocaleString("ru-RU")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}
