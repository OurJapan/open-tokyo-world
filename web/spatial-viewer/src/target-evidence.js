import {horizontalENU} from './spatial.js';
export function buildingCandidates(draft,dataset) {
  const l=draft.location;
  if(!l||![l.latitude,l.longitude,l.accuracy_m].every(Number.isFinite)||l.accuracy_m<0)return {reason:'撮影時の位置がありません。素材としてそのまま保存します。',items:[]};
  const [south,west,north,east]=dataset.bbox;
  if(l.latitude<south||l.latitude>north||l.longitude<west||l.longitude>east)return {reason:'撮影位置は飯田橋の建物データ範囲外です。選択エリア名だけでは場所を確定しません。',items:[]};
  if(l.accuracy_m>50)return {reason:'位置の誤差が50mを超えるため、建物候補を絞れません。',items:[]};
  const o=draft.orientation;
  const heading=o?.reference==='webkit-compass'&&Number.isFinite(o.heading_deg)?o.heading_deg:
    o?.reference==='earth-frame'&&Number.isFinite(o.alpha)?(360-o.alpha)%360:null;
  const items=dataset.buildings.map(b=>{
    const points=b.outline.map(([lat,lon])=>horizontalENU({latitude:lat,longitude:lon},l));
    let distance=Infinity,nearest;
    for(let i=1;i<points.length;i++){
      const a=points[i-1],z=points[i],dx=z.east-a.east,dy=z.north-a.north;
      const t=Math.max(0,Math.min(1,-(a.east*dx+a.north*dy)/(dx*dx+dy*dy||1)));
      const p={east:a.east+t*dx,north:a.north+t*dy},d=Math.hypot(p.east,p.north);
      if(d<distance){distance=d;nearest=p;}
    }
    const bearing=(Math.atan2(nearest?.east,nearest?.north)*180/Math.PI+360)%360;
    const angle=heading===null?null:Math.abs(((bearing-heading+540)%360)-180);
    // Ordering aid only: compass, map outlines, viewpoint and occlusion are uncertain.
    const margin=Math.atan2(l.accuracy_m,Math.max(distance,1))*180/Math.PI;
    return {building:b,distance_m:distance,bearing_deg:bearing,angle_deg:angle,score:distance+(angle===null?0:Math.max(0,angle-margin)*3)};
  }).filter(x=>x.distance_m<=300).sort((a,b)=>a.score-b.score).slice(0,8);
  return {reason:heading===null?'方位なし：近い順の候補です。対象は未確定です。':'GPSと概略方位からの候補です。写っている建物とは限りません。対象は未確定です。',items};
}
