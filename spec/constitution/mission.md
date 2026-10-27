# Misión

> **Aprobada por el propietario (2026-10-27).** Primera fase del flujo SDD: constitución.

## Qué construimos

**OGR FEM2D** es el programa de elementos finitos 2D de la suite OpenGeoRock: análisis
tensión-deformación de excavaciones, taludes, cimentaciones y obras subterráneas, con fases de
construcción, reducción de resistencia al corte, agua, sostenimiento y juntas. Comparte con OGR Slip2D
la interfaz, el formato de proyecto, el idioma y las reglas de trabajo.

Más adelante, la misma aplicación incorporará otros métodos numéricos: diferencias finitas
explícitas, elementos discretos de partículas y bloques.

## Para quién

- **Ingenieros geotécnicos** que necesitan un programa profesional sin licencia y que puedan auditar:
  cuando un factor de reducción sale 1.32, se puede leer por qué.
- **Investigadores** que necesitan modificar el método o añadir un modelo constitutivo.
- **Docentes y estudiantes**, para quienes el código es material didáctico.

## Principio rector

> Un resultado que no se puede comprobar no vale nada, por bonito que sea el gráfico que lo acompaña.

Todo método se publica con el caso de referencia contra el que se validó, y la suite se valida
contra soluciones analíticas, casos publicados e identidades, no contra sus propias salidas ni contra
lo que otro programa calcule cuando lo reproducimos nosotros. Un resultado numéricamente igual al
esperado sin una explicación física, matemática y geotécnica no se da por válido.

## Lo que NO somos

- No somos un clon de ningún producto comercial. Nos inspiramos en su interfaz porque es la que los
  ingenieros conocen, pero el código no contiene ninguna referencia a esos productos.
- No somos una herramienta de decisión automática. **El programa calcula; quien firma es una persona.**
