const statuses = ['Interested','Preparing application','Applied','Assessment','Interview','Offer','Rejected','Withdrawn'];
const seed = [
  {id:'a1',company:'Linear',role:'Product Designer',location:'Remote · US',status:'Interview',applied:'2026-10-22',followup:'2026-10-29',salary:'',contact:'',notes:'Second round interview'},
  {id:'a2',company:'Figma',role:'Senior UX Designer',location:'San Francisco, CA',status:'Applied',applied:'2026-10-20',followup:'2026-10-30',salary:'',contact:'',notes:''},
  {id:'a3',company:'Notion',role:'Product Designer',location:'Remote · US',status:'Assessment',applied:'2026-10-17',followup:'2026-10-28',salary:'',contact:'',notes:'Take-home exercise'},
  {id:'a4',company:'Webflow',role:'UX Designer',location:'Remote · US',status:'Applied',applied:'2026-10-14',followup:'',salary:'',contact:'',notes:''},
  {id:'a5',company:'Stripe',role:'Product Designer',location:'New York, NY',status:'Offer',applied:'2026-10-09',followup:'',salary:'',contact:'',notes:'Offer received'},
];
let applications = JSON.parse(localStorage.getItem('applytrack-applications') || 'null') || seed;
const $ = (s) => document.querySelector(s);
const esc = (v='') => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const save = () => { localStorage.setItem('applytrack-applications', JSON.stringify(applications)); render(); };
const prettyDate = value => value ? new Date(`${value}T12:00:00`).toLocaleDateString('en-US',{month:'short',day:'numeric'}) : '—';
function render(){
  const count = s => applications.filter(a=>a.status===s).length;
  const statItems=[['Total applications',applications.length,'▤','All the roles you’re tracking'],['Pending response',count('Applied')+count('Assessment'),'◷','Waiting to hear back'],['Interviews',count('Interview'),'↗','You’re making progress'],['Offers',count('Offer'),'✳','The exciting part'],['Upcoming follow-ups',applications.filter(a=>a.followup && a.followup>=new Date().toISOString().slice(0,10)).length,'◴','Keep the momentum going']];
  $('#stats').innerHTML=statItems.map(([label,value,icon,foot])=>`<article class="stat-card"><div class="stat-top">${label}<span class="stat-icon">${icon}</span></div><div class="stat-value">${value}</div><div class="stat-foot">${foot}</div></article>`).join('');
  $('#nav-total').textContent=applications.length;
  const select=$('#status-filter'); const selected=select.value; select.innerHTML='<option value="all">All statuses</option>'+statuses.map(s=>`<option>${esc(s)}</option>`).join('');select.value=selected||'all';
  const query=$('#search').value.toLowerCase(); const filter=select.value;
  const rows=applications.filter(a=>(filter==='all'||a.status===filter)&&`${a.company} ${a.role} ${a.location||''}`.toLowerCase().includes(query));
  $('#application-rows').innerHTML=rows.map(a=>`<tr><td><div class="company-cell"><span class="company-logo">${esc(a.company.slice(0,1).toUpperCase())}</span><span><span class="company-name">${esc(a.company)}</span><span class="company-role">${esc(a.role)}${a.location?` · ${esc(a.location)}`:''}</span></span></div></td><td><span class="status-badge status-${a.status.replaceAll(' ','-')}">${esc(a.status)}</span></td><td class="muted">${prettyDate(a.applied)}</td><td class="muted">${prettyDate(a.followup)}</td><td><button class="row-menu" aria-label="Edit ${esc(a.company)}" data-edit="${esc(a.id)}">···</button></td></tr>`).join('');
  $('#empty-state').hidden=applications.length>0;
  $('#application-rows').closest('.table-scroll').hidden=applications.length===0;
  const funnel=[['Applications',applications.length],['Interviews',count('Interview')],['Offers',count('Offer')]];const max=Math.max(...funnel.map(x=>x[1]),1);
  $('#snapshot').innerHTML=`<div class="snapshot">${funnel.map(([label,n])=>`<div class="snapshot-row"><span>${label}</span><span class="snapshot-track"><span class="snapshot-fill" style="display:block;width:${Math.max(4,n/max*100)}%"></span></span><b>${n}</b></div>`).join('')}</div>`;
  const months=[];const now=new Date();for(let i=5;i>=0;i--){const d=new Date(now.getFullYear(),now.getMonth()-i,1);const key=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;months.push({label:d.toLocaleDateString('en-US',{month:'short'}),count:applications.filter(a=>(a.applied||'').startsWith(key)).length});}
  $('#activity-chart').innerHTML=months.map(m=>`<div class="chart-month"><span class="bar" style="height:${Math.max(3,m.count/8*100)}%"></span><span class="bar secondary" style="height:${Math.max(3,m.count/10*70)}%"></span><label>${m.label}</label></div>`).join('');
  const upcoming=applications.filter(a=>a.followup).sort((a,b)=>a.followup.localeCompare(b.followup));$('#reminder-count').textContent=upcoming.length?`${upcoming.length} upcoming →`:'See upcoming →';
}
function openForm(app){const form=$('#application-form');form.reset();$('#application-id').value=app?.id||'';$('#modal-title').textContent=app?'Edit application':'Add an application';$('#company').value=app?.company||'';$('#role').value=app?.role||'';$('#link').value=app?.link||'';$('#location').value=app?.location||'';$('#status').innerHTML=statuses.map(s=>`<option>${esc(s)}</option>`).join('');$('#status').value=app?.status||'Interested';$('#applied').value=app?.applied||new Date().toISOString().slice(0,10);$('#followup').value=app?.followup||'';$('#salary').value=app?.salary||'';$('#contact').value=app?.contact||'';$('#notes').value=app?.notes||'';$('#delete-application').hidden=!app;$('#application-dialog').showModal();}
$('#add-application').addEventListener('click',()=>openForm());$('#empty-add').addEventListener('click',()=>openForm());$('#search').addEventListener('input',render);$('#status-filter').addEventListener('change',render);
$('#application-rows').addEventListener('click',e=>{const btn=e.target.closest('[data-edit]');if(btn)openForm(applications.find(a=>a.id===btn.dataset.edit));});
$('#application-form').addEventListener('submit',e=>{e.preventDefault();const id=$('#application-id').value;const data={id:id||crypto.randomUUID(),company:$('#company').value.trim(),role:$('#role').value.trim(),link:$('#link').value.trim(),location:$('#location').value.trim(),status:$('#status').value,applied:$('#applied').value,followup:$('#followup').value,salary:$('#salary').value.trim(),contact:$('#contact').value.trim(),notes:$('#notes').value.trim()};applications=id?applications.map(a=>a.id===id?data:a):[data,...applications];$('#application-dialog').close();save();});
$('#delete-application').addEventListener('click',()=>{const id=$('#application-id').value;applications=applications.filter(a=>a.id!==id);$('#application-dialog').close();save();});
$('#export').addEventListener('click',()=>{const keys=['company','role','link','location','status','applied','followup','salary','contact','notes'];const csv=[keys.join(','),...applications.map(a=>keys.map(k=>`"${String(a[k]||'').replaceAll('"','""')}"`).join(','))].join('\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));const a=document.createElement('a');a.href=url;a.download='applytrack-applications.csv';a.click();URL.revokeObjectURL(url);});
$('#reminder-count').addEventListener('click',()=>{const date=new Date().toISOString().slice(0,10);const next=applications.filter(a=>a.followup&&a.followup>=date).sort((a,b)=>a.followup.localeCompare(b.followup))[0];if(next)openForm(next);else openForm();});
$('#today-label').textContent=new Date().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'}).toUpperCase();render();
