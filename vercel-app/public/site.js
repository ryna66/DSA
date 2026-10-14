function filterCards(query) {
  const q = query.trim().toLowerCase();
  let visible = 0;
  document.querySelectorAll('.project-card').forEach(card => {
    const matches = (card.dataset.terms + ' ' + card.textContent).toLowerCase().includes(q);
    card.style.display = matches ? '' : 'none';
    if (matches) visible++;
  });
  const empty = document.getElementById('empty-search');
  if (empty) empty.hidden = visible > 0;
}

// Keep names/initials visible even if a profile image cannot be loaded.
document.querySelectorAll('.avatar img').forEach(img => {
  const hideBrokenImage = () => { img.hidden = true; img.style.display = 'none'; };
  img.addEventListener('error', hideBrokenImage);
  if (img.complete && img.naturalWidth === 0) hideBrokenImage();
});

// Pause decorative motion offscreen and when the tab is hidden.
const animatedSections = document.querySelectorAll('.landing-hero, .about-hero, .members-section');
if ('IntersectionObserver' in window) {
  const updateMotion = element => {
    const paused = document.hidden || element.dataset.inView === 'false';
    element.querySelectorAll('.beams-layer, .aurora-waves, .avatar-orbit, .orbit, .orbit-node, .team-core, .ambient').forEach(node => {
      node.style.animationPlayState = paused ? 'paused' : 'running';
    });
  };
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      entry.target.dataset.inView = String(entry.isIntersecting);
      updateMotion(entry.target);
    });
  });
  animatedSections.forEach(section => observer.observe(section));
  document.addEventListener('visibilitychange', () => animatedSections.forEach(updateMotion));
}
