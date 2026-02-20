# Mobile Touch Issues & Patterns for Canvas Games

Reusable patterns for preventing zoom, scroll, and orientation problems in mobile browser games. Learned from fixing Div Vaders; applicable to Rug Pull and future projects.

## 1. Viewport Meta Lockdown

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no">
```

`user-scalable=no` alone is **not enough** — iOS Safari has ignored it since iOS 10. You need all four constraints (`initial-scale`, `maximum-scale`, `minimum-scale`, `user-scalable`) to fully hint at the browser. Even then, Safari may still allow gestures, which is why the JS-level prevention below is essential.

## 2. Universal `touch-action: none`

```css
* { touch-action: none; }
```

Applying `touch-action: none` only to `body` or the canvas misses child elements and overlays. The universal selector covers everything — canvas, touch buttons, HUD overlays, modals — without needing per-element rules.

## 3. `overscroll-behavior: none`

```css
html { overscroll-behavior: none; }
```

Prevents pull-to-refresh and overscroll bounce on mobile browsers. Without this, dragging the game canvas can trigger Chrome's pull-to-refresh or Safari's rubber-band effect.

## 4. Safari Gesture Event Prevention

```javascript
document.addEventListener('gesturestart', function(e) { e.preventDefault(); }, { passive: false });
document.addEventListener('gesturechange', function(e) { e.preventDefault(); }, { passive: false });
document.addEventListener('gestureend', function(e) { e.preventDefault(); }, { passive: false });
```

Safari (iOS and macOS) fires proprietary `gesture*` events for pinch/rotate. These are separate from standard touch events. Preventing them blocks Safari's built-in pinch-to-zoom even when the viewport meta is ignored.

## 5. Multi-Touch `preventDefault` for Pinch

```javascript
document.addEventListener('touchstart', function(e) {
  if (e.touches.length > 1) e.preventDefault();
}, { passive: false });
document.addEventListener('touchmove', function(e) {
  if (e.touches.length > 1) e.preventDefault();
}, { passive: false });
```

Chrome and Firefox don't use `gesture*` events. Instead, prevent default on any multi-finger `touchstart`/`touchmove` to block pinch-zoom on those browsers.

## 6. `{ passive: false }` Requirement

Touch event listeners default to `passive: true` in modern browsers (Chrome 56+, Firefox, Safari) for performance. Calling `e.preventDefault()` inside a passive listener is silently ignored. You **must** explicitly pass `{ passive: false }` or the prevention won't work.

## 7. Visual Viewport API Zoom Recovery

```javascript
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', function() {
    if (window.visualViewport.scale !== 1) {
      var vp = document.querySelector('meta[name="viewport"]');
      vp.setAttribute('content', vp.getAttribute('content'));
    }
    resize();
  });
}
```

If the user somehow gets zoomed in (e.g., assistive zoom, browser bug), this detects a non-1 scale via the Visual Viewport API and forces a viewport meta re-evaluation by re-setting the attribute. This "refresh trick" causes Safari to snap back to scale 1.

## 8. Orientation Change with Delayed Resize

```javascript
window.addEventListener('orientationchange', function() {
  setTimeout(resize, 150);
});
```

iOS doesn't update `window.innerWidth`/`innerHeight` at the moment `orientationchange` fires — the values still reflect the old orientation. A 150ms delay allows the layout engine to settle before reading new dimensions.

## 9. Entity Re-Clamping on Resize

When the viewport changes (rotation, zoom recovery, resize), game entities can end up outside the visible area. After recalculating `W`, `H`, and `gameBottom`, re-clamp formations/entities:

```javascript
// Inside resize():
if (enemies.length > 0) {
  let aliveMinLX = Infinity, aliveMaxLX = -Infinity, aliveMaxLY = -Infinity;
  for (const e of enemies) {
    if (!e.alive) continue;
    aliveMinLX = Math.min(aliveMinLX, e.localX);
    aliveMaxLX = Math.max(aliveMaxLX, e.localX + e.w);
    aliveMaxLY = Math.max(aliveMaxLY, e.localY + e.h);
  }
  if (aliveMaxLX !== -Infinity) {
    if (formationX + aliveMaxLX > W - 10) formationX = W - 10 - aliveMaxLX;
    if (formationX + aliveMinLX < 10) formationX = 10 - aliveMinLX;
    if (formationY + aliveMaxLY > gameBottom - 50 * S) {
      formationY = gameBottom - 50 * S - aliveMaxLY;
    }
    if (formationY < 10) formationY = 10;
  }
}
```

The pattern: find the bounding box of alive entities in local coordinates, then adjust the formation origin so nothing extends beyond the margins. Apply this to any group of entities that moves as a unit.

## Checklist for New Games (e.g., Rug Pull)

- [ ] Viewport meta with all four scale constraints
- [ ] `* { touch-action: none; }` in CSS
- [ ] `html { overscroll-behavior: none; }` in CSS
- [ ] `gesturestart`/`gesturechange`/`gestureend` prevention (Safari)
- [ ] Multi-touch `preventDefault` on `touchstart`/`touchmove` (Chrome/Firefox)
- [ ] All touch listeners use `{ passive: false }`
- [ ] Visual Viewport zoom recovery if applicable
- [ ] `orientationchange` listener with delayed resize
- [ ] Entity re-clamping in resize handler
