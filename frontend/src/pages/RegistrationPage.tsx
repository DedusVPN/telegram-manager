import { FormEvent, useEffect, useState } from "react";
import { KeyRound, Play, RefreshCw, StopCircle, UserPlus } from "lucide-react";
import { ProxyItem, RegistrationJobDetail, api } from "../api/client";
import { Icon } from "../components/Icon";

const STATUS_LABELS: Record<string, string> = {
  pending: "В очереди",
  sending_code: "Отправка кода",
  code_sent: "Ожидает код",
  password_required: "Нужен 2FA",
  verifying: "Проверка",
  success: "Готово",
  failed: "Ошибка",
  skipped: "Пропущен",
};

export function RegistrationPage() {
  const [phonesText, setPhonesText] = useState("");
  const [delaySeconds, setDelaySeconds] = useState(3);
  const [default2fa, setDefault2fa] = useState("");
  const [proxyId, setProxyId] = useState<string>("");
  const [proxies, setProxies] = useState<ProxyItem[]>([]);
  const [job, setJob] = useState<RegistrationJobDetail | null>(null);
  const [codes, setCodes] = useState<Record<number, string>>({});
  const [passwords, setPasswords] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [polling, setPolling] = useState(false);

  useEffect(() => {
    api.getProxies().then(setProxies).catch(() => {});
  }, []);

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "cancelled") {
      setPolling(false);
      return;
    }
    setPolling(true);
    const timer = setInterval(async () => {
      try {
        const updated = await api.getRegistrationJob(job.id);
        setJob(updated);
      } catch {
        /* ignore */
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [job?.id, job?.status]);

  async function handleStart(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const phones = phonesText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    try {
      const created = await api.createRegistrationJob({
        phones,
        delay_seconds: delaySeconds,
        proxy_id: proxyId ? Number(proxyId) : undefined,
        default_2fa_password: default2fa || undefined,
      });
      setJob(created);
      setPhonesText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel() {
    if (!job) return;
    try {
      const updated = await api.cancelRegistrationJob(job.id);
      setJob(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  async function handleSubmitCode(itemId: number, needs2fa: boolean) {
    setSubmitting(true);
    setError("");
    try {
      if (needs2fa) {
        await api.submitRegistration2FA(itemId, passwords[itemId] || "");
      } else {
        await api.submitRegistrationCode(itemId, codes[itemId] || "");
      }
      if (job) {
        setJob(await api.getRegistrationJob(job.id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setSubmitting(false);
    }
  }

  const awaitingItems =
    job?.items.filter((i) => i.status === "code_sent" || i.status === "password_required") ?? [];

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Авторегистрация</h1>
          <p>Пакетная отправка кодов через прокси с привязкой аккаунтов</p>
        </div>
        {job && job.status === "running" ? (
          <button className="btn btn-danger btn-with-icon" onClick={handleCancel}>
            <Icon icon={StopCircle} size="sm" />
            Отменить задачу
          </button>
        ) : null}
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="card-body form-stack">
          <h2 className="card-title">
            <Icon icon={Play} size="sm" />
            Новая задача
          </h2>
          <form className="form-stack" onSubmit={handleStart}>
            <div className="field">
              <label>Номера телефонов (по одному на строку)</label>
              <textarea
                rows={6}
                value={phonesText}
                onChange={(e) => setPhonesText(e.target.value)}
                placeholder={"+79123456789\n+79987654321"}
                required
              />
            </div>
            <div className="form-grid-2">
              <div className="field">
                <label>Прокси (опционально)</label>
                <select value={proxyId} onChange={(e) => setProxyId(e.target.value)}>
                  <option value="">Автовыбор (ротация)</option>
                  {proxies
                    .filter((p) => p.is_active)
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.protocol}://{p.host}:{p.port}
                      </option>
                    ))}
                </select>
              </div>
              <div className="field">
                <label>Пауза между номерами (сек)</label>
                <input
                  type="number"
                  min={1}
                  max={120}
                  value={delaySeconds}
                  onChange={(e) => setDelaySeconds(Number(e.target.value))}
                />
              </div>
            </div>
            <div className="field">
              <label>Общий пароль 2FA (если одинаковый для всех)</label>
              <input
                type="password"
                value={default2fa}
                onChange={(e) => setDefault2fa(e.target.value)}
                placeholder="Опционально"
              />
            </div>
            <button className="btn btn-with-icon" type="submit" disabled={submitting}>
              <Icon icon={UserPlus} size="sm" />
              Запустить регистрацию
            </button>
          </form>
        </div>
      </div>

      {job ? (
        <div className="card">
          <div className="card-body">
            <div className="page-header" style={{ marginBottom: "1rem" }}>
              <div>
                <h2 className="card-title">Задача #{job.id}</h2>
                <p>
                  Статус: <strong>{job.status}</strong>
                  {polling ? (
                    <>
                      {" "}
                      <Icon icon={RefreshCw} size="sm" className="spin" />
                    </>
                  ) : null}
                </p>
                <p>
                  Успешно: {job.success_count} · Ошибки: {job.failed_count} · Ожидают код:{" "}
                  {job.awaiting_code_count}
                </p>
              </div>
            </div>

            <table className="table">
              <thead>
                <tr>
                  <th>Телефон</th>
                  <th>Статус</th>
                  <th>Код / 2FA</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {job.items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.phone}</td>
                    <td>
                      <span
                        className={`badge ${
                          item.status === "success"
                            ? "success"
                            : item.status === "failed"
                              ? "danger"
                              : item.status === "code_sent" || item.status === "password_required"
                                ? "warning"
                                : ""
                        }`}
                      >
                        {STATUS_LABELS[item.status] || item.status}
                      </span>
                      {item.error ? (
                        <div className="field-hint" style={{ color: "var(--danger)" }}>
                          {item.error}
                        </div>
                      ) : null}
                    </td>
                    <td>
                      {item.status === "code_sent" ? (
                        <input
                          value={codes[item.id] || ""}
                          onChange={(e) =>
                            setCodes((prev) => ({ ...prev, [item.id]: e.target.value }))
                          }
                          placeholder="Код из SMS"
                        />
                      ) : null}
                      {item.status === "password_required" ? (
                        <input
                          type="password"
                          value={passwords[item.id] || ""}
                          onChange={(e) =>
                            setPasswords((prev) => ({ ...prev, [item.id]: e.target.value }))
                          }
                          placeholder="Пароль 2FA"
                        />
                      ) : null}
                    </td>
                    <td>
                      {item.status === "code_sent" ? (
                        <button
                          className="btn btn-sm btn-with-icon"
                          disabled={submitting}
                          onClick={() => handleSubmitCode(item.id, false)}
                        >
                          <Icon icon={KeyRound} size="sm" />
                          Подтвердить
                        </button>
                      ) : null}
                      {item.status === "password_required" ? (
                        <button
                          className="btn btn-sm btn-with-icon"
                          disabled={submitting}
                          onClick={() => handleSubmitCode(item.id, true)}
                        >
                          <Icon icon={KeyRound} size="sm" />
                          2FA
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {awaitingItems.length === 0 && job.status === "completed" ? (
              <div className="empty-state" style={{ marginTop: "1rem" }}>
                Задача завершена
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
