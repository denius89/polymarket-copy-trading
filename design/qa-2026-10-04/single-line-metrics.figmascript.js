await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));
figma.skipInvisibleInstanceChildren=false;
function active(n){for(let p=n;p&&p.type!=="PAGE";p=p.parent)if(p.visible===false)return false;return true;}
const changed=[];
const texts=figma.currentPage.findAllWithCriteria({types:["TEXT"]}).filter(n=>active(n)&&n.name==="Value"&&/^(Не подтверждена|Unverified)$/.test(n.characters)&&n.parent.name==="Shared/Data metric");
for(const n of texts){
 let root=n;while(root.parent&&root.parent.type!=="PAGE"&&root.parent.type!=="SECTION")root=root.parent;
 n.parent.setProperties({"Value#1216:3":"—"});
 const body=root.findAllWithCriteria({types:["TEXT"]}).find(t=>t.name==="Card body"&&/Reading this profile|Как читать|Reading|профиль/i.test(t.parent.name));
 if(!body)throw new Error("Missing explanation "+root.id);
 for(const s of body.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
 const note=PAGE_ID==="33:2"||PAGE_ID==="205:2"?"Максимальная просадка: — означает, что значение не подтверждено источником.":"Maximum drawdown: — means the value is not verified by the source.";
 if(!body.characters.includes(note))body.characters+=" "+note;
 changed.push({value:n.id,root:root.id,explanation:body.id,metric:n.parent.id});
}
return changed;
