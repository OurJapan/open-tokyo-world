// Device-only evidence. A successful request is not a successful transaction.
export function createDraftStore(factory=globalThis.indexedDB) {
  let connection;
  function open() {
    if(!factory)return Promise.reject(new Error('このブラウザでは端末内保存が使えません。ZIPを保存してください。'));
    return connection??=new Promise((resolve,reject)=>{
      const r=factory.open('otw-field-drafts',1);
      r.onupgradeneeded=()=>r.result.createObjectStore('drafts',{keyPath:'id'});
      r.onsuccess=()=>{r.result.onversionchange=()=>{r.result.close();connection=null;};resolve(r.result);};
      r.onerror=()=>{connection=null;reject(r.error);};
      r.onblocked=()=>{connection=null;reject(new Error('別のタブを閉じて保存を再試行してください。'));};
    });
  }
  async function run(mode,action) {
    const db=await open();
    return new Promise((resolve,reject)=>{
      const tx=db.transaction('drafts',mode),req=action(tx.objectStore('drafts'));
      tx.oncomplete=()=>resolve(req.result);
      tx.onerror=tx.onabort=()=>reject(tx.error||new Error('端末内保存に失敗しました。ZIPで保存してください。'));
    });
  }
  return {
    put(record){if(!record.id||record.id!==record.draft?.client_submission_id||!(record.photo instanceof ArrayBuffer))throw new Error('保存データが不正です。');return run('readwrite',s=>s.put(record));},
    get:id=>run('readonly',s=>s.get(id)),
    list:()=>run('readonly',s=>s.getAll()).then(rows=>rows.sort((a,b)=>b.updatedAt-a.updatedAt)),
    delete:id=>run('readwrite',s=>s.delete(id)),
  };
}
