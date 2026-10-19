import { useCallback, useEffect, useState } from "react";
import Decorations from "./components/Decorations";
import { Books, Chat, Close, Logout, Menu } from "./components/Icons";
import Intro from "./components/Intro";
import LoadingScreen from "./components/LoadingScreen";
import Sidebar from "./components/Sidebar";
import SparkleTrail from "./components/SparkleTrail";
import { useAuth } from "./context/AuthContext";
import { useToast } from "./context/ToastContext";
import { api } from "./lib/api";
import { navigate, useHashRoute } from "./lib/useHashRoute";
import AuthPage from "./pages/AuthPage";
import ChatPage from "./pages/ChatPage";
import LibraryPage from "./pages/LibraryPage";

export default function App() {
  const { session, loading } = useAuth();
  const [introDone, setIntroDone] = useState(false);

  return (
    <>
      <SparkleTrail />
      <Decorations />
      {/* La app se monta debajo de la intro para que esté lista al terminar el video */}
      {!loading && (session ? <Shell /> : <AuthPage />)}
      {introDone && loading && <LoadingScreen label="Abriendo tu sesión" />}
      {!introDone && <Intro onDone={() => setIntroDone(true)} />}
    </>
  );
}

function Shell() {
  const route = useHashRoute();
  const notify = useToast();
  const { user, signOut } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const name = user?.user_metadata?.full_name || user?.email?.split("@")[0] || "Tú";

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
      <header className="hdr">
        <div className="hdr__left">
          <button className="iconbtn hdr__menu" onClick={() => setMenuOpen(true)} aria-label="Abrir conversaciones">
            <Menu />
          </button>
          <nav className="tabs" aria-label="Secciones">
            <button className="tab" aria-current={route.page === "chat"} onClick={() => navigate("/chat")}>
              <Chat /> <span>Chat</span>
            </button>
            <button className="tab" aria-current={route.page === "library"} onClick={() => navigate("/biblioteca")}>
              <Books /> <span>Biblioteca</span>
            </button>
          </nav>
        </div>

        <img src="/deco/logo-barbie.png" alt="Barbie" className="hdr__logo" />

        <div className="hdr__user">
          <span className="avatar" aria-hidden="true">
            {name.charAt(0).toUpperCase()}
          </span>
          <span className="hdr__who">
            <strong>{name}</strong>
            <small>{user?.email}</small>
          </span>
          <button className="iconbtn" onClick={signOut} aria-label="Cerrar sesión" title="Cerrar sesión">
            <Logout />
          </button>
        </div>
      </header>

      {menuOpen && (
        <button className="scrim" aria-label="Cerrar menú" onClick={() => setMenuOpen(false)}>
          <Close />
        </button>
      )}

      <div className="stage">
        <Sidebar
          route={route}
          conversations={conversations}
          loading={loadingConvs}
          onDelete={deleteConversation}
          open={menuOpen}
          onClose={() => setMenuOpen(false)}
        />
        <main className="main">
          {route.page === "library" ? (
            <LibraryPage />
          ) : (
            <ChatPage conversationId={route.conversationId} conversations={conversations} onChanged={refresh} />
          )}
        </main>
      </div>
    </div>
  );
}
