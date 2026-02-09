import asyncio
from datetime import datetime, timezone

from connect_mapmyrun import get_distance, DistanceUnit

start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
end_date = datetime(2027, 1, 1, tzinfo=timezone.utc)

print(
    asyncio.run(
        get_distance(
            start_date=start_date,
            end_date=end_date,
            unit=DistanceUnit.KM,
            run_headless=False,
        )
    )
)
