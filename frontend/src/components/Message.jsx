import { useState } from "react";
import { navigate } from "../lib/useHashRoute";
import { FileIcon, Sparkle } from "./Icons";

export default function Message({ message }) {
  if (message.role === "user") {
    return (
      <div className="msg msg--user">
        <p className="msg__bubble">{message.content}</p>
      </div>
    );
  }

  if (message.error) {
    return (
      <div className="msg msg--bot">
        <span className="msg__avatar msg__avatar--error" aria-hidden="true">!</span>
        <div className="msg__bubble msg__bubble--error" role="alert">
          <p>{message.content}</p>
          {message.onRetry && (
            <button className="btn btn--ghost btn--sm" onClick={message.onRetry}>
              Reintentar
            </button>
          )}
        </div>
      </div>
    );
  }

  if (message.rejected) {
    return (
      <div className="msg msg--bot">
        <span className="msg__avatar msg__avatar--muted" aria-hidden="true">
          <Sparkle size={16} />
        </span>
        <div className="msg__bubble msg__bubble--rejected">
          <p>{message.content}</p>
          <p className="msg__hint">
            Si tienes un documento sobre este tema, súbelo a la biblioteca y vuelve a preguntar.
          </p>
          <button className="btn btn--ghost btn--sm" onClick={() => navigate("/biblioteca")}>
            Ir a la biblioteca
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="msg msg--bot">
      <span className="msg__avatar" aria-hidden="true">
        <Sparkle size={16} />
      </span>
      <div className="msg__body">
        <p className="msg__bubble">{message.content}</p>
        {message.sources?.length > 0 && <Sources sources={message.sources} />}
      </div>
    </div>
  );
}

function Sources({ sources }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="sources">
      <button className="sources__toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
        <FileIcon width={16} height={16} />
        <span className="sources__count">{sources.length === 1 ? "1 fuente" : `${sources.length} fuentes`}</span>
        <span className="sources__names">{[...new Set(sources.map((s) => s.document))].join(", ")}</span>
      </button>
      {open && (
        <ol className="sources__list">
          {sources.map((s, i) => (
            <li key={i} className="source">
              <div className="source__head">
                <strong>{s.document}</strong>
                {typeof s.score === "number" && (
                  <span className="source__score" title="Similitud con tu pregunta">
                    <span className="meter" style={{ "--v": Math.max(0, Math.min(1, s.score)) }} />
                    {Math.round(s.score * 100)} %
                  </span>
                )}
              </div>
              <blockquote>{s.fragment}</blockquote>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
