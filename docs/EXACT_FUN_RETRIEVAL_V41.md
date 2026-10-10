# Exact-Fun retrieval and overlap update

Checked 10 October 2026.
This supplements the earlier retrieval limitation; it does not claim full-paper inspection.

Primary records:

- Author PDF: https://zuobinxiong.github.io/assets/pdf/ExactFedUnlearning.pdf
- NSF deposited PDF: https://par.nsf.gov/servlets/purl/10525207
- DOI: https://doi.org/10.1109/ICDM58522.2023.00188

Search indexing exposed Algorithm 2 and the surrounding Theorem 2 discussion from the author PDF.
Algorithm 2 updates stored training information using gradients on deleted examples.
It requantizes the updated federated model and compares that result with the stored quantized model.
Matching codes permit continuation; differing codes trigger retraining from the affected iteration.
Theorem 2 discusses retraining probability through quantization granularity, a perturbation bound, and model dimension.
Its visible proof invokes distributional assumptions, including uniform positions within a cell and independence across dimensions.

Consequently, quantization stability plus conditional retraining is already established prior work.
Our possible distinction requires the declared calibration-code target and universal recovery from compressed feature evidence.
That distinction remains a candidate, not a demonstrated priority claim.

Direct retrieval still failed: the author PDF returned 404, the NSF PDF timed out, and its record page returned 502.
The indexed passage narrows the gap but does not provide complete theorem or proof inspection.
Do not transplant its probability expression without auditing its assumptions.
Recover a readable complete primary copy before making a final theorem-level separation.
No empirical baseline reproduction was performed during this literature check.
