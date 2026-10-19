import { useCallback, useEffect, useRef, useState } from "react";
import LoadingScreen from "./LoadingScreen";

const DOOR = "/intro/puerta.jpg";
const VIDEO = "/intro/entrada";
const FADE_MS = 900;

/**
 * Entrada al mundo Barbie:
 * 1) carga  -> 2) puerta (espera un clic) -> 3) video -> 4) se desvanece y deja ver la app.
 */
export default function Intro({ onDone }) {
  const [phase, setPhase] = useState("loading"); // loading | door | video
  const [buffering, setBuffering] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const video = useRef(null);
  const finished = useRef(false);

  const finish = useCallback(() => {
    if (finished.current) return;
    finished.current = true;
    setBuffering(false);
    setLeaving(true);
    setTimeout(onDone, FADE_MS);
  }, [onDone]);

  // Precargar la imagen de la puerta
  useEffect(() => {
    const img = new Image();
    img.onload = () => setPhase("door");
    img.onerror = () => setPhase("door");
    img.src = DOOR;
  }, []);

  const enter = useCallback(() => {
    if (phase !== "door") return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || !video.current) return finish();
    setPhase("video");
    video.current.currentTime = 0;
    video.current.play().catch(() => finish());
  }, [phase, finish]);

  // Teclado: Enter o espacio también abren la puerta
  useEffect(() => {
    const onKey = (e) => {
      if (phase === "door" && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        enter();
      }
      if (phase === "video" && e.key === "Escape") finish();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, enter, finish]);

  return (
    <div className={`intro intro--${phase} ${leaving ? "is-leaving" : ""}`}>
      <video
        ref={video}
        className="intro__video"
        poster={DOOR}
        preload="auto"
        playsInline
        onEnded={finish}
        onWaiting={() => setBuffering(true)}
        onPlaying={() => setBuffering(false)}
        aria-hidden="true"
      >
        {/* WebM pesa menos; MP4 queda de respaldo (Safari) */}
        <source src={`${VIDEO}.webm`} type="video/webm" />
        <source src={`${VIDEO}.mp4`} type="video/mp4" onError={() => phase === "video" && finish()} />
      </video>

      {phase !== "video" && (
        <button type="button" className="intro__door" onClick={enter} aria-label="Entrar al mundo Barbie">
          <img src={DOOR} alt="" />
          {phase === "door" && (
            <span className="intro__hint">
              <img src="/cursor/varita-96.png" alt="" />
              Toca en cualquier parte para entrar
            </span>
          )}
        </button>
      )}

      {phase === "video" && !leaving && (
        <button type="button" className="intro__skip" onClick={finish}>
          Saltar
        </button>
      )}

      {(phase === "loading" || buffering) && <LoadingScreen label={phase === "loading" ? "Preparando la casa" : "Abriendo la puerta"} />}
    </div>
  );
}
