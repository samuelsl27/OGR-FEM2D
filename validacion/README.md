# Casos de validación

**Esto es lo más valioso del repositorio.** Un motor de cálculo no vale por sus funciones, sino por
los casos cuyo resultado correcto se conoce y reproduce.

## Estructura de un caso

```
validacion/casos/NNN-nombre-corto/
├── caso.md          ← qué es, de dónde sale el valor esperado (fuente científica), ficha de origen
├── modelo.ogr       ← el modelo, listo para abrir
└── esperado.json    ← valores de referencia y tolerancia, legibles por el test
```

## `esperado.json`

```json
{
  "id": "001-kirsch",
  "ficha": "VER-STR-01",
  "fuente": "Kirsch (1898), en Jaeger y Cook (1976), Fundamentals of Rock Mechanics, 3.ª ed.",
  "tipo_referencia": "analitica",
  "tolerancia_relativa": 0.01,
  "comparaciones": [
    {"magnitud": "sigma_theta", "donde": {"tipo": "contorno_excavacion"}, "valor": 60.0, "unidad": "MPa"}
  ],
  "notas": "Malla y orden de elemento con los que se fija la tolerancia."
}
```

`ficha` apunta a la ficha de trabajo (fuera del repositorio) de la que sale el caso. `tipo_referencia`:
`analitica`, `publicada`, `identidad` o `comparacion` (otro programa; **una comparación no es una
validación**).

Lo que calculamos nosotros al reproducir un caso en otro programa **nunca** es un valor esperado:
sirve para entender cómo se comporta ese programa. Un valor publicado en su manual sí se puede usar,
citando la fuente; si es el resultado de ese programa, el caso es `comparacion`, y si es una solución
analítica, se cita por su fuente científica original.

## Qué va aquí y qué no

| Va aquí (se versiona) | Se queda fuera (no se versiona) |
|---|---|
| El modelo `.ogr` propio | Archivos de proyecto de programas comerciales |
| El valor esperado y **su fuente científica** | Capturas o informes de otros programas |
| El test que lo comprueba | Los PDF de manuales de terceros |

La distinción es de copyright: el `.ogr` es propio y el número esperado es un hecho citable; el
archivo nativo y el manual de otro programa son material de terceros.

## Reglas

- **La tolerancia va en el caso, no en el test**, porque depende de la calidad de la fuente y de la
  malla con que se fija.
- Un test recorre todos los casos automáticamente.
- **Si un caso falla, no se toca el caso**: el fallo está en el código o en el propio valor de
  referencia, y averiguar cuál es el trabajo que hace útil la validación.
