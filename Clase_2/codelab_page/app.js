/* ============================================
   App.js - Interactive Codelab Navigation
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
  // ── State ──
  let currentModule = 'general';
  let currentSteps = {};

  // ── DOM References ──
  const moduleTabs = document.querySelectorAll('.module-tab');
  const moduleContents = document.querySelectorAll('.module-content');
  const sidebar = document.querySelector('.sidebar');
  const menuToggle = document.querySelector('.menu-toggle');
  const progressBar = document.querySelector('.progress-bar');

  // ── Module Tab Navigation ──
  moduleTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const moduleId = tab.dataset.module;
      switchModule(moduleId);
    });
  });

  function switchModule(moduleId) {
    currentModule = moduleId;

    // Update tabs
    moduleTabs.forEach(t => t.classList.remove('active'));
    document.querySelector(`.module-tab[data-module="${moduleId}"]`)?.classList.add('active');

    // Update content
    moduleContents.forEach(c => c.classList.remove('active'));
    document.getElementById(`module-${moduleId}`)?.classList.add('active');

    // Update sidebar
    updateSidebar(moduleId);

    // Show first step if none active
    const firstStep = document.querySelector(`#module-${moduleId} .step-section`);
    if (firstStep && !document.querySelector(`#module-${moduleId} .step-section.active`)) {
      showStep(moduleId, firstStep.dataset.step);
    }

    updateProgress();
  }

  // ── Sidebar ──
  function updateSidebar(moduleId) {
    document.querySelectorAll('.sidebar-nav-group').forEach(g => {
      g.style.display = g.dataset.module === moduleId ? 'block' : 'none';
    });
  }

  // ── Step Navigation (Sidebar click) ──
  document.querySelectorAll('.sidebar-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const moduleId = item.closest('.sidebar-nav-group').dataset.module;
      const stepId = item.dataset.step;
      showStep(moduleId, stepId);

      // Close mobile sidebar
      if (window.innerWidth <= 768) {
        sidebar.classList.remove('open');
      }
    });
  });

  function showStep(moduleId, stepId) {
    currentSteps[moduleId] = stepId;

    // Update sidebar items
    const group = document.querySelector(`.sidebar-nav-group[data-module="${moduleId}"]`);
    if (group) {
      group.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
      group.querySelector(`.sidebar-item[data-step="${stepId}"]`)?.classList.add('active');
    }

    // Update step sections
    const moduleEl = document.getElementById(`module-${moduleId}`);
    if (moduleEl) {
      moduleEl.querySelectorAll('.step-section').forEach(s => s.classList.remove('active'));
      moduleEl.querySelector(`.step-section[data-step="${stepId}"]`)?.classList.add('active');
    }

    // Scroll top
    window.scrollTo({ top: 0, behavior: 'smooth' });
    updateProgress();
  }

  // ── Prev/Next Navigation ──
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const direction = btn.dataset.direction;
      const moduleId = btn.closest('.module-content').id.replace('module-', '');
      navigateStep(moduleId, direction);
    });
  });

  function navigateStep(moduleId, direction) {
    const moduleEl = document.getElementById(`module-${moduleId}`);
    const steps = Array.from(moduleEl.querySelectorAll('.step-section'));
    const currentIdx = steps.findIndex(s => s.classList.contains('active'));

    let nextIdx = direction === 'next' ? currentIdx + 1 : currentIdx - 1;
    if (nextIdx >= 0 && nextIdx < steps.length) {
      // Mark previous step completed
      if (direction === 'next' && currentIdx >= 0) {
        const group = document.querySelector(`.sidebar-nav-group[data-module="${moduleId}"]`);
        const items = group?.querySelectorAll('.sidebar-item');
        if (items && items[currentIdx]) {
          items[currentIdx].classList.add('completed');
        }
      }
      showStep(moduleId, steps[nextIdx].dataset.step);
    }
  }

  // ── Progress Bar ──
  function updateProgress() {
    const moduleEl = document.getElementById(`module-${currentModule}`);
    if (!moduleEl) return;
    const steps = moduleEl.querySelectorAll('.step-section');
    const activeStep = moduleEl.querySelector('.step-section.active');
    if (!activeStep || steps.length === 0) return;

    const idx = Array.from(steps).indexOf(activeStep);
    const pct = ((idx + 1) / steps.length) * 100;
    progressBar.style.width = pct + '%';
  }

  // ── Copy Code Buttons ──
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const codeBlock = btn.closest('.code-block') || btn.closest('.prompt-box');
      const codeEl = codeBlock.querySelector('pre') || codeBlock.querySelector('.prompt-text');
      if (!codeEl) return;

      const text = codeEl.textContent;
      navigator.clipboard.writeText(text).then(() => {
        btn.classList.add('copied');
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓ Copiado';
        setTimeout(() => {
          btn.classList.remove('copied');
          btn.innerHTML = originalText;
        }, 2000);
      }).catch(() => {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        btn.classList.add('copied');
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓ Copiado';
        setTimeout(() => {
          btn.classList.remove('copied');
          btn.innerHTML = originalText;
        }, 2000);
      });
    });
  });

  // ── Collapsible Sections ──
  document.querySelectorAll('.collapsible-header').forEach(header => {
    header.addEventListener('click', () => {
      const collapsible = header.closest('.collapsible');
      collapsible.classList.toggle('open');
    });
  });

  // ── Mobile Menu Toggle ──
  if (menuToggle) {
    menuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }

  // Close sidebar on click outside (mobile)
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
      if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    }
  });

  // ── Prompt boxes clickable (copy) ──
  document.querySelectorAll('.prompt-box').forEach(box => {
    if (!box.querySelector('.copy-btn')) return;
    box.style.cursor = 'pointer';
  });

  // ── Initialize ──
  switchModule('general');
});
