# 04 — Sistema de diseño “Biblioteca”

## 1. Intención

Vibebook no es una app de productividad genérica ni un lector más. La identidad
actual nace de una biblioteca física: papel cálido, tinta, cuero oxblood, latón,
pizarra y tipografía editorial. Esa identidad funciona y debe conservarse. La
refactorización Flutter no debe convertirla en “Material 3 por defecto”.

Objetivos visuales:

- **Editorial, no corporativa.** La lectura y los libros son el centro.
- **Cálida en luz, sobria en oscuro.** El papel manda; el dark mode no es negro
  puro.
- **Jerarquía clara.** Una acción primaria por pantalla; metadatos en mono;
  lectura en serif; UI en sans.
- **Movimiento con propósito.** Giros de página, progreso y transiciones; nada
  decorativo que compita con el texto.
- **Accesible por defecto.** Contraste, foco, teclado, lector de pantalla y
  movimiento reducido.

## 2. Principios

1. **El contenido es la interfaz.** Portadas, texto y audio tienen prioridad
   sobre chrome.
2. **Un acento fuerte, no cinco.** Oxblood para acción/selección; latón para
   detalles; pizarra para audio; el resto es papel/tinta.
3. **Superficies planas con profundidad puntual.** Sombras solo en player,
   tarjetas elevadas y menús; nada de glassmorphism.
4. **Bordes finos y radios pequeños.** La app se siente impresa, no “burbuja”.
5. **Tipografía con oficio.** Spectral para display, Literata para lectura,
   Public Sans para UI, IBM Plex Mono para metadata.
6. **Densidad adaptable.** Desktop puede mostrar más; mobile respira.
7. **Nada de efectos que cuesten frames.** Sin blur de pantalla completa, sin
   gradientes animados, sin WebGL.

## 3. Tokens

### 3.1 Color — app light

| Token | Valor | Uso |
|---|---|---|
| `paper` | `#F2EBDD` | Fondo principal |
| `paperDeep` | `#E7DDCB` | Fondo secundario/lomo |
| `surface` | `#FAF6EE` | Tarjetas/superficies |
| `surfaceRaised` | `#FDFAF4` | Elevada |
| `ink` | `#211D19` | Texto principal |
| `inkSoft` | `#574C43` | Texto secundario |
| `inkFaint` | `#6E6258` | Metadata |
| `line` | `#D8CDBD` | Bordes |
| `lineStrong` | `#B9AA97` | Bordes activos |
| `accent` | `#7A2E2E` | Acción/selección |
| `accentStrong` | `#5E2028` | Hover/pressed |
| `accentSoft` | `#EADDD8` | Fondo selección |
| `onAccent` | `#FDFAF4` | Texto sobre acento |
| `brass` | `#A8771F` | Detalle/emphasis |
| `audio` | `#35505F` | Player/audio |
| `audioSoft` | `#DCE5E9` | Fondo audio |
| `warning` | `#8C5A1F` | Advertencia |
| `danger` | `#A33A32` | Error/destructivo |
| `focus` | `#35505F` | Foco |
| `highlight` | `#EAD9A8` | Segmento activo |
| `highlightWord` | `#DCC173` | Palabra activa |

### 3.2 Color — app dark

| Token | Valor |
|---|---|
| `paper` | `#14110F` |
| `paperDeep` | `#0E0C0A` |
| `surface` | `#1D1916` |
| `surfaceRaised` | `#26211D` |
| `ink` | `#EDE6DA` |
| `inkSoft` | `#B8AC9E` |
| `inkFaint` | `#92857A` |
| `line` | `#332D27` |
| `lineStrong` | `#4B4239` |
| `accent` | `#D19A8A` |
| `accentStrong` | `#E5B4A6` |
| `accentSoft` | `#3A2523` |
| `onAccent` | `#14110F` |
| `brass` | `#D6B36A` |
| `audio` | `#9BB7D4` |
| `audioSoft` | `#1B2B3A` |
| `warning` | `#D9A45C` |
| `danger` | `#E0857A` |
| `focus` | `#9BB7D4` |
| `highlight` | `#3B3120` |
| `highlightWord` | `#574A25` |

### 3.3 Paletas del lector

Independientes del tema de la app:

- **Paper:** `#FBF7EF` / tinta `#211D19` / acento `#7A2E2E` / highlight
  `#EAD9A8` / palabra `#DCC173`.
- **Sepia:** `#F1E4CC` / tinta `#2D2822` / acento `#7A2E2E` / highlight
  `#E5CFA0` / palabra `#D4B36A`.
- **Night:** `#12100E` / tinta `#EDE6D8` / acento `#D19A8A` / highlight
  `#3B3120` / palabra `#574A25`.

El lector puede sobrescribir la paleta por libro; el tema global es el default.

### 3.4 Tipografía

| Rol | Familia | Uso | Licencia |
|---|---|---|---|
| Display | Spectral | Títulos, portadas, hero | OFL |
| Lectura | Literata Variable | Texto del lector | OFL |
| UI | Public Sans Variable | Navegación, botones, forms | OFL |
| Mono | IBM Plex Mono | Metadata, índices, tiempo | OFL |
| Accesibilidad | Atkinson Hyperlegible | Opción de lectura | OFL |

Escala (rem base 16):

| Token | Tamaño | Line-height | Uso |
|---|---:|---:|---|
| `step-0` | 12 | 1.3 | Micro/mono |
| `step-1` | 14 | 1.45 | UI secundaria |
| `step-2` | 16 | 1.55 | UI/base |
| `step-3` | 18 | 1.5 | Subtítulos |
| `step-4` | 22 | 1.3 | Títulos de sección |
| `step-5` | 28 | 1.2 | Títulos de pantalla |
| `step-6` | 36 | 1.1 | Hero |
| `step-7` | 48 | 1.05 | Portada/landing |

Pesos: 400/500/600/700. No usar más de 3 pesos en una pantalla. Evitar
`letterSpacing` negativo agresivo; solo display (`-0.02em` a `-0.04em`).

### 3.5 Espaciado

Base 4 px: `4, 8, 12, 16, 24, 32, 48, 64, 96`.

- Padding de pantalla desktop: 32–48 px.
- Mobile: 16–24 px.
- Gap entre tarjetas: 16–24 px.
- Secciones: 32–48 px.
- Reader: medidas en `em`/`ch`, no píxeles fijos.

### 3.6 Radios

| Token | Valor | Uso |
|---|---:|---|
| `sm` | 2 | Inputs/“impreso” |
| `md` | 4 | Botones/tarjetas |
| `lg` | 6 | Superficies grandes |
| `pill` | 999 | Chips/avatares |

No usar radios de 16–24 px en toda la app: rompe la identidad editorial.

### 3.7 Elevación

| Token | Uso |
|---|---|
| `none` | Mayoría de superficies |
| `soft` | Tarjetas elevadas, menús |
| `player` | Player fijo, diálogo |
| `overlay` | Modal/sheet |

Sombras: `0 8px 28px rgb(33 29 25 / 8%)` en luz; `0 8px 28px rgb(0 0 0 / 30%)`
en oscuro. Nada de sombras de color ni múltiples capas.

### 3.8 Movimiento

| Token | Duración | Uso |
|---|---:|---|
| `fast` | 120 ms | Hover/press/focus |
| `base` | 200 ms | Aparición, tabs |
| `slow` | 320 ms | Sheets/diálogos |
| `page` | 520 ms | Giro de página |

Curvas: `easeOutCubic` (`0.22, 1, 0.36, 1`) para entrada; `easeInOutCubic`
para page-turn. Reduced motion: duración 0 y sin transform 3D.

### 3.9 Breakpoints

| Nombre | Ancho | Layout |
|---|---:|---|
| compact | <600 | Bottom nav, una columna, lector 1 página |
| medium | 600–1023 | Rail compacto, 2 columnas, lector 1–2 páginas |
| expanded | 1024–1439 | Sidebar 264, grillas 3–4, lector 2 páginas |
| wide | ≥1440 | Sidebar + contenido max 1680, lector 2 páginas amplio |

### 3.10 Z-index

`base 0`, `sticky 10`, `player 20`, `dropdown 30`, `dialog 40`, `toast 50`,
`debug 100`.

## 4. Componentes

### Base

- `AppScaffold`: sidebar/rail/bottom nav, topbar, safe areas.
- `SurfaceCard`: borde 1 px, radio 4, sin sombra por defecto.
- `SectionHeader`: eyebrow mono + título display + acción.
- `Button`: primary (oxblood), secondary (outline), ghost, destructive.
- `IconButton`: 40/44 px target, tooltip obligatorio.
- `TextField`: label flotante no; label arriba, helper/error abajo, borde 1 px.
- `Select`/`Combobox`: búsqueda, teclado, virtualización si hay muchas voces.
- `Switch`, `Checkbox`, `Radio`, `Slider` con estados claros.
- `Dialog`, `Sheet`, `Popover`, `Toast` con foco atrapado y escape.
- `ProgressBar`/`ProgressRing` determinados; skeletons para carga.
- `EmptyState` con una acción clara.
- `ErrorState` con código, mensaje y “Reintentar”.

### Biblioteca

- `BookShelf`: grilla responsive de `BookCoverCard`.
- `BookCoverCard`: portada 4:5, lomo, progreso, badge de estado, menú.
- `BookListRow`: variante compacta para listas/resultados.
- `LibraryToolbar`: búsqueda, orden, filtros, vista.
- `ImportDropZone`: drag/drop desktop, selector mobile.
- `DeleteBookDialog`: confirmación con nombre y consecuencias.

### Detalle

- `BookHero`: portada, título, autor, metadata, acciones.
- `ChapterList`: TOC con duración/estado, navegación.
- `BookFacts`: mono, columnas, sin tablas pesadas.
- `CoverPicker`: búsqueda, preview, set.
- `AmbienceSummary`: plan, cama, efectos, export.

### Estudio

- `EnginePicker`: cartas con disponibilidad, red/clave, descripción.
- `VoicePicker`: búsqueda, locale, género, estilos, preview.
- `StylePicker`: chips/emoji sobrio.
- `RateControl`: slider + valor.
- `ConversionOptions`: salida, max chars, timings.
- `JobProgress`: stage, capítulo, segmento, barra, cancelar/reanudar.
- `JobLog`: colapsable, mono, sin ruido.

### Lector

- `ReaderShell`: topbar, contenido, player, TOC, ajustes.
- `ReaderText`: párrafos con spans de karaoke; selección.
- `ReaderBook`: página(s), lomo, giro, sombra de hoja.
- `ReaderOriginal`: HTML sanitizado.
- `ReaderPlayer`: play/pausa, ±15 s, capítulo, velocidad, volumen, timer.
- `ReaderTOC`: drawer/sheet con estructura real.
- `ReaderSettings`: paleta, fuente, tamaño, modo, karaoke.
- `ReaderSearch`: input, resultados, salto.
- `ReaderBookmarks`: lista, nota, borrar.
- `KaraokeToggle`: estado por libro.
- `AmbienceBar`: activar/apagar, escena, volúmenes.

### Ajustes

- `SettingsSection`: título + descripción + filas.
- `SettingsRow`: label, helper, control; sin cards dentro de cards.
- `ProviderCard`: estado, test, key input enmascarado, docs.
- `EngineCard`: disponibilidad, instalar/descargar, licencia.
- `ThemePreview`: light/dark/system.
- `AboutSection`: versión, licencia, notices.

## 5. Layout

### Desktop

```text
┌──────────────┬─────────────────────────────────────────────┐
│ Sidebar 264  │ Topbar contextual                           │
│ brand        ├─────────────────────────────────────────────┤
│ nav          │ Contenido max 1680, padding 32–48           │
│ footer       │                                             │
└──────────────┴─────────────────────────────────────────────┘
```

- Sidebar con “lomo” vertical (34 px) y navegación.
- Topbar sticky con contexto y acciones.
- Player del lector fijo abajo, sin tapar contenido.
- Lector 2K: libro hasta 1680 px, dos páginas, sin columna angosta.

### Mobile

- App bar compacta; bottom nav de 4 ítems (Biblioteca, Importar, Ajustes,
  Actividad) o 3 + “más”.
- Lector inmersivo: topbar mínima, player compacto, sheets para TOC/ajustes.
- Targets ≥44 px; gestos de swipe en página; safe areas.

### Responsive

- No “esconder” features en mobile: se reubican en sheets/menús.
- Tablas → listas; grillas → 1–2 columnas; sidebars → drawers.
- Texto del lector: ancho de medida 60–75 caracteres; en desktop dos columnas
  solo en modo Libro.

## 6. Accesibilidad

- WCAG 2.2 AA: contraste ≥4.5:1 texto normal, ≥3:1 grande/iconos.
- Foco visible con `focus` y ring de 2 px; nunca `outline: none` sin sustituto.
- Orden de tabulación lógico; skip link en desktop.
- `Semantics`/`ExcludeSemantics` explícitos en portadas, barras y player.
- Labels en iconos; no solo color para estado.
- Text scaling 200% sin clipping; layouts flexibles.
- Reduced motion; sin autoplay de audio.
- Subtítulos/transcripción no aplican; sí timings y karaoke.
- Teclado: espacio, flechas, J/K, +/-, T, F, ?; documentados en ayuda.
- Pruebas con TalkBack/VoiceOver/NVDA en el plan de QA.

## 7. Iconografía

- Lucide, stroke 1.5–1.75, tamaños 16/20/24.
- Un icono por acción; no iconos decorativos en cada label.
- `lucide_icons_flutter` 4.0.3; los iconos custom se bundelean como SVG.
- No mezclar Material Icons, Lucide y emojis en la misma jerarquía.

## 8. Contenido y tono

- Español rioplatense neutro, cálido y directo; “vos” consistente.
- Títulos de acción concretos: “Convertir en audiolibro”, “Reanudar”,
  “Exportar M4B ambientado”.
- Errores: qué pasó, por qué, qué hacer; sin culpar al usuario.
- Microcopy de estados: “Analizando EPUB…”, “Sintetizando 12 de 84…”.
- No usar “AI-powered”, “seamless”, “revolutionary” ni jerga vacía.

## 9. Implementación en Flutter

- `ThemeData` base con `ColorScheme` derivado de los tokens; `useMaterial3:
  true` pero componentes custom.
- `ThemeExtension<BibliotecaColors>`, `<BibliotecaTypography>`,
  `<BibliotecaSpacing>`, `<BibliotecaRadii>`, `<BibliotecaMotion>`.
- `TextTheme` con las familias y escalas; `TextScaler` respetado.
- `AppTheme.light`, `AppTheme.dark`, `ReaderTheme.paper/sepia/night`.
- Componentes en `core/design/components`, sin lógica de negocio.
- Golden tests por tema, breakpoint y text scale.
- No usar `google_fonts` en runtime: fuentes bundleadas en `assets/fonts`.

## 10. Anti-patrones prohibidos

- Glassmorphism, blur global, gradientes decorativos sin función.
- Sombras en cada card; bordes + sombra + fondo elevado a la vez.
- Material 3 default con `primary` azul.
- Emojis como iconos de navegación.
- Animaciones de 800 ms+ o rebotes en lectura.
- Texto gris claro sobre papel claro.
- Cards dentro de cards dentro de cards.
- Tablas de 8 columnas en mobile.
- “Hero” gigante que empuja la biblioteca fuera del primer viewport.

## 11. Criterios de aceptación visual

- [ ] La biblioteca se reconoce como Vibebook sin ver el logo.
- [ ] El lector en paper/sepia/night mantiene contraste AA.
- [ ] Un usuario nuevo encuentra “Importar”, “Leer” y “Convertir” en <10 s.
- [ ] 200% text scale no rompe navegación, player ni lector.
- [ ] Teclado-only permite completar importar → convertir → leer.
- [ ] 60 fps en scroll de biblioteca y page-turn en hardware objetivo.
- [ ] Golden tests de light/dark/paper/sepia/night y compact/expanded.
