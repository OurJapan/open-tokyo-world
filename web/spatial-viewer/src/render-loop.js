// Coalesce scene changes into one frame, then sleep until another change.
// draw returns true while a camera feed or controls damping needs more frames.
export function createRenderLoop(draw, {
  requestFrame = requestAnimationFrame,
  cancelFrame = cancelAnimationFrame,
} = {}) {
  let pending = null, paused = false;
  function requestRender() {
    if (paused || pending !== null) return;
    pending = requestFrame(now => {
      pending = null;
      if (draw(now)) requestRender();
    });
  }
  return {
    requestRender,
    pause() {
      paused = true;
      if (pending !== null) cancelFrame(pending);
      pending = null;
    },
    resume() {
      paused = false;
      requestRender();
    },
  };
}
