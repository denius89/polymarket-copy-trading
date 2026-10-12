const page=await figma.getNodeByIdAsync('1976:2');await figma.setCurrentPageAsync(page);
COMMON
const board=await makeBoard('Shadow · Client UI kit','Foundations / Основы · Native Figma tokens and shared typography · 12 Oct 2026');
await text(board,'Usage','Build with instances. Change copy via properties. RU/EN share the same components. Current product uses Dark; Light is an existing foundation, not an approved redesign.','Body/Medium');
const colors=Object.values(vars).filter(v=>v.variableCollectionId==='VariableCollectionId:2:3');
for(let i=0;i<colors.length;i+=4){const r=row(board,'Semantic colors',1120);gap(r,16);for(const v of colors.slice(i,i+4)){const cell=track(figma.createAutoLayout('VERTICAL'));r.appendChild(cell);layout(cell,'VERTICAL',268,12,'color/bg/surface');radius(cell);await text(cell,'Token',v.name,'Caption');const sw=track(figma.createRectangle());cell.appendChild(sw);sw.resize(244,40);sw.fills=[paint(v.name)];await text(cell,'Syntax',v.codeSyntax.WEB,'Caption','color/text/secondary');}}
await text(board,'Type heading','Typography / Типографика','Heading/Large');
for(const name of ['Display','Heading/Large','Heading/Medium','Heading/Small','Body/Medium','Body/Small','Label','Caption','Numeric','Numeric/Large'])await text(board,'Type specimen',name+' · Копирование / Copy trading · $209.77',name);
await text(board,'Space heading','Spacing / Отступы · 0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64','Heading/Small');
await text(board,'Radius heading','Radius / Скругления · 6, 10, 14, 20, 999','Body/Medium');
await text(board,'Layout notes','Mobile reference 390×844 · Desktop reference 1440×960. Content reflows; use 44 px touch targets, ≥8 px between actions. Check 320/360/390 and 1280/1440. Amounts are decimal data, not visual tokens. Unknown is unavailable, never $0.','Body/Medium');
await text(board,'Business boundaries','No fee, budget or risk business rules are stored as design tokens. Example / prepared demo is isolated from a new EMPTY session. Deposit/Withdraw remain gated future functions.','Body/Small','color/text/secondary');
return result();