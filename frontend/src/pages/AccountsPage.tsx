import { FormEvent, useEffect, useState } from "react";
import {
  KeyRound,
  Phone,
  Plus,
  Search,
  ShieldCheck,
  Trash2,
  UserPlus,
} from "lucide-react";
import { Account, ProxyItem, api } from "../api/client";
import { Icon } from "../components/Icon";

type AuthStep = "phone" | "code" | "password";

export function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [step, setStep] = useState<AuthStep>("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [proxyId, setProxyId] = useState("");
  const [proxies, setProxies] = useState<ProxyItem[]>([]);
  const [submitting, setSubmitting] = useState(false);

  async function loadAccounts(query = searchQuery) {
    setLoading(true);
    try {
      const data = await api.getAccounts(query || undefined);
      setAccounts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      loadAccounts();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    if (modalOpen) {
      api.getProxies().then(setProxies).catch(() => {});
    }
  }, [modalOpen]);

  function resetModal() {
    setModalOpen(false);
    setStep("phone");
    setPhone("");
    setCode("");
    setPassword("");
    setSessionId("");
    setProxyId("");
    setError("");
  }

  async function handlePhoneSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const response = await api.startAccountAuth(
        phone,
        proxyId ? Number(proxyId) : undefined,
      );
      setSessionId(response.session_id);
      setStep("code");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCodeSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const response = await api.verifyAccountAuth(sessionId, code);
      if (response.status === "password_required") {
        setStep("password");
      } else {
        resetModal();
        await loadAccounts();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePasswordSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await api.verifyAccount2FA(sessionId, password);
      resetModal();
      await loadAccounts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(accountId: number) {
    if (!confirm("Деактивировать аккаунт?")) return;
    try {
      await api.deleteAccount(accountId);
      await loadAccounts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка удаления");
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Аккаунты</h1>
          <p>Добавление и управление Telegram-сессиями</p>
        </div>
        <button className="btn btn-with-icon" onClick={() => setModalOpen(true)}>
          <Icon icon={Plus} size="sm" />
          Добавить аккаунт
        </button>
      </div>

      {error && !modalOpen ? <div className="error-banner">{error}</div> : null}

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="card-body">
          <div className="field">
            <label>Поиск по username, имени или телефону</label>
            <div className="input-with-icon">
              <Icon icon={Search} size="sm" className="input-icon" />
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="@username"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          {loading ? (
            <div className="empty-state">Загрузка...</div>
          ) : accounts.length === 0 ? (
            <div className="empty-state">
              <Icon icon={UserPlus} size="xl" className="empty-state-icon" />
              Аккаунты не добавлены
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Имя</th>
                  <th>Телефон</th>
                  <th>Username</th>
                  <th>Статус</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.id}>
                    <td>{account.first_name || "—"} {account.last_name || ""}</td>
                    <td>{account.phone}</td>
                    <td>{account.username ? `@${account.username}` : "—"}</td>
                    <td>
                      <span className={`badge ${account.is_active ? "success" : "danger"}`}>
                        {account.is_active ? "active" : "inactive"}
                      </span>
                    </td>
                    <td>
                      {account.is_active ? (
                        <button
                          className="btn btn-danger btn-with-icon btn-sm"
                          onClick={() => handleDelete(account.id)}
                        >
                          <Icon icon={Trash2} size="sm" />
                          Деактивировать
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {modalOpen ? (
        <div className="modal-backdrop" onClick={resetModal}>
          <div className="card modal" onClick={(event) => event.stopPropagation()}>
            <div className="card-body form-stack">
              <h2 className="card-title">
                <Icon icon={UserPlus} size="sm" />
                Добавить аккаунт
              </h2>
              {error ? <div className="error-banner">{error}</div> : null}

              {step === "phone" ? (
                <form className="form-stack" onSubmit={handlePhoneSubmit}>
                  <div className="field">
                    <label>Номер телефона</label>
                    <div className="input-with-icon">
                      <Icon icon={Phone} size="sm" className="input-icon" />
                      <input
                        value={phone}
                        onChange={(event) => setPhone(event.target.value)}
                        placeholder="+79123456789"
                        required
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label>Прокси</label>
                    <select value={proxyId} onChange={(e) => setProxyId(e.target.value)}>
                      <option value="">Автовыбор</option>
                      {proxies
                        .filter((p) => p.is_active)
                        .map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.protocol}://{p.host}:{p.port}
                          </option>
                        ))}
                    </select>
                  </div>
                  <div className="actions-row">
                    <button className="btn btn-with-icon" type="submit" disabled={submitting}>
                      <Icon icon={ShieldCheck} size="sm" />
                      Отправить код
                    </button>
                    <button className="btn btn-secondary" type="button" onClick={resetModal}>
                      Отмена
                    </button>
                  </div>
                </form>
              ) : null}

              {step === "code" ? (
                <form className="form-stack" onSubmit={handleCodeSubmit}>
                  <div className="field">
                    <label>Код из Telegram</label>
                    <div className="input-with-icon">
                      <Icon icon={KeyRound} size="sm" className="input-icon" />
                      <input value={code} onChange={(event) => setCode(event.target.value)} required />
                    </div>
                  </div>
                  <button className="btn btn-with-icon" type="submit" disabled={submitting}>
                    <Icon icon={ShieldCheck} size="sm" />
                    Подтвердить
                  </button>
                </form>
              ) : null}

              {step === "password" ? (
                <form className="form-stack" onSubmit={handlePasswordSubmit}>
                  <div className="field">
                    <label>Пароль 2FA</label>
                    <div className="input-with-icon">
                      <Icon icon={KeyRound} size="sm" className="input-icon" />
                      <input
                        type="password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <button className="btn btn-with-icon" type="submit" disabled={submitting}>
                    <Icon icon={ShieldCheck} size="sm" />
                    Войти
                  </button>
                </form>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
