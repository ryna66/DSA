/* Shared, cancellable handoff from input to output. Never scroll on page load. */
window.DemoUX = (() => {
  let target, input, last, playButton, controller;
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  function cancel() { controller?.abort(); controller = null; }
  function mount(options) {
    target = document.querySelector(options.target);
    input = document.querySelector(options.input);
    last = document.getElementById(options.last);
    playButton = document.getElementById(options.play);
    target.id = 'demo-output'; target.tabIndex = -1;
    target.classList.add('demo-output');
    const bar = document.createElement('div'); bar.className = 'demo-handoff';
    const hint = document.createElement('span'); hint.className = 'demo-hint';
    hint.textContent = 'Watch the steps · pause, explore, or skip ahead';
    const actions = document.createElement('div');
    const edit = document.createElement('button'); edit.type = 'button'; edit.textContent = '↑ Edit inputs';
    edit.addEventListener('click', () => { cancel(); input.scrollIntoView({behavior: reduced() ? 'instant' : 'smooth', block: 'start'}); });
    const finish = document.createElement('button'); finish.type = 'button'; finish.textContent = 'Show final result ↗';
    finish.addEventListener('click', () => { cancel(); if (!last.disabled) last.click(); });
    actions.append(edit, finish); bar.append(hint, actions);
    const sync = () => { finish.disabled = last.disabled; };
    new MutationObserver(sync).observe(last, {attributes:true, attributeFilter:['disabled']}); sync();
    target.querySelector('.panel-title, .panel-heading').after(bar);
    // Playback belongs above the picture, within immediate reach on mobile.
    const playback = target.querySelector('.playback');
    const timeline = target.querySelector('.timeline');
    if (playback) bar.after(playback);
    if (timeline) playback.after(timeline);
    target.addEventListener('click', cancel, {capture:true});
    target.addEventListener('input', cancel);
    input.addEventListener('input', cancel);
    input.addEventListener('click', cancel, {capture:true});
    document.addEventListener('visibilitychange', () => { if (document.hidden) cancel(); });
  }
  function present({play, finish}) {
    cancel();
    if (!target) return;
    if (reduced()) { finish(); target.scrollIntoView({behavior: 'instant', block: 'start'}); target.focus({preventScroll:true}); return; }
    const current = new AbortController(); controller = current;
    // A manual scroll/key or control interaction cancels pending autoplay.
    const opts = {once:true, passive:true, signal:current.signal};
    window.addEventListener('wheel', cancel, opts);
    window.addEventListener('touchstart', cancel, opts);
    window.addEventListener('keydown', cancel, opts);
    target.scrollIntoView({behavior:'smooth', block:'start'});
    let previous = window.scrollY, stable = 0, started = performance.now();
    function settle(now) {
      if (current.signal.aborted) return;
      stable = Math.abs(window.scrollY - previous) < .5 ? stable + 1 : 0;
      previous = window.scrollY;
      if ((stable >= 5 && now - started > 250) || now - started > 1400) {
        cancel();
        target.focus({preventScroll:true});
        if (!document.hidden) play();
      } else requestAnimationFrame(settle);
    }
    requestAnimationFrame(settle);
  }
  return {mount, present, cancel};
})();
