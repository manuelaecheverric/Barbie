import { useCallback, useEffect, useRef, useState } from "react";
import { FileIcon, Trash, Upload } from "../components/Icons";
import { useToast } from "../context/ToastContext";
import { api } from "../lib/api";

const ACCEPTED = [".pdf", ".txt", ".md", ".csv", ".docx"];
const MAX_MB = 15;

const STATUS = {
  processing: { label: "Procesando", tone: "processing" },
  ready: { label: "Listo", tone: "ready" },
  error: { label: "Error", tone: "error" },
};

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const dateFmt = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export default function LibraryPage() {
  const notify = useToast();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [confirming, setConfirming] = useState(null);
  const inputRef = useRef(null);
  const prev = useRef({});

  const load = useCallback(async () => {
    try {
      const list = await api.documents();
      // Avisar cuando un documento termina de procesarse
      for (const d of list) {
        if (prev.current[d.id] === "processing" && d.status === "ready") {
          notify(`«${d.filename}» está listo: ${d.chunks} fragmentos guardados en la base de conocimiento.`, "success");
        }
        if (prev.current[d.id] === "processing" && d.status === "error") {
          notify(`No se pudo procesar «${d.filename}».`, "error");
        }
      }
      prev.current = Object.fromEntries(list.map((d) => [d.id, d.status]));
      setDocs(list);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  // Mientras haya documentos procesando, consultar cada 2.5 s
  const processing = docs.some((d) => d.status === "processing");
  useEffect(() => {
    if (!processing) return;
    const t = setInterval(load, 2500);
    return () => clearInterval(t);
  }, [processing, load]);

  async function handleFiles(fileList) {
    const files = Array.from(fileList || []);
    for (const file of files) {
      const ext = `.${file.name.split(".").pop().toLowerCase()}`;
      if (!ACCEPTED.includes(ext)) {
        notify(`«${file.name}» no es un formato permitido. Usa ${ACCEPTED.join(", ")}.`, "error");
        continue;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        notify(`«${file.name}» supera ${MAX_MB} MB.`, "error");
        continue;
      }
      setUploading((u) => [...u, file.name]);
      try {
        const doc = await api.uploadDocument(file);
        prev.current[doc.id] = "processing";
        setDocs((d) => [doc, ...d]);
        notify(`«${file.name}» subido. Lo estamos procesando.`, "info");
      } catch (err) {
        notify(`«${file.name}»: ${err.message}`, "error");
      } finally {
        setUploading((u) => u.filter((n) => n !== file.name));
      }
    }
    if (inputRef.current) inputRef.current.value = "";
  }

  async function remove(doc) {
    setConfirming(null);
    try {
      await api.deleteDocument(doc.id);
      setDocs((d) => d.filter((x) => x.id !== doc.id));
      notify(`«${doc.filename}» eliminado de la base de conocimiento.`, "success");
    } catch (err) {
      notify(err.message, "error");
    }
  }

  return (
    <section className="box library">
      <header className="box__head">
        <h1 className="box__title">Biblioteca</h1>
        <p className="muted">Los documentos que subas alimentan las respuestas del oráculo.</p>
      </header>

      <div className="library__body">
        <label
          className={`dropzone ${dragging ? "dropzone--active" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPTED.join(",")}
            className="sr-only"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <Upload width={28} height={28} />
          <span className="dropzone__title">
            {uploading.length ? `Subiendo ${uploading.join(", ")}…` : "Arrastra archivos aquí o haz clic para elegirlos"}
          </span>
          <span className="muted">PDF, TXT, Markdown, CSV o DOCX, hasta {MAX_MB} MB</span>
        </label>

        {error && (
          <p className="alert alert--error" role="alert">
            {error}{" "}
            <button className="link" onClick={load}>
              Reintentar
            </button>
          </p>
        )}

        {loading ? (
          <p className="muted center">Cargando documentos…</p>
        ) : docs.length === 0 ? (
          <p className="library__empty">
            La biblioteca está vacía. Sube el primer documento sobre Barbie para que el oráculo pueda responder.
          </p>
        ) : (
          <ul className="docs">
            {docs.map((d) => {
              const st = STATUS[d.status] || STATUS.processing;
              return (
                <li key={d.id} className="doc">
                  <FileIcon className="doc__icon" />
                  <div className="doc__main">
                    <strong className="doc__name" title={d.filename}>
                      {d.filename}
                    </strong>
                    <span className="doc__meta">
                      {formatSize(d.size_bytes)}
                      {d.status === "ready" && `, ${d.chunks} fragmentos`}
                      {`, ${dateFmt.format(new Date(d.created_at))}`}
                      {!d.is_owner && ", subido por otra persona"}
                    </span>
                    {d.status === "error" && d.error && <span className="doc__error">{d.error}</span>}
                  </div>
                  <span className={`badge badge--${st.tone}`}>{st.label}</span>
                  {d.is_owner &&
                    (confirming === d.id ? (
                      <span className="doc__confirm">
                        <button className="link link--danger" onClick={() => remove(d)}>
                          Eliminar
                        </button>
                        <button className="link" onClick={() => setConfirming(null)}>
                          Cancelar
                        </button>
                      </span>
                    ) : (
                      <button
                        className="iconbtn"
                        aria-label={`Eliminar ${d.filename}`}
                        onClick={() => setConfirming(d.id)}
                        disabled={d.status === "processing"}
                      >
                        <Trash />
                      </button>
                    ))}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
