(function () {
  const btn = document.querySelector('[data-load-more]');
  if (!btn) return;

  const BATCH = 12;
  const STORAGE_KEY = 'demos-revealed';

  function revealCards(count, animate) {
    const hidden = document.querySelectorAll('.card[data-hidden]');
    const toShow = Array.from(hidden).slice(0, count);

    toShow.forEach(function (card, i) {
      card.removeAttribute('data-hidden');
      if (animate) {
        card.classList.add('card--reveal');
        card.style.animationDelay = (i * 0.06) + 's';
      }
    });

    if (document.querySelectorAll('.card[data-hidden]').length === 0) {
      btn.style.display = 'none';
    }
  }

  // Restore previous scroll depth from session
  var saved = parseInt(sessionStorage.getItem(STORAGE_KEY) || '0', 10);
  if (saved > 0) {
    revealCards(saved, false);
  }

  btn.addEventListener('click', function () {
    revealCards(BATCH, true);
    // Save total revealed count (all cards minus still-hidden ones minus initial batch)
    var totalRevealed = document.querySelectorAll('.card:not([data-hidden])').length - BATCH;
    if (totalRevealed > 0) {
      sessionStorage.setItem(STORAGE_KEY, totalRevealed);
    }
  });
})();
