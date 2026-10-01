function openOperationModal(){document.getElementById('operationModal')?.classList.add('open');document.body.style.overflow='hidden'}
function closeOperationModal(){document.getElementById('operationModal')?.classList.remove('open');document.body.style.overflow=''}
function ars(v){return new Intl.NumberFormat('es-AR',{style:'currency',currency:'ARS',maximumFractionDigits:0}).format(v||0)}
function renderTrendChart(series){
 const el=document.getElementById('trendChart'); if(!el||typeof Chart==='undefined') return;
 const labels=series.map(x=>{const [y,m,d]=x.operation_date.split('-');return `${d}/${m}`});
 new Chart(el,{type:'line',data:{labels,datasets:[
  {label:'Ingresos',data:series.map(x=>x.income),borderColor:'#16a394',backgroundColor:'rgba(22,163,148,.08)',borderWidth:2,tension:.35,pointRadius:0,pointHoverRadius:4,fill:true},
  {label:'Costos',data:series.map(x=>x.costs),borderColor:'#aeb7c4',backgroundColor:'transparent',borderWidth:1.6,tension:.35,pointRadius:0,pointHoverRadius:4}
 ]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{backgroundColor:'#111827',padding:10,displayColors:true,callbacks:{label:c=>`${c.dataset.label}: ${ars(c.raw)}`}}},scales:{x:{grid:{display:false},border:{display:false},ticks:{color:'#8a94a3',maxTicksLimit:8,font:{size:10}}},y:{grid:{color:'#edf0f2'},border:{display:false},ticks:{color:'#8a94a3',font:{size:10},callback:v=>v>=1000000?(v/1000000).toFixed(1)+'M':v>=1000?(v/1000).toFixed(0)+'k':v}}}}
 });
}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeOperationModal()});
