/* ==========================================================================
   UNiQ Games - shared script

   1) EDIT THIS: the GitHub release page for each game.
      Every Download button on the site reads its link from here, so you only
      change it in this one place.
   ========================================================================== */
const SITE = {
  releases: {
    tictactoe: "https://github.com/YOUR-USERNAME/YOUR-TICTACTOE-REPO/releases/latest",
    checkers: "https://github.com/YOUR-USERNAME/YOUR-CHECKERS-REPO/releases/latest",
  },
};

/* --------------------------------------------------------------------------
   Download buttons: <a data-download="tictactoe"> gets its link from SITE.
   -------------------------------------------------------------------------- */
document.querySelectorAll("[data-download]").forEach((a) => {
  const url = SITE.releases[a.dataset.download];
  if (!url) return;
  a.href = url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
});

/* Footer year */
document.querySelectorAll("[data-year]").forEach((el) => {
  el.textContent = new Date().getFullYear();
});

/* --------------------------------------------------------------------------
   Shelf: horizontal slider with arrows, progress bar and mouse dragging.
   Markup: .shelf > ( [data-prev] [data-next] ) + .track + .progress > i
   Touch devices use native swipe + CSS scroll-snap, which is the smoothest.
   -------------------------------------------------------------------------- */
function initShelf(shelf) {
  const track = shelf.querySelector(".track");
  const prev = shelf.querySelector("[data-prev]");
  const next = shelf.querySelector("[data-next]");
  const thumb = shelf.querySelector(".progress i");
  if (!track) return;

  let ticking = false;

  const update = () => {
    ticking = false;
    const max = track.scrollWidth - track.clientWidth;
    const scrollable = max > 4;
    shelf.classList.toggle("is-static", !scrollable);
    if (!scrollable) return;

    if (prev) prev.disabled = track.scrollLeft <= 4;
    if (next) next.disabled = track.scrollLeft >= max - 4;

    if (thumb) {
      const ratio = track.clientWidth / track.scrollWidth;
      const progress = track.scrollLeft / max;
      thumb.style.width = ratio * 100 + "%";
      thumb.style.transform = `translate3d(${progress * (1 / ratio - 1) * 100}%,0,0)`;
    }
  };

  const queueUpdate = () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(update);
    }
  };

  const step = () => {
    const first = track.firstElementChild;
    if (!first) return track.clientWidth * 0.8;
    const gap = parseFloat(getComputedStyle(track).columnGap) || 0;
    return first.getBoundingClientRect().width + gap;
  };

  prev && prev.addEventListener("click", () => track.scrollBy({ left: -step(), behavior: "smooth" }));
  next && next.addEventListener("click", () => track.scrollBy({ left: step(), behavior: "smooth" }));

  track.addEventListener("scroll", queueUpdate, { passive: true });
  if ("ResizeObserver" in window) new ResizeObserver(queueUpdate).observe(track);
  window.addEventListener("resize", queueUpdate);
  update();

  /* Mouse drag (touch and trackpads already scroll natively) */
  let down = false;
  let moved = false;
  let startX = 0;
  let startLeft = 0;

  const snapToNearest = () => {
    const max = track.scrollWidth - track.clientWidth;
    const pad = parseFloat(getComputedStyle(track).scrollPaddingInlineStart) || 0;
    let best = 0;
    let bestDist = Infinity;
    for (const card of track.children) {
      const target = Math.min(Math.max(card.offsetLeft - pad, 0), max);
      const dist = Math.abs(target - track.scrollLeft);
      if (dist < bestDist) {
        bestDist = dist;
        best = target;
      }
    }
    track.scrollTo({ left: best, behavior: "smooth" });
    // Re-enable CSS snapping once the glide has finished
    setTimeout(() => track.classList.remove("is-dragging"), 480);
  };

  track.addEventListener("pointerdown", (e) => {
    if (e.pointerType !== "mouse" || e.button !== 0) return;
    down = true;
    moved = false;
    startX = e.clientX;
    startLeft = track.scrollLeft;
  });

  window.addEventListener("pointermove", (e) => {
    if (!down) return;
    const dx = e.clientX - startX;
    if (!moved && Math.abs(dx) > 6) {
      moved = true;
      track.classList.add("is-dragging");
    }
    if (moved) track.scrollLeft = startLeft - dx;
  });

  window.addEventListener("pointerup", () => {
    if (!down) return;
    down = false;
    if (moved) snapToNearest();
  });

  // A drag should not count as a click on the card underneath
  track.addEventListener(
    "click",
    (e) => {
      if (moved) {
        e.preventDefault();
        e.stopPropagation();
        moved = false;
      }
    },
    true
  );
}

document.querySelectorAll(".shelf").forEach(initShelf);

/* --------------------------------------------------------------------------
   Pointer glow on cards and panels (desktop only)
   -------------------------------------------------------------------------- */
if (window.matchMedia("(hover: hover)").matches) {
  document.querySelectorAll(".card, .panel").forEach((el) => {
    let raf = 0;
    el.addEventListener("pointermove", (e) => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        const r = el.getBoundingClientRect();
        el.style.setProperty("--mx", e.clientX - r.left + "px");
        el.style.setProperty("--my", e.clientY - r.top + "px");
      });
    });
  });
}
