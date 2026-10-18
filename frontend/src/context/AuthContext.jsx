import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { supabase } from "../lib/supabase";

const AuthContext = createContext(null);

const AUTH_ERRORS = {
  "Invalid login credentials": "Correo o contraseña incorrectos.",
  "Email not confirmed": "Confirma tu correo antes de entrar. Revisa tu bandeja de entrada.",
  "User already registered": "Ya existe una cuenta con ese correo. Inicia sesión.",
  "Password should be at least 6 characters": "La contraseña debe tener al menos 6 caracteres.",
};

function translate(error) {
  if (!error) return null;
  const key = Object.keys(AUTH_ERRORS).find((k) => error.message?.includes(k));
  if (key) return AUTH_ERRORS[key];
  if (error.status === 429) return "Demasiados intentos. Espera un minuto y vuelve a intentarlo.";
  return error.message || "No se pudo completar la operación.";
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
    return () => data.subscription.unsubscribe();
  }, []);

  const value = useMemo(
    () => ({
      session,
      user: session?.user ?? null,
      loading,
      async signIn(email, password) {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw new Error(translate(error));
      },
      async signUp(name, email, password) {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: name }, emailRedirectTo: window.location.origin },
        });
        if (error) throw new Error(translate(error));
        // Si el proyecto exige confirmar el correo, no hay sesión todavía
        return { needsConfirmation: !data.session };
      },
      async signOut() {
        await supabase.auth.signOut();
        window.location.hash = "";
      },
    }),
    [session, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
