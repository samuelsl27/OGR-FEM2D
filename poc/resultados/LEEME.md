# Resultados de `poc/benchmark.py`

Cada medida deja un `.json` (todo, con el estado del equipo) y un `.txt` (el resumen). Desde el
2026-10-27 el benchmark registra la carga de los demás programas antes y después de cada bloque y la
proporción CPU/reloj de cada medida, y dice si la medida es **válida**; con el equipo cargado se
niega a medir salvo con `--force` (regla del propietario, 2026-10-27).

| Archivo | Validez |
|---|---|
| `benchmark_2026-10-27_NO_VALIDA_equipo_cargado.*` | **No válida.** Se midió antes de registrar el estado del equipo; al comprobarlo justo después, los demás programas (Chrome, sobre todo) usaban entre el 36 % y el 99 % de la CPU, quedaban 2 GB libres de 16 y un bucle de prueba solo tenía su núcleo el 93 % del tiempo. NumPy / Rust = 9.5 (control 8.6) aquí, y 10.4–12.3 en otra ejecución del mismo código: la diferencia es del equipo, no del código |
