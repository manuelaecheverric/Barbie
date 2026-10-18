import { useEffect, useState } from "react";

/** Router mínimo basado en el hash: #/chat, #/chat/<id>, #/biblioteca */
function parse() {
  const parts = window.location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const page = parts[0] === "biblioteca" ? "library" : "chat";
  return { page, conversationId: page === "chat" ? parts[1] || null : null };
}

export function navigate(path, { replace = false } = {}) {
  const hash = `#${path}`;
  if (window.location.hash === hash) return;
  if (replace) {
    window.history.replaceState(null, "", hash);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  } else {
    window.location.hash = path;
  }
}

export function useHashRoute() {
  const [route, setRoute] = useState(parse);
  useEffect(() => {
    const onChange = () => setRoute(parse());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
