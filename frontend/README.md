# Frontend: React + Vite

```powershell
npm install
copy .env.example .env
npm run dev
```

Abre http://localhost:5173.

| Carpeta | Contenido |
|---|---|
| `src/pages/` | Acceso (login y registro), chat y biblioteca |
| `src/components/` | Barra lateral, mensajes con fuentes, íconos |
| `src/context/` | Sesión de Supabase y avisos |
| `src/lib/api.js` | Cliente de la API; agrega el token a cada request |
| `src/styles.css` | Sistema visual (colores, tipografía, componentes) |

Despliegue en Vercel: usa `frontend` como Root Directory y define las variables `VITE_*`.
