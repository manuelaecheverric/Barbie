import { useCallback, useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import { Close, Menu } from "./components/Icons";
import { useAuth } from "./context/AuthContext";
import { useToast } from "./context/ToastContext";
import { api } from "./lib/api";
import { navigate, useHashRoute } from "./lib/useHashRoute";
import AuthPage from "./pages/AuthPage";
import ChatPage from "./pages/ChatPage";
import LibraryPage from "./pages/LibraryPage";

export default function App() {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <div className="splash" aria-busy="true">
        Pink Oracle
      </div>
    );
  }
  // Sin sesión, solo se puede ver la pantalla de acceso
  return session ? <Shell /> : <AuthPage />;
}

function Shell() {
  const route = useHashRoute();
  const notify = useToast();
  const [conversations, setConversations] = useState([]);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setConversations(await api.conversations());
    } catch (err) {
      notify(err.message, "error");
    } finally {
      setLoadingConvs(false);
    }
  }, [notify]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function deleteConversation(id) {
    try {
      await api.deleteConversation(id);
      setConversations((c) => c.filter((x) => x.id !== id));
      if (route.conversationId === id) navigate("/chat");
      notify("Conversación eliminada.", "success");
    } catch (err) {
      notify(err.message, "error");
    }
  }

  return (
    <div className="shell">
      <header className="topbar">
        <button className="iconbtn" onClick={() => setMenuOpen(true)} aria-label="Abrir menú">
          <Menu />
        </button>
        <span className="topbar__brand">Pink Oracle</span>
      </header>

      {menuOpen && (
        <button className="scrim" aria-label="Cerrar menú" onClick={() => setMenuOpen(false)}>
          <Close />
        </button>
      )}

      <Sidebar
        route={route}
        conversations={conversations}
        loading={loadingConvs}
        onDelete={deleteConversation}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
      />

      <main className="stage">
        {route.page === "library" ? (
          <LibraryPage />
        ) : (
          <ChatPage conversationId={route.conversationId} conversations={conversations} onChanged={refresh} />
        )}
      </main>
    </div>
  );
}
