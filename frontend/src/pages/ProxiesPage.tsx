import { FormEvent, useEffect, useState } from "react";
import { Globe, Plus, RefreshCw, Trash2, Upload } from "lucide-react";
import { ProxyItem, api } from "../api/client";
import { Icon } from "../components/Icon";

export function ProxiesPage() {
  const [proxies, setProxies] = useState<ProxyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rawLine, setRawLine] = useState("");
  const [bulkText, setBulkText] = useState("");
  const [showBulk, setShowBulk] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);

  async function loadProxies() {
    setLoading(true);
    try {
      setProxies(await api.getProxies());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProxies();
  }, []);

  async function handleAdd(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await api.createProxy({ raw_line: rawLine.trim() });
      setRawLine("");
      await loadProxies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleBulkImport(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await api.importProxies(bulkText);
      setBulkText("");
      setShowBulk(false);
      await loadProxies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTest(proxyId: number) {
    setTestingId(proxyId);
    try {
      const result = await api.testProxy(proxyId);
      if (!result.ok) {
        setError(result.error || "Прокси не отвечает");
      } else {
        setError("");
      }
      await loadProxies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка проверки");
    } finally {
      setTestingId(null);
    }
  }

  async function handleToggle(proxy: ProxyItem) {
    try {
      await api.updateProxy(proxy.id, { is_active: !proxy.is_active });
      await loadProxies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  async function handleDelete(proxyId: number) {
    if (!confirm("Удалить прокси?")) return;
    try {
      await api.deleteProxy(proxyId);
      await loadProxies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Прокси</h1>
          <p>Настройка SOCKS5/HTTP прокси для регистрации и работы аккаунтов</p>
        </div>
        <button className="btn btn-secondary btn-with-icon" onClick={() => setShowBulk((v) => !v)}>
          <Icon icon={Upload} size="sm" />
          Импорт списком
        </button>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="card-body form-stack">
          <h2 className="card-title">
            <Icon icon={Plus} size="sm" />
            Добавить прокси
          </h2>
          <form className="form-stack" onSubmit={handleAdd}>
            <div className="field">
              <label>Строка прокси</label>
              <div className="input-with-icon">
                <Icon icon={Globe} size="sm" className="input-icon" />
                <input
                  value={rawLine}
                  onChange={(e) => setRawLine(e.target.value)}
                  placeholder="socks5://user:pass@host:port или host:port:user:pass"
                  required
                />
              </div>
              <p className="field-hint">
                Поддерживаются socks5, socks4, http. По одному на строку при импорте.
              </p>
            </div>
            <button className="btn btn-with-icon" type="submit" disabled={submitting}>
              <Icon icon={Plus} size="sm" />
              Добавить
            </button>
          </form>
        </div>
      </div>

      {showBulk ? (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <div className="card-body form-stack">
            <h2 className="card-title">
              <Icon icon={Upload} size="sm" />
              Массовый импорт
            </h2>
            <form className="form-stack" onSubmit={handleBulkImport}>
              <div className="field">
                <label>Список прокси (по одному на строку)</label>
                <textarea
                  rows={8}
                  value={bulkText}
                  onChange={(e) => setBulkText(e.target.value)}
                  placeholder={"socks5://user:pass@1.2.3.4:1080\n1.2.3.5:1080:user:pass"}
                  required
                />
              </div>
              <button className="btn btn-with-icon" type="submit" disabled={submitting}>
                <Icon icon={Upload} size="sm" />
                Импортировать
              </button>
            </form>
          </div>
        </div>
      ) : null}

      <div className="card">
        <div className="card-body">
          {loading ? (
            <div className="empty-state">Загрузка...</div>
          ) : proxies.length === 0 ? (
            <div className="empty-state">
              <Icon icon={Globe} size="xl" className="empty-state-icon" />
              Прокси не добавлены
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Прокси</th>
                  <th>Метка</th>
                  <th>Статус</th>
                  <th>Использований</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {proxies.map((proxy) => (
                  <tr key={proxy.id}>
                    <td>
                      <code>
                        {proxy.protocol}://{proxy.host}:{proxy.port}
                        {proxy.username ? ` (${proxy.username})` : ""}
                      </code>
                    </td>
                    <td>{proxy.label || "—"}</td>
                    <td>
                      <span
                        className={`badge ${proxy.is_active && proxy.is_healthy ? "success" : proxy.is_active ? "warning" : "danger"}`}
                      >
                        {!proxy.is_active
                          ? "выкл"
                          : proxy.is_healthy
                            ? "ok"
                            : "проблема"}
                      </span>
                    </td>
                    <td>{proxy.usage_count}</td>
                    <td>
                      <div className="actions-row" style={{ justifyContent: "flex-end" }}>
                        <button
                          className="btn btn-secondary btn-sm btn-with-icon"
                          onClick={() => handleTest(proxy.id)}
                          disabled={testingId === proxy.id}
                        >
                          <Icon icon={RefreshCw} size="sm" />
                          Проверить
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleToggle(proxy)}
                        >
                          {proxy.is_active ? "Выкл" : "Вкл"}
                        </button>
                        <button
                          className="btn btn-danger btn-sm btn-with-icon"
                          onClick={() => handleDelete(proxy.id)}
                        >
                          <Icon icon={Trash2} size="sm" />
                        </button>
                      </div>
                    </td>
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
