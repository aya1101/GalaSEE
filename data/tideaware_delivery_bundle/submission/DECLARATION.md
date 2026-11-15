# DECLARATION.md

## Libraries
See THIRD_PARTY.md (versions pinned from this runtime).

## Models
- Layer 2: pixel-wise OLS tide regression fit on Reference only; LOO RMSE reported.
- Layer 3: TideAware L-TAE, trained from scratch, self-supervised on NISAR Reference.
Track 047 L-TAE Ref RMSE: 1.137 dB vs OLS=0.580 dB, Med=0.718 dB
Track 155 L-TAE Ref RMSE: 1.285 dB vs OLS=0.616 dB, Med=0.746 dB
- No pretrained mangrove-loss classifier. Metrics are backscatter expectation errors, not deforestation accuracy.
- Layer 4: Robust Z + CUSUM + rules (not an ML model). nrt status: {'047': 'NRT: NOT APPLICABLE (n_ref=4)', '155': 'NRT: NOT APPLICABLE (n_ref=4)'}

## Data
### Organizer data
NISAR L2 GCOV - 12 granules (Track 155 x 6, Track 047 x 6). Product versions PROVISIONAL_V1 (P05023) and V1 (P05036).

### Extra data
- UHSLC station 383 (Vung Tau) hourly sea level - open - support for tide correction.
- GMW: {'047': 'PROVISIONAL_UNVALIDATED_OTSU', '155': 'PROVISIONAL_UNVALIDATED_OTSU'}
- HLS/S2 / Sentinel-1: SKIPPED - INPUT UNAVAILABLE (not fetched in this run) / SKIPPED - INPUT UNAVAILABLE

No closed copyrighted datasets used.
