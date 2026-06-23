// ═══════════════════════════════════════════════════════
// TIENDAS MASS — PROYECTO ACADÉMICO
// JavaScript principal
// ═══════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function () {

  // Menú hamburguesa (mobile)
  const hamburger = document.getElementById('hamburger');
  const mobileMenu = document.getElementById('mobileMenu');
  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', function () {
      mobileMenu.classList.toggle('open');
      hamburger.textContent = mobileMenu.classList.contains('open') ? '✕' : '☰';
    });
  }

  // Auto-cerrar mensajes flash después de 5 segundos
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(function (flash) {
    setTimeout(function () {
      flash.style.transition = 'opacity .4s ease';
      flash.style.opacity = '0';
      setTimeout(function () { flash.remove(); }, 400);
    }, 5000);
  });

});

// Función global usada por sendPrompt-like helpers si se requiere en el futuro
function formatMoney(value) {
  return 'S/ ' + Number(value).toFixed(2);
}
