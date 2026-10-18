/* Íconos propios en SVG (sin librerías externas) */
const base = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", "aria-hidden": true };
const stroke = { stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" };

export const Sparkle = ({ size = 20, ...p }) => (
  <svg {...base} width={size} height={size} {...p}>
    <path d="M12 1.5c.9 5.6 4.4 9.1 10 10-5.6.9-9.1 4.4-10 10-.9-5.6-4.4-9.1-10-10 5.6-.9 9.1-4.4 10-10z" fill="currentColor" />
  </svg>
);

export const Plus = (p) => (
  <svg {...base} {...p}><path d="M12 5v14M5 12h14" {...stroke} /></svg>
);
export const Send = (p) => (
  <svg {...base} {...p}><path d="M5 12h12M12 5l7 7-7 7" {...stroke} /></svg>
);
export const Chat = (p) => (
  <svg {...base} {...p}><path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 3.5V17h0A2.5 2.5 0 0 1 4 14.5z" {...stroke} /></svg>
);
export const Books = (p) => (
  <svg {...base} {...p}><path d="M5 4h4v16H5zM10 4h4v16h-4zM15.5 5l3.5-.9 3 15.5-3.5.9z" {...stroke} /></svg>
);
export const Upload = (p) => (
  <svg {...base} {...p}><path d="M12 16V4M7 9l5-5 5 5M4 16v2.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V16" {...stroke} /></svg>
);
export const Trash = (p) => (
  <svg {...base} {...p}><path d="M4 7h16M10 11v6M14 11v6M6 7l1 12.5A1.5 1.5 0 0 0 8.5 21h7a1.5 1.5 0 0 0 1.5-1.5L18 7M9 7V4h6v3" {...stroke} /></svg>
);
export const Logout = (p) => (
  <svg {...base} {...p}><path d="M15 4h3.5A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5H15M10 16l4-4-4-4M14 12H4" {...stroke} /></svg>
);
export const Menu = (p) => (
  <svg {...base} {...p}><path d="M4 7h16M4 12h16M4 17h16" {...stroke} /></svg>
);
export const Close = (p) => (
  <svg {...base} {...p}><path d="M6 6l12 12M18 6L6 18" {...stroke} /></svg>
);
export const FileIcon = (p) => (
  <svg {...base} {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5" {...stroke} /></svg>
);
