# Tareas — Spec 002, motor elástico general

Pequeñas y verificables, ordenadas por dependencia. Al terminar cada una: este archivo y el
changelog al día, la suite entera en verde, commit y push.

## Antes de programar

- [x] T0. El propietario responde D1–D7 de `spec.md` y aprueba el plan — Hecho cuando: las
      respuestas están anotadas en `spec.md`. (Hecho el 2026-10-27: las siete, como se propusieron.)
- [x] T1. Fuentes que faltan: el T3 (Z&T cap. 4), los términos de fuerzas de volumen, de superficie
      y la carga puntual de la (2.13) de Z&T, y el desplazamiento de Flamant en T&G §33 — Hecho
      cuando: la tabla «Formulación» de `plan.md` no tiene ningún «por comprobar». (Hecho ya: Michell,
      Flamant, Lamé esférico, axisimetría §5.2, tabla 9.2, JCZ §13.2; soluciones cerradas en
      `comprobaciones/`.) (Hecho el 2026-10-27: T3, Z&T §4.2, ecs. (4.5)–(4.10); cargas, Z&T
      ecs. (2.10)–(2.15) y §5.2.6–5.2.8; desplazamiento de Flamant, T&G §33, ecs. (g)–(72).
      Hallazgos: la carga puntual dentro de un elemento no está impresa y se deriva del trabajo
      virtual de la (2.10); la (5.13) y el §5.2.6 confirman D2; en STR-04 no hay desplazamiento de
      referencia; y en axisimetría con T3 la regla del centroide no integra exactos ni Bᵀσ₀·r ni
      Nᵀb·r (grado 2), así que la identidad gravitatoria solo es exacta con T6 o en deformación
      plana: con T3 axisimétrico se espera un desplazamiento que baje con h², no nulo (se
      comprobará en la T8). **Anomalía en D3, pendiente del propietario**: en axisimetría el
      equilibrio radial lleva (σr − σθ)/r (T&G §116, ec. 177), y un campo gravitatorio con
      K ≠ Kz, o uno constante con σr ≠ σθ o τrz ≠ 0, no está en equilibrio.)

## Entrada y elementos (referencia)

- [ ] T2. `model.py` y `docs/motor/entrada.md`: esquema y `validate()` — RF-1, RF-2 — Hecho cuando:
      cada regla tiene su test con una entrada que la incumple.
- [ ] T3. `quadrature.py` con las reglas lineal, cuadrática y quíntica — Hecho cuando: cada una
      integra exactos los monomios hasta su grado y falla en el siguiente.
- [ ] T4. T6 generalizado y T3 en deformación plana — RF-3 — Hecho cuando: parcela, sólido rígido y
      tensión inicial uniforme pasan con los dos, y los casos 001 y 002 dan los mismos números.
- [ ] T5. Axisimetría de T3 y T6 — RF-3, RF-4 — Hecho cuando: parcela axisimétrica (u = a·r,
      v = b·z), sólido rígido (solo traslación en z), u_r constante con tensión, ningún punto sobre
      el eje.

## Contorno, cargas, tensión inicial y fases (referencia)

- [ ] T6. Restricciones, desplazamientos impuestos en totales y reacciones — RF-5 — Hecho cuando:
      equilibrio global de reacciones en cada fase.
- [ ] T7. Cargas nodales, puntuales, repartidas y peso propio — RF-6 — Hecho cuando: resultante y
      momento de cada carga, y peso propio, contra su valor cerrado.
- [ ] T8. Preproceso de tensión inicial, constante y gravitatoria — RF-7 — Hecho cuando: campo
      gravitatorio más peso propio con estratos horizontales da desplazamiento nulo.
- [ ] T9. Fases y excavación por desactivación — RF-8, RF-9 — Hecho cuando: desactivar el anillo
      interior da lo mismo que la malla sin él, y una fase sin cambios da incremento nulo.

## Casos

- [ ] T10. Mallas estructuradas de prueba (rectángulo graduado T3/T6; cuarto de corona T3) —
      Hecho cuando: área exacta y ningún elemento degenerado.
- [ ] T11. Caso 003, STR-09 en axisimetría, con su estudio de convergencia y la identidad de la
      esfera finita — Hecho cuando: dentro de la tolerancia de D4 con la malla que la fija.
- [ ] T12. Caso 004, STR-04, con los estudios de convergencia y de dominio y la identidad del
      semiespacio truncado — Hecho cuando: dentro de la tolerancia de D4 con la malla y el dominio
      que la fijan.

## Rust y distribución

- [ ] T13. T3 y axisimetría en Rust; Mohr-Coulomb rechazado fuera de lo validado (D6) — RF-10,
      RF-11 — Hecho cuando: referencia = Rust a ~1e-10 en elemento, malla y casos.
- [ ] T14. CI de ruedas y congelado con los casos 003 y 004 — Hecho cuando: CI verde en las tres
      plataformas y el ejecutable resuelve los cuatro casos.
- [ ] T15. Cierre: `CHANGELOG_v0.0.2.md`, fichas STR-04 y STR-09 («Seguimiento») y criterios de
      finalización de `spec.md` marcados.
