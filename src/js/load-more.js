(function () {
  const btn = document.querySelector('[data-load-more]');
  if (!btn) return;

  const BATCH = 12;

  function revealNext() {
    const hidden = document.querySelectorAll('.card[data-hidden]');
    const toShow = Array.from(hidden).slice(0, BATCH);

    toShow.forEach(function (card, i) {
      card.removeAttribute('data-hidden');
      card.classList.add('card--reveal');
      card.style.animationDelay = (i * 0.06) + 's';
    });

    if (document.querySelectorAll('.card[data-hidden]').length === 0) {
      btn.style.display = 'none';
    }
  }

  btn.addEventListener('click', revealNext);
})();
