const page=await figma.getNodeByIdAsync("1981:30");await figma.setCurrentPageAsync(page);
const buttonKeys=["Show icon#2081:7","Show icon#2081:28","Show icon#2081:49","Show icon#2081:70","Show icon#2033:4","Show icon#2033:6","Show icon#2033:8"];
function semantic(label){
 const s=String(label).toLowerCase().trim();
 if(/^(отмен|cancel|отказ|reject|decline|не готов|not ready|пример|example)/.test(s))return null;
 if(/^(назад|к\s|верну|back|return|to\s)/.test(s))return "2032:47";
 if(/^(обновить|повторить|перепровер|загрузить актуаль|refresh|reload|retry|recheck|check again|load latest)/.test(s))return "2032:50";
 if(/^(изменить|редакт|настроить|edit|change|configure)/.test(s))return "2032:41";
 if(/^(отправить|send)/.test(s))return "2032:28";
 if(/^(поставить на паузу|пауза$|pause)/.test(s))return "2032:53";
 if(/^(возобновить|resume)/.test(s))return "2032:56";
 if(/^(предпросмотр|preview)/.test(s))return "2032:66";
 if(/^(подтвердить|утвердить|применить|approve|confirm|apply)/.test(s))return "1978:718";
 if(/^(скопировать|copy)/.test(s))return "1978:727";
 return null;
}
async function applyButtons(page){
 const list=page.findAllWithCriteria({types:["INSTANCE"]}).filter(n=>buttonKeys.some(k=>k in n.componentProperties));
 const fonts=new Map();for(const n of list)for(const t of n.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))fonts.set(JSON.stringify(s.fontName),s.fontName);for(const font of fonts.values())await figma.loadFontAsync(font);
 const stats={noIcon:0,icons:{}},mutated=[];
 for(const n of list){const cp=n.componentProperties,show=buttonKeys.find(k=>k in cp),label=Object.entries(cp).find(([k])=>k.startsWith("Label#"))?.[1].value,ip=Object.keys(cp).find(k=>k.startsWith("Icon#"));const icon=semantic(label),props={[show]:!!icon};if(icon&&ip)props[ip]=icon;n.setProperties(props);mutated.push(n.id);if(icon)stats.icons[icon]=(stats.icons[icon]||0)+1;else stats.noIcon++;}
 return {createdNodeIds:[],mutatedNodeIds:mutated,count:list.length,stats};
}return await applyButtons(page);