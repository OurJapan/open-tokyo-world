# Iidabashi building catalogue

`iidabashi-buildings.json` is derived from OpenStreetMap data, © OpenStreetMap contributors, under ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/ . Attribution: https://www.openstreetmap.org/copyright . This data is not covered by any repository code license. The downloadable JSON contains the complete derived catalogue used by this feature.

The file includes the query, source endpoint, database timestamp and SHA-256 of the source response. Rebuild with `node scripts/build-target-catalog.mjs <saved-overpass-json>`. It includes only closed building ways; relation/multipolygon buildings and missing map features are not inferred. East-west/north-south extents are approximate axis-aligned map footprint spans, not facade width/depth or surveyed measurements. Height is included only when explicitly tagged in metres; missing heights stay null, never guessed from floor count.

User photographs, GPS histories and submission credentials are not part of this dataset. The app downloads this fixed catalogue from its own host and searches locally.
