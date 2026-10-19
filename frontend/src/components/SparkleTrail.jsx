import { useEffect } from "react";

const COLORS = ["#ff299a", "#fca7e0", "#ffffff", "#f8c24e", "#ec65ad"];
const SHAPES = ["✦", "✧", "✦", "⋆"];

/** Estela de destellos de la varita (solo con mouse) y explosión al hacer clic. */
export default function SparkleTrail() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let last = 0;

    function sparkle(x, y, burst = false) {
      const el = document.createElement("span");
      el.className = "sparkle";
      el.textContent = SHAPES[Math.floor(Math.random() * SHAPES.length)];
      el.style.left = `${x}px`;
      el.style.top = `${y}px`;
      el.style.color = COLORS[Math.floor(Math.random() * COLORS.length)];
      el.style.fontSize = `${8 + Math.random() * 12}px`;
      document.body.appendChild(el);
      const dx = (Math.random() - 0.5) * (burst ? 180 : 60);
      const dy = (Math.random() - 0.5) * (burst ? 180 : 70) + 16;
      const anim = el.animate(
        [
          { transform: "translate(-50%,-50%) scale(.3) rotate(0deg)", opacity: 0 },
          { offset: 0.2, transform: "translate(-50%,-50%) scale(1)", opacity: 1 },
          { transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(0) rotate(95deg)`, opacity: 0 },
        ],
        { duration: burst ? 750 : 560, easing: "ease-out" },
      );
      anim.onfinish = () => el.remove();
    }

    // La estela sale de la estrella de la varita (arriba del puntero)
    const onMove = (e) => {
      if (e.pointerType !== "mouse") return;
      const now = performance.now();
      if (now - last < 32) return;
      last = now;
      sparkle(e.clientX, e.clientY);
    };
    const onClick = (e) => {
      for (let i = 0; i < 14; i++) sparkle(e.clientX, e.clientY, true);
    };

    document.addEventListener("pointermove", onMove);
    document.addEventListener("click", onClick);
    return () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("click", onClick);
    };
  }, []);

  return null;
}
