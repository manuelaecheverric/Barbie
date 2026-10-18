import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const isConfigured = Boolean(url && anonKey);

if (!isConfigured) {
  console.warn("Faltan VITE_SUPABASE_URL o VITE_SUPABASE_ANON_KEY en frontend/.env");
}

export const supabase = createClient(url || "https://example.supabase.co", anonKey || "public-anon-key", {
  auth: { persistSession: true, autoRefreshToken: true },
});
