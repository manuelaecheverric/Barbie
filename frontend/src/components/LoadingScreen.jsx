import { useEffect, useRef, useState } from "react";
import loaderData from "../assets/cargando.json";

/** Animación rosa de carga (Lottie). Si la librería no carga, muestra un aro CSS. */
export function PinkLoader({ size = 110 }) {
  const box = useRef(null);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    let anim;
    let cancelled = false;
    import("lottie-web/build/player/lottie_light")
      .then((mod) => {
        if (cancelled || !box.current) return;
        const lottie = mod.default || mod;
        anim = lottie.loadAnimation({
          container: box.current,
          renderer: "svg",
          loop: true,
          autoplay: true,
          animationData: loaderData,
        });
      })
      .catch(() => setFallback(true));
    return () => {
      cancelled = true;
      anim?.destroy();
    };
  }, []);

  return (
    <div className="pink-loader" style={{ width: size, height: size }} role="progressbar" aria-label="Cargando">
      {fallback ? <span className="pink-loader__ring" /> : <div ref={box} className="pink-loader__lottie" />}
    </div>
  );
}

/** Pantalla de carga: patrón de siluetas + logo rosa + animación. */
export default function LoadingScreen({ label = "Cargando", leaving = false }) {
  return (
    <div className={`loading-screen ${leaving ? "is-leaving" : ""}`} aria-live="polite" aria-busy="true">
      <div className="loading-screen__card">
        <img src="/deco/logo-barbie-rosa.svg" alt="" className="loading-screen__logo" />
        <PinkLoader />
        <p className="loading-screen__label">{label}…</p>
      </div>
    </div>
  );
}
