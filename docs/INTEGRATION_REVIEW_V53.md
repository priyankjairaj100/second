# V53 integration and pre-execution review

V53 adds a separately named compressed48 format, derived from the preserved V43
state implementation. The new magic/schema isolate it from every historical
compressed40 state. Forty-eight bits and block256 are fixed uniformly across
all stages. Retained-source identity, target, scale, complete-code extent,
canonical ordering and exact actual-byte comparison checks are retained.

All three state formats now use the same V53 framing. The service is a versioned
V43 adaptation with the V45 thirteen-source Gram limits. No source/model target,
normalization, ridge or grid changes. The worker is a V45 adaptation wrapped once
per process in the V50 neighbor backend; all arms, preparation and fresh oracle
share that choice. The original token and Gram routes remain as dispatched.
Backend selection is restored on failure and its identity is audited.

Tests cover canonical formats and actual successive deletion bytes; independently
rebuilt fixture states; old40 rejecting48 and new48 rejecting40/wrong block size;
representation/target/membership tampering; actual sealed CPU receipts; stale NFS
metadata; model-export/state equality; replay on certificate refusal and rejection
of replay with incorrect source bytes. The replay fixture explicitly checks a
single charged traversal shared across two refused stages. Old40 state tests and
V50 native word/exception tests remain part of Linux validation. These are small
software fixtures, not empirical model or independent scientific replication.

The new resource policy is explicit in research_v53/PROTOCOL.txt. CPU ceilings
are larger than V45's failed ceilings and are not runtime predictions. Total new
worker allowance is81012 CPU seconds, separate from all historical charges.
Shape-only admission covers24 stages x3 retained sizes x3 representations and
point replay reservations. The OS and scheduler caps remain decisive.

The Slurm launcher submits a sequential dependency chain, with no requeue and
kill-on-invalid-dependency. Any earlier failure blocks all later empirical arms.
Submission itself is one-use; a partially submitted chain must be inspected and
never blindly resubmitted. Primary and supplemental audits gate completed-model
claims. No quality data, new root or paper readiness is established by this code.
