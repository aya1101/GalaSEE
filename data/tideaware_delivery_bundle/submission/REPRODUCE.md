# REPRODUCE.md

1. Open Google Colab and upload TideAware_AI_Engine.ipynb.
2. Set Earthdata token via Colab Secret EARTHDATA_TOKEN or env (do not commit token).
3. Runtime -> Run all.
4. Estimated: multi-hour if downloading ~12 x ~6 GB raw (KEEP_RAW=False deletes after crop). With Drive cache of scenes/*.h5, re-runs skip download.
5. Disk: >= 20 GB free recommended for first run.
6. Outputs under /content/tideaware: scenes/, layer2_v2/, layer3/, layer4/, figures/, app_bundle/, submission/.
