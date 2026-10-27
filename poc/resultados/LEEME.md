# Resultados de `poc/benchmark.py`

Cada medida deja un `.json` (todo, con el estado del equipo) y un `.txt` (el resumen). Desde el
2026-10-27 el benchmark registra la carga de los demás programas antes y después de cada bloque y la
proporción CPU/reloj de cada medida, y dice si la medida es **válida**; con el equipo cargado se
niega a medir salvo con `--force` (regla del propietario, 2026-10-27).

| Archivo | Validez |
|---|---|
| `benchmark_2026-10-27_NO_VALIDA_equipo_cargado.*` | **No válida.** Se midió antes de registrar el estado del equipo; al comprobarlo justo después, los demás programas (Chrome, sobre todo) usaban entre el 36 % y el 99 % de la CPU, quedaban 2 GB libres de 16 y un bucle de prueba solo tenía su núcleo el 93 % del tiempo. NumPy / Rust = 9.5 (control 8.6) aquí, y 10.4–12.3 en otra ejecución del mismo código: la diferencia es del equipo, no del código |
| (sin archivo) 2026-10-27, hacia las 19:10 | **No válida por la regla del 10 %** (Chrome cerrado; los demás programas, que no se pueden cerrar —TextInputHost, la aplicación de Claude, VS Code y ráfagas de procesos `pythonw`—, usaban del 19 % al 29 %), pero limpia dentro del proceso: proporción CPU/reloj 0.96–0.99 en la integración y rondas que difieren un 2–4 %. **NumPy / Rust = 9.6 (control 9.6).** Su JSON lo sobrescribió la medida siguiente (el nombre llevaba solo la fecha; ahora lleva la hora) |
| `benchmark_2026-10-27_192230.*` | **No válida**, mismas condiciones (19–23 %); la primera ronda de Rust perdió su núcleo a ratos (proporción 0.93): NumPy / Rust = 8.6 en esa ronda y **10.9 en el control**, cuyas medidas tienen proporción 0.98–1.00. La etiqueta «1.07… rust» del veredicto original era un error de texto (ya corregido en el código y aquí) |
| `revision_variantes_AB_2026-10-27.txt` | **A/B de la revisión** de las dos variantes (las de antes, del commit f1ab573, y las revisadas, en el mismo proceso), con la suite de otra sesión corriendo de fondo (37–39 %, constante) y limpia dentro del proceso: proporción CPU/reloj 0.97–1.01, rondas a ~3 %. La revisión hace a Rust ×1.32–1.37 y a NumPy ×1.35–1.36 más rápidos; **NumPy / Rust = 9.5–9.9 antes y 9.3–9.9 después**. Una primera ejecución del mismo A/B, con la carga subiendo al 97 % al empezar, no vale y no se guardó |
| `benchmark_2026-10-27_195205.*` | **Medida oficial con las variantes revisadas.** No válida por la regla del 10 % (fondo constante del 32–34 %), con proporción CPU/reloj 0.97–1.00 en todo. **NumPy / Rust = 10.2 (control 9.2)** en la integración; en la llamada por iteración sobre la malla del caso 002, 82–88 ms frente a 5.1–5.3 ms (unas 16 veces) |
