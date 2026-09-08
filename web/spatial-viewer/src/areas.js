export const AREAS = Object.freeze({
  'tokyo-tower': {label:'東京タワー周辺', manifest:'manifest.json'},
  iidabashi: {label:'飯田橋駅付近（千代田区側）', manifest:'manifest-iidabashi.json'},
});
export function selectedArea(search) {
  const id=new URLSearchParams(search).get('area')||'tokyo-tower';
  if(!Object.hasOwn(AREAS,id))throw new Error('未対応のエリアです。URLのareaを確認してください。');
  return {id,...AREAS[id]};
}
