// Credentials live only in memory. Only explicitly opted-in records enter this queue.
export function createAutoUpload({store,submit,onChange=()=>{}}) {
  let token='',running=false,pending=false;
  return {
    get enabled(){return !!token;},
    get running(){return running;},
    enable(value){token=value;return this.pump();},
    disable(){token='';},
    async pump(){
      if(running){pending=true;return;}
      if(!token)return;
      running=true;
      try {
        do {
        pending=false;
        for(const row of await store.list()) {
          if(!token)break;
          if(!row.autoUpload||row.receipt||!row.submissionSnapshot)continue;
          try {
            row.receipt=await submit({token,draft:row.submissionSnapshot,photo:row.photo});
            row.uploadError=null;await store.put(row);
          }catch(e){row.uploadError=e.name==='AbortError'?'受付結果を確認できませんでした。':e.message;await store.put(row);await onChange();pending=false;return;}
          await onChange();
        }
        }while(pending&&token);
      }catch(e){await onChange(e);}finally{running=false;await onChange();}
    }
  };
}
