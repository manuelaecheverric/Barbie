import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { navigate } from "../lib/useHashRoute";
import { Books, Chat, Logout, Plus, Trash } from "./Icons";

export default function Sidebar({ route, conversations, loading, onDelete, open, onClose }) {
  const { user, signOut } = useAuth();
  const [confirming, setConfirming] = useState(null);
  const name = user?.user_metadata?.full_name || user?.email?.split("@")[0] || "Tú";

  function go(path) {
    navigate(path);
    onClose();
  }

  return (
    <aside className={`sidebar ${open ? "sidebar--open" : ""}`} aria-label="Navegación">
      <div className="sidebar__brand">Pink Oracle</div>

      <button className="btn btn--primary btn--block" onClick={() => go("/chat")}>
        <Plus /> Nueva conversación
      </button>

      <nav className="sidebar__nav">
        <button className="navlink" aria-current={route.page === "chat"} onClick={() => go("/chat")}>
          <Chat /> Chat
        </button>
        <button className="navlink" aria-current={route.page === "library"} onClick={() => go("/biblioteca")}>
          <Books /> Biblioteca
        </button>
      </nav>

      <p className="sidebar__heading">Tus conversaciones</p>
      <ul className="convs">
        {loading && <li className="convs__empty">Cargando…</li>}
        {!loading && conversations.length === 0 && (
          <li className="convs__empty">Aquí aparecerán tus conversaciones.</li>
        )}
        {conversations.map((c) => (
          <li key={c.id} className="conv" aria-current={route.conversationId === c.id}>
            {confirming === c.id ? (
              <div className="conv__confirm">
                <span>¿Eliminar?</span>
                <button className="link link--danger" onClick={() => { setConfirming(null); onDelete(c.id); }}>
                  Sí
                </button>
                <button className="link" onClick={() => setConfirming(null)}>
                  No
                </button>
              </div>
            ) : (
              <>
                <button className="conv__title" onClick={() => go(`/chat/${c.id}`)} title={c.title}>
                  {c.title}
                </button>
                <button className="iconbtn" aria-label={`Eliminar ${c.title}`} onClick={() => setConfirming(c.id)}>
                  <Trash width={16} height={16} />
                </button>
              </>
            )}
          </li>
        ))}
      </ul>

      <div className="sidebar__user">
        <span className="avatar" aria-hidden="true">{name.charAt(0).toUpperCase()}</span>
        <span className="sidebar__who">
          <strong>{name}</strong>
          <small>{user?.email}</small>
        </span>
        <button className="iconbtn" onClick={signOut} aria-label="Cerrar sesión" title="Cerrar sesión">
          <Logout />
        </button>
      </div>
    </aside>
  );
}
