# Guía de interfaz: buenas prácticas

> **Propuesta (2026-11-24), para el OK de la propietaria.** Parte de la constitución: se consulta
> antes de diseñar o revisar cualquier pantalla, diálogo, menú o mensaje. No sustituye a las reglas
> de `AGENTS.md`: las concreta para la interfaz.

## Cómo se usa

1. **Mandan las reglas del proyecto** (`AGENTS.md`). Si una buena práctica choca con una regla, gana
   la regla, y aquí se dice cómo se resuelve el choque (abajo, «Cuando chocan»).
2. **La base es la estética de OGR Slip2D**: el mismo aspecto, los mismos atajos, el mismo orden de
   menús y la misma forma de entrar datos. Un ingeniero que sabe usar uno sabe usar el otro.
3. **Las guías de abajo sirven para mejorar esa base, no para cambiarla por gusto.** Una mejora que
   rompe la coherencia con Slip2D se propone a la propietaria y, si se acepta, se pide también para
   Slip2D (a su sesión), para que la suite no diverja.
4. Cada tarea de interfaz de una spec cierra con la lista de comprobación de esta guía
   («Lista por componente»), además de sus tests.

## Las fuentes

Se citan y se enlazan; **no se copia su texto** (varias no lo permiten: Laws of UX es CC BY-NC-ND 4.0
y Growth.Design, «all rights reserved»). Lo de abajo es nuestra lectura, con nuestras palabras.

| Fuente | Qué es | Para qué la usamos |
|---|---|---|
| [Laws of UX](https://lawsofux.com/articles/) (Jon Yablonski) | 30 «leyes» de psicología aplicada al diseño: Jakob, Fitts, Hick, Miller, Tesler, Doherty, Postel, Peak-End, Von Restorff, Zeigarnik, las de la Gestalt… | El porqué de cada decisión de distribución, agrupación y respuesta |
| [Fluent 2](https://fluent2.microsoft.design/) (Microsoft) | Sistema de diseño: color, tipografía, espaciado, elevación, iconos, movimiento, accesibilidad; sus herramientas de contraste y de orden de foco | Los fundamentos visuales en Windows, la plataforma principal, y la accesibilidad |
| [Checklist Design](https://www.checklist.design/) | Listas de comprobación por componente y por página | La estructura de nuestra «Lista por componente» (la página no se pudo leer de forma automática el 2026-11-24: la lista de abajo es propia, siguiendo esa idea) |
| [Autodesk HIG / Weave](https://github.com/Autodesk/hig) (Apache-2.0) | Sistema de diseño de Autodesk en componentes: entrada numérica, árbol, tablas, progreso, densidades alta y baja | La referencia más cercana a un programa de ingeniería: densidad compacta, entrada numérica con unidades, árbol del modelo |
| [Humane by Design](https://humanebydesign.com/) | Principios de diseño que respetan a la persona: que dé control, que tenga fin, que sea inclusivo… | Un cálculo se puede parar siempre; el programa no retiene ni distrae |
| [Growth.Design, psicología](https://growth.design/psychology) | 106 sesgos y principios cognitivos, en cuatro grupos | Los sesgos que afectan a un experto: el del valor por defecto, la revelación progresiva, reconocer frente a recordar |
| [GoodUI](https://goodui.org/) | Patrones contrastados con pruebas A/B, «prueba X en lugar de Y» | Validación en línea, entradas tolerantes, deshacer en lugar de confirmar, atajos de teclado |
| [Deceptive Patterns](https://deceptive.design/) (Harry Brignull) | Catálogo de patrones engañosos | Lo que **nunca** se hace (abajo, «Lo que no se hace») |

## Principios, aplicados a este programa

### 1. Lo conocido primero (Jakob, modelo mental)

- Los menús siguen el orden del flujo de trabajo (Archivo → … → Interpretar), como Slip2D y como
  los programas que el ingeniero ya conoce. Los mismos atajos que Slip2D para lo mismo.
- Los nombres son los del oficio (tensión de campo, excavar, fase), no los del código.
- La novedad se justifica: si algo se hace distinto de Slip2D, la spec dice por qué.

### 2. Menos carga, sin esconder lo que decide (Hick, Miller, *chunking*, Tesler, revelación progresiva)

- Un diálogo agrupa sus campos en bloques con título (geometría, material, fase), de pocos campos
  cada uno. Las listas largas, con búsqueda o en dos niveles.
- Las opciones avanzadas pueden ir plegadas, **pero un valor por defecto que cambia el resultado no
  se esconde**: se ve junto al resultado (regla 12). Plegar es ordenar, no ocultar.
- La complejidad que no se puede quitar (Tesler) la asume el programa: calcula el valor por defecto
  razonable, lo escribe explícito en el modelo y lo lista.

### 3. Objetivos cerca y grandes (Fitts)

- Las acciones frecuentes, en la barra de herramientas y en el menú contextual, donde está el cursor.
- Botones e iconos de al menos 24 px de lado útil (32 px en la barra principal), a escala de la
  pantalla (alta densidad de píxeles).
- El enganche (*snap*) del lienzo trabaja en píxeles de pantalla, y el diálogo lo dice.

### 4. Respuesta inmediata y progreso visible (Doherty, Zeigarnik, gradiente de meta)

- Todo lo que dura más de 0.4 s da señal de vida; más de 2 s, progreso con lo que se está haciendo
  (fase, escalón, iteración) y un **Cancelar** que funciona de verdad (RF de la spec 006).
- La interfaz nunca se congela: el cálculo va en un subproceso.
- Lo pendiente se ve: el modelo sin malla, la malla vieja o los resultados obsoletos se dicen en la
  barra de estado y en la acción deshabilitada (con su porqué).

### 5. Un buen final (Peak-End)

- Al terminar un cálculo, un resumen breve: qué fases se resolvieron, con qué ajustes y avisos, y un
  botón para ir a los resultados. Un fallo dice qué objeto del modelo lo causa.

### 6. Agrupar a la vista (Gestalt: proximidad, región común, semejanza, conexión, Prägnanz)

- La unidad va pegada a su campo; la leyenda, pegada a su dibujo, con la magnitud, la unidad y el
  convenio (compresión positiva o tracción positiva).
- Cada tipo de objeto tiene un color y un trazo fijos en toda la suite (contorno externo,
  excavación, material, fase, cargas, restricciones), los mismos en el lienzo, la leyenda y la ayuda.
- Lo que va junto se dibuja junto; lo distinto se separa con espacio antes que con líneas.

### 7. Destacar solo lo que importa (Von Restorff, atención selectiva)

- Un aviso destaca porque es el único: un solo color de aviso y un solo color de error.
- Los resultados obsoletos o incompletos se marcan de forma que no se puedan confundir con válidos.

### 8. Entradas tolerantes, nunca silenciosas (Postel, validación en línea)

- Se acepta lo que no es ambiguo (espacios, signo +, el separador decimal de la configuración
  regional y el punto) y **se muestra lo que se entendió**, con su unidad.
- Lo ambiguo o inválido se rechaza en el campo, al escribir, con un mensaje que dice qué falta y
  cómo arreglarlo. Nunca se acepta en silencio ni se corrige sin decirlo (es la misma regla que
  siguen las operaciones: un argumento inválido da un error que lo nombra).

### 9. Deshacer antes que confirmar (GoodUI, corrección)

- Toda edición es un paso de deshacer; por eso casi nada necesita un «¿Seguro?».
- Se confirma solo lo irreversible (sobrescribir un archivo, descartar cambios sin guardar, borrar
  unos resultados), con el botón que dice el verbo: «Descartar cambios», no «Aceptar».

### 10. El valor por defecto pesa (sesgo del valor por defecto)

- El experto también acepta el defecto sin mirarlo. Por eso cada defecto que mueve el número se ve
  con el resultado (regla 12) y se escribe explícito en el modelo.
- No hay defectos «cómodos» que favorezcan un resultado: el defecto es el que tiene fuente o el que
  la spec decidió, y lo dice.

### 11. Reconocer, no recordar

- Las listas muestran lo real: colores de material, número de elementos, tamaño de la malla, la vista
  previa de la paleta. Mejor una vista previa que un nombre.
- Lo que no aplica se **deshabilita con un tooltip que dice qué hacer antes**; no se oculta (así se
  descubre la capacidad, como en Slip2D).

### 12. Inclusivo y accesible (Fluent, Humane by Design)

- Contraste de al menos 4.5:1 en el texto y 3:1 en los gráficos y los iconos (la herramienta de
  contraste de Fluent sirve para comprobarlo).
- El color nunca es el único portador de información: las paletas de contornos son de luminosidad
  monótona y legibles con daltonismo; la leyenda lleva números; los estados llevan texto o icono.
- Todo se puede hacer con el teclado: el orden del foco en los diálogos sigue la lectura, cada menú
  tiene su tecla, y Esc cierra sin aplicar.
- La interfaz respeta el tamaño de letra y la escala de pantalla del sistema, y tiene tema claro y
  oscuro (los de Slip2D).

### 13. Fundamentos visuales (Fluent 2, Weave)

- Espaciado en múltiplos de 4 px; márgenes de diálogo y separaciones de un mismo juego de valores.
- La tipografía del sistema (Segoe UI en Windows) con una escala corta: título, cuerpo, nota. Los
  números de los resultados, con cifras tabulares para que las columnas se alineen.
- Densidad compacta, como un programa de ingeniería (Weave tiene densidad alta y baja): mucha
  información visible, sin apretar los objetivos por debajo de 24 px.
- Sin animaciones decorativas. Una transición, si la hay, corta (≤ 150 ms) y que no retrase nada.
- Iconos de un mismo juego y una misma licencia compatible, nítidos a toda escala.

### 14. Dar el control y tener fin (Humane by Design)

- El programa calcula; quien decide es la persona (`mission.md`). No hay asistentes que decidan
  solos ni resultados «recomendados».
- Un cálculo largo se puede cancelar y retomar; cerrar el programa con un cálculo en marcha pregunta
  una vez y lo para de verdad.
- Sin telemetría, sin llamadas de red no pedidas, sin notificaciones que reclamen atención.

## Lo que no se hace (Deceptive Patterns)

Ninguno de estos patrones tiene sitio en el programa, ni siquiera «sin querer»:

| Patrón | Cómo aparecería aquí sin darnos cuenta | Qué se hace en su lugar |
|---|---|---|
| Preselección | Una casilla marcada por defecto que cambia el cálculo | El defecto, escrito y mostrado con el resultado (regla 12) |
| *Sneaking* (colar) | Un ajuste que cambia al importar o al cambiar de unidades sin decirlo | El informe de la importación lo lista todo; cambiar de unidades no toca los valores |
| Redacción engañosa | Botones «Aceptar / Cancelar» con un significado dudoso; dobles negaciones | Botones con el verbo; opciones en positivo |
| Interferencia visual | Una leyenda que tapa los datos; un aviso en gris claro | Leyenda movible y fuera del dato; avisos con su color y su contraste |
| Insistencia (*nagging*) | El mismo aviso en cada cálculo | Se dice una vez, en la barra de estado o en el resumen, y se puede consultar |
| Difícil de cancelar | Un cálculo que no se para o que deja resultados que parecen completos | Cancelar en un clic; el `.h5` dice que está cancelado (spec 005) |
| Obstrucción y acción forzada | Pedir cuenta, registro o conexión para usar el programa | Nada de eso |
| Urgencia o escasez falsas, prueba social falsa, *confirmshaming* | — | No aplican a un programa así y no se introducen |

## Cuando chocan

| Choque | Se resuelve así |
|---|---|
| Revelación progresiva frente a la regla 12 | Se puede plegar un ajuste; su valor se ve siempre junto al resultado |
| Entrada tolerante (Postel) frente a «nunca aceptar en silencio» | Se acepta lo no ambiguo y se muestra lo entendido; lo ambiguo se rechaza en el campo |
| Menos opciones (Hick) frente a la regla 7 | Una opción que no mueve el número no se añade; una que lo mueve no se quita por simplificar: se agrupa o se pliega |
| Mejorar el aspecto frente a la coherencia con Slip2D | Se propone, y si se acepta se pide también para Slip2D |
| Esconder lo que no aplica frente a descubrirlo | Se deshabilita con su porqué, no se oculta |

## Lista por componente

Al cerrar una tarea de interfaz, cada componente nuevo o cambiado pasa su lista. Lo que no aplica se
dice («no aplica: …»), no se salta.

**Acción (menú, barra, contextual)**
- [ ] En un menú (regla 3), con `tr()` y su traducción (regla 2), con tecla y, si es frecuente, atajo.
- [ ] Deshabilitada con un tooltip que dice qué hacer antes cuando no aplica; nunca oculta.
- [ ] El mismo nombre e icono que en Slip2D si hace lo mismo.

**Diálogo**
- [ ] Título que dice qué se edita; los campos agrupados en bloques con título.
- [ ] Cada campo numérico con su unidad pegada, su rango y su validación en línea.
- [ ] Los convenios escritos junto al campo (compresión positiva, sentido de la carga).
- [ ] Los valores por defecto salen del modelo, no de literales; los que mueven el número, señalados.
- [ ] Botón principal con el verbo; Esc cierra sin aplicar; Intro aplica; el foco sigue la lectura.
- [ ] Toda opción tiene su test que demuestra que mueve el número (regla 7).
- [ ] Probado sin pantalla, sin bloquear (nada de `exec()` en los tests) y sin dejar estado (regla 5).

**Lienzo**
- [ ] Respuesta inmediata al mover el cursor (coordenadas, enganche) por debajo de 0.4 s con la
      malla del caso 005.
- [ ] Colores y trazos de cada tipo de objeto, los de la suite.
- [ ] Selección visible con contraste suficiente en los temas claro y oscuro.

**Proceso largo (mallar, calcular)**
- [ ] Progreso con lo que se hace; Cancelar que para de verdad; la interfaz no se congela.
- [ ] Un final con su resumen y sus avisos; un fallo que nombra el objeto culpable.

**Resultado (contornos, gráficos, tablas)**
- [ ] Leyenda con magnitud, unidad, convenio, fase y procedencia (punto de integración o recuperado).
- [ ] Paleta de luminosidad monótona y apta para daltonismo; números en la leyenda.
- [ ] Los valores por defecto que decidieron el resultado, a la vista (regla 12).
- [ ] Obsoleto o incompleto, imposible de confundir con válido.
- [ ] Tablas con cabecera, unidades en la cabecera, cifras alineadas y exportables.

**Mensaje (error, aviso, estado vacío)**
- [ ] Dice qué pasó, en qué objeto y cómo seguir; sin códigos sin explicar.
- [ ] Un estado vacío dice qué hacer para llenarlo (por ejemplo, «Sin malla: Malla → Mallar»).
- [ ] Se dice una vez; no insiste.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
