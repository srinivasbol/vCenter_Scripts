# vCenter_Scripts
vCenter_Scripts

## Research pipeline

### Install

```bash
python -m pip install -r research_pipeline/requirements.txt
```

System tools required:
- Graphviz (`graphviz`) for `diagrams` image rendering
- PlantUML (`plantuml`) for `.puml` to image rendering (optional)
- LaTeX with IEEEtran support (for PDF compilation of generated `.tex`)

### Run

```bash
python research_pipeline/ingest_trends.py
python research_pipeline/generate_diagrams.py
python research_pipeline/draft_manuscript.py
```
