# Spec 002 — Motor elástico general

> **Borrador (2026-10-27), pendiente de las decisiones D1–D7 del propietario.** Primera spec de la
> fase 1 del plan de desarrollo (`spec/constitution/plan_de_desarrollo.md`). Solo el **qué** y el
> **porqué**; el cómo va en `plan.md`. Nada se programa antes de T0 (decisiones y OK del plan).

## Contexto y objetivo

La spec 001 dejó un motor que resuelve **un** problema: el hueco circular en un cuarto de corona,
con T6 en deformación plana, una fase de excavación hecha con la malla sin el hueco y el contorno
exterior fijo. Esta spec lo convierte en un motor general **elástico**: recibe cualquier malla de
triángulos con sus materiales, restricciones, cargas, tensiones iniciales y fases, en deformación
plana o en axisimetría, y devuelve desplazamientos, tensiones y reacciones. Es lo que necesitan la
malla (spec 003), el modelo `.ogr` (spec 004) y la interfaz (spec 006) para el primer análisis de
principio a fin.

El motor sigue sin conocer la interfaz (regla 11): recibe datos discretos con un esquema documentado
y validado al recibirlos, y dice qué dato está mal y dónde.

## Usuarios / actores

- **El modelo y la interfaz** (specs 004–006), que traducen lo que dibuja el usuario a la entrada
  discreta del motor.
- **Los tests**, que usan la referencia en Python como oráculo de Rust (ADR-0001).
- **El ingeniero**, que necesita fiarse de STR-04 y STR-09 antes de usar el programa.

## Historias de usuario

- H1: Como ingeniero quiero calcular un problema axisimétrico (una cavidad esférica, una zapata
  circular, un pilote) con el mismo motor que uno de deformación plana, para no cambiar de programa.
- H2: Como ingeniero quiero aplicar cargas repartidas uniformes o triangulares sobre un contorno y
  cargas puntuales, y obtener las reacciones, para comprobar el equilibrio de mi modelo.
- H3: Como ingeniero quiero partir de una tensión inicial constante o gravitatoria con K0 y excavar
  en una fase posterior, para modelizar una obra subterránea o una excavación a cielo abierto.
- H4: Como desarrollador del modelo (spec 004) quiero que el motor rechace una entrada mal formada
  con un mensaje que diga qué elemento, nudo o fase está mal, para no depurar a ciegas.

## Requisitos funcionales (EARS)

**Entrada**

- RF-1: EL SISTEMA recibe una entrada discreta con nudos, elementos (T3 o T6, un tipo por modelo),
  material de cada elemento, tipo de análisis (deformación plana o axisimetría) y una secuencia de
  fases; cada fase da los elementos activos, las restricciones, los desplazamientos impuestos y las
  cargas, **en totales** (D2 de la spec 001).
- RF-2: CUANDO la entrada no cumple el esquema (índices fuera de rango, elemento de área nula o
  invertido, material sin definir, un grado de libertad restringido e impuesto a la vez, nudo con
  r < 0 en axisimetría, nudo libre sin rigidez…), EL SISTEMA la rechaza **antes de calcular**, con
  un error que nombra la fase, el elemento o el nudo y la regla incumplida.

**Elementos**

- RF-3: EL SISTEMA calcula rigidez, fuerzas internas y tensiones de los triángulos de 3 y de 6
  nudos en deformación plana y en axisimetría, con la tensión fuera del plano guardada en cada punto
  de integración (σzz en deformación plana; la circunferencial σθθ en axisimetría).
- RF-4: EN axisimetría, EL SISTEMA exige que el eje de simetría sea x = 0 y que ningún nudo tenga
  x < 0, y ningún punto de integración cae sobre el eje (D1).

**Contorno y cargas**

- RF-5: EL SISTEMA aplica restricciones en X, en Y o en las dos, y desplazamientos impuestos, por
  nudo y por fase, y devuelve las **reacciones** en los grados de libertad restringidos.
- RF-6: EL SISTEMA aplica cargas nodales, cargas puntuales en cualquier punto de un elemento,
  cargas repartidas uniformes y lineales (triangulares o trapeciales) sobre lados de elemento,
  normales al lado o en componentes x, y, y el peso propio de cada material, todas como **fuerzas
  nodales consistentes**.

**Tensión inicial y fases**

- RF-7: EL SISTEMA acepta, como tensión inicial, un tensor por punto de integración (regla 11), y
  ofrece fuera del motor el cálculo de los dos campos habituales: **constante** (σ1, σ3, σz y el
  ángulo de σ1) y **gravitatorio** con superficie horizontal, estratos horizontales y coeficiente K
  dentro y fuera del plano por material (D3).
- RF-8: EL SISTEMA resuelve una secuencia de fases; CUANDO un elemento deja de estar activo en una
  fase (excavación), su contribución desaparece y el desequilibrio que dejan sus tensiones es la
  carga de esa fase (Zienkiewicz y Taylor 2000, ec. 2.13b); los nudos que se quedan sin elementos
  activos salen del sistema y se señalan en el resultado.
- RF-9: EL SISTEMA da, por fase, desplazamientos totales, tensiones totales en los puntos de
  integración, reacciones, la historia de convergencia y los elementos activos.

**Variantes**

- RF-10: EL SISTEMA ofrece todo lo anterior en la referencia en Python y en Rust, con la misma
  interfaz de una llamada por iteración global; la variante NumPy de la spec 001 no se extiende (D7).
- RF-11: SI se pide Mohr-Coulomb con T3 o en axisimetría, ENTONCES EL SISTEMA lo rechaza con un
  error hasta que un caso lo valide (D6); con T6 en deformación plana sigue funcionando como en la
  spec 001.

## Validación numérica

| Caso | Fuente científica | Qué se compara |
|---|---|---|
| `validacion/casos/003-cavidad-esferica-elastica` (ficha `VER-STR-09`), axisimetría | Lamé (1852), en Timoshenko y Goodier (1951), §121, ecs. (197)–(198), págs. 358–359; ur por la ley de Hooke | σR, σt en los puntos de integración y ur en los nudos a lo largo de un radio, R de 1 a 5 m |
| Identidad de la esfera finita con el exterior fijo | Las mismas, con u(b) = 0 (derivación propia, `comprobaciones/`, `sphere_fixed_outer`) | El modelo tiene solución cerrada: mide solo la discretización |
| `validacion/casos/004-carga-en-faja-elastica` (ficha `VER-STR-04`), deformación plana | J. H. Michell (1902), en Timoshenko y Goodier (1951), §34, ec. (f), págs. 92–95; comprobada por superposición de Flamant, §33, ec. (66), pág. 85 | σ1 y σ3 en los puntos de integración bajo el centro de la faja, z de 0 a 5 m |
| Identidad del semiespacio truncado | Michell, con las tracciones exactas de su solución aplicadas en el contorno del dominio finito | Sin efecto del dominio: mide solo la discretización |
| Casos 001 y 002 por el motor general | Los de la spec 001 | Los mismos números que en la spec 001, a redondeo (el motor general no cambia lo validado) |
| Excavación por desactivación | — | Desactivar el anillo interior de una malla da lo mismo, a redondeo, que la malla sin ese anillo (lo que hacía la spec 001) |
| Identidades de elemento | Zienkiewicz y Taylor (2000), §5.2.2 (pág. 115) y cap. 2 | Parcela en deformación plana y en axisimetría (u = a·r, v = b·z da deformación constante, la única según la fuente); sólido rígido (en axisimetría solo la traslación en z lo es: u_r constante **no** es rígido); equilibrio global de reacciones con todas las cargas |
| Tensión gravitatoria | Jaeger, Cook y Zimmerman (2007), §13.2, ecs. (13.1) y (13.5), págs. 400–401 | Con superficie horizontal, estratos horizontales y rodillos laterales, tensión gravitatoria más peso propio da desplazamiento nulo |
| Identidad entre variantes | — | Referencia y Rust coinciden a ~1e-10 en todo lo anterior |

Datos de las fichas: STR-09, a = 1 m, E = 20 000 MPa, ν = 0.2, campo hidrostático p0 = 10 MPa,
excavación sin presión interior; STR-04, E = 20 000 MPa, ν = 0.2, q = 1 MPa sobre una faja de
semianchura b = 1 m, dominio de 50 × 25 m en la ficha.

Valores de referencia, comprobados contra las fuentes (`comprobaciones/soluciones_cerradas.py`):

- STR-09: σt(a) = 15 MPa, σR(a) = 0, ur(a) = 3.000·10⁻⁴ m. Con el contorno exterior esférico y
  fijo a 21 m, la solución exacta del modelo se aparta de la del medio infinito un **0.022 %** en
  ur(a) y un 0.011 % en σt(a) (1/b³: mucho menos que el 0.60 % del hueco cilíndrico, que va con
  1/b²). Por eso aquí basta **una** geometría.
- STR-04: Michell y la superposición numérica de Flamant coinciden a 2·10⁻¹⁶ MPa en seis puntos;
  en el eje, a 1 m, σ1 = 0.818310 y σ3 = 0.181690 MPa; a 5 m, 0.248093 y 0.003239 MPa.

**Lo que la ficha de STR-04 no dice y hay que tener en cuenta:** el semiespacio es infinito y el
modelo no; la ficha compara solo tensiones, y es lo correcto, porque en deformación plana el
desplazamiento bajo una carga en un semiespacio no está acotado (crece con el logaritmo de la
distancia; por comprobar en T&G §33 en la tarea T1). Además σ3 es muy pequeño a 5 m (0.3 % de q),
así que un error relativo en σ3 no significa nada: la tolerancia va relativa a q (D4). El error
del 0.6 % en σ1 de la ficha es lo que obtuvo el programa de referencia: **no es valor esperado**.

## Requisitos no funcionales

- La referencia en Python se escribe para leerse: es el oráculo de Rust.
- Toda fórmula se comprueba contra su fuente original antes de programarla y se cita en el código.
- Las tensiones iniciales que el motor recibe y las que devuelve, en tracción positiva (D1 de la
  spec 001); el preproceso de la tensión inicial acepta compresión positiva y convierte en un único
  sitio.
- Sin dependencias nuevas.

## Casos límite

- Lado de un elemento sobre el eje de simetría (puntos de integración con r = 0: D1).
- Nudo sobre el eje en axisimetría: su u_r es nulo por simetría; si el usuario no lo restringe, el
  motor lo restringe y lo dice (D1 bis).
- Nudo que se queda sin elementos activos tras una excavación.
- Fase sin ningún cambio (debe dar desplazamiento incremental nulo).
- Modelo sin restricciones suficientes (matriz singular): error con el modo libre, no un resultado.
- Carga repartida sobre un lado que no es lado de un elemento activo: error.
- Mohr-Coulomb con T3 o en axisimetría: error (D6).

## Fuera de alcance

- Generador de mallas general y la malla de STR-01 con contorno rectangular: spec 003 (D5).
- El formato `.ogr`, unidades de usuario y la interfaz: specs 004–006.
- K variable con la profundidad y superficie del terreno irregular en la tensión gravitatoria
  (D3); presiones intersticiales (spec 010).
- Cuadriláteros; otras leyes; SSR; soporte; juntas.
- Llevar el bucle global a Rust (P4: fase 2).

## Criterios de finalización

- [ ] D1–D7 decididas por el propietario y anotadas aquí
- [ ] Cada fórmula comprobada contra su fuente (tabla «Formulación» de `plan.md`) y citada en el
      código
- [ ] STR-09 y STR-04 dentro de la tolerancia fijada antes de medir, con la malla y el estudio de
      convergencia (y de dominio, en STR-04) que la justifican
- [ ] Las identidades de la tabla, en verde y con dientes
- [ ] Los casos 001 y 002 dan lo mismo que en la spec 001
- [ ] Referencia y Rust idénticos a ~1e-10; ruedas y congelado con los casos nuevos
- [ ] `CHANGELOG_v0.0.2.md` con lo encontrado; fichas STR-04 y STR-09 con su «Seguimiento»

## Decisiones que se piden al propietario

| # | Pregunta | Propuesta | Por qué |
|---|---|---|---|
| D1 | **Regla de integración.** La regla cuadrática que usa el T6 (tabla 9.2 de Zienkiewicz y Taylor 2000, pág. 222) pone sus tres puntos en el centro de los lados; en axisimetría, un lado sobre el eje deja un punto con r = 0, donde Nᵢ/r no se puede evaluar | Deformación plana: T6 con la regla de los lados (validada en la spec 001, no se cambia: regla 9), T3 con el centroide. Axisimetría: T6 con la **quíntica de 7 puntos** de la misma tabla (todos interiores, pesos positivos), T3 con el centroide | La cúbica de 4 puntos también es interior pero tiene un peso negativo (−27/48); la de 7 puntos es exacta hasta grado 5 y no tiene ese problema. No se usa ninguna regla que no esté en la fuente |
| D1 bis | **Nudos sobre el eje**: u_r = 0 por simetría | El motor lo impone siempre y lo dice en el resultado (regla 12) | Dejarlo libre no tiene sentido físico; imponerlo en silencio sería un valor por defecto oculto |
| D2 | **Axisimetría: por radián o por el anillo entero.** La (5.13) de Zienkiewicz y Taylor integra «sobre el anillo entero» (factor 2π) | **Anillo entero, como la fuente**: una carga puntual sobre el eje (un pilote) es la fuerza total, y las reacciones también. Se muestra con el resultado (regla 12) | El factor multiplica la rigidez y las cargas por igual: los desplazamientos y tensiones no cambian, solo las fuerzas. Seguir la fuente evita una conversión que el usuario tendría que recordar |
| D3 | **Tensión inicial.** El motor recibe un tensor por punto; el campo constante y el gravitatorio se calculan fuera, como preproceso | Gravitatorio con superficie horizontal y estratos horizontales: σv = Σ γᵢ·hᵢ (JCZ 2007, ec. 13.1), σh = K·σv dentro del plano y σz = Kz·σv fuera (ec. 13.5), K y Kz constantes por material. **K variable con la profundidad y superficie irregular, después**: K = a + b·zᶜ (S01) no tiene fuente; la ec. (13.10) de JCZ es otra forma. La superficie irregular necesita la geometría (spec 004) | Sin fuente no entra (AGENTS); con superficie y estratos horizontales el campo está en equilibrio y hay identidad exacta para probarlo |
| D4 | **Tolerancias, fijadas antes de medir** | STR-09: **0.5 %** en σt(a) y en ur(a), como STR-01. STR-04: en el eje, de z = 0.25 a 5 m, \|σ1 − σ1ᴹ\| ≤ **0.01·q** y \|σ3 − σ3ᴹ\| ≤ **0.01·q**; el tamaño del dominio, por estudio (si 50 × 25 m no basta, es un hallazgo y se agranda, no se afloja) | σ3 es del orden de 0.003·q a 5 m: el error relativo no significa nada. En z = 0 hay un salto de tracción en los bordes de la faja; por eso se empieza en 0.25 m |
| D5 | **STR-01 con malla general** | A la spec 003, cuando haya generador de mallas; aquí el caso 001 pasa por el motor general con su misma malla y debe dar lo mismo | Sin generador, «malla general» sería una malla estructurada más |
| D6 | **Mohr-Coulomb fuera de lo validado** | Solo con T6 en deformación plana; con T3 o en axisimetría el motor se niega con un error hasta que un caso lo valide (fase 2, spec 008) | El retorno valdría igual con σθθ como tensión fuera del plano, y el T3 tiene problemas conocidos de bloqueo en plasticidad; ninguna de las dos cosas está validada ni tiene fuente leída aún |
| D7 | **La variante NumPy y la medida de la spec 001** | Se congelan: `poc/` se queda con la interfaz de la 001 (deformación plana, T6) como registro de la medida del ADR-0001; si la interfaz general no puede mantenerla compatible, sus tests se retiran con nota en el changelog | El plan de desarrollo ya dice que NumPy no se mantiene (D4 de la 001); mantenerla obligaría a escribir cada novedad tres veces |
