# Maintenance Notes

## Update workflow

1. Replace the local, untracked `swc.zip` when the SWC archive changes.
2. Update the local, untracked `readme.docx` when dataset descriptions, thumbnails, or source links change.
3. Run:

   ```bash
   python3 scripts/generate_site_data.py
   ```

4. Review:

   - `public/data/datasets.json`
   - `public/data/manifest.json`
   - `public/assets/thumbnails/`

5. Serve locally from the repository root:

   ```bash
   python3 -m http.server 8000
   ```

6. Open `http://localhost:8000/`.

## Data model

The website is generated from `public/data/datasets.json`. Dataset cards, filters,
summary statistics, and detail panels are not hardcoded in the HTML. Future
collections should be added to the local `readme.docx` and then regenerated, or added
directly to the JSON if the DOCX is no longer the source of truth.

The current release metadata includes an empty DOI/version field. Fill those in
after the Zenodo record is finalized.
