# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The Mohr-Coulomb of the engine in Python and in Rust, side by side, for the
owner to judge whether he reads the Rust one at least as well as the Python
one (spec 001, task T16; ADR-0001, criterion 4).

    .venv/Scripts/python poc/lado_a_lado.py --out mohr_coulomb.html

The page is built from the source files as they are, piece by piece (the
Python with ``ast``, the Rust by its braces, each with its documentation
comments), so it cannot drift from the code: rebuild it whenever either file
changes. The notes between the pieces say only what differs between the two
languages.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import argparse
import ast
import html
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "ogr_fem2d" / "engine" / "reference" / "mohr_coulomb.py"
RS = ROOT / "rust" / "src" / "mohr_coulomb.rs"

#: (title, Python pieces, Rust pieces, note). A piece is a top-level name;
#: "__doc__" is the module documentation.
PAIRS = [
    ("Cabecera: fuentes y alcance", ["__doc__"], ["__doc__"],
     "El mismo texto: la fuente (de Souza Neto et al. 2008, §8.2), las ecuaciones y la errata del "
     "Box 8.6. En Python es la cadena de documentación del módulo; en Rust, las líneas que "
     "empiezan por <code>//!</code>."),
    ("La tolerancia", ["TOLERANCE"], ["TOLERANCE"],
     "Rust declara el tipo (<code>f64</code>, el <code>float</code> de Python) y "
     "<code>pub</code> la hace visible fuera del módulo. Los comentarios <code>///</code> son la "
     "documentación del elemento que sigue, como el <code>#:</code> de Python."),
    ("El error del vértice con ψ = 0", ["ReturnMappingError"], ["ReturnMappingError"],
     "Rust no tiene excepciones. En vez de lanzar un error, la función devuelve un "
     "<code>Result</code>: <code>Ok(valor)</code> o <code>Err(error)</code>, y este tipo vacío "
     "es el error. Lo veréis en <code>return_principal</code>."),
    ("El material", ["MohrCoulomb"], ["MohrCoulomb", "impl MohrCoulomb"],
     "La <code>@dataclass(frozen=True)</code> es un <code>struct</code>; "
     "<code>#[derive(Clone, Copy, Debug)]</code> le da copia barata e impresión. Las "
     "<code>@property</code> son métodos en un bloque <code>impl</code>, y se llaman con "
     "paréntesis: <code>m.shear_modulus()</code>."),
    ("La región y el resultado de una actualización", ["Update"], ["Region", "Update"],
     "Python nombra la región con una cadena (<code>\"plane\"</code>, <code>\"right edge\"</code>…); "
     "Rust con un <code>enum</code> de cinco valores, así que una región mal escrita no compila. "
     "El <code>Update</code> de Python lleva además los multiplicadores <code>dgamma</code>, que "
     "solo usan los tests; el de Rust no."),
    ("Tensiones principales en el plano", ["principal_in_plane"], ["principal_in_plane"],
     "Lo mismo, con la sintaxis de método de Rust para las funciones matemáticas: "
     "<code>a.hypot(b)</code> es <code>math.hypot(a, b)</code> y <code>y.atan2(x)</code> es "
     "<code>math.atan2(y, x)</code>. <code>-&gt; (f64, f64, f64)</code> declara que devuelve "
     "tres números."),
    ("La función de fluencia", ["yield_function"], ["yield_function"],
     "<code>&amp;MohrCoulomb</code> pasa el material por referencia (sin copiarlo), que es lo que "
     "Python hace siempre. <code>m.phi.sin()</code> es <code>math.sin(m.phi)</code>."),
    ("El término 2G N_dev + K tr N", ["_stress_change"], ["stress_change"],
     "La comprensión de tupla de Python es aquí un bucle <code>for j in 0..3</code> (el "
     "<code>range(3)</code> de Python) que rellena un array de tamaño fijo <code>[f64; 3]</code>. "
     "<code>let mut</code> declara una variable que se va a modificar; sin <code>mut</code>, Rust "
     "no deja cambiarla."),
    ("Los vectores de flujo N1, N6 y N2", ["_flows"], ["flows"],
     "Python los devuelve en un diccionario por nombre; Rust en una tupla con ese orden, que se "
     "desempaqueta al usarla: <code>let (n1, n6, n2) = flows(m);</code>."),
    ("El orden de las tensiones", ["_in_order"], ["in_order", "dot"],
     "Lo mismo. Rust añade <code>dot</code>, el producto escalar que Python escribe en línea "
     "dentro de <code>principal_derivatives</code>."),
    ("El retorno: plano, arista y vértice", ["return_principal"], ["return_principal"],
     "Los mismos pasos en el mismo orden (Box 8.4). Las diferencias: devuelve "
     "<code>Ok((tensiones, región))</code> o <code>Err(ReturnMappingError)</code> en lugar de "
     "lanzar; <code>let (db, phi_b, row_a, row_b);</code> declara cuatro variables que reciben su "
     "valor en una de las dos ramas del <code>if</code>; y <code>let [s1, s2, s3] = trial;</code> "
     "desempaqueta el array como en Python. Python devuelve también los multiplicadores."),
    ("Derivadas de las tensiones principales (P)", ["principal_derivatives"],
     ["principal_derivatives"],
     "La cadena de <code>if</code> de Python sobre la región es un <code>match</code> en Rust, "
     "que obliga a tratar las cinco regiones: si falta una, no compila. Las comprensiones de "
     "listas de Python son bucles que restan sobre la identidad."),
    ("La tangente consistente", ["_tangent"], ["tangent"],
     "Las funciones internas de Python (<code>def de(i, j)</code>) son cierres en Rust: "
     "<code>let de = |i, j| …</code>. <code>(0..3).map(|q| …).sum::&lt;f64&gt;()</code> es "
     "<code>sum(… for q in range(3))</code>. Python recibe los nombres <code>\"hi\"</code>, "
     "<code>\"lo\"</code> de las posiciones; Rust, las posiciones <code>h</code> y <code>l</code> "
     "ya buscadas."),
    ("La actualización completa (Box 8.4)", ["update"], ["update"],
     "El <code>?</code> tras <code>return_principal(m, trial)?</code> devuelve el error hacia "
     "arriba si lo hay, como una excepción que nadie captura. La ordenación es estable en los "
     "dos (<code>sort_by</code> y <code>sort(reverse=True)</code> conservan el orden de los "
     "empates); Rust nombra hi, lo y zz con los índices 0, 1 y 2 en vez de cadenas. Python "
     "calcula la tangente solo si se pide; Rust siempre."),
]

GLOSSARY = [
    ("let x = 1.0;", "x = 1.0", "Declara una variable; no se puede cambiar después."),
    ("let mut x = 1.0;", "x = 1.0", "Declara una variable que sí se puede cambiar."),
    ("f64, usize, bool", "float, int, bool", "Tipos: real de doble precisión, índice, lógico."),
    ("[f64; 3]", "tuple de 3 float", "Array de tamaño fijo, aquí tres números."),
    ("[[f64; 3]; 3]", "lista de listas 3 × 3", "Matriz de tamaño fijo."),
    ("&m", "m", "Pasa una referencia, sin copiar: lo que Python hace siempre."),
    ("fn f(a: f64) -> f64 { … }", "def f(a: float) -> float: …", "Una función; la última expresión sin «;» es el valor que devuelve."),
    ("for j in 0..3 { … }", "for j in range(3): …", "Bucle."),
    ("|i, j| expresión", "lambda i, j: expresión", "Función anónima (cierre)."),
    ("x.sin(), a.max(b), x.abs()", "math.sin(x), max(a, b), abs(x)", "Funciones matemáticas como métodos."),
    ("Result, Ok(v), Err(e)", "return v / raise e", "Resultado o error, sin excepciones."),
    ("f(x)?", "f(x)", "Si f devuelve un error, lo devuelve hacia arriba."),
    ("match r { A => …, B => … }", "if r == A: … elif r == B: …", "Elige por casos; obliga a cubrirlos todos."),
    ("struct, impl, enum", "@dataclass, métodos, cadenas", "Datos, sus métodos y un conjunto cerrado de valores."),
    ("pub", "(sin _ delante)", "Visible fuera del módulo."),
]


def python_pieces(source: str) -> dict:
    tree = ast.parse(source)
    lines = source.splitlines()
    out = {}
    doc = tree.body[0]
    out["__doc__"] = (doc.lineno, doc.end_lineno)
    for node in tree.body:
        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        while start > 1 and lines[start - 2].lstrip().startswith("#:"):
            start -= 1                                   # its documentation comments
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            out[node.name] = (start, node.end_lineno)
        elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            out[node.targets[0].id] = (start, node.end_lineno)
    return out


ITEM = re.compile(r"^(?:pub )?(?:fn|struct|enum|const) (\w+)|^impl (\w+)")


def rust_pieces(source: str) -> dict:
    lines = source.splitlines()
    out = {}
    first_doc = next(i for i, l in enumerate(lines) if l.startswith("//!"))
    last_doc = first_doc
    while last_doc + 1 < len(lines) and lines[last_doc + 1].startswith("//!"):
        last_doc += 1
    out["__doc__"] = (first_doc + 1, last_doc + 1)
    for i, line in enumerate(lines):
        m = ITEM.match(line)
        if not m:
            continue
        name = m.group(1) or f"impl {m.group(2)}"
        start = i
        while start > 0 and lines[start - 1].startswith(("///", "#[")):
            start -= 1
        end, depth, opened = i, 0, False
        for j in range(i, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            opened = opened or "{" in lines[j]
            if (opened and depth == 0) or (not opened and lines[j].rstrip().endswith(";")):
                end = j
                break
        out[name] = (start + 1, end + 1)
    return out


def _block(lines, span, language, file_label):
    start, end = span
    code = "\n".join(lines[start - 1:end])
    return (f'<figure class="pane {language}"><figcaption><span class="lang">'
            f'{"Python" if language == "python" else "Rust"}</span>'
            f'<span class="where">{file_label}, líneas {start}–{end}</span></figcaption>'
            f'<pre><code class="language-{language}">{html.escape(code)}</code></pre></figure>')


def build(out: Path) -> None:
    py_src, rs_src = PY.read_text(encoding="utf-8"), RS.read_text(encoding="utf-8")
    py_lines, rs_lines = py_src.splitlines(), rs_src.splitlines()
    py, rs = python_pieces(py_src), rust_pieces(rs_src)
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = "?"
    sections, py_total, rs_total = [], 0, 0
    for k, (title, py_names, rs_names, note) in enumerate(PAIRS, 1):
        left = "".join(_block(py_lines, py[n], "python", "mohr_coulomb.py") for n in py_names)
        right = "".join(_block(rs_lines, rs[n], "rust", "mohr_coulomb.rs") for n in rs_names)
        n_py = sum(py[n][1] - py[n][0] + 1 for n in py_names)
        n_rs = sum(rs[n][1] - rs[n][0] + 1 for n in rs_names)
        py_total += n_py
        rs_total += n_rs
        anchor = f"p{k}"
        sections.append(
            f'<section class="pair" id="{anchor}"><header class="pair-head">'
            f'<h2><a href="#{anchor}">{html.escape(title)}</a></h2>'
            f'<p class="count">{n_py} líneas en Python · {n_rs} en Rust</p></header>'
            f'<p class="note">{note}</p><div class="panes">{left}{right}</div></section>')
    toc = "".join(f'<li><a href="#p{k}">{html.escape(t)}</a></li>'
                  for k, (t, _a, _b, _c) in enumerate(PAIRS, 1))
    glossary = "".join(f"<tr><td><code>{html.escape(r)}</code></td><td><code>{html.escape(p)}</code>"
                       f"</td><td>{html.escape(m)}</td></tr>" for r, p, m in GLOSSARY)
    page = TEMPLATE.format(commit=html.escape(commit), toc=toc, glossary=glossary,
                           sections="".join(sections), py_total=py_total, rs_total=rs_total)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")


TEMPLATE = """<title>Mohr-Coulomb lado a lado</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Sans+Condensed:wght@600&display=swap">
<style>
/* Two columns of source under one note per pair: a reading desk for code. */
:root {{
  --paper: #f6f7f9; --ink: #1d2430; --muted: #5b6474; --rule: #d9dee6;
  --pane: #ffffff; --py: #2f5f9e; --rs: #b4532a; --accent: #2f5f9e;
  --k: #7a3e9d; --s: #2d7a46; --n: #a35a00; --c: #6b7686; --t: #1f5fbf;
  --f-head: "IBM Plex Sans Condensed", "Arial Narrow", sans-serif;
  --f-body: "IBM Plex Sans", "Segoe UI", Roboto, sans-serif;
  --f-code: "IBM Plex Mono", Consolas, "Courier New", monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --paper: #14181f; --ink: #e3e7ee; --muted: #9aa4b4; --rule: #2a313d;
  --pane: #1b2029; --py: #7fa8e0; --rs: #e48a62; --accent: #7fa8e0;
  --k: #c792ea; --s: #8fd18f; --n: #f0b45e; --c: #8a94a6; --t: #82aaff; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --paper: #14181f; --ink: #e3e7ee; --muted: #9aa4b4; --rule: #2a313d;
  --pane: #1b2029; --py: #7fa8e0; --rs: #e48a62; --accent: #7fa8e0;
  --k: #c792ea; --s: #8fd18f; --n: #f0b45e; --c: #8a94a6; --t: #82aaff; color-scheme: dark }}
body {{ background: var(--paper); color: var(--ink); font: 15px/1.55 var(--f-body);
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 28px 48px }}
main {{ max-width: 1500px; margin: 0 auto; display: grid; gap: 40px }}
h1, h2 {{ font-family: var(--f-head); font-weight: 600; text-wrap: balance; margin: 0 }}
h1 {{ font-size: 2rem; line-height: 1.15 }}
h2 {{ font-size: 1.3rem }}
h2 a {{ color: inherit; text-decoration: none }}
h2 a:hover, h2 a:focus-visible {{ text-decoration: underline }}
a {{ color: var(--accent) }}
a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px }}
.intro {{ display: grid; gap: 14px; max-width: 72ch }}
.intro p {{ margin: 0 }}
.meta {{ color: var(--muted); font-size: .9rem }}
.question {{ border-left: 3px solid var(--rs); padding: 4px 0 4px 14px }}
.twin {{ display: flex; flex-wrap: wrap; gap: 18px; font-size: .9rem; color: var(--muted) }}
.twin b {{ font-weight: 600 }}
.twin .py b {{ color: var(--py) }} .twin .rs b {{ color: var(--rs) }}
.columns {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr); gap: 32px }}
.columns > * {{ min-width: 0 }}
.label {{ font-family: var(--f-head); text-transform: uppercase; letter-spacing: .06em;
  font-size: .78rem; color: var(--muted); margin: 0 0 8px }}
ol.toc {{ margin: 0; padding-left: 1.4em; columns: 2; column-gap: 28px }}
ol.toc li {{ break-inside: avoid; padding: 1px 0 }}
.glossary {{ overflow-x: auto }}
table {{ border-collapse: collapse; width: 100%; font-size: .88rem }}
td {{ border-top: 1px solid var(--rule); padding: 6px 10px 6px 0; vertical-align: top }}
td code {{ white-space: nowrap }}
code {{ font-family: var(--f-code); font-size: .92em }}
.pair {{ display: grid; gap: 10px; border-top: 1px solid var(--rule); padding-top: 22px }}
.pair-head {{ display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 18px }}
.count {{ margin: 0; color: var(--muted); font-size: .85rem; font-variant-numeric: tabular-nums }}
.note {{ margin: 0; max-width: 95ch }}
.note code {{ background: var(--pane); border: 1px solid var(--rule); border-radius: 3px; padding: 0 3px }}
.panes {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; align-items: start }}
.panes > * {{ min-width: 0 }}
.pane {{ margin: 0; background: var(--pane); border: 1px solid var(--rule); border-radius: 6px }}
.pane + .pane.python, .pane.python + .pane.python {{ margin-top: 0 }}
figcaption {{ display: flex; justify-content: space-between; gap: 10px; padding: 7px 12px;
  border-bottom: 1px solid var(--rule); font-size: .8rem; color: var(--muted) }}
.lang {{ font-family: var(--f-head); font-weight: 600; letter-spacing: .04em; text-transform: uppercase }}
.python .lang {{ color: var(--py) }} .rust .lang {{ color: var(--rs) }}
.python {{ border-top: 3px solid var(--py) }} .rust {{ border-top: 3px solid var(--rs) }}
pre {{ margin: 0; padding: 12px; overflow-x: auto; font: 13px/1.5 var(--f-code); tab-size: 4 }}
.panes .python ~ .rust {{ grid-column: 2 }}
.hljs-keyword, .hljs-meta .hljs-keyword {{ color: var(--k) }}
.hljs-string, .hljs-char {{ color: var(--s) }}
.hljs-number, .hljs-literal {{ color: var(--n) }}
.hljs-comment, .hljs-doctag, .hljs-quote {{ color: var(--c); font-style: italic }}
.hljs-title, .hljs-title.function_, .hljs-type, .hljs-built_in, .hljs-title.class_ {{ color: var(--t) }}
.hljs-meta {{ color: var(--muted) }}
@media (max-width: 900px) {{
  .columns {{ grid-template-columns: minmax(0, 1fr) }}
  .panes {{ grid-template-columns: minmax(0, 1fr) }}
  .panes .python ~ .rust {{ grid-column: auto }}
  ol.toc {{ columns: 1 }}
}}
</style>
<main>
  <header class="intro">
    <h1>El Mohr-Coulomb del motor, en Python y en Rust</h1>
    <p>La misma ley, función a función: a la izquierda la implementación de referencia en Python, el
    oráculo de los tests; a la derecha la variante compilada en Rust, que coincide con ella a 1e-15. Las
    dos están escritas con los mismos nombres y la misma estructura, a partir de de Souza Neto, Perić y
    Owen (2008), §8.2.</p>
    <p class="question"><b>La pregunta (criterio 4 del ADR-0001):</b> ¿entiendes el Mohr-Coulomb en Rust
    al menos tan bien como en Python? Si la respuesta es no, la alternativa que prevé el ADR es C++ con
    nanobind.</p>
    <div class="twin">
      <span class="py"><b>Python</b> ogr_fem2d/engine/reference/mohr_coulomb.py · {py_total} líneas mostradas</span>
      <span class="rs"><b>Rust</b> rust/src/mohr_coulomb.rs · {rs_total} líneas mostradas</span>
    </div>
    <p class="meta">Generado desde el código del commit {commit} con poc/lado_a_lado.py; sin
    transcripciones a mano.</p>
  </header>
  <div class="columns">
    <nav aria-label="Índice">
      <p class="label">Los catorce pares</p>
      <ol class="toc">{toc}</ol>
    </nav>
    <section aria-label="Cómo leer este Rust">
      <p class="label">Cómo leer este Rust</p>
      <div class="glossary"><table><tbody>{glossary}</tbody></table></div>
    </section>
  </div>
  {sections}
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script>
  try {{ hljs.highlightAll(); }} catch (e) {{ /* plain text is readable too */ }}
</script>
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=ROOT / "build" / "lado_a_lado" / "mohr_coulomb.html")
    args = parser.parse_args(argv)
    build(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
