# Third-Party Components
| name | version | license | role | citation |
|---|---|---|---|---|
| numpy | 2.4.6 | see THIRD_PARTY.md | arrays |  |
| h5py | 3.14.0 | see THIRD_PARTY.md | NISAR HDF5 |  |
| rasterio | 1.5.2 | see THIRD_PARTY.md | GeoTIFF |  |
| matplotlib | 3.10.0 | see THIRD_PARTY.md | figures |  |
| scipy | 1.16.3 | see THIRD_PARTY.md | ndimage/label/stats |  |
| pandas | 2.2.3 | see THIRD_PARTY.md | tables/tide |  |
| scikit-image | 0.25.2 | see THIRD_PARTY.md | Otsu mask |  |
| pyproj | 3.8.0 | see THIRD_PARTY.md | CRS/bbox |  |
| requests | 2.32.4 | see THIRD_PARTY.md | download |  |
| tqdm | 4.67.3 | see THIRD_PARTY.md | progress |  |
| torch | 2.14.1+cu130 | see THIRD_PARTY.md | L-TAE train | Garnot & Landrieu 2020 (architecture) |
| nrt | 0.3.0 | EUPL-1.2 | EWMA/CuSum trial | Dutrieux & Viehweger JOSS 2024 |

REACTIV composite: self-implemented HSV; cite Colin & Nicolas (2020) Remote Sensing 12(13):2089; Colin Koeniguer et al. EUSAR 2018. No upstream code copied.
L-TAE: self-contained TinyLTAE inspired by Garnot & Landrieu (2020) arXiv:2007.00586; trained from scratch (no pretrained weights).
CUSUM: self-implemented (~15 lines); Page; Verbesselt et al. 2012.
