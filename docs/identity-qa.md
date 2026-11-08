# Identidad Verdín — QA de I5

> Cierre visual de la ola I1–I5. Las capturas usan los fixtures de E2E y un libro
> convertido con el motor `fake`; no son assets de producción.

## Capturas

Todas a 1440 × 960, con las fuentes de producción y los tokens reales.

### Biblioteca

| Claro | Oscuro |
|---|---|
| ![Biblioteca en claro](assets/identity/library-light.jpg) | ![Biblioteca en oscuro](assets/identity/library-dark.jpg) |

### Detalle

| Claro | Oscuro |
|---|---|
| ![Detalle en claro](assets/identity/detail-light.jpg) | ![Detalle en oscuro](assets/identity/detail-dark.jpg) |

### Lector

| Papel (app clara) | Sepia (app clara) | Noche (app oscura) |
|---|---|---|
| ![Lector papel](assets/identity/reader-light.jpg) | ![Lector sepia](assets/identity/reader-sepia.jpg) | ![Lector noche](assets/identity/reader-dark.jpg) |

El lector noche con app oscura demuestra que la paleta de lectura no depende del
tema de la app. La app clara con lector sepia demuestra lo mismo en la otra
dirección.

### Ajustes / Apariencia

| Claro | Oscuro |
|---|---|
| ![Ajustes en claro](assets/identity/settings-light.jpg) | ![Ajustes en oscuro](assets/identity/settings-dark.jpg) |

## Axe y teclado

- `cd web && npm run e2e` → **6 tests**, incluido `a11y.spec.ts` con AxeBuilder
  en biblioteca, detalle, estudio y lector.
- Resultado: **sin violaciones serious/critical**.
- La navegación mobile se cubre en `shell.spec.ts`.
- El toggle de tema se cubre en `shell.spec.ts` y `theme.spec.ts`.
- Skip link, foco visible, `aria-current`, `aria-pressed` y labels de tema se
  mantienen.

## Contraste manual

Pares principales (WCAG AA normal = 4.5:1):

| Par | Ratio | Resultado |
|---|---:|---|
| Claro · ink / paper | 14.13 | AA |
| Claro · ink-soft / paper | 6.43 | AA |
| Claro · ink-faint / paper | 4.73 | AA |
| Claro · on-accent / accent-strong | 9.70 | AA |
| Claro · warning / paper | 5.24 | AA |
| Claro · danger / paper | 5.81 | AA |
| Oscuro · ink / paper | 15.40 | AA |
| Oscuro · ink-faint / paper | 5.82 | AA |
| Oscuro · on-accent / accent-strong | 10.71 | AA |
| Papel · ink / page | 15.33 | AA |
| Sepia · ink / page | 11.95 | AA |
| Sepia · faint / page | 5.16 | AA |
| Noche · ink / page | 15.40 | AA |
| Noche · faint / page | 5.82 | AA |

Se ajustó `--ink-faint` claro de `#6E7A72` a `#626E66` y se usó `--warning` en
lugar de `--brass` para textos pequeños sobre papel. El latón queda para líneas,
cintas y adornos, no para texto de bajo contraste.

## Rendimiento

- JS inicial: **150,9 KiB gzip / 550**.
- CSS inicial: **10,9 KiB gzip / 60**.
- Sin Three.js, WebGL, canvas decorativo ni textura de ruido full-screen.
- Se eliminó el último `backdrop-filter: blur()` del player.
- Fuentes: 5 familias OFL, subsets y `font-display: swap`; sin CDN en producción.
- Animaciones: `transform`/`opacity`; reduced motion desactiva el page-turn.

## Limitaciones conocidas

- Las capturas usan un libro de fixture con poco texto; el lector real llena más
  la página.
- Las portadas sin arte usan una tapa tipográfica; títulos largos se clampean a
  4 líneas.
- El modo Álbum se guarda como `reader_mode: book` porque el contrato no tiene un
  valor `album`; al reabrir vuelve a Libro, sin perder la posición.
- Las capturas se generaron en Chromium/Windows; WebKitGTK y WKWebView se revisan
  en las fases de plataforma.

## Regenerar las capturas

Con el backend y Vite corriendo, y un libro convertido:

```powershell
cd web
$env:BOOK_ID="<id-del-libro>"
npm run capture:identity
```

El script deja los JPG en `docs/assets/identity/` y restaura
`theme_mode=system`, `reader_palette=paper` al terminar.
