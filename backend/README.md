# brAIn — Django backend scaffold

Each axis lives in its own Django app so colleagues can work in parallel.
Mock responses are currently served from `src/lib/mockApi.ts` on the frontend.

| Axis | App folder | Endpoint |
|------|------------|----------|
| 1 — Alzheimer vs Other Dementias | `axis1_alzheimer_dementia/` | `POST /api/axis1-alzheimer-dementia/analyze/` |
| 2 — Parkinson vs Atypical | `axis2_parkinson_atypical/` | `POST /api/axis2-parkinson-atypical/analyze/` |
| 3 — Cerebellar Dysfunction | `axis3_cerebellar_dysfunction/` | `POST /api/axis3-cerebellar-dysfunction/analyze/` |
| 4 — Uneven Brain Aging | `axis4_brain_aging/` | `POST /api/axis4-brain-aging/analyze/` |
| 5 — Functional Connectivity | `axis5_functional_connectivity/` | `POST /api/axis5-functional-connectivity/analyze/` |
| 6 — Neuromotor Video | `axis6_neuromotor_video/` | `POST /api/axis6-neuromotor-video/analyze/` |
| 7 — Epilepsy Network | `axis7_epilepsy_network/` | `POST /api/axis7-epilepsy-network/analyze/` |

When wiring a real endpoint, replace the corresponding `runAnalysis` branch
in `src/lib/mockApi.ts` with a `fetch()` call to your Django URL.
