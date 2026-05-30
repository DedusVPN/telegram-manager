import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, Lock } from "lucide-react";
import { api, setToken } from "../api/client";
import { Icon } from "../components/Icon";

export function LoginPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await api.login(password);
      setToken(response.access_token);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card card animate-fade-in">
        <div className="login-card-header">
          <div className="login-icon">
            <Icon icon={Lock} size="lg" />
          </div>
          <div>
            <h1>Вход в панель</h1>
            <p>Пароль из переменной <code>WEB_PASSWORD</code> в <code>.env</code></p>
          </div>
        </div>

        <div className="card-body">
          {error ? (
            <div className="error-banner">
              <Icon icon={AlertCircle} size="sm" />
              {error}
            </div>
          ) : null}
          <form className="form-stack" onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="password">Пароль панели</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoFocus
                required
              />
            </div>
            <button className="btn btn-lg" type="submit" disabled={loading}>
              {loading ? "Вход..." : "Войти"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
