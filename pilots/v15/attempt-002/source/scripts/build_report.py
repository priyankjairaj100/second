"""Build the research note using a local LaTeX installation; no experiments."""
from pathlib import Path
import subprocess


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "output" / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    command = [
        "pdflatex", "-interaction=nonstopmode", "-halt-on-error",
        f"-output-directory={out}",
        str(root / "reports" / "theory_algorithm_revision.tex"),
    ]
    for _ in range(2):
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        (out / "build_stdout.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit(f"LaTeX failed; inspect {out / 'build_stdout.log'}")
    print(out / "theory_algorithm_revision.pdf")


if __name__ == "__main__":
    main()
