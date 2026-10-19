import { useCallback, useEffect, useRef, useState } from "react";
import Message from "../components/Message";
import { Send, Sparkle } from "../components/Icons";
import { api } from "../lib/api";
import { navigate } from "../lib/useHashRoute";

const SUGGESTIONS = [
  "¿Quién creó a Barbie y en qué año apareció?",
  "¿Cómo se llaman las hermanas de Barbie?",
  "¿Cuándo apareció Ken por primera vez?",
  "¿De qué trata la película de 2023?",
];

export default function ChatPage({ conversationId, conversations, onChanged }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState(false);
  const [draft, setDraft] = useState("");
  const skipLoad = useRef(null);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  const title = conversations.find((c) => c.id === conversationId)?.title;

  // Cargar el historial al abrir una conversación
  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    if (skipLoad.current === conversationId) {
      skipLoad.current = null; // ya tenemos los mensajes recién creados
      return;
    }
    let alive = true;
    setLoading(true);
    api
      .messages(conversationId)
      .then((m) => alive && setMessages(m))
      .catch((err) => alive && setMessages([{ id: "err", role: "assistant", error: true, content: err.message }]))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [conversationId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, pending]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [conversationId]);

  const send = useCallback(
    async (text) => {
      const question = text.trim();
      if (!question || pending) return;
      setDraft("");
      const tempId = `tmp-${Date.now()}`;
      setMessages((m) => [...m.filter((x) => !x.error), { id: tempId, role: "user", content: question }]);
      setPending(true);
      try {
        const res = await api.ask(question, conversationId);
        setMessages((m) => [...m.filter((x) => x.id !== tempId), res.question, res.answer]);
        if (res.conversation.id !== conversationId) {
          skipLoad.current = res.conversation.id;
          navigate(`/chat/${res.conversation.id}`, { replace: true });
        }
        onChanged();
      } catch (err) {
        setMessages((m) => [
          ...m.filter((x) => x.id !== tempId),
          { id: tempId, role: "user", content: question },
          { id: `err-${tempId}`, role: "assistant", error: true, content: err.message, onRetry: () => send(question) },
        ]);
      } finally {
        setPending(false);
        inputRef.current?.focus();
      }
    },
    [conversationId, pending, onChanged],
  );

  function onKeyDown(ev) {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      send(draft);
    }
  }

  const empty = !conversationId && messages.length === 0;

  return (
    <section className="panel glass chat">
      <header className="panel__head">
        <h1 className="panel__title">{title || (conversationId ? "Conversación" : "Nueva conversación")}</h1>
      </header>

      <div className="window" aria-live="polite">
        {empty ? (
          <div className="welcome">
            <img src="/deco/estrellas-rosas.png" alt="" className="welcome__star" />
            <h2 className="welcome__title">¿Qué quieres saber del mundo Barbie?</h2>
            <p className="muted">
              Respondo solo con lo que hay en la biblioteca de documentos. Si no lo sé, te lo digo.
            </p>
            <div className="chips">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="thread">
            {loading && <p className="muted center">Cargando conversación…</p>}
            {messages.map((m) => (
              <Message key={m.id} message={m} />
            ))}
            {pending && (
              <div className="msg msg--bot">
                <span className="msg__avatar" aria-hidden="true">
                  <img src="/deco/estrella-brillante.png" alt="" />
                </span>
                <div className="msg__bubble typing" aria-label="El oráculo está buscando en la biblioteca">
                  <Sparkle size={12} />
                  <Sparkle size={12} />
                  <Sparkle size={12} />
                  <span>Buscando en la biblioteca…</span>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <label htmlFor="question" className="sr-only">
          Tu pregunta
        </label>
        <textarea
          id="question"
          ref={inputRef}
          rows={1}
          value={draft}
          maxLength={2000}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Pregunta sobre películas, personajes o la historia de Barbie"
        />
        <button className="btn btn--primary composer__send" disabled={!draft.trim() || pending} aria-label="Enviar">
          <Send />
        </button>
      </form>
    </section>
  );
}
