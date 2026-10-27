# Spec 001 — Prueba de concepto del motor

> **Borrador (2026-10-27).** Fase 0 de la hoja de ruta. Decide si el ADR-0001 (motor en Rust) se
> queda o se reabre. Solo el **qué** y el **porqué**; el cómo va en `plan.md`. Decisiones D1–D6 tomadas
> (al final) y fuentes comprobadas (tarea T1).

## Contexto y objetivo

El ADR-0001 aceptó un motor numérico en Rust con una condición: que una prueba de concepto lo
justifique con criterios fijados **antes** de medir. Esta función es esa prueba. Resuelve el mismo
problema —un elemento finito, dos leyes de material, dos casos con solución cerrada— en tres
variantes (Python de referencia, NumPy vectorizado y Rust), comprueba que las tres dan lo mismo y
que dan lo que dice la solución analítica, y mide lo que cuesta cada una. Si Rust no gana lo
bastante, o no se puede distribuir, o el propietario no lo entiende, la decisión se reabre con las
medidas delante.

Lo que sale de aquí y se queda, pase lo que pase: la implementación de referencia en Python del
elemento y de las dos leyes (es el oráculo de los tests, ADR-0001), los dos primeros casos de
validación y el convenio de signos del motor.

## Usuarios / actores

- **El propietario**, que decide con las medidas si sigue Rust (criterios 4 y 5 del ADR-0001).
- **Los tests**, que usan la implementación de referencia como oráculo del código compilado.

## Historias de usuario

- H1: Como propietario quiero ver, con números medidos de la misma forma, cuánto más rápido es Rust
  que NumPy en la integración constitutiva, para decidir si compensa un segundo lenguaje.
- H2: Como propietario quiero leer el Mohr-Coulomb en Rust al lado del de Python, para juzgar si
  podré auditarlo.
- H3: Como ingeniero quiero que el resultado del hueco circular coincida con Kirsch y con Salençon,
  con una tolerancia fijada antes de medir y una malla documentada, para fiarme del elemento y de la
  ley.

## Requisitos funcionales (EARS)

**Elemento y material**

- RF-1: EL SISTEMA calcula, para un triángulo de 6 nudos en deformación plana con deformaciones
  pequeñas, la matriz de rigidez y el vector de fuerzas internas a partir de las tensiones en sus
  puntos de integración.
- RF-2: EL SISTEMA integra la ley elástica lineal isótropa y la ley de Mohr-Coulomb perfectamente
  plástica (cohesión, rozamiento y dilatancia; flujo asociado y no asociado) en cada punto de
  integración, dado el incremento de deformación, guardando también la tensión fuera del plano.
- RF-3: EL SISTEMA ofrece RF-1 y RF-2 en tres variantes con la misma interfaz: **Python de
  referencia** (bucles legibles, una función por paso de la formulación), **NumPy vectorizado** y
  **Rust** expuesto con PyO3.
- RF-4: CUANDO un punto de integración plastifica, EL SISTEMA devuelve la tensión corregida sobre la
  superficie de fluencia, sea cual sea la región de retorno (plano, arista o vértice). SI el
  algoritmo de retorno no converge, ENTONCES EL SISTEMA lo dice con el punto, el elemento y el
  incremento, y no devuelve una tensión.

**Análisis**

- RF-5: EL SISTEMA resuelve una fase de excavación: tensión inicial de campo constante, excavación
  sin presión interior, contorno exterior fijo, en escalones de carga con iteraciones de equilibrio
  hasta una tolerancia dada, con la frontera Python ↔ Rust de **una llamada por iteración global**.
- RF-6: SI una iteración no converge en el número máximo dado, ENTONCES EL SISTEMA se detiene y
  devuelve la historia de convergencia, sin dar el resultado como válido.
- RF-7: EL SISTEMA construye una malla radial estructurada de T6 para el hueco circular, con
  número de divisiones y gradación radial como parámetros.

**Medida y distribución**

- RF-8: EL SISTEMA mide, con el método A/B en el mismo proceso que usa la suite, el tiempo de la
  integración constitutiva de las tres variantes sobre el mismo conjunto de puntos e incrementos, y
  además el del ensamblaje y el de la solución lineal.
- RF-9: EL SISTEMA se construye como una rueda por plataforma (Windows, macOS ARM, Linux) en la
  integración continua, y la rueda se instala y pasa los casos en las tres.
- RF-10: EL SISTEMA se puede congelar con PyInstaller y el ejecutable resuelve los dos casos.

## Validación numérica

| Caso | Fuente científica | Qué se compara |
|---|---|---|
| `validacion/casos/001-kirsch-hueco-elastico` (ficha `VER-STR-01`), contorno a 100 m | Kirsch (1898), en Jaeger, Cook y Zimmerman (2007), *Fundamentals of Rock Mechanics*, 4.ª ed., §8.4–8.5 | σr, σθ en los puntos de integración y ur en los nudos a lo largo de un radio, r de 1 a 5 m |
| `validacion/casos/002-salencon-hueco-mohr-coulomb` (ficha `VER-STR-02`), ψ = 0° y ψ = 30°, contorno a 100 m | Salençon (1969), §5, con la zona de arista donde su hipótesis no se cumple (D8) | Lo mismo, más el radio plástico R0 |
| Identidad del anillo finito: el modelo de las fichas, con el contorno fijo a 21 m, elástico y Mohr-Coulomb | Solución general de Jaeger, Cook y Zimmerman (2007), ecs. (8.78)–(8.81), con u(b) = 0, y el modelo de Salençon en el mismo anillo (derivación propia, comprobada) | El modelo de 21 m **tiene** solución cerrada: mide solo la discretización y comprueba el contorno fijo |
| Identidad entre variantes | — | Python de referencia y Rust coinciden con tolerancia relativa del orden de 1e-10, en punto material y en malla (criterio 1 del ADR-0001) |
| Convergencia de malla | — | Con tres mallas cada vez más finas, el error frente a la solución cerrada **disminuye**; la tolerancia de cada caso se fija con la malla elegida (regla 9) |

Datos de los dos casos (fichas): radio a = 1 m, E = 10 000 MPa, ν = 0.2, tensión de campo
hidrostática p0 = 30 MPa de compresión; en STR-02, c = 3.45 MPa, φ = 30°, ψ = 0° y 30°,
presión interior nula. El contorno exterior de las fichas está a 21 m; aquí, a 100 m para los
casos y a 21 m para la identidad (D3 bis). Valores de referencia en medio infinito, comprobados
contra las fuentes (tarea T1, `comprobaciones/soluciones_cerradas.py`): en STR-01, σθ(a) = 60 MPa
y ur(a) = 0.0036 m; en STR-02, R0 = 1.734998 m, ur(a) = 0.008236 m (ψ = 0°) y 0.019086 m
(ψ = 30°).

**Las reproducciones propias del programa de referencia no son valor esperado** (regla de
`validacion/README.md`). Sí sirven de aviso: en la reproducción P02, con la misma malla gruesa, el
cuadrilátero de 4 nudos se quedó un 11 % corto en ur(a) y el de 8 nudos un 1.9 %. Por eso esta spec
exige el estudio de convergencia.

## Requisitos no funcionales

- **Criterios de aceptación del ADR-0001, fijados antes de medir**: (1) Python de referencia y Rust
  coinciden a ~1e-10; (2) los casos cumplen su tolerancia; (3) las ruedas se instalan y funcionan en
  los tres sistemas y el congelado con PyInstaller funciona; (4) el propietario entiende el
  Mohr-Coulomb en Rust al menos tan bien como en Python; (5) **Rust ≥ ×10 más rápido que NumPy
  vectorizado** en la integración constitutiva.
- Python ≥ 3.11 (CI con 3.11, 3.12 y 3.13; en local solo hay 3.14).
- Sin dependencias nuevas sin el OK del propietario y sin comprobar su licencia (AGPL-3.0).

## Casos límite

- Punto que plastifica en la arista o en el vértice del cono de Mohr-Coulomb.
- Incremento que pasa de elástico a plástico dentro del mismo escalón.
- Elemento degenerado (área nula o negativa): error con el número de elemento, no un resultado.
- Iteración que no converge (RF-6).
- ψ = φ (asociado) frente a ψ = 0 (no asociado): el segundo no es simétrico en la matriz tangente
  consistente; el solver lineal (SuperLU) lo resuelve igual (D7).

## Fuera de alcance

- Interfaz, proyecto `.ogr`, resultados en `.h5`, MCP, idiomas: nada de eso entra en la fase 0.
- Otros elementos (T3, Q4, Q8), axisimetría, otras leyes, fases múltiples, SSR, agua, soporte.
- Elegir el solver lineal definitivo: aquí se usa SuperLU de SciPy en las tres variantes.
- Paralelismo: se mide en un hilo; el paralelo (rayon) se mira después, si la prueba sale bien.

## Criterios de finalización

- [ ] Los cinco criterios del ADR-0001 medidos y anotados con sus números, y la decisión del
      propietario sobre el ADR (se queda o se reabre)
- [ ] Los dos casos de validación dentro de tolerancia, con la malla que la fija y el estudio de
      convergencia que la justifica
- [ ] Cada fórmula del código, comprobada contra su fuente original (autor, año, ecuación)
- [ ] Changelog registrando **qué se encontró**

## Decisiones del propietario (2026-10-27)

| # | Decisión | Por qué |
|---|---|---|
| D1 | **Tracción positiva dentro del motor.** La interfaz muestra compresión positiva donde sea la costumbre geotécnica, con la conversión en un único sitio | Es el convenio de los textos de elementos finitos y de plasticidad que se siguen, y el del motor de referencia por dentro; dar la vuelta a un algoritmo de retorno dentro del motor es donde un signo cambiado no se ve |
| D2 | **Cargas y desplazamientos impuestos de cada fase, en totales.** El motor recibe el estado total que define el usuario y calcula él el incremento | Un solo convenio para los dos y sin errores acumulados; el motor de referencia los mezcla (duda 12 de S06) |
| D3 | **Tolerancias fijadas ya:** STR-01, 0.5 % en σθ(a) y en ur(a); STR-02 (ψ = 0° y 30°), 2 % en ur(a), y R0 dentro de un tamaño de elemento. El estudio de convergencia elige la malla que las cumple; si ninguna malla razonable las cumple, es un hallazgo que se reporta, no una tolerancia que se afloja | Criterio fijado antes de medir |
| D3 bis | **Dos geometrías** (decidido el mismo día, tras la tarea T1): los casos de validación, con el contorno a **100 m**, contra Kirsch y Salençon; y el modelo de las fichas, a **21 m**, contra la solución exacta del anillo finito, como identidad. Las tolerancias de D3 no cambian | Al calcularlo (T1) resultó que con el contorno a 21 m la solución exacta del modelo ya se aparta de las fórmulas de medio infinito en ur(a) un **0.60 %** (STR-01), un **1.42 %** (STR-02, ψ = 0°) y un **1.83 %** (ψ = 30°): ninguna malla cumpliría D3 frente a ellas. La versión anterior de esta spec decía «en torno a un 0.2 %»: era una estimación sin calcular, y estaba mal. A 100 m el efecto es del 0.03–0.08 % |
| D4 | **La referencia en Python en su sitio final** (`ogr_fem2d/engine/reference/`); la variante NumPy en `poc/`; el crate de Rust en `rust/`, compilado como `ogr_fem2d._engine` | La referencia se queda pase lo que pase (es el oráculo); NumPy solo sirve para medir |
| D5 | **Fuentes conseguidas** por el propietario (2026-10-27) y comprobadas en la tarea T1: Salençon (1969); Jaeger, Cook y Zimmerman (2007, 4.ª ed.); de Souza Neto, Perić y Owen (2008); Zienkiewicz y Taylor (2000, 5.ª ed., vol. 1); de contraste, Timoshenko y Goodier y la tesis de Clausen (2007) | Tabla de fuentes y hallazgos en `plan.md`, «Formulación» |
| D7 | **Iteraciones de Newton completo con la tangente consistente**, no con la rigidez inicial (decidido el 2026-10-27, tras la T7; el propietario lo deja a criterio de la validez de los resultados) | En la T7 la rigidez inicial necesitó miles de iteraciones por escalón en Mohr-Coulomb, con un factor de reducción del residuo de 0.965 a 0.9966 que empeora al refinar la malla; con un factor tan cerca de 1 un residuo pequeño no asegura un desplazamiento preciso (el error en u va como r/(1 − ρ)), y las mallas que pide D3 tardarían horas. Con Newton la convergencia es cuadrática y el residuo sí mide el error. La tangente sale de de Souza Neto et al. (2008), §8.2.4, y se comprueba contra su derivada numérica y contra la subrutina CTMC. La variante Rust tendrá que dar también la tangente |
| D8 | **Referencia de ur(a) en STR-02: la solución exacta del modelo**, Salençon (1969) más la zona de arista donde su hipótesis no se cumple (`salencon_edge_infinite` y `salencon_edge_finite` en `comprobaciones/`); Salençon queda como dato informativo; las tolerancias de D3 no cambian (decidido el 2026-10-27) | Con los datos de la ficha, σz sería la principal mayor para r < 1.281 m y el material está en la arista σz = σθ: las tensiones y R0 son los de Salençon, pero ur(a) es un 0.99 % (ψ = 0°) y un 1.90 % (ψ = 30°) mayor. Frente a Salençon, ψ = 30° habría pasado el 2 % por 0.1 %, sin razón. El modelo y la solución extendida coinciden a 0.03 % en el anillo de 21 m |
| D6 | **OK a `pyo3` 0.30 (MIT o Apache-2.0), `numpy` 0.30 (BSD-2-Clause), `ndarray` 0.17 (MIT o Apache-2.0) y PyInstaller 6.22** (GPL-2.0-or-later con excepción para distribuir programas de cualquier licencia); PyInstaller solo en el `.venv`, como herramienta | Licencias comprobadas el 2026-10-27, compatibles con AGPL-3.0 |
