/** Decoración de los bordes: cabeza y estrellas. Solo visual, no recibe clics. */
export default function Decorations() {
  return (
    <div className="decor" aria-hidden="true">
      <img src="/deco/cabeza.png" alt="" className="decor__item decor--head-left" />
      <img src="/deco/estrellas-rosas.png" alt="" className="decor__item decor--stars-right" />
      <img src="/deco/estrella-brillante.png" alt="" className="decor__item decor--star-left" />
      <img src="/deco/cabeza.png" alt="" className="decor__item decor--head-right" />
      <img src="/deco/estrella-brillante.png" alt="" className="decor__item decor--star-top" />
    </div>
  );
}
