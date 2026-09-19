/* ===================================================
   CAMPUS BITES: INTERACTIVE CLIENT JAVASCRIPT
   =================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Food Menu Filtering & Live Search
  const searchInput = document.getElementById('foodSearchInput');
  const categoryPills = document.querySelectorAll('.pill-btn');
  const foodCards = document.querySelectorAll('.food-card');

  let activeCategory = 'All';
  let searchTerm = '';

  function filterFoodItems() {
    let visibleCount = 0;
    foodCards.forEach(card => {
      const cardCategory = card.getAttribute('data-category') || '';
      const cardName = (card.getAttribute('data-name') || '').toLowerCase();

      const matchesCategory = (activeCategory === 'All') || (cardCategory.toLowerCase() === activeCategory.toLowerCase());
      const matchesSearch = cardName.includes(searchTerm.toLowerCase());

      if (matchesCategory && matchesSearch) {
        card.style.display = 'flex';
        visibleCount++;
      } else {
        card.style.display = 'none';
      }
    });

    const noItemsMsg = document.getElementById('noFoodItemsMsg');
    if (noItemsMsg) {
      noItemsMsg.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  }

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchTerm = e.target.value.trim();
      filterFoodItems();
    });
  }

  if (categoryPills.length > 0) {
    categoryPills.forEach(pill => {
      pill.addEventListener('click', () => {
        categoryPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        activeCategory = pill.getAttribute('data-category');
        filterFoodItems();
      });
    });
  }

  // 2. Ready Notification chime on Tracking Page
  const readyBanner = document.getElementById('readyCalloutBanner');
  if (readyBanner && !sessionStorage.getItem('notifiedReady_' + window.location.pathname)) {
    sessionStorage.setItem('notifiedReady_' + window.location.pathname, 'true');
    // Optional web audio chime
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
      osc.frequency.setValueAtTime(880, audioCtx.currentTime + 0.15); // A5
      gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.6);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.6);
    } catch(e) {
      // Audio context might be restricted before user interaction
    }

    // Try browser notification if permitted
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('🎉 Campus Bites Canteen', {
        body: 'Your food token is READY for pickup at the counter!',
        icon: '/static/images/samosa.jpg'
      });
    }
  }

  // Auto-dismiss alert boxes after 5 seconds
  const alerts = document.querySelectorAll('.alert');
  if (alerts.length > 0) {
    setTimeout(() => {
      alerts.forEach(a => {
        a.style.transition = 'opacity 0.5s ease';
        a.style.opacity = '0';
        setTimeout(() => a.remove(), 500);
      });
    }, 5000);
  }
});
