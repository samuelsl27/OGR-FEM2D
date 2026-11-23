# Spec 008 — Leyes de la fase 2

> **Borrador de alcance (2026-11-23), sin aprobar.** Fase 2 del plan de desarrollo
> (`spec/constitution/plan_de_desarrollo.md`, «Spec 008 — Leyes de la fase 2»). Solo el **qué** y
> el **porqué**, sin fórmulas ni decisiones tomadas. **Antes de abrirla hay que reevaluarla**
> (sección siguiente); después, plan y tareas con el OK de la propietaria.

## Antes de abrirla: reevaluar esta spec

Este borrador se escribió antes de que existieran las specs que lo preceden; el código, el núcleo y
OGR Slip2D habrán avanzado. Al abrirla, y antes de escribir el plan:

- [ ] Contrastarla con el código de este programa y con las specs cerradas desde el 2026-11-23: qué
      ya está hecho, qué cambió y qué se movió de sitio.
- [ ] Mirar qué tienen ya OGR Slip2D y `ogr_core` en la etiqueta fijada. Lo genérico se pide a la
      sesión de OGR-Core, no se copia (`AGENTS.md`, «Un núcleo y varios programas»). Puntos de
      partida vistos al escribir el borrador:
      `ogr_fem2d/engine/reference/mohr_coulomb.py` y `rust/src/mohr_coulomb.rs` (Mohr-Coulomb
      perfecto con c, φ y ψ, retorno a plano, aristas y vértice, tangente consistente;
      `ReturnMappingError` en el vértice con ψ = 0°); `ogr_fem2d/engine/interface.py`
      (`material_row`, la fila de parámetros que cruza a Rust); `ogr_fem2d/engine/model.py`
      (`Material`, hoy elástico o Mohr-Coulomb). En el núcleo: `ogr_core/materials/
      parameter_calculator.py` (mb, s y a desde GSI, mi y D, Hoek et al. 2002),
      `ogr_core/materials/builtin_models.py` (`HoekBrown`, `GeneralizedHoekBrown`, `PowerCurve`:
      criterios de equilibrio límite, sin regla de flujo), `ogr_core/materials/strength_model.py`
      (el registro de criterios de Slip2D, un posible modelo para el contrato).
- [ ] Leer y comprobar las fuentes de «Validación numérica» y de «Fuentes por conseguir»; las fichas
      de los casos no son fuente.
- [ ] Releer las fichas de los casos que la cierran y su «Seguimiento».
- [ ] Convertir las «Dudas abiertas» en decisiones propuestas (D1, D2…) con su porqué, para el OK de
      la propietaria.

## Depende de

- Spec 007 (tolerancia, colapso y escalones): las leyes nuevas se prueban en modelo con su criterio.
- Spec `004-modelo-y-proyecto`: los parámetros de cada ley en el material, por fase, con sus valores
  por defecto a la vista.
- Spec `005-resultados`: el estado de rotura por punto (corte, tracción, residual) y el factor de
  resistencia (T05), que hoy solo cubre Mohr-Coulomb.
- Spec `006-interfaz-y-calculo`: el diálogo de materiales de cada ley.

## Contexto y objetivo

El motor tiene un único Mohr-Coulomb perfecto, sin límite de tracción ni resistencia residual, solo
con T6 en deformación plana (la spec 002, D6, rechaza T3 y axisimetría hasta que un caso lo valide,
y remite aquí). Los casos de la fase 2 piden más: casi todos los taludes trabajan con una resistencia
a tracción (la grieta de tracción de la 020 es una zona sin ella), STR-30 es un Mohr-Coulomb
frágil-plástico, STR-03 un Hoek-Brown frágil, SLP-56 a 58 comparan Mohr-Coulomb con Drucker-Prager
en el SSR, SLP-60 es un Hoek-Brown generalizado en un talud, y los de curva potencial de la 020 se
convierten a Hoek-Brown generalizado.

Ninguno de los manuales de teoría describe la integración de tensiones (T00 §3.1, duda 6 de S06):
cada ley sale de la literatura, con su referencia en Python como oráculo (ADR-0001) y su prueba en
un punto de Gauss (regla 8). El contrato común de ley constitutiva se diseña ya pensando en la
fase 5 y en el SSR, que necesita copias de la ley con la resistencia reducida.

## Usuarios / actores

- **Ingeniero de taludes y de túneles**, que elige el criterio que usa en la práctica.
- **Investigador**, que añadirá leyes de la fase 5 sobre el mismo contrato.
- **La spec 009**, que reduce la resistencia de cada ley; **la 020**, que convierte la curva potencial.
- **Los tests**, que usan la referencia en Python como oráculo de Rust.

## Historias de usuario

- H1: Como ingeniero quiero un Mohr-Coulomb con resistencia a tracción, residual y dilatancia, para
  modelar roca frágil y taludes con zona sin tracción.
- H2: Como ingeniero de roca quiero un Hoek-Brown generalizado definido por GSI, mi y D, con pico y
  residual, para usar los parámetros del macizo como los publica la fuente.
- H3: Como ingeniero quiero un Drucker-Prager con su ajuste a Mohr-Coulomb documentado, para
  comparar con los casos publicados que lo usan.
- H4: Como investigador quiero un contrato de ley único y documentado, para añadir una ley nueva sin
  tocar el resto del motor.

## Requisitos funcionales (EARS)

**Leyes**

- RF-1: EL SISTEMA integra Mohr-Coulomb completo: resistencia a tracción con su superficie, valores
  de pico y residuales con caída a residual tras la primera plastificación, y dilatancia.
- RF-2: EL SISTEMA integra Drucker-Prager con pico, residual, tracción y dilatancia, con la relación
  entre sus parámetros y los de Mohr-Coulomb documentada con su fuente y mostrada al usuario.
- RF-3: EL SISTEMA integra Hoek-Brown generalizado con pico y residual, definido por sus parámetros
  o por GSI, mi y D, con dilatancia y las opciones de tracción que tengan fuente.
- RF-4: EL SISTEMA convierte, como preproceso, una envolvente no lineal (curva potencial, función
  tensión tangencial–normal) en un Hoek-Brown generalizado, y guarda la envolvente original, el
  rango usado y el resultado, para la trazabilidad (T07a §8; lo usa la 020).

**Cada ley**

- RF-5: Cada ley tiene su referencia en Python, su tangente (consistente, o la que dé la fuente),
  comprobada contra su derivada numérica, su prueba en un punto de Gauss contra una trayectoria de
  tensiones conocida (regla 8) y su identidad con Rust del orden de 1e-10 (ADR-0001).
- RF-6: CUANDO un punto plastifica, EL SISTEMA guarda el modo (corte, tracción o los dos) y si pasó a
  residual, para los resultados (005) y para el factor de resistencia de cada ley (T05).
- RF-7: SI los parámetros están fuera del dominio de la fuente (dilatancia mayor que el rozamiento,
  residual mayor que pico, parámetros de Hoek-Brown fuera de rango), ENTONCES EL SISTEMA lo rechaza
  con el material y el parámetro, sin corregirlo en silencio.

**Contrato común**

- RF-8: EL SISTEMA define un contrato único de ley: recibe la tensión, el incremento de deformación,
  las variables de estado y el contexto del punto; devuelve la tensión, la tangente, el estado y el
  modo de rotura; y sabe dar una copia con la resistencia reducida por un factor (para la 009).
- RF-9: El contrato trabaja en tracción positiva (regla 10) y no conoce unidades de usuario ni la
  interfaz (regla 11); las fórmulas de las fuentes que usan compresión positiva se reescriben en un
  solo sitio, con un test de signo por ley.

**Elementos y análisis**

- RF-10: CUANDO un caso con solución lo valide, EL SISTEMA admite las leyes plásticas con T3 y en
  axisimetría (levanta D6 de la spec 002); hasta entonces sigue rechazándolas con un error.
- RF-11: Cada opción (tipo de tracción, caída a residual, reducción de tracción tras rotura, ajuste
  de Drucker-Prager) tiene su test que mueve el número (regla 7) y su valor por defecto a la vista.

## Validación numérica

| Caso | Fuente científica (por comprobar) | Qué se compararía |
|---|---|---|
| `VER-STR-03`, hueco circular en Hoek-Brown frágil | Hoek y Brown, *Underground Excavations in Rock* (la ficha dice 1982; T07a, 1980) | Radio plástico y σr, σθ a lo largo de un radio |
| `VER-STR-30`, hueco circular en Mohr-Coulomb frágil-plástico | Reed (1986) | σr, σθ y ur a lo largo de un radio; radio plástico |
| `validacion/casos/002` (STR-02) | Salençon (1969) con la zona de arista | Regresión: el Mohr-Coulomb del contrato nuevo da los mismos números |
| Punto material, cada ley | Ensayos triaxiales de trayectoria conocida (resistencia en compresión y extensión) | Superficie, dirección del flujo, tangente frente a derivada numérica |
| Identidades entre leyes | — | Drucker-Prager ajustado a Mohr-Coulomb coincide en el meridiano del ajuste; GHB con GSI frente a los valores publicados de Hoek et al. (2002) |
| Mohr-Coulomb en axisimetría (si RF-10) | Salençon (1969) trae también la cavidad esférica, por comprobar | Cavidad esférica en Mohr-Coulomb |

STR-03 y STR-30 traen elementos infinitos en un contorno cercano (fase 3): se modelan con el contorno
fijo lejos y la identidad del dominio finito, como en la D3 bis de la spec 001. Con SSR, estas leyes
se validan en la 009: SLP-56 a 58 (Drucker-Prager; Pruska 2003 publica resultados de otros
programas, así que es una **comparación**) y SLP-60 (Hoek-Brown generalizado; ábacos de Li,
Merifield y Lyamin 2008, referencia **aproximada**).

## Fuentes por conseguir

- Hoek y Brown (1980a, 1980b), Hoek, Carranza-Torres y Corkum (2002), Hoek y Martin (2014) (opción
  de tracción), Reed (1986), Balmer (1952) (conversión), todas por comprobar.
- Owen y Hinton (1980) y Pietruszczak (2010), que citan los manuales de Mohr-Coulomb y
  Drucker-Prager; Simo y Hughes (1998), citado de forma incompleta.
- La integración de Mohr-Coulomb con superficie de tracción y la de Hoek-Brown: por localizar.
- Disponibles: de Souza Neto, Perić y Owen (2008), cap. 8 (Mohr-Coulomb ya usado; Drucker-Prager,
  sección por localizar); la tesis de Clausen (2007), que trata Hoek-Brown (contraste del retorno).

## Requisitos no funcionales

- Una ley nueva no debe hacer más lenta la integración de las demás: medida A/B antes de cerrar.
- El Mohr-Coulomb de Rust y el de Python se leen lado a lado, como en la spec 001 (criterio 4).

## Casos límite

- φ = 0° (Tresca) y ψ = 0°: el vértice no tiene retorno (spec 001); la superficie de tracción sí.
- La esquina entre la superficie de corte y la de tracción.
- Caída a residual dentro de un escalón; residual igual a pico (perfectamente plástico).
- Hoek-Brown con s = 0 (vértice en el origen) y a distinto de 0.5; D en el borde de su rango.
- Tensión hidrostática (factor de resistencia sin cociente definido, T05).
- Ley plástica pedida con T3 o en axisimetría sin caso que la valide (RF-10).

## Fuera de alcance

- Modelos de la fase 5 (Cam-Clay, endurecimiento, roca diaclasada, anisotropía), salvo el contrato.
- La reducción de resistencia (009) y los criterios de taludes de la 020.
- Juntas y sus leyes (fase 3).
- Comportamiento no drenado (fase 4).

## Criterios de finalización

- [ ] Todos los RF con su test en verde
- [ ] STR-03 y STR-30 dentro de la tolerancia fijada antes de medir, con su estudio de malla
- [ ] Cada ley probada en un punto de Gauss contra su fuente y con identidad Python–Rust
- [ ] Cada fórmula comprobada contra su fuente original (autor, año, ecuación)
- [ ] Todo texto nuevo con traducción española y toda acción nueva en un menú
- [ ] Changelog registrando qué se encontró

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Signo de la superficie de tracción**: los manuales de Mohr-Coulomb,
  Drucker-Prager y Hoek-Brown la escriben sobre σ3 con tracción positiva (T07a §4.8, §6.8, §7.8);
  con ese convenio la más traccionada es σ1. Hay que fijarlo contra la fuente original, no contra el
  manual. Liga con la **duda 14 de S06** (convenios de signo incoherentes entre manuales).
- [NECESITA ACLARACIÓN] **Resistencia a tracción por defecto**: P13 usó un valor muy alto para quitar
  el límite (Prandtl es sin él); P22, cero (el defecto del programa de referencia). Cambia el número
  (regla 12): ¿cuál, y dónde se muestra?
- [NECESITA ACLARACIÓN] **Opciones de rotura por tracción**: el programa de referencia lleva por
  defecto el corte a residual tras una rotura por tracción, y tiene otra opción que anula la tracción
  de Hoek-Brown (D01). ¿Se adoptan, con qué fuente y con qué defecto?
- [NECESITA ACLARACIÓN] **Frágil-plástico**: la caída instantánea a residual no tiene algoritmo en
  ningún manual; ¿en la integración del punto, entre escalones o entre iteraciones? Reed (1986) da la
  verificación, no el algoritmo.
- [NECESITA ACLARACIÓN] **Dilatancia en residual**: hay un solo ángulo (T07a §4.8). ¿Se limita al
  rozamiento residual? En Hoek-Brown, ¿qué exponente lleva el potencial en residual?
- [NECESITA ACLARACIÓN] **Ajuste de Drucker-Prager a Mohr-Coulomb**: el manual no lo da (T07a §6.8)
  y SLP-56 exige fijarlo. Opciones: cono por el meridiano de compresión, de extensión, inscrito o
  equivalente en deformación plana; solo con fuente.
- [NECESITA ACLARACIÓN] **Conversión a GHB**: cómo se fija la tensión máxima del rango (T07a §8.8,
  no documentado) y si vive aquí o en la 020, que es quien la usa.
- [NECESITA ACLARACIÓN] **Contrato**: ¿cuatro componentes (deformación plana y axisimetría) o seis
  pensando en 3D? ¿Tangente obligatoria, o una ley sin ella se rechaza (D7 descartó la rigidez
  inicial)? ¿Variables de estado de tamaño fijo por ley?
- [NECESITA ACLARACIÓN] **D6 de la spec 002**: ¿qué caso valida las leyes plásticas con T3 y en
  axisimetría? Ninguno de la fase 2 lo pide; ¿se deja el rechazo hasta que un caso lo pida?
- [NECESITA ACLARACIÓN] **Factor de resistencia (T05)** para Hoek-Brown generalizado: T05 solo lo da
  para el exponente 0.5. ¿Se extiende con fuente o se limita?
- [NECESITA ACLARACIÓN] **Duda 6 de S06**: la integración de tensiones no tiene manual; la fuente de
  cada retorno se decide al abrir la spec.
