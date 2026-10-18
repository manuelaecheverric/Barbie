import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { isConfigured } from "../lib/supabase";
import { Sparkle } from "../components/Icons";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate(mode, f) {
  const e = {};
  if (mode === "register" && f.name.trim().length < 2) e.name = "Escribe tu nombre.";
  if (!EMAIL_RE.test(f.email.trim())) e.email = "Escribe un correo válido.";
  if (f.password.length < 8) e.password = "Usa al menos 8 caracteres.";
  if (mode === "register" && f.confirm !== f.password) e.confirm = "Las contraseñas no coinciden.";
  return e;
}

export default function AuthPage() {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState(false);
  const [status, setStatus] = useState({ busy: false, error: "", info: "" });

  const isRegister = mode === "register";

  function update(field) {
    return (ev) => {
      const next = { ...form, [field]: ev.target.value };
      setForm(next);
      if (touched) setErrors(validate(mode, next));
    };
  }

  function switchMode(next) {
    setMode(next);
    setErrors({});
    setTouched(false);
    setStatus({ busy: false, error: "", info: "" });
  }

  async function submit(ev) {
    ev.preventDefault();
    setTouched(true);
    const found = validate(mode, form);
    setErrors(found);
    if (Object.keys(found).length) return;

    setStatus({ busy: true, error: "", info: "" });
    try {
      if (isRegister) {
        const { needsConfirmation } = await signUp(form.name.trim(), form.email.trim(), form.password);
        if (needsConfirmation) {
          setMode("login");
          setStatus({ busy: false, error: "", info: "Cuenta creada. Te enviamos un correo para confirmarla; después inicia sesión." });
          return;
        }
      } else {
        await signIn(form.email.trim(), form.password);
      }
    } catch (err) {
      setStatus({ busy: false, error: err.message, info: "" });
      return;
    }
    setStatus({ busy: false, error: "", info: "" });
  }

  return (
    <main className="auth">
      <section className="auth__box" aria-hidden="true">
        <div className="auth__window">
          <span className="auth__glare" />
          <Sparkle className="float float--a" size={34} />
          <Sparkle className="float float--b" size={18} />
          <Sparkle className="float float--c" size={26} />
          <p className="auth__wordmark">
            Pink
            <br />
            Oracle
          </p>
        </div>
        <p className="auth__tagline">
          Pregúntale todo sobre las películas, la familia, las amigas, Ken y más de sesenta años de historia de Barbie.
        </p>
      </section>

      <section className="auth__panel">
        <div className="tabs" role="tablist" aria-label="Acceso">
          <button role="tab" aria-selected={!isRegister} className="tab" onClick={() => switchMode("login")}>
            Iniciar sesión
          </button>
          <button role="tab" aria-selected={isRegister} className="tab" onClick={() => switchMode("register")}>
            Crear cuenta
          </button>
        </div>

        <h1 className="auth__title">{isRegister ? "Crea tu cuenta" : "Hola de nuevo"}</h1>
        <p className="muted">
          {isRegister ? "Solo necesitas un correo y una contraseña." : "Entra para seguir conversando con el oráculo."}
        </p>

        {!isConfigured && (
          <p className="alert alert--error">
            Falta configurar Supabase: crea <code>frontend/.env</code> a partir de <code>.env.example</code>.
          </p>
        )}
        {status.info && <p className="alert alert--info">{status.info}</p>}
        {status.error && (
          <p className="alert alert--error" role="alert">
            {status.error}
          </p>
        )}

        <form onSubmit={submit} noValidate className="form">
          {isRegister && (
            <Field label="Nombre" error={errors.name}>
              <input value={form.name} onChange={update("name")} autoComplete="name" />
            </Field>
          )}
          <Field label="Correo" error={errors.email}>
            <input type="email" value={form.email} onChange={update("email")} autoComplete="email" />
          </Field>
          <Field label="Contraseña" error={errors.password}>
            <input
              type="password"
              value={form.password}
              onChange={update("password")}
              autoComplete={isRegister ? "new-password" : "current-password"}
            />
          </Field>
          {isRegister && (
            <Field label="Confirma la contraseña" error={errors.confirm}>
              <input type="password" value={form.confirm} onChange={update("confirm")} autoComplete="new-password" />
            </Field>
          )}
          <button className="btn btn--primary btn--block" disabled={status.busy}>
            {status.busy ? "Un momento…" : isRegister ? "Crear cuenta" : "Iniciar sesión"}
          </button>
        </form>
      </section>
    </main>
  );
}

function Field({ label, error, children }) {
  return (
    <label className={`field ${error ? "field--error" : ""}`}>
      <span className="field__label">{label}</span>
      {children}
      {error && <span className="field__error">{error}</span>}
    </label>
  );
}
