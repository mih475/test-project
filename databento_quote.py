import os
import databento as db

key=os.environ.get('DATABENTO_API_KEY')
if not key:
    raise SystemExit('DATABENTO_API_KEY is not set')

client=db.Historical(key)

# Metadata-only quotes. These calls do not purchase/download market data.
# `trades` on GLBX.MDP3 includes the trade-initiating side when CME provides it,
# allowing buyer- vs seller-aggressor volume and therefore true CVD construction.
queries=[
    ('2021','2021-01-01','2022-01-01'),
    ('2022','2022-01-01','2023-01-01'),
    ('2023','2023-01-01','2024-01-01'),
    ('2024','2024-01-01','2025-01-01'),
    ('2025','2025-01-01','2026-01-01'),
    ('2026_through_Jun11','2026-01-01','2026-06-12'),
    ('fresh_holdout_Jun12_to_Sep21_2026','2026-06-12','2026-09-22'),
    ('2021_to_Sep21_2026','2021-01-01','2026-09-22'),
]

for label,start,end in queries:
    cost=client.metadata.get_cost(
        dataset='GLBX.MDP3',
        symbols=['ES.v.0'],
        stype_in='continuous',
        schema='trades',
        start=start,
        end=end,
    )
    size=client.metadata.get_billable_size(
        dataset='GLBX.MDP3',
        symbols=['ES.v.0'],
        stype_in='continuous',
        schema='trades',
        start=start,
        end=end,
    )
    print(f'{label}: estimated_cost_usd={cost:.4f} billable_bytes={size} billable_gb={size/1e9:.3f}')
