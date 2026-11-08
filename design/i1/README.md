# I1 — Contexto de diseño y direcciones visuales

Artefactos de diseño para aprobar la identidad antes de tocar tokens.

## Cómo abrir

Abrí `design/i1/index.html` en un navegador. No hace falta levantar Vite ni el
backend: son páginas estáticas.

- `index.html` — resumen, comparación y criterios de decisión.
- `verdin.html` — dirección recomendada.
- `senal.html` — alternativa gráfica/técnica.
- `nocturno.html` — alternativa dramática/nocturna.

Cada tablero muestra la identidad y los mockups de **Biblioteca**, **Detalle** y
**Lector** en claro y oscuro (seis frames por dirección).

## Qué contiene cada tablero

1. Concepto, personalidad y anti-referencias.
2. Paleta clara y oscura con tokens y hex.
3. Especímenes tipográficos (display, lectura, UI, mono).
4. Radios, reglas, sombras, movimiento y detalle de marca.
5. Mockups de las tres pantallas en ambos temas.
6. Fortalezas, riesgos y notas de implementación.

## Contexto canónico

El contexto de diseño vive en `.better-web-ui.md`, en la raíz del repo. Es la
fuente para todo el trabajo de UI posterior. Si una dirección se aprueba, se
actualiza allí y recién entonces empieza I2.

## Estado

- **I1:** completo, pendiente de aprobación explícita.
- **Recomendación:** Verdín.
- **No implementar I2** (tokens, temas, fuentes) hasta elegir una dirección.

## Notas

- Las fuentes de los tableros se cargan desde Google Fonts solo para la
  presentación. Producción usa Fontsource, como el resto de la app.
- Los mockups son HTML/CSS estáticos; no agregan dependencias ni peso al bundle.
- Las portadas son inventadas y generadas con CSS: no hay assets externos ni
  material con copyright.
