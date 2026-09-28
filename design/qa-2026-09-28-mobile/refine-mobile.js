const LANG='EN';const ru=LANG==='RU',prefix=ru?'33':'29';const page=await figma.getNodeByIdAsync(prefix+':2');await figma.setCurrentPageAsync(page);await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));const created=[],mutated=[],removed=[];const vars=Object.fromEntries((await figma.variables.getLocalVariablesAsync()).map(v=>[v.name,v]));const L=(a,b)=>ru?b:a;
for(const s of page.children.filter(n=>/^M\d|^MRU\d/.test(n.name))){
for(const t of s.findAllWithCriteria({types:['TEXT']})){
let next=t.characters;
if(next==='Sep 1'||next==='1 сен')next=L('Day 1','День 1');
if(next==='Sep 30'||next==='30 сен')next=s.id===prefix+':236'?L('Day 3','День 3'):s.name.includes('Example result')?L('Day 7','День 7'):L('Day 30','День 30');
if(next==='+$24.60')next='+$25.60';
if(next==='30-day simulation after virtual fees')next='30-day example · $200 budget · net of fees';
if(next==='Симуляция за 30 дней с учётом комиссий')next='Пример за 30 дней · бюджет $200 · после комиссий';
if(next==='$4.80')next='$3.25';
if(next==='Example at a 0.60% average fee. No fee is charged in the demo.')next='Example: 0.40625% average fee. No fee is charged in the demo.';
if(next==='Пример при средней ставке 0,60%. В демо комиссия не списывается.')next='Пример: средняя ставка 0,40625%. В демо комиссия не списывается.';
if(next==='Only virtual positions. Fees are shown for comparison and are not charged.')next='Demo fee: 0%. Future example: 0.50% taker / 0.25% maker, shown virtually.';
if(next==='Только виртуальные позиции. Комиссии показаны для сравнения и не списываются.')next='В демо: 0%. Будущий пример: 0,50% taker / 0,25% maker, только для расчёта.';
if(next==='The venue has not confirmed the simulated action. The system will check its history automatically.')next='The simulator has not recorded a confirmed result. We are checking the session history.';
if(next==='Площадка не подтвердила действие в симуляции. Система автоматически проверит историю.')next='Симулятор не записал подтверждённый результат. Проверяем историю сессии.';
if(next!==t.characters){t.characters=next;mutated.push(t.id);}
}
for(const input of s.findAll(n=>n.type==='FRAME'&&n.name==='Input')){input.strokes=[figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:0,g:0,b:0}},'color',vars['color/border/strong'])];mutated.push(input.id);}
for(const chart of s.findAll(n=>n.type==='FRAME'&&n.name==='Plot / one continuous series')){
const w=chart.width,h=chart.height;for(const child of [...chart.children]){removed.push(child.id);child.remove();}
const xs=[0,.10,.21,.31,.42,.52,.63,.72,.83,.92,1],ys=[.83,.78,.62,.68,.55,.57,.34,.39,.24,.29,.12];const pts=xs.map((x,i)=>[2+x*(w-4),ys[i]*(h-4)+2]);let d=`M ${pts[0][0]} ${pts[0][1]}`;for(let i=0;i<pts.length-1;i++){const p0=pts[Math.max(0,i-1)],p1=pts[i],p2=pts[i+1],p3=pts[Math.min(pts.length-1,i+2)];d+=` C ${p1[0]+(p2[0]-p0[0])/6} ${p1[1]+(p2[1]-p0[1])/6} ${p2[0]-(p3[0]-p1[0])/6} ${p2[1]-(p3[1]-p1[1])/6} ${p2[0]} ${p2[1]}`;}
const grid=figma.createVector();chart.appendChild(grid);created.push(grid.id);grid.name='Grid / quiet horizontal guides';grid.vectorPaths=[{windingRule:'NONZERO',data:[.25,.6,.95].map(y=>`M 0 ${h*y} L ${w} ${h*y}`).join(' ')}];grid.fills=[];grid.strokes=[{type:'SOLID',color:{r:.64,g:.68,b:.76},opacity:.12}];grid.strokeWeight=.7;
const area=figma.createVector();chart.appendChild(area);created.push(area.id);area.name='Area / subtle gradient';area.vectorPaths=[{windingRule:'NONZERO',data:d+` L ${w-2} ${h} L 2 ${h} Z`}];area.fills=[{type:'GRADIENT_LINEAR',gradientTransform:[[0,1,0],[-1,0,1]],gradientStops:[{position:0,color:{r:.63,g:.54,b:1,a:.20}},{position:1,color:{r:.63,g:.54,b:1,a:0}}]}];area.strokes=[];
const line=figma.createVector();chart.appendChild(line);created.push(line.id);line.name='Series / one continuous net-result curve';line.vectorPaths=[{windingRule:'NONZERO',data:d}];line.fills=[];line.strokes=[{type:'SOLID',color:{r:.66,g:.6,b:1}}];line.strokeWeight=2;line.strokeCap='ROUND';line.strokeJoin='ROUND';mutated.push(chart.id);
}
}
return{createdNodeIds:created,mutatedNodeIds:mutated,removedNodeIds:removed};
