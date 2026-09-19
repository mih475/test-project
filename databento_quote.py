import os
import databento as db

key=os.environ.get('DATABENTO_API_KEY')
if not key:
    raise SystemExit('DATABENTO_API_KEY is not set')

client=db.Historical(key)
queries=[
    ('2024','2024-01-01','2025-01-01'),
    ('2025','2025-01-01','2026-01-01'),
    ('2026_YTD','2026-01-01','2026-06-12'),
    ('2024_to_2026YTD','2024-01-01','2026-06-12'),
]
for label,start,end in queries:
    cost=client.metadata.get_cost(
        dataset='GLBX.MDP3',
        symbols=['ES.v.0'],
        schema='trades',
        stype_in='continuous',
        start=start,
        end=end,
    )
    size=client.metadata.get_billable_size(
        dataset='GLBX.MDP3',
        symbols=['ES.v.0'],
        schema='trades',
        stype_in='continuous',
        start=start,
        end=end,
    )
    print(f'{label}: estimated_cost_usd={cost:.4f} billable_bytes={size} billable_gb={size/1e9:.3f}')
