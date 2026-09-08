const messages={daily_limit:'本日の受付は上限に達しました。',monthly_limit:'今月の受付は上限に達しました。',storage_limit:'保存容量の上限に達したため受付を停止しています。',intake_paused:'現在、受付を停止しています。',unauthorized:'参加用コードをご確認ください。',photo_limit:'写真は5MB以内にしてください。',body_limit:'送信データが大きすぎます。',id_conflict:'同じ下書きの内容が変更されています。保存済みの送信内容をご確認ください。',submission_pending_or_expired:'この投稿は確認待ち、または保存期限切れです。繰り返し送信せず、運営にお問い合わせください。'};
export async function submitObservation({endpoint,token,draft,photo}) {
  if(!endpoint.startsWith('https://'))throw new Error('送信先が設定されていません。');
  if(photo.byteLength>5000000)throw new Error(messages.photo_limit);
  const form=new FormData();
  form.set('observation',JSON.stringify(draft));form.set('photo',new Blob([photo],{type:'image/jpeg'}),'photo.jpg');
  const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),30000);
  try {
    const response=await fetch(`${endpoint.replace(/\/$/,'')}/v1/observations`,{method:'POST',headers:{Authorization:`Bearer ${token}`},body:form,signal:controller.signal,credentials:'omit',referrerPolicy:'no-referrer'});
    const result=await response.json();
    if(!response.ok)throw new Error(messages[result.error]||'受付を確認できませんでした。下書きを保存して時間をおいてお試しください。');
    if(typeof result.observation_id!=='string')throw new Error('受付番号を確認できませんでした。');
    return result.observation_id;
  } finally {clearTimeout(timeout);}
}
