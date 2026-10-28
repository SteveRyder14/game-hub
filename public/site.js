/* ==========================================================================
   UNiQ Games - shared script
   Every page loads this file. To change a download link, edit RELEASES.
   ========================================================================== */
(() => {
  "use strict";

  const RELEASES = {
    tictactoe: "https://github.com/SteveRyder14/tictactoe-server/releases/tag/v1.0",
    checkers: "https://github.com/SteveRyder14/tictactoe-server/releases/tag/v1.0", // same release page as Tic Tac Toe
  };

  const root = document.documentElement;
  root.classList.add("js");

  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  /* 1. Download buttons read their link from RELEASES */
  $$("[data-download]").forEach((el) => {
    const url = RELEASES[el.dataset.download];
    const label = el.querySelector("span");
    if (url) {
      el.href = url;
      el.target = "_blank";
      el.rel = "noopener noreferrer";
    } else {
      el.removeAttribute("href");
      el.setAttribute("aria-disabled", "true");
      if (label) label.textContent = "Coming soon";
    }
  });

  /* 2. Scroll reveal */
  const revealEls = $$(".rv");
  let revealObserver = null;
  const reveal = (el) => {
    el.classList.add("in");
    if (revealObserver) revealObserver.unobserve(el);
  };
  if (reduce || !("IntersectionObserver" in window)) {
    revealEls.forEach(reveal);
  } else {
    let ioWorked = false;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            ioWorked = true;
            reveal(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" }
    );
    revealObserver = io;
    revealEls.forEach((el) => io.observe(el));

    // Embedded webviews sometimes never run the observer until the user
    // scrolls. Fall back to a plain viewport check so content is never
    // left invisible; it steps aside as soon as the observer reports.
    const revealVisible = () => {
      if (ioWorked) return;
      revealEls.forEach((el) => {
        if (el.classList.contains("in")) return;
        const r = el.getBoundingClientRect();
        if (r.top < window.innerHeight * 0.94 && r.bottom > 0) reveal(el);
      });
    };
    setTimeout(revealVisible, 600);
    window.addEventListener("scroll", revealVisible, { passive: true });
    window.addEventListener("resize", revealVisible);
  }

  /* 3. Scroll state: nav shadow, progress bar, back-to-top, active link */
  const nav = document.querySelector(".nav");
  const bar = document.querySelector(".scroll-progress i");
  const toTop = document.querySelector(".to-top");
  const navAnchors = $$(".nav-links a[href^='#']")
    .map((a) => ({ a, target: document.querySelector(a.getAttribute("href")) }))
    .filter((x) => x.target);

  const onScroll = () => {
    const y = window.scrollY;
    if (nav) nav.classList.toggle("scrolled", y > 24);
    if (bar) {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.transform = `scaleX(${max > 0 ? Math.min(y / max, 1) : 0})`;
    }
    if (toTop) toTop.classList.toggle("show", y > 640);
    if (navAnchors.length) {
      const offset = y + 150;
      let best = null;
      navAnchors.forEach(({ target, a }) => {
        if (target.offsetTop <= offset) best = a;
      });
      navAnchors.forEach(({ a }) => a.classList.toggle("active", best === a));
    }
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  if (toTop) {
    toTop.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
    });
  }

  /* 4. Pointer light on glass and buttons, restrained tilt on surfaces */
  if (fine && !reduce) {
    // Written directly (not via rAF) so the highlight keeps tracking in
    // embedded webviews that only paint on interaction.
    $$(".glass, .btn").forEach((el) => {
      el.addEventListener("pointermove", (e) => {
        const r = el.getBoundingClientRect();
        el.style.setProperty("--mx", `${e.clientX - r.left}px`);
        el.style.setProperty("--my", `${e.clientY - r.top}px`);
      });
    });

    $$(".tilt, .card, .panel").forEach((el) => {
      let frame = 0;
      const intensity = el.classList.contains("card") ? 3.5 : el.classList.contains("panel") ? 2.5 : 7;
      el.addEventListener("pointermove", (e) => {
        if (frame) return;
        frame = requestAnimationFrame(() => {
          frame = 0;
          const r = el.getBoundingClientRect();
          const x = (e.clientX - r.left) / r.width - 0.5;
          const y = (e.clientY - r.top) / r.height - 0.5;
          el.style.setProperty("--ry", `${x * intensity}deg`);
          el.style.setProperty("--rx", `${-y * intensity * 0.7}deg`);
        });
      });
      el.addEventListener("pointerleave", () => {
        el.style.setProperty("--rx", "0deg");
        el.style.setProperty("--ry", "0deg");
      });
    });
  }

  /* 5. Interactive 3D showcase: drag the cube to spin it, with momentum.
     Works for mouse, pen and touch (vertical swipes still scroll the page). */
  const stage = document.querySelector(".showcase-stage");
  if (stage) {
    const spin = stage.querySelector(".stage-spin");
    let rotX = 0, rotY = 0;
    let dragging = false, pid = null;
    let lastX = 0, lastY = 0, velX = 0, velY = 0, glide = 0;

    const apply = () => {
      if (!spin) return;
      spin.style.setProperty("--spin-x", `${rotX.toFixed(2)}deg`);
      spin.style.setProperty("--spin-y", `${rotY.toFixed(2)}deg`);
    };
    const stopGlide = () => {
      if (glide) cancelAnimationFrame(glide);
      glide = 0;
      stage.classList.remove("is-spinning");
    };
    const startGlide = () => {
      stopGlide();
      velX = Math.max(-12, Math.min(12, velX));
      velY = Math.max(-14, Math.min(14, velY));
      if (reduce || (Math.abs(velX) < 0.06 && Math.abs(velY) < 0.06)) return;
      stage.classList.add("is-spinning");
      const step = () => {
        velX *= 0.93;
        velY *= 0.93;
        rotX += velX;
        rotY += velY;
        apply();
        if (Math.abs(velX) < 0.06 && Math.abs(velY) < 0.06) {
          stopGlide();
          return;
        }
        glide = requestAnimationFrame(step);
      };
      glide = requestAnimationFrame(step);
    };
    const endDrag = (e) => {
      if (!dragging) return;
      dragging = false;
      stage.classList.remove("is-dragging");
      if (pid !== null) {
        try { stage.releasePointerCapture(pid); } catch {}
      }
      pid = null;
      // A cancelled gesture (e.g. a vertical touch scroll) should not coast.
      if (e && e.type === "pointercancel") stopGlide();
      else startGlide();
    };

    stage.addEventListener("pointerenter", () => stage.classList.add("is-live"));
    stage.addEventListener("pointerdown", (e) => {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      stopGlide();
      dragging = true;
      pid = e.pointerId;
      lastX = e.clientX;
      lastY = e.clientY;
      velX = 0;
      velY = 0;
      stage.classList.add("is-dragging", "has-spun", "is-live");
      try { stage.setPointerCapture(pid); } catch {}
    });
    stage.addEventListener("pointermove", (e) => {
      const r = stage.getBoundingClientRect();
      const px = e.clientX - r.left;
      const py = e.clientY - r.top;
      stage.style.setProperty("--mx", `${px}px`);
      stage.style.setProperty("--my", `${py}px`);

      if (dragging) {
        const dx = e.clientX - lastX;
        const dy = e.clientY - lastY;
        lastX = e.clientX;
        lastY = e.clientY;
        rotY += dx * 0.5;
        rotX -= dy * 0.42;
        velY = dx * 0.5;
        velX = -dy * 0.42;
        apply();
        return;
      }
      if (fine && !reduce) {
        stage.style.setProperty("--tilt-x", `${(0.5 - py / r.height) * 40}deg`);
        stage.style.setProperty("--tilt-y", `${(px / r.width - 0.5) * 64}deg`);
      }
    });
    stage.addEventListener("pointerup", endDrag);
    stage.addEventListener("pointercancel", endDrag);
    stage.addEventListener("pointerleave", () => {
      if (dragging) return;
      stage.classList.remove("is-live");
      stage.style.setProperty("--tilt-x", "0deg");
      stage.style.setProperty("--tilt-y", "0deg");
    });
    stage.addEventListener("keydown", (e) => {
      const step = e.shiftKey ? 45 : 15;
      const moves = {
        ArrowLeft: [0, -step],
        ArrowRight: [0, step],
        ArrowUp: [-step, 0],
        ArrowDown: [step, 0],
      };
      const move = moves[e.key];
      if (!move) return;
      e.preventDefault();
      stopGlide();
      rotX += move[0];
      rotY += move[1];
      stage.classList.add("has-spun");
      apply();
    });
  }

  /* 6. Press ripple on buttons */
  if (!reduce) {
    $$(".btn").forEach((btn) => {
      btn.addEventListener("pointerdown", (e) => {
        if (e.button !== 0) return;
        const r = btn.getBoundingClientRect();
        const size = Math.max(r.width, r.height) * 1.8;
        const ripple = document.createElement("span");
        ripple.className = "ripple";
        ripple.setAttribute("aria-hidden", "true");
        ripple.style.width = ripple.style.height = `${size}px`;
        ripple.style.left = `${e.clientX - r.left - size / 2}px`;
        ripple.style.top = `${e.clientY - r.top - size / 2}px`;
        btn.appendChild(ripple);
        ripple.addEventListener("animationend", () => ripple.remove(), { once: true });
        setTimeout(() => ripple.remove(), 900);
      });
    });
  }

  /* 7. Horizontal shelves: arrows, progress bar, mouse drag, keyboard */
  $$(".shelf").forEach((shelf) => {
    const track = shelf.querySelector(".track");
    if (!track) return;
    const prev = shelf.querySelector("[data-prev]");
    const next = shelf.querySelector("[data-next]");
    const bar = shelf.querySelector(".progress i");
    const maxScroll = () => track.scrollWidth - track.clientWidth;
    let queued = false;

    const update = () => {
      queued = false;
      const max = maxScroll();
      shelf.classList.toggle("is-static", max < 4);
      if (prev) prev.disabled = track.scrollLeft <= 4;
      if (next) next.disabled = track.scrollLeft >= max - 4;
      if (bar && max > 0) {
        const ratio = track.clientWidth / track.scrollWidth;
        const p = track.scrollLeft / max;
        bar.style.width = `${ratio * 100}%`;
        bar.style.transform = `translate3d(${((p * (1 - ratio)) / ratio) * 100}%, 0, 0)`;
      }
    };
    const queue = () => {
      if (!queued) {
        queued = true;
        requestAnimationFrame(update);
      }
    };
    const step = () => {
      const item = track.firstElementChild;
      const gap = parseFloat(getComputedStyle(track).columnGap) || 0;
      return item ? item.getBoundingClientRect().width + gap : track.clientWidth * 0.8;
    };

    if (prev) prev.addEventListener("click", () => track.scrollBy({ left: -step(), behavior: "smooth" }));
    if (next) next.addEventListener("click", () => track.scrollBy({ left: step(), behavior: "smooth" }));
    track.addEventListener("scroll", queue, { passive: true });
    track.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") {
        e.preventDefault();
        track.scrollBy({ left: step(), behavior: "smooth" });
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        track.scrollBy({ left: -step(), behavior: "smooth" });
      }
    });
    new ResizeObserver(queue).observe(track);
    window.addEventListener("resize", queue);
    update();

    let down = false;
    let moved = false;
    let startX = 0;
    let startLeft = 0;

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
        track.classList.add("dragging");
      }
      if (moved) track.scrollLeft = startLeft - dx;
    });
    // Stop the browser starting its own image/link drag, which would swallow our pointer events
    track.addEventListener("dragstart", (e) => e.preventDefault());

    const release = () => {
      if (!down) return;
      down = false;
      if (!moved) return;
      const pad = parseFloat(getComputedStyle(track).scrollPaddingLeft) || 0;
      const max = maxScroll();
      let best = track.scrollLeft;
      let bestDist = Infinity;
      for (const child of track.children) {
        const target = Math.min(Math.max(child.offsetLeft - pad, 0), max);
        const dist = Math.abs(target - track.scrollLeft);
        if (dist < bestDist) {
          bestDist = dist;
          best = target;
        }
      }
      track.scrollTo({ left: best, behavior: "smooth" });
      setTimeout(() => {
        track.classList.remove("dragging");
        moved = false;
      }, 500);
    };
    window.addEventListener("pointerup", release);
    window.addEventListener("pointercancel", release);
    // A drag must not also count as a click on a card or screenshot
    track.addEventListener(
      "click",
      (e) => {
        if (moved) {
          e.preventDefault();
          e.stopPropagation();
        }
      },
      true
    );
  });

  /* 8. Screenshot viewer */
  const lb = document.createElement("div");
  lb.className = "lb";
  lb.setAttribute("role", "dialog");
  lb.setAttribute("aria-modal", "true");
  lb.setAttribute("aria-label", "Screenshot viewer");
  lb.innerHTML = `
    <figure><img alt=""><figcaption></figcaption></figure>
    <button class="lb-btn lb-close" type="button" aria-label="Close"><i class="fa-solid fa-xmark"></i></button>
    <button class="lb-btn lb-prev" type="button" aria-label="Previous screenshot"><i class="fa-solid fa-chevron-left"></i></button>
    <button class="lb-btn lb-next" type="button" aria-label="Next screenshot"><i class="fa-solid fa-chevron-right"></i></button>`;
  document.body.appendChild(lb);

  const lbImg = lb.querySelector("img");
  const lbCaption = lb.querySelector("figcaption");
  let items = [];
  let index = 0;
  let returnFocus = null;

  const showItem = (i) => {
    if (!items.length) return;
    index = (i + items.length) % items.length;
    const item = items[index];
    lbImg.src = item.src;
    lbImg.alt = item.alt;
    lbCaption.textContent = item.caption;
  };
  const openViewer = (list, i) => {
    items = list;
    returnFocus = document.activeElement;
    showItem(i);
    lb.classList.add("open");
    root.style.overflow = "hidden";
    lb.querySelector(".lb-close").focus({ preventScroll: true });
  };
  const closeViewer = () => {
    lb.classList.remove("open");
    root.style.overflow = "";
    if (returnFocus) returnFocus.focus({ preventScroll: true });
  };

  lb.querySelector(".lb-close").addEventListener("click", closeViewer);
  lb.querySelector(".lb-prev").addEventListener("click", () => showItem(index - 1));
  lb.querySelector(".lb-next").addEventListener("click", () => showItem(index + 1));
  lb.addEventListener("click", (e) => {
    if (e.target === lb) closeViewer();
  });
  document.addEventListener("keydown", (e) => {
    if (!lb.classList.contains("open")) return;
    if (e.key === "Escape") { closeViewer(); return; }
    if (e.key === "ArrowRight") { e.preventDefault(); showItem(index + 1); }
    if (e.key === "ArrowLeft") { e.preventDefault(); showItem(index - 1); }
    // Keep keyboard focus inside the dialog
    if (e.key === "Tab") {
      const btns = $$(".lb-btn", lb);
      const first = btns[0];
      const last = btns[btns.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });

  $$("[data-zoom]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const group = $$(`[data-zoom][data-group="${btn.dataset.group}"]`);
      openViewer(
        group.map((b) => ({ src: b.dataset.src, alt: b.dataset.alt, caption: b.dataset.caption })),
        group.indexOf(btn)
      );
    });
  });

  /* 9. Count-up numbers in the stats band */
  const countEls = $$("[data-count]");
  if (countEls.length && "IntersectionObserver" in window && !reduce) {
    const lerp = (t) => 1 - Math.pow(1 - t, 3);
    const run = (el) => {
      const target = parseInt(el.dataset.count, 10) || 0;
      const t0 = performance.now();
      const dur = 1400;
      const tick = (now) => {
        const t = Math.min((now - t0) / dur, 1);
        el.textContent = Math.round(lerp(t) * target);
        if (t < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    const cio = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            run(entry.target);
            cio.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.5 }
    );
    countEls.forEach((el) => cio.observe(el));
  }

  /* 10. Footer year */
  $$("[data-year]").forEach((el) => {
    el.textContent = new Date().getFullYear();
  });
})();

