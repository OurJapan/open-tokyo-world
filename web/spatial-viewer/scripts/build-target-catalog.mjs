// Converts a manually downloaded, bounded Overpass snapshot; never queries live GPS.
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const input=process.argv[2];if(!input)throw new Error('Usage: node scripts/build-target-catalog.mjs <overpass-json>');
const raw=await readFile(input),source=JSON.parse(raw);
if(source.remark||!Array.isArray(source.elements)||source.elements.length===0)throw new Error('Incomplete or empty Overpass response');
const buildings=[];
for(const e of source.elements){
 if(e.type!=='way'||!e.tags?.building||!Array.isArray(e.geometry))continue;
 const outline=e.geometry.map(p=>[p.lat,p.lon]);if(outline.length<4||outline.some(p=>!p.every(Number.isFinite)))continue;
 if(JSON.stringify(outline[0])!==JSON.stringify(outline.at(-1)))continue;
 const lat=outline.map(p=>p[0]),lon=outline.map(p=>p[1]);const center=[(Math.min(...lat)+Math.max(...lat))/2,(Math.min(...lon)+Math.max(...lon))/2];
 const value=e.tags.height?.trim(),height=value&&/^\d+(?:\.\d+)?(?:\s*m)?$/.test(value)?parseFloat(value):null;
 buildings.push({id:`osm:way:${e.id}`,name:e.tags['name:ja']||e.tags.name||`名称未登録の建物（${e.id}）`,source_url:`https://www.openstreetmap.org/way/${e.id}`,center,outline,
 dimensions:{east_west_m:Math.round((Math.max(...lon)-Math.min(...lon))*111320*Math.cos(center[0]*Math.PI/180)*10)/10,north_south_m:Math.round((Math.max(...lat)-Math.min(...lat))*110574*10)/10,height_m:height>0?height:null,method:'map_outline_axis_aligned_extent_and_height_tag',accuracy:'unknown'}});
}
const catalog={schema_version:'otw-building-catalog/0.1',area_id:'iidabashi',bbox:[35.6975,139.741,35.7043,139.749],version:'sha256:'+createHash('sha256').update(raw).digest('hex'),source_timestamp:source.osm3s.timestamp_osm_base,source_endpoint:'https://overpass-api.de/api/interpreter',query:'[out:json][timeout:25];way[building](35.6975,139.741,35.7043,139.749);out tags geom;',attribution:'© OpenStreetMap contributors',license:'ODbL-1.0',license_url:'https://opendatacommons.org/licenses/odbl/1-0/',coverage_note:'Closed building ways only; not complete coverage, multipolygon relations excluded.',buildings};
await writeFile(new URL('../public/data/iidabashi-buildings.json',import.meta.url),JSON.stringify(catalog)+'\n');
console.log(JSON.stringify({buildings:buildings.length,heights:buildings.filter(b=>b.dimensions.height_m!==null).length,bytes:Buffer.byteLength(JSON.stringify(catalog))}));
