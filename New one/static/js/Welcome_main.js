(function () {
  'use strict';

  /* ===== SLIDESHOW ===== */
  const slides = document.querySelectorAll('.slide');
  const dots = document.querySelectorAll('.dot');
  let current = 0;
  let slideshowTimer = null;

  function goToSlide(idx) {
    slides[current].classList.remove('active');
    dots[current].classList.remove('active');
    current = (idx + slides.length) % slides.length;
    slides[current].classList.add('active');
    dots[current].classList.add('active');
  }

  function nextSlide() {
    goToSlide(current + 1);
  }

  function startSlideshow() {
    slideshowTimer = setInterval(nextSlide, 5000);
  }

  dots.forEach((dot) => {
    dot.addEventListener('click', () => {
      clearInterval(slideshowTimer);
      goToSlide(Number(dot.dataset.idx));
      startSlideshow();
    });
  });

  startSlideshow();

  /* ===== SOFT PAGE TRANSITION — Enter Library button ===== */
  const overlay = document.getElementById('pageExitOverlay');
  const enterBtn = document.getElementById('enterBtn');

  function softNavigate(url) {
    if (!overlay) { window.location.href = url; return; }
    overlay.classList.add('fading');
    setTimeout(() => { window.location.href = url; }, 620);
  }

  if (enterBtn) {
    enterBtn.addEventListener('click', function (e) {
      e.preventDefault();
      softNavigate('/landing');
    });
  }

  /* Fade in on page load (arriving from transition) */
  document.addEventListener('DOMContentLoaded', function () {
    if (overlay) {
      overlay.style.opacity = '1';
      overlay.style.transition = 'none';
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          overlay.style.transition = 'opacity 0.6s ease';
          overlay.style.opacity = '0';
        });
      });
    }
  });

  /* ===== CREATORS MODAL ===== */
  let creatorsEscHandler = null;

  window.openCreatorsModal = function () {
    const bd = document.getElementById('creatorsBackdrop');
    if (!bd) return;
    bd.classList.add('active');
    bd.setAttribute('aria-hidden', 'false');
    creatorsEscHandler = function (e) {
      if (e.key === 'Escape') window.closeCreatorsModal();
    };
    document.addEventListener('keydown', creatorsEscHandler);
  };

  window.closeCreatorsModal = function () {
    const bd = document.getElementById('creatorsBackdrop');
    if (!bd) return;
    bd.classList.remove('active');
    bd.setAttribute('aria-hidden', 'true');
    if (creatorsEscHandler) {
      document.removeEventListener('keydown', creatorsEscHandler);
      creatorsEscHandler = null;
    }
  };

})();
