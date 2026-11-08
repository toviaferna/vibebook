/* Injects the three app mockups, once in light and once in dark. */

const library = `
<div class="m-shell">
  <aside class="m-sidebar">
    <div class="m-brand">
      <span class="m-mark">V</span>
      <span class="m-wordmark">vibe<span>book</span></span>
    </div>
    <nav class="m-nav" aria-label="Navegación de muestra">
      <p class="m-nav-label">Taller</p>
      <a class="is-active" href="#"><span class="m-nav-icon"></span>Biblioteca</a>
      <a href="#"><span class="m-nav-icon"></span>Importar</a>
      <a href="#"><span class="m-nav-icon"></span>Ajustes</a>
    </nav>
    <div class="m-side-note">
      <span>Modo local</span>
      <strong>Tu biblioteca, tu máquina.</strong>
      <p>Los libros y el audio no salen de acá.</p>
    </div>
  </aside>

  <div class="m-rail" aria-hidden="true">
    <span class="m-mark">V</span>
    <span class="m-rail-icon is-active">B</span>
    <span class="m-rail-icon">I</span>
    <span class="m-rail-icon">A</span>
    <span class="m-rail-index">VB · 014</span>
  </div>

  <header class="m-masthead">
    <div class="m-brand">
      <span class="m-mark">V</span>
      <span class="m-wordmark">vibe<span>book</span></span>
    </div>
    <nav class="m-masthead-nav">
      <span class="is-active">Biblioteca</span>
      <span>Importar</span>
      <span>Ajustes</span>
      <span>Modo local</span>
    </nav>
  </header>

  <main class="m-main">
    <div class="m-page-head">
      <div>
        <p class="m-eyebrow">Biblioteca</p>
        <h1>Tu taller de escucha</h1>
        <p class="m-sub">Importá EPUB, leelos a tu ritmo y convertí a audiolibro solo cuando quieras.</p>
      </div>
      <div class="m-head-actions">
        <button class="m-icon" type="button">↻</button>
        <button class="m-btn m-btn--primary" type="button">+ Importar EPUB</button>
      </div>
    </div>

    <section class="m-continue">
      <div class="m-continue-cover" data-cover="moss">La isla<br>de los<br>nombres</div>
      <div class="m-continue-copy">
        <p class="m-eyebrow">Continuar leyendo</p>
        <h2>La isla de los nombres</h2>
        <p>42% leído · Capítulo 4 · hace un momento</p>
      </div>
      <button class="m-btn m-btn--primary" type="button">Continuar</button>
    </section>

    <div class="m-toolbar">
      <div class="m-search">Buscar por título o autor</div>
      <div class="m-sort">Recientes ▾</div>
      <span class="m-count">8 libros</span>
    </div>

    <div class="m-filters">
      <button class="is-active" type="button">Todos</button>
      <button type="button">Leyendo</button>
      <button type="button">Con audio</button>
      <button type="button">Sin audio</button>
    </div>

    <div class="m-grid">
      <a class="m-book" href="#">
        <div class="m-cover" data-cover="moss">
          <span class="m-cover-kicker">Novela</span>
          <strong>La isla de los nombres</strong>
          <div>
            <div class="m-cover-rule"></div>
            <span class="m-cover-author">Elena Márquez</span>
          </div>
        </div>
        <div class="m-book-meta">
          <h3 class="m-book-title">La isla de los nombres</h3>
          <p class="m-book-author">Elena Márquez</p>
          <div class="m-book-bottom">
            <span class="m-chip m-chip--audio">Audio</span>
            <span class="m-mono">6 h 42</span>
          </div>
          <div class="m-progress"><i style="width:42%"></i></div>
        </div>
      </a>

      <a class="m-book" href="#">
        <div class="m-cover" data-cover="ochre">
          <span class="m-cover-kicker">Ensayo</span>
          <strong>El archivo de la lluvia</strong>
          <div>
            <div class="m-cover-rule"></div>
            <span class="m-cover-author">Tomás Rivas</span>
          </div>
        </div>
        <div class="m-book-meta">
          <h3 class="m-book-title">El archivo de la lluvia</h3>
          <p class="m-book-author">Tomás Rivas</p>
          <div class="m-book-bottom">
            <span class="m-chip m-chip--audio">Audio</span>
            <span class="m-mono">4 h 12</span>
          </div>
          <div class="m-progress"><i style="width:0%"></i></div>
        </div>
      </a>

      <a class="m-book" href="#">
        <div class="m-cover" data-cover="slate">
          <span class="m-cover-kicker">Cuentos</span>
          <strong>Cartas del faro</strong>
          <div>
            <div class="m-cover-rule"></div>
            <span class="m-cover-author">Ana Belén Soto</span>
          </div>
        </div>
        <div class="m-book-meta">
          <h3 class="m-book-title">Cartas del faro</h3>
          <p class="m-book-author">Ana Belén Soto</p>
          <div class="m-book-bottom">
            <span class="m-chip m-chip--quiet">Sin audio</span>
            <span class="m-mono">EPUB</span>
          </div>
          <div class="m-progress"><i style="width:18%"></i></div>
        </div>
      </a>

      <a class="m-book" href="#">
        <div class="m-cover" data-cover="oxblood">
          <span class="m-cover-kicker">Novela</span>
          <strong>La casa de los relojes</strong>
          <div>
            <div class="m-cover-rule"></div>
            <span class="m-cover-author">Julián Paredes</span>
          </div>
        </div>
        <div class="m-book-meta">
          <h3 class="m-book-title">La casa de los relojes</h3>
          <p class="m-book-author">Julián Paredes</p>
          <div class="m-book-bottom">
            <span class="m-chip m-chip--audio">Audio</span>
            <span class="m-mono">9 h 05</span>
          </div>
          <div class="m-progress"><i style="width:0%"></i></div>
        </div>
      </a>

      <a class="m-book" href="#">
        <div class="m-cover" data-cover="linen">
          <span class="m-cover-kicker">Poesía</span>
          <strong>Cuaderno de sombras</strong>
          <div>
            <div class="m-cover-rule"></div>
            <span class="m-cover-author">Marta Quiroga</span>
          </div>
        </div>
        <div class="m-book-meta">
          <h3 class="m-book-title">Cuaderno de sombras</h3>
          <p class="m-book-author">Marta Quiroga</p>
          <div class="m-book-bottom">
            <span class="m-chip m-chip--quiet">Sin audio</span>
            <span class="m-mono">EPUB</span>
          </div>
          <div class="m-progress"><i style="width:0%"></i></div>
        </div>
      </a>
    </div>
  </main>
</div>`;

const detail = `
<div class="m-shell">
  <aside class="m-sidebar">
    <div class="m-brand">
      <span class="m-mark">V</span>
      <span class="m-wordmark">vibe<span>book</span></span>
    </div>
    <nav class="m-nav" aria-label="Navegación de muestra">
      <p class="m-nav-label">Taller</p>
      <a class="is-active" href="#"><span class="m-nav-icon"></span>Biblioteca</a>
      <a href="#"><span class="m-nav-icon"></span>Importar</a>
      <a href="#"><span class="m-nav-icon"></span>Ajustes</a>
    </nav>
    <div class="m-side-note">
      <span>Modo local</span>
      <strong>Tu biblioteca, tu máquina.</strong>
      <p>Los libros y el audio no salen de acá.</p>
    </div>
  </aside>

  <div class="m-rail" aria-hidden="true">
    <span class="m-mark">V</span>
    <span class="m-rail-icon is-active">B</span>
    <span class="m-rail-icon">I</span>
    <span class="m-rail-icon">A</span>
    <span class="m-rail-index">VB · 014</span>
  </div>

  <header class="m-masthead">
    <div class="m-brand">
      <span class="m-mark">V</span>
      <span class="m-wordmark">vibe<span>book</span></span>
    </div>
    <nav class="m-masthead-nav">
      <span class="is-active">Biblioteca</span>
      <span>Importar</span>
      <span>Ajustes</span>
      <span>Modo local</span>
    </nav>
  </header>

  <main class="m-main m-main--detail">
    <div class="m-back">← Biblioteca</div>
    <div class="m-detail">
      <div class="m-detail-cover">
        <div class="m-cover m-cover--lg" data-cover="moss">
          <span class="m-cover-kicker">Novela · 2024</span>
          <strong>La isla de los nombres</strong>
          <div>
            <div class="m-cover-rule"></div>
            <span class="m-cover-author">Elena Márquez</span>
          </div>
        </div>
      </div>
      <div class="m-detail-copy">
        <div class="m-detail-top">
          <span class="m-chip m-chip--audio">Audio listo</span>
          <span class="m-mono">Actualizado hoy · 14:02</span>
        </div>
        <h1>La isla de los nombres</h1>
        <p class="m-byline">Elena Márquez · ES</p>
        <p class="m-desc">Una cartógrafa llega a una isla donde cada habitante lleva el nombre de un lugar que ya no existe. Leerla es recorrer un mapa que se corrige a sí mismo.</p>
        <div class="m-facts">
          <div class="m-fact"><strong>12</strong><span>Capítulos</span></div>
          <div class="m-fact"><strong>6 h 42</strong><span>Duración</span></div>
          <div class="m-fact"><strong>-10%</strong><span>Velocidad</span></div>
          <div class="m-fact"><strong>Piper</strong><span>Motor</span></div>
        </div>
        <div class="m-actions">
          <button class="m-btn m-btn--primary" type="button">Leer y escuchar</button>
          <button class="m-btn" type="button">Abrir estudio</button>
          <button class="m-btn m-btn--ghost" type="button">Descargar M4B</button>
        </div>
        <div class="m-tabs">
          <span class="is-active">Leer</span>
          <span>Escuchar</span>
          <span>Ambientación</span>
          <span>Ficha</span>
        </div>
      </div>
    </div>
    <div class="m-detail-lower">
      <div class="m-lower-panel">
        <p class="m-eyebrow">Tu progreso</p>
        <strong>42% leído</strong>
        <p>Capítulo 4 · La casa del faro</p>
        <div class="m-progress"><i style="width:42%"></i></div>
      </div>
      <div class="m-lower-panel">
        <p class="m-eyebrow">Marcadores</p>
        <strong>3 guardados</strong>
        <p>La isla · El mapa · La marea</p>
      </div>
      <div class="m-lower-panel">
        <p class="m-eyebrow">Ficha</p>
        <strong>12 capítulos</strong>
        <p>EPUB 3 · 2024 · Español</p>
      </div>
    </div>
    <div class="m-colophon">
      <span>EDICIÓN LOCAL</span>
      <p>EPUB 3 · 12 capítulos · voz es_MX-ald-medium · sync 0 ms</p>
      <span>VB · 014</span>
    </div>
  </main>
</div>`;

const reader = `
<div class="m-reader">
  <header class="m-reader-top">
    <div class="m-reader-left">
      <button class="m-icon m-icon--plain" type="button">←</button>
      <div class="m-reader-title">
        <strong>La isla de los nombres</strong>
        <span>Capítulo 4 · La casa del faro</span>
      </div>
    </div>
    <div class="m-viewtoggle">
      <button class="is-active" type="button">Libro</button>
      <button type="button">Texto</button>
      <button type="button">Original</button>
    </div>
    <div class="m-reader-actions">
      <button class="m-icon m-icon--plain" type="button">⌕</button>
      <button class="m-icon m-icon--plain" type="button">☰</button>
      <button class="m-icon m-icon--plain" type="button">⌑</button>
      <button class="m-icon" type="button">Aa</button>
    </div>
  </header>

  <div class="m-reader-body">
    <aside class="m-toc">
      <p class="m-eyebrow">Índice</p>
      <div class="m-toc-item">
        <span class="m-toc-number">01</span>
        <span class="m-toc-title">La costa</span>
        <span class="m-toc-duration">12 min</span>
      </div>
      <div class="m-toc-item">
        <span class="m-toc-number">02</span>
        <span class="m-toc-title">El faro</span>
        <span class="m-toc-duration">18 min</span>
      </div>
      <div class="m-toc-item">
        <span class="m-toc-number">03</span>
        <span class="m-toc-title">Los nombres</span>
        <span class="m-toc-duration">21 min</span>
      </div>
      <div class="m-toc-item is-active">
        <span class="m-toc-number">04</span>
        <span class="m-toc-title">La casa del faro</span>
        <span class="m-toc-duration">38 min</span>
      </div>
      <div class="m-toc-item">
        <span class="m-toc-number">05</span>
        <span class="m-toc-title">El mapa</span>
        <span class="m-toc-duration">26 min</span>
      </div>
      <div class="m-toc-item">
        <span class="m-toc-number">06</span>
        <span class="m-toc-title">La marea</span>
        <span class="m-toc-duration">31 min</span>
      </div>
    </aside>

    <main class="m-spread">
      <section class="m-page m-page--left">
        <p class="m-running"><span>La isla de los nombres</span><span>IV</span></p>
        <h2>IV</h2>
        <p class="m-drop">Al principio creyó que el faro era una casa vacía. La luz giraba cada noche sobre el agua, pero nadie subía la escalera; las cartas se acumulaban en el umbral, escritas con una letra que reconocía sin poder nombrarla.</p>
        <p>Esa noche, la puerta estaba abierta. Entró sin hacer ruido. En la pared, un mapa de la isla marcaba nombres que no figuraban en ningún registro; junto a cada nombre, una fecha y una pequeña marca de tinta.</p>
        <p>El primero era el suyo.</p>
        <p>El viento movía las cortinas. Sobre la mesa había un vaso con agua y una llave pequeña, como de una caja de música.</p>
        <p>La llave tenía una etiqueta: «Para la noche en que vuelvas».</p>
        <span class="m-folio">42</span>
      </section>
      <section class="m-page m-page--right">
        <p class="m-running"><span>La casa del faro</span><span>42</span></p>
        <p>Subió la escalera con la lámpara apagada. En el cuarto de arriba había una mesa, un cuaderno y una silla vuelta hacia la ventana. El cuaderno tenía la misma letra de las cartas, pero las fechas eran futuras.</p>
        <p>Buscó su nombre durante mucho tiempo. Cuando lo encontró, la tinta todavía estaba húmeda. Afuera, la luz del faro barrió el agua y, por un instante, la isla entera pareció <mark>la puerta estaba abierta</mark>.</p>
        <p>Entonces comprendió que el mapa no señalaba lugares: señalaba las noches en que alguien decidía quedarse.</p>
        <p>Bajó la escalera despacio. El faro seguía girando, ajeno a la historia que acababa de empezar. En el umbral, las cartas ya no estaban.</p>
        <p>Guardó la llave en el bolsillo y salió a la luz del amanecer.</p>
        <span class="m-folio">43</span>
      </section>
    </main>
  </div>

  <footer class="m-player">
    <div class="m-player-meta">
      <p class="m-eyebrow">Ahora</p>
      <strong>La casa del faro</strong>
    </div>
    <div class="m-player-controls">
      <button type="button">‹</button>
      <button type="button">↺</button>
      <button class="m-play" type="button" aria-label="Reproducir"></button>
      <button type="button">↻</button>
      <button type="button">›</button>
    </div>
    <div class="m-player-tools">
      <span class="m-tool-pill">1.25×</span>
      <span>Volumen</span>
      <span class="m-tool-pill">Seguir</span>
    </div>
    <div class="m-player-progress">
      <span>12:04</span>
      <div class="m-player-range"><i></i></div>
      <span>38:21</span>
    </div>
  </footer>
</div>`;

const templates = { library, detail, reader };

for (const host of document.querySelectorAll("[data-mock]")) {
  const markup = templates[host.dataset.mock];
  if (!markup) continue;
  host.innerHTML = `
    <figure class="frame" data-theme="light">
      <figcaption class="frame-label">Claro</figcaption>
      <div class="frame-stage">
        <div class="mock mock--light" aria-hidden="true">${markup}</div>
      </div>
    </figure>
    <figure class="frame" data-theme="dark">
      <figcaption class="frame-label">Oscuro</figcaption>
      <div class="frame-stage">
        <div class="mock mock--dark" aria-hidden="true">${markup}</div>
      </div>
    </figure>`;
}
