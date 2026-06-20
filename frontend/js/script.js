(() => {
  'use strict';

  // Если фронтенд раздаётся отдельно от backend (например, через GitHub Pages,
  // пока API задеплоен на Render) — укажите здесь полный адрес API:
  //   const API_BASE_URL = 'https://your-api.onrender.com';
  // Если фронтенд раздаётся самим backend'ом (как в этом проекте, через
  // FastAPI StaticFiles — см. app/main.py) — оставьте пустую строку,
  // запросы пойдут на тот же origin.
  const API_BASE_URL = '';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.getElementById('year').textContent = new Date().getFullYear();

  /* ---------------------------------------------------------------------
   * Hero panel: печатает запрос, реально дёргает GET /api/health и
   * показывает настоящий ответ. Если backend недоступен — мягкий fallback.
   * ------------------------------------------------------------------- */
  async function runHeroDemo() {
    const codeEl = document.getElementById('hero-code');
    const requestLine = 'GET /api/health';

    if (prefersReducedMotion) {
      codeEl.textContent = `$ ${requestLine}`;
    } else {
      await typeLine(codeEl, `$ ${requestLine}`);
    }

    let resultHtml;
    try {
      const res = await fetch(`${API_BASE_URL}/api/health`, { cache: 'no-store' });
      const data = await res.json();
      resultHtml =
        `<span class="line-status">200 OK</span>\n` +
        JSON.stringify(data, null, 2);
    } catch (err) {
      resultHtml =
        `<span class="line-muted">— нет соединения с backend —</span>\n` +
        JSON.stringify(
          { status: 'demo', note: 'Запустите backend локально, чтобы увидеть реальный ответ' },
          null,
          2
        );
    }

    const responseEl = document.createElement('div');
    responseEl.innerHTML = '\n\n' + resultHtml;
    codeEl.innerHTML = `$ ${requestLine}`;
    codeEl.parentElement.appendChild(responseEl);
  }

  function typeLine(el, text, speed = 28) {
    return new Promise((resolve) => {
      let i = 0;
      el.textContent = '';
      const tick = () => {
        el.textContent = text.slice(0, i) + (i < text.length ? '▌' : '');
        i += 1;
        if (i <= text.length) {
          setTimeout(tick, speed);
        } else {
          resolve();
        }
      };
      tick();
    });
  }

  /* ---------------------------------------------------------------------
   * Footer status indicator — реальный пинг /api/health
   * ------------------------------------------------------------------- */
  async function pingHealth() {
    const dot = document.getElementById('api-status-dot');
    const text = document.getElementById('api-status-text');
    try {
      const res = await fetch(`${API_BASE_URL}/api/health`, { cache: 'no-store' });
      if (!res.ok) throw new Error('not ok');
      dot.classList.add('online');
      text.textContent = 'API онлайн';
    } catch (err) {
      dot.classList.add('offline');
      text.textContent = 'API недоступен';
    }
  }

  /* ---------------------------------------------------------------------
   * Contact form — отправка на реальный POST /api/contact
   * ------------------------------------------------------------------- */
  const FIELD_LABELS = { name: 'имя', phone: 'телефон', email: 'email', comment: 'комментарий' };
  const SENTIMENT_LABELS = { positive: 'позитивная', neutral: 'нейтральная', negative: 'негативная' };
  const TYPE_LABELS = {
    question: 'вопрос',
    complaint: 'жалоба',
    feedback: 'отзыв',
    proposal: 'предложение',
    other: 'другое',
  };

  function clearFieldErrors(form) {
    form.querySelectorAll('.field-error').forEach((el) => (el.textContent = ''));
    form.querySelectorAll('[aria-invalid]').forEach((el) => el.removeAttribute('aria-invalid'));
  }

  function showBanner(banner, message, kind) {
    banner.hidden = false;
    banner.textContent = message;
    banner.classList.remove('success', 'error');
    banner.classList.add(kind);
  }

  function initContactForm() {
    const form = document.getElementById('contact-form');
    const banner = document.getElementById('form-banner');
    const submitBtn = document.getElementById('submit-btn');
    const submitLabel = document.getElementById('submit-btn-label');

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      clearFieldErrors(form);
      banner.hidden = true;

      const payload = {
        name: form.name.value.trim(),
        phone: form.phone.value.trim(),
        email: form.email.value.trim(),
        comment: form.comment.value.trim(),
      };

      submitBtn.disabled = true;
      submitLabel.textContent = 'Отправка…';

      try {
        const res = await fetch(`${API_BASE_URL}/api/contact`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const data = await res.json();

        if (res.status === 201) {
          const sentiment = SENTIMENT_LABELS[data.analysis.sentiment] || data.analysis.sentiment;
          const type = TYPE_LABELS[data.analysis.request_type] || data.analysis.request_type;
          const aiNote = data.analysis.ai_used
            ? 'оценил AI-провайдер'
            : 'оценено резервным алгоритмом (AI временно недоступен)';

          showBanner(
            banner,
            `Заявка получена · id ${data.id.slice(0, 8)}\n` +
              `Тональность: ${sentiment} · Тип обращения: ${type} (${aiNote})\n` +
              `Черновик ответа: «${data.analysis.suggested_reply}»`,
            'success'
          );
          form.reset();
        } else if (res.status === 422) {
          let hasFieldError = false;
          (data.detail || []).forEach((err) => {
            const field = err.loc && err.loc[err.loc.length - 1];
            const errorEl = document.getElementById(`error-${field}`);
            const inputEl = document.getElementById(`field-${field}`);
            if (errorEl && inputEl) {
              errorEl.textContent = err.msg;
              inputEl.setAttribute('aria-invalid', 'true');
              hasFieldError = true;
            }
          });
          showBanner(
            banner,
            hasFieldError ? 'Проверьте поля, отмеченные ниже.' : 'Не удалось отправить форму — проверьте данные.',
            'error'
          );
        } else if (res.status === 429) {
          showBanner(banner, data.detail || 'Слишком много запросов. Попробуйте позже.', 'error');
        } else {
          showBanner(banner, data.detail || 'Что-то пошло не так. Попробуйте ещё раз позже.', 'error');
        }
      } catch (err) {
        showBanner(
          banner,
          'Не удалось связаться с сервером. Убедитесь, что backend запущен, и попробуйте снова.',
          'error'
        );
      } finally {
        submitBtn.disabled = false;
        submitLabel.textContent = 'Отправить заявку';
      }
    });
  }

  runHeroDemo();
  pingHealth();
  initContactForm();
})();
