export const $=s=>document.querySelector(s);
export function el(tag,text,className) {const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(className)e.className=className;return e;}
export function button(text,handler) {const b=el('button',text);b.type='button';b.addEventListener('click',handler);return b;}
export function message(text) {$('#message').textContent=text;$('#message').hidden=false;}
export const values=form=>Object.fromEntries(new FormData(form));
export function fill(form,data) {form.dataset.filling='1';form.reset();delete form.dataset.filling;for(const [key,value] of Object.entries(data)){const input=[...form.elements].find(input=>input.name===key);if(input){if(input.type==='checkbox')input.checked=!!value;else input.value=value??'';}}}
export function options(select,records,label='Pilih') {const value=select.value;select.replaceChildren();const first=el('option',label);first.value='';select.append(first);for(const record of records){const item=el('option',record.name);item.value=record.id;select.append(item);}select.value=value;}
let csrf='';export let user=null;
export async function api(path,method='GET',body) {
 const response=await fetch('/api/'+path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:method==='GET'?undefined:JSON.stringify(body||{})});
 const data=await response.json();if(!response.ok)throw new Error(data.error||'Permintaan gagal.');return data;
}
export async function bindAuth(refresh) {
 const show=session=>{
  user=session.user;csrf=session.csrf||'';
  $('#login-section').hidden=!!user;$('#workspace').hidden=!user;
  $('#logout').hidden=!user;$('#account').textContent=user?user.name+' / '+user.role:'';
  $('#setup-note').textContent=session.configured===false?'Belum ada akun. Jalankan python -m core.users --role Admin melalui terminal server untuk membuat Admin dan Petugas.':'Masuk dengan akun yang dibuat pengelola server.';
 };
 $('#login-form').addEventListener('submit',async e=>{e.preventDefault();const form=e.currentTarget;try{show(await api('login','POST',values(form)));form.reset();await refresh();message('Anda telah masuk.');}catch(e){message(e.message);}});
 $('#logout').addEventListener('click',async()=>{try{await api('logout','POST');show({user:null});message('Anda telah keluar.');}catch(e){message(e.message);}});
 show(await api('session'));if(user)await refresh();
}
export function money(value) {return new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(value);}
export function download(url) {const a=document.createElement('a');a.href=url;a.click();}
