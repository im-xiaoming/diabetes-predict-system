// Motion layer powered by anime.js v3.
// It only changes presentation: no backend calls, no business state updates.
(function () {
  const ready = (fn) => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn, { once: true });
      return;
    }
    fn();
  };

  ready(() => {
    const canAnimate =
      typeof window.anime === 'function' &&
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const $ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
    const isRenderable = (el) => {
      if (!el || !(el instanceof Element)) return false;
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    };

    const withLayer = (el) => {
      if (!el) return () => {};
      const previousTransition = el.style.transition;
      const previousWillChange = el.style.willChange;
      const previousTransform = el.style.transform;
      const previousOpacity = el.style.opacity;
      el.style.transition = 'none';
      el.style.willChange = 'transform, opacity';
      return () => {
        el.style.transition = previousTransition;
        el.style.willChange = previousWillChange;
        el.style.transform = previousTransform;
        el.style.opacity = previousOpacity;
      };
    };

    const withLayers = (items) => {
      const restores = items.map(withLayer);
      return () => restores.forEach((restore) => restore());
    };

    const animateOnce = (targets, options) => {
      if (!canAnimate) return null;
      window.anime.remove(targets);
      return window.anime(Object.assign({ targets }, options));
    };

    const hasPlayedPageIntro = () => {
      try {
        return window.sessionStorage.getItem('clinicalMotionIntroPlayed') === 'true';
      } catch (error) {
        return false;
      }
    };

    const markPageIntroPlayed = () => {
      try {
        window.sessionStorage.setItem('clinicalMotionIntroPlayed', 'true');
      } catch (error) {
        // Storage can be blocked in private contexts; animation still works.
      }
    };

    const makeObserver = (onEnter, options) => {
      if (!('IntersectionObserver' in window)) {
        return {
          observe: (el) => onEnter(el),
          unobserve: () => {},
        };
      }

      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          observer.unobserve(entry.target);
          onEnter(entry.target);
        });
      }, Object.assign({ threshold: 0.12, rootMargin: '0px 0px -8% 0px' }, options));

      return observer;
    };

    const animateLayout = (onComplete) => {
      const useFullIntro = !hasPlayedPageIntro();
      const sidebar = document.querySelector('nav.docked');
      const topbar = document.querySelector('header.sticky');
      const main = document.querySelector('main');
      const pageRoot = main && Array.from(main.children).find((child) => !child.classList.contains('clinical-three-scene'));
      const navLinks = sidebar
        ? $('.flex-1 > a, .mt-auto > a, form button, .px-3.pt-3', sidebar).filter(isRenderable)
        : [];
      const statusPills = pageRoot
        ? $('[class*="rounded-full"], [class*="shadow-soft"]', pageRoot).slice(0, 8).filter(isRenderable)
        : [];

      const layers = [sidebar, topbar, pageRoot].filter(isRenderable);
      const restoreLayout = withLayers(layers);
      const restoreNav = withLayers(navLinks);
      const restorePills = withLayers(statusPills);

      const timeline = window.anime.timeline({
        easing: 'easeOutCubic',
        complete: () => {
          restoreLayout();
          restoreNav();
          restorePills();
          markPageIntroPlayed();
          if (typeof onComplete === 'function') onComplete();
        },
      });

      if (useFullIntro && sidebar && isRenderable(sidebar)) {
        timeline.add({
          targets: sidebar,
          translateX: [-18, 0],
          opacity: [0, 1],
          duration: 420,
        }, 0);
      }

      if (useFullIntro && topbar && isRenderable(topbar)) {
        timeline.add({
          targets: topbar,
          translateY: [-12, 0],
          opacity: [0, 1],
          duration: 360,
        }, 60);
      }

      if (useFullIntro && navLinks.length) {
        timeline.add({
          targets: navLinks,
          translateX: [-8, 0],
          opacity: [0, 1],
          delay: window.anime.stagger(28),
          duration: 300,
        }, 120);
      }

      if (pageRoot && isRenderable(pageRoot)) {
        timeline.add({
          targets: pageRoot,
          translateY: useFullIntro ? [16, 0] : [4, 0],
          opacity: useFullIntro ? [0, 1] : [0.96, 1],
          duration: useFullIntro ? 460 : 160,
        }, useFullIntro ? 110 : 0);
      }

      if (useFullIntro && statusPills.length) {
        timeline.add({
          targets: statusPills,
          translateY: [8, 0],
          opacity: [0, 1],
          scale: [0.98, 1],
          delay: window.anime.stagger(24),
          duration: 280,
        }, 240);
      }

      // Active items keep their Tailwind transform class; avoid overlapping
      // anime.js transforms during sidebar startup.
    };

    const revealStaggerGroups = () => {
      const observer = makeObserver((parent) => {
        const items = $('[data-anim-item]', parent).filter(isRenderable);
        if (!items.length) return;

        const restore = withLayers(items);
        animateOnce(items, {
          translateY: [14, 0],
          opacity: [0, 1],
          scale: [0.985, 1],
          delay: window.anime.stagger(42),
          duration: 420,
          easing: 'easeOutQuart',
          complete: restore,
        });
      });

      $('[data-anim="stagger"]').forEach((parent) => observer.observe(parent));
    };

    const animateCounters = () => {
      const observer = makeObserver((el) => {
        const target = Number.parseFloat(el.dataset.to || el.textContent || '0');
        if (!Number.isFinite(target)) return;

        const decimals = Number.parseInt(el.dataset.decimals || '0', 10);
        const suffix = el.dataset.suffix || '';
        const value = { current: 0 };

        animateOnce(value, {
          current: target,
          duration: 950,
          easing: 'easeOutExpo',
          update: () => {
            el.textContent = value.current.toLocaleString('vi-VN', {
              minimumFractionDigits: decimals,
              maximumFractionDigits: decimals,
            }) + suffix;
          },
          complete: () => {
            el.textContent = target.toLocaleString('vi-VN', {
              minimumFractionDigits: decimals,
              maximumFractionDigits: decimals,
            }) + suffix;
          },
        });
      }, { threshold: 0.35 });

      $('[data-anim="count"]').forEach((el) => observer.observe(el));
    };

    const animateBars = () => {
      const observer = makeObserver((el) => {
        const target = Number.parseFloat(el.dataset.to || el.style.width || '0');
        if (!Number.isFinite(target)) return;
        el.style.width = '0%';

        animateOnce(el, {
          width: `${Math.max(0, Math.min(target, 100))}%`,
          duration: 850,
          easing: 'easeOutQuart',
        });
      }, { threshold: 0.35 });

      $('[data-anim="bar"]').forEach((el) => observer.observe(el));
    };

    const animatePulse = () => {
      $('[data-anim="pulse"]').filter(isRenderable).forEach((el) => {
        animateOnce(el, {
          scale: [1, 1.08, 1],
          opacity: [1, 0.82, 1],
          duration: 1600,
          easing: 'easeInOutSine',
          loop: true,
        });
      });
    };

    const animateAuthCards = () => {
      $('[data-anim="auth-card"]').filter(isRenderable).forEach((card) => {
        const restoreCard = withLayer(card);
        animateOnce(card, {
          translateY: [24, 0],
          scale: [0.97, 1],
          opacity: [0, 1],
          duration: 540,
          easing: 'easeOutQuart',
          complete: restoreCard,
        });

        const children = $('label, input, button, a, .auth-stagger', card).filter(isRenderable);
        if (!children.length) return;

        const restoreChildren = withLayers(children);
        animateOnce(children, {
          translateY: [8, 0],
          opacity: [0, 1],
          delay: window.anime.stagger(34, { start: 180 }),
          duration: 320,
          easing: 'easeOutQuart',
          complete: restoreChildren,
        });
      });
    };

    const attachMicroInteractions = () => {
      const interactiveSelector = [
        'button:not([disabled])',
        'a[href]',
        '[role="button"]',
        'tbody tr',
        '[data-anim-item]',
      ].join(',');

      const targets = $(interactiveSelector)
        .filter(isRenderable)
        .filter((el) => !el.closest('[data-anim="auth-card"] input'));

      targets.forEach((el) => {
        if (el.dataset.motionBound === 'true') return;
        el.dataset.motionBound = 'true';

        el.addEventListener('mouseenter', () => {
          if (!canAnimate || el.matches(':disabled')) return;
          animateOnce(el, {
            translateY: -2,
            scale: el.tagName === 'TR' ? 1 : 1.01,
            duration: 180,
            easing: 'easeOutQuad',
          });
        });

        el.addEventListener('mouseleave', () => {
          if (!canAnimate) return;
          animateOnce(el, {
            translateY: 0,
            scale: 1,
            duration: 220,
            easing: 'easeOutQuad',
          });
        });

        el.addEventListener('pointerdown', () => {
          if (!canAnimate || el.matches(':disabled')) return;
          animateOnce(el, {
            scale: el.tagName === 'TR' ? 1 : 0.985,
            duration: 90,
            easing: 'easeOutQuad',
          });
        });

        el.addEventListener('pointerup', () => {
          if (!canAnimate || el.matches(':disabled')) return;
          animateOnce(el, {
            scale: 1,
            duration: 160,
            easing: 'easeOutQuad',
          });
        });
      });
    };

    const animateFilterChanges = () => {
      if (!('MutationObserver' in window)) return;
      const rows = $('.patient-row, tr[data-anim-item]').filter(isRenderable);

      rows.forEach((row) => {
        if (row.dataset.filterMotionBound === 'true') return;
        row.dataset.filterMotionBound = 'true';

        const observer = new MutationObserver((mutations) => {
          mutations.forEach((mutation) => {
            if (mutation.attributeName !== 'class') return;
            if (row.classList.contains('hidden')) return;

            animateOnce(row, {
              opacity: [0, 1],
              translateX: [-6, 0],
              duration: 220,
              easing: 'easeOutQuad',
            });
          });
        });

        observer.observe(row, { attributes: true, attributeFilter: ['class'] });
      });
    };

    const animateInsertedRows = () => {
      const body = document.getElementById('records-body');
      if (!body || !('MutationObserver' in window)) return;

      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          mutation.addedNodes.forEach((node) => {
            if (!(node instanceof HTMLElement) || !node.matches('tr')) return;
            attachMicroInteractions();
            animateOnce(node, {
              opacity: [0, 1],
              translateY: [10, 0],
              duration: 280,
              easing: 'easeOutQuart',
            });
          });
        });
      });

      observer.observe(body, { childList: true });
    };

    const createToastHost = () => {
      let host = document.getElementById('anim-toast-host');
      if (host) return host;

      host = document.createElement('div');
      host.id = 'anim-toast-host';
      host.className = 'fixed bottom-6 right-6 z-[100] flex flex-col gap-2 pointer-events-none';
      document.body.appendChild(host);
      return host;
    };

    window.showToast = function showToast(message, kind) {
      const palette = {
        success: 'bg-primary text-on-primary',
        error: 'bg-error text-on-error',
        info: 'bg-secondary-container text-on-secondary-container',
      };
      const host = createToastHost();
      const el = document.createElement('div');
      el.className = `${palette[kind] || palette.info} px-4 py-2 rounded-lg shadow-lg text-label-md font-label-md pointer-events-auto`;
      el.textContent = message;
      host.appendChild(el);

      if (!canAnimate) {
        setTimeout(() => el.remove(), 2800);
        return;
      }

      animateOnce(el, {
        translateY: [14, 0],
        opacity: [0, 1],
        scale: [0.98, 1],
        duration: 260,
        easing: 'easeOutQuart',
      });

      setTimeout(() => {
        animateOnce(el, {
          translateX: [0, 20],
          opacity: [1, 0],
          duration: 220,
          easing: 'easeInQuad',
          complete: () => el.remove(),
        });
      }, 2600);
    };

    if (!canAnimate) return;

      animateLayout(() => {
        attachMicroInteractions();
        animateFilterChanges();
        animateInsertedRows();
      });
      revealStaggerGroups();
      animateCounters();
      animateBars();
      animatePulse();
      animateAuthCards();
  });
})();
