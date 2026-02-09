import asyncio

from connect_mapmyrun import get_distance, DistanceUnit

print(asyncio.run(get_distance(unit=DistanceUnit.KM, run_headless=False)))
