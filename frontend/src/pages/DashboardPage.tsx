import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  MessageCircle,
  Plus,
  Send,
  UserPlus,
  Users,
} from "lucide-react";
import { Account, Stats, api } from "../api/client";
import { Icon } from "../components/Icon";

export function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.getStats(), api.getAccounts()])
      .then(([statsData, accountsData]) => {
        setStats(statsData);
        setAccounts(accountsData.filter((account) => account.is_active));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Дашборд</h1>
          <p>Обзор активности платформы</p>
        </div>
        <Link className="btn btn-with-icon" to="/chats">
          <Icon icon={MessageCircle} size="sm" />
          Открыть чаты
        </Link>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      <div className="grid grid-3" style={{ marginBottom: "1rem" }}>
        <div className="card stat-card">
          <div className="stat-card-icon">
            <Icon icon={CheckCircle2} size="lg" />
          </div>
          <span>Успешные отправки</span>
          <strong>{stats?.success ?? 0}</strong>
        </div>
        <div className="card stat-card">
          <div className="stat-card-icon">
            <Icon icon={Users} size="lg" />
          </div>
          <span>Активные аккаунты</span>
          <strong>{accounts.length}</strong>
        </div>
        <div className="card stat-card">
          <div className="stat-card-icon stat-card-icon-danger">
            <Icon icon={AlertTriangle} size="lg" />
          </div>
          <span>Ошибки</span>
          <strong>{stats?.error ?? 0}</strong>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-body">
            <h2 className="card-title">
              <Icon icon={Send} size="sm" />
              Статистика отправок
            </h2>
            <div className="grid grid-2">
              <div><span className="badge success">success: {stats?.success ?? 0}</span></div>
              <div><span className="badge">pending: {stats?.pending ?? 0}</span></div>
              <div><span className="badge danger">error: {stats?.error ?? 0}</span></div>
              <div><span className="badge">flood_wait: {stats?.flood_wait ?? 0}</span></div>
              <div><span className="badge danger">forbidden: {stats?.forbidden ?? 0}</span></div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <h2 className="card-title">
              <Icon icon={Plus} size="sm" />
              Быстрые действия
            </h2>
            <div className="actions-row">
              <Link className="btn btn-with-icon" to="/accounts">
                <Icon icon={UserPlus} size="sm" />
                Добавить аккаунт
              </Link>
              <Link className="btn btn-secondary btn-with-icon" to="/broadcast">
                <Icon icon={Send} size="sm" />
                Создать рассылку
              </Link>
              <Link className="btn btn-secondary btn-with-icon" to="/history">
                <Icon icon={MessageCircle} size="sm" />
                История
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
