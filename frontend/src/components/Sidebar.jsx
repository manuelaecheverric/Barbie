import { useState } from "react";
import { navigate } from "../lib/useHashRoute";
import { Plus, Trash } from "./Icons";

export default function Sidebar({ route, conversations, loading, onDelete, open, onClose }) {
  const [confirming, setConfirming] = useState(null);

  function go(path) {
    navigate(path);
    onClose();
  }

  return (
    <aside className={`sidebar glass ${open ? "sidebar--open" : ""}`} aria-label="Tus conversaciones">
      <button className="btn btn--primary btn--block" onClick={() => go("/chat")}>
        <Plus /> Nueva conversación
      </button>

      <h2 className="sidebar__heading">Tus conversaciones</h2>
      <ul className="convs">
        {loading && <li className="convs__empty">Cargando…</li>}
        {!loading && conversations.length === 0 && (
          <li className="convs__empty">Aquí aparecerán las conversaciones que tengas con el oráculo.</li>
        )}
        {conversations.map((c) => (
          <li key={c.id} className="conv" aria-current={route.conversationId === c.id}>
            {confirming === c.id ? (
              <div className="conv__confirm">
                <span>¿Eliminar?</span>
                <button
                  className="link link--danger"
                  onClick={() => {
                    setConfirming(null);
                    onDelete(c.id);
                  }}
                >
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
    </aside>
  );
}
