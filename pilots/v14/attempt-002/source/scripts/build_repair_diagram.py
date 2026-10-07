"""Build the deterministic method figure; no dataset or experiment is read.

The SVG is the canonical vector source. Optional Inkscape conversion produces
an outlined-font PDF and a review PNG. SOURCE_DATE_EPOCH fixes converter time.
"""
from pathlib import Path
from html import escape
import argparse
import os
import shutil
import subprocess
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / 'output/figures/sequential_repair.svg'
PDF = ROOT / 'output/figures/sequential_repair.pdf'
PREVIEW = ROOT / 'tmp/figures/sequential_repair.png'


def text(x, y, value, size=22, weight=400, color='#243244', anchor='middle'):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}">{escape(value)}</text>')


def node(x, y, width, height, title, lines, fill='#ffffff', stroke='#8e9baa', title_size=23, body_size=20):
    result = [f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
              f'rx="13" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
              text(x + width / 2, y + 36, title, title_size, 700)]
    result.extend(text(x + width / 2, y + 68 + 29 * i, value, body_size) for i, value in enumerate(lines))
    return '\n'.join(result)


def arrow(path, color='#42556c', width=3, marker='arrow', dashed=False):
    dash = ' stroke-dasharray="7 6"' if dashed else ''
    return (f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round" marker-end="url(#{marker})"{dash}/>')


def make_svg():
    parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1050" viewBox="0 0 1400 1050" role="img" aria-labelledby="title desc">
<title id="title">Exact sequential repair with certified aggregate bounds and retained replay</title>
<desc id="desc">Deletion regenerates and subtracts intrinsic moments. Each quantization stage uses its newly certified ancestor prefix. A spectral certificate runs first. An optional interval certificate runs after rejection. Unresolved groups replay retained token records under the new prefix and add exact Grams. Complete replay permits exact quantization. Certified stage codes update later prefixes. Commit occurs only after every stage and canonical retained state succeed. Any necessary finite-evaluator failure aborts without approximate output.</desc>
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L10,4 L0,8 Z" fill="#42556c"/></marker>
  <marker id="purple" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L10,4 L0,8 Z" fill="#7251a5"/></marker>
  <marker id="green" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L10,4 L0,8 Z" fill="#227b62"/></marker>
</defs>
<rect width="1400" height="1050" fill="white"/>
<g font-family="DejaVu Sans, sans-serif">
''']
    parts += [text(35, 49, 'Exact repair follows the new ancestor prefix', 32, 700, anchor='start'),
              text(35, 86, 'Fixed base weights, grids, ridge, original normalization, and finite target V_cert', 22, anchor='start'),
              '<rect x="370" y="122" width="995" height="682" rx="20" fill="#f6f8fc" stroke="#b6c2d1" stroke-width="2"/>',
              text(395, 150, 'REPEAT IN DEPENDENCY ORDER', 18, 700, '#506277', 'start')]
    parts += [node(35, 172, 290, 126, 'Verified request', ['Committed state', 'Deletion IDs + payloads'], '#eef3f8'),
              node(35, 350, 290, 151, 'Update intrinsic index', ['Regenerate deleted moments', 'Subtract exact totals', 'Deleted records only'], '#eef3f8', title_size=20, body_size=18),
              node(410, 182, 500, 105, 'New certified prefix p_l', ['Includes changed ancestor codes'], '#eee8f7', '#947ab7'),
              node(410, 335, 500, 125, 'Query retained aggregate moments', ['Use p_l and a proved domain', 'No retained feature reads'], '#e9f3fc', '#79a5ce'),
              node(410, 520, 500, 125, 'Certify every code', ['Spectral check; then interval check*', 'Exact grids and lower midpoint ties'], '#e9f3fc', '#79a5ce'),
              node(1000, 495, 315, 126, 'Replay retained group', ['Read retained token records', 'Evaluate features under p_l'], '#fff1de', '#c29b5d'),
              node(410, 699, 500, 84, 'Install exact stage codes q_l', ['Certificate or full exact Gram'], '#e6f3ee', '#74a693')]
    parts += [arrow('M180 298 V350'),
              arrow('M325 405 H410'),
              arrow('M660 287 V335'),
              arrow('M660 460 V520'),
              text(682, 493, 'Complete retained covariance bound', 18, anchor='start'),
              arrow('M660 645 V699', '#227b62', marker='green'),
              text(804, 678, 'all checks pass', 19, color='#227b62'),
              arrow('M910 579 H1000'),
              text(955, 558, 'else', 18),
              arrow('M1158 495 V397 H910'),
              text(1114, 363, 'Exact group Gram', 20),
              text(1114, 389, 'tightens the enclosure', 18),
              arrow('M1030 621 V743 H910'),
              text(1047, 665, 'All groups exact:', 20, anchor='start'),
              text(1047, 692, 'run exact quantizer', 20, anchor='start'),
              arrow('M910 761 H1342 V234 H910', '#7251a5', marker='purple'),
              text(1125, 217, 'Next stage', 21, 700, '#7251a5'),
              text(1125, 269, 'Changed ancestors alter', 20, color='#7251a5'),
              text(1125, 297, 'downstream feature maps', 20, color='#7251a5')]
    parts += [node(35, 573, 290, 190, 'Charge complete costs', ['Deleted extraction + state', 'Bound queries + factorization', 'Retained reads + replay', 'Verification + output'], '#ffffff', '#9da9b5', title_size=20, body_size=18),
              node(410, 874, 905, 92, 'Commit after every stage and complete retained state succeed', ['Exact model + canonical moments + retained source bindings'], '#e6f3ee', '#74a693'),
              arrow('M660 783 V874', '#227b62', marker='green'),
              text(820, 842, 'all stages complete', 20, color='#227b62'),
              arrow('M180 501 V541 H15 V920 H410', width=2, dashed=True),
              text(180, 816, 'Retained canonical index', 19),
              text(180, 845, 'is carried into the commit', 18),
              text(35, 1004, 'Any required finite-evaluator failure: abort the request; preserve the last committed state.', 21, 700, '#9a3f3f', 'start'),
              text(35, 1034, '*Optional policy: spectral_or_interval. Unknown proof data require replay. All arithmetic and output costs remain charged.', 18, anchor='start'),
              '</g>\n</svg>\n']
    return '\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', action='store_true', help='Export a vector PDF through Inkscape.')
    parser.add_argument('--preview', action='store_true', help='Render a review PNG through Inkscape.')
    args = parser.parse_args()
    SVG.parent.mkdir(parents=True, exist_ok=True)
    SVG.write_text(make_svg(), encoding='utf-8', newline='\n')
    print(SVG)
    if args.pdf or args.preview:
        inkscape = shutil.which('inkscape')
        if inkscape is None:
            raise SystemExit('SVG saved. Inkscape is required for requested conversion.')
        env = dict(os.environ, SOURCE_DATE_EPOCH='0')
        if args.pdf:
            subprocess.run([inkscape, str(SVG), '--export-type=pdf', '--export-text-to-path',
                            f'--export-filename={PDF}'], check=True, env=env, capture_output=True)
            # Cairo does not honor SOURCE_DATE_EPOCH in every installed version.
            # Normalize its volatile creation metadata without rasterizing content.
            from pypdf import PdfReader, PdfWriter
            reader = PdfReader(BytesIO(PDF.read_bytes()))
            writer = PdfWriter()
            writer.clone_document_from_reader(reader)
            writer.add_metadata({'/CreationDate': 'D:19700101000000Z',
                                 '/ModDate': 'D:19700101000000Z'})
            with PDF.open('wb') as stream:
                writer.write(stream)
            print(PDF)
        if args.preview:
            PREVIEW.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([inkscape, str(SVG), '--export-type=png', '--export-width=1400',
                            f'--export-filename={PREVIEW}'], check=True, env=env, capture_output=True)
            print(PREVIEW)


if __name__ == '__main__':
    main()
