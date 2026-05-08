# axis4_brain_aging

Django app placeholder for this brAIn axis.

## Endpoint
`POST /api/axis4-brain-aging/analyze/`

## Suggested layout
- `views.py`        – DRF `AnalyzeView(APIView)` accepting upload + metadata
- `serializers.py`  – request/response serializers (mirror `AnalysisResult` in `src/lib/mockApi.ts`)
- `models.py`       – Case, Result persistence
- `ml/`             – model loading + inference
- `explain/`        – axis-specific explainability (heatmaps, regions, signal markers)
- `urls.py`         – route wiring

## Response contract (matches frontend)
```json
{
  "axisId": "axis4-brain-aging",
  "caseId": "BRN-XXXXXX",
  "predictedClass": "string",
  "topConfidence": 0.0,
  "summary": "string",
  "disclaimer": "string",
  "confidence": [{ "label": "string", "value": 0.0 }],
  "regions": [{ "region": "string", "side": "L|R|B", "contribution": 0.0 }],
  "signal":  [{ "t": 0, "v": 0.0 }],
  "timeline": [{ "t": 0, "label": "string", "severity": "low|moderate|high" }],
  "network": { "nodes": [], "edges": [] },
  "metrics": [{ "label": "string", "value": "string" }]
}
```
