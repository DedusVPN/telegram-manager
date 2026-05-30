import { FormEvent, useEffect, useState } from "react";
import { CheckCircle2, ListTodo, Megaphone, Send } from "lucide-react";
import { Account, TaskItem, api } from "../api/client";
import { Icon } from "../components/Icon";

export function BroadcastPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [targetChat, setTargetChat] = useState("");
  const [messageText, setMessageText] = useState("");
  const [repeatCount, setRepeatCount] = useState(1);
  const [interval, setIntervalValue] = useState(30);
  const [accountDelay, setAccountDelay] = useState(10);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([api.getAccounts(), api.getTasks()])
      .then(([accountsData, tasksData]) => {
        setAccounts(accountsData.filter((account) => account.is_active));
        setTasks(tasksData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
  }, []);

  function toggleAccount(id: number) {
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (selected.length === 0) {
      setError("Выберите хотя бы один аккаунт");
      return;
    }

    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await api.createTask({
        target_chat: targetChat,
        message_text: messageText,
        account_ids: selected,
        repeat_count: repeatCount,
        interval,
        account_delay: accountDelay,
      });
      setSuccess("Рассылка запущена");
      setTasks(await api.getTasks());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка создания задачи");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Рассылка</h1>
          <p>Массовая отправка сообщений через несколько аккаунтов</p>
        </div>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}
      {success ? (
        <div className="badge success success-banner">
          <Icon icon={CheckCircle2} size="sm" />
          {success}
        </div>
      ) : null}

      <div className="grid grid-2">
        <div className="card">
          <div className="card-body form-stack">
            <h2 className="card-title">
              <Icon icon={Megaphone} size="sm" />
              Новая задача
            </h2>
            <form className="form-stack" onSubmit={handleSubmit}>
              <div className="field">
                <label>Целевой чат</label>
                <input
                  value={targetChat}
                  onChange={(event) => setTargetChat(event.target.value)}
                  placeholder="@username, t.me/username или chat_id"
                  required
                />
              </div>
              <div className="field">
                <label>Текст сообщения</label>
                <textarea
                  value={messageText}
                  onChange={(event) => setMessageText(event.target.value)}
                  required
                />
              </div>
              <div className="grid grid-2">
                <div className="field">
                  <label>Повторы</label>
                  <input
                    type="number"
                    min={1}
                    value={repeatCount}
                    onChange={(event) => setRepeatCount(Number(event.target.value))}
                  />
                </div>
                <div className="field">
                  <label>Интервал (сек)</label>
                  <input
                    type="number"
                    min={10}
                    value={interval}
                    onChange={(event) => setIntervalValue(Number(event.target.value))}
                  />
                </div>
              </div>
              <div className="field">
                <label>Задержка между аккаунтами (сек)</label>
                <input
                  type="number"
                  min={1}
                  value={accountDelay}
                  onChange={(event) => setAccountDelay(Number(event.target.value))}
                />
              </div>
              <div className="field">
                <label>Аккаунты</label>
                <div className="grid">
                  {accounts.map((account) => (
                    <label key={account.id} className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={selected.includes(account.id)}
                        onChange={() => toggleAccount(account.id)}
                      />
                      {account.first_name || account.phone}
                    </label>
                  ))}
                </div>
              </div>
              <button className="btn btn-with-icon" type="submit" disabled={loading}>
                <Icon icon={Send} size="sm" />
                {loading ? "Запуск..." : "Запустить рассылку"}
              </button>
            </form>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <h2 className="card-title">
              <Icon icon={ListTodo} size="sm" />
              Последние задачи
            </h2>
            {tasks.length === 0 ? (
              <div className="empty-state">
                <Icon icon={ListTodo} size="xl" className="empty-state-icon" />
                Задач пока нет
              </div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Чат</th>
                    <th>Статус</th>
                    <th>Создана</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((task) => (
                    <tr key={task.id}>
                      <td>{task.id}</td>
                      <td>{task.target_chat}</td>
                      <td>{task.status}</td>
                      <td>{new Date(task.created_at).toLocaleString("ru-RU")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
