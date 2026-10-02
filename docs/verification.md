# Stage 1–4 verification

Verified October 2, 2026 on Windows, Python 3.14.7, Node.js 24.20.0, and headless Microsoft Edge.

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s tests -v` | 22 backend tests passed. |
| `npm.cmd run test:e2e` | 4 browser tests passed, including complete divorce review, contact sync/conflicts, refresh/resume, search context, and 390px mobile layouts. |
| `npm.cmd run build` | TypeScript check and Vite production build passed. |
| `git diff --check` | Passed. |

Backend checks exercise actual HTTP endpoints against isolated persistent SQLite files. Ten concurrent repeated submissions create one logical request. Missing approvals, documents, signatures, changed evidence, and revoked assignment block direct API submissions. Changed instruction evidence also blocks draft preparation. Account-owner death cannot use the beneficiary-death fixture.

Browser checks use separate synthetic state and loopback servers; normal demo work is preserved. Screenshots are generated in ignored `frontend/test-results/`. UI fonts are bundled locally, so loading does not depend on a font service.

These results cover stages 1–4. Live Bedrock inference, AWS persistence, production identity, and the proposed latency/manual-review savings targets have not been implemented or measured in this scope.
