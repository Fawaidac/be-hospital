// Mutation observer to detect when Flutter mounts the app
const observer = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    mutation.addedNodes.forEach((node) => {
      if (node.tagName === 'FLUTTER-VIEW' || node.tagName === 'FLT-GLASS-PANE') {
        const loader = document.getElementById('loading-container');
        if (loader) {
          loader.style.opacity = '0';
          setTimeout(() => {
            loader.remove();
          }, 600);
        }
        observer.disconnect();
      }
    });
  });
});
observer.observe(document.body, { childList: true });

// Fun dynamic loading status messages for Gen Z and young pros
const messages = [
  "initializing digital realm...",
  "decrypting the matrix...",
  "brewing fresh code...",
  "warming up pixels...",
  "aligning the stars...",
  "loading awesome features...",
  "reticulatng splines...",
  "almost there, hang tight..."
];
let index = 0;
const statusEl = document.getElementById('status-message');
if (statusEl) {
  setInterval(() => {
    statusEl.style.opacity = '0';
    setTimeout(() => {
      index = (index + 1) % messages.length;
      statusEl.textContent = messages[index];
      statusEl.style.opacity = '1';
    }, 300);
  }, 2200);
}
