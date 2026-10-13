"""Fill README.template.md with the numbers in report/numbers.tex -> README.md."""

import re

from _common import ROOT

macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", (ROOT / "report" / "numbers.tex").read_text()))


def sub(m):
    key = m.group(1)
    if key not in macros:
        raise KeyError(f"README uses unknown number {key}")
    return macros[key].replace("{,}", ",").replace("\\%", "%")


for src, dst in (("scripts/templates/README.md.in", "README.md"),
                 ("scripts/templates/VIDEO_SCRIPT.md.in", "presentation/VIDEO_SCRIPT.md")):
    text = (ROOT / src).read_text()
    (ROOT / dst).write_text(re.sub(r"\{\{(\w+)\}\}", sub, text))
    print(dst, "written")
