# Contribuir a OGR FEM2D

Gracias por querer ayudar. *OpenGeoRock* (u *OGR Suite*) es el paraguas de los programas de la
suite; **OGR FEM2D** es el de elementos finitos, y es lo que contiene este repositorio.

Licencia: **AGPL-3.0-or-later**. Las contribuciones se aceptan en los términos de
[`CLA.md`](CLA.md), el mismo acuerdo que en OGR Slip2D: léelo antes de tu primera *pull request*.
Existe para que la versión libre no pueda desaparecer nunca.

> **Estado:** todavía no hay código. Las instrucciones de instalación y de tests se añadirán con la
> primera versión; mientras tanto, lo que se puede revisar es la constitución (`spec/constitution/`),
> las decisiones (`docs/decisiones/`) y la estructura de validación (`validacion/`).

## Qué debe cumplir un cambio

Las reglas están en [`AGENTS.md`](AGENTS.md), que es la fuente única y vale igual para personas y
para agentes de IA. Las de más peso:

- El trabajo numérico se valida contra algo **externo** (solución analítica, caso publicado o
  identidad), nunca contra lo que el código imprime hoy ni contra lo que otro programa calcula.
- Cada ley constitutiva se prueba en un punto de Gauss contra su fuente, y su versión en Rust contra
  la de referencia en Python.
- Las anomalías se reportan **antes** de corregirlas, con la evidencia.
- Ningún ajuste puede no hacer nada, y un valor por defecto que cambia el resultado se muestra junto
  al resultado.

## Commits y ramas

- Rama desde `main` con el nombre `dev/descripcion-corta`.
- Firma los commits con el *Developer Certificate of Origin*: `git commit -s -m "..."`.
- El asunto dice qué cambió y por qué.
- Los cambios sin relación van en commits separados; un reformateo nunca viaja con un cambio de
  comportamiento.

## Para aceptar el CLA

Añade una línea a [`CONTRIBUTORS.md`](CONTRIBUTORS.md) en la misma *pull request*:

```
- Tu nombre <correo o usuario de GitHub> — I agree to the CLA in CLA.md
```

## Informar de un problema

En todo lo numérico, adjunta el modelo y el valor obtenido junto al esperado, con su fuente. Un
factor de seguridad sin referencia no se puede investigar.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
