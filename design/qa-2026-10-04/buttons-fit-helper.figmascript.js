
const changed=new Set(),fonts=new Map(),required=new Map();
const vars=await figma.variables.getLocalVariablesAsync(),byId=new Map(vars.map(v=>[v.id,v]));
const style=(await figma.getLocalTextStylesAsync()).find(s=>s.name==="Controls/Button label");
function active(n){for(let p=n;p&&p.type!=="PAGE";p=p.parent)if(p.visible===false&&!p.boundVariables?.visible)return false;return true;}
function isButton(n){
 if(n.type==="INSTANCE"&&n.componentProperties.Style&&n.componentProperties.State)return true;
 return /^(Action\s*\/|Button\s*\/|GuestButton|buttonPrimary|buttonSecondary|buttonQuiet|Unavailable\s*\/|Admin\/Button)/i.test(n.name)&&!/Content group|Header|Help|notifications|Profile|Balance/i.test(n.name);
}
function role(n){const props=n.type==="INSTANCE"?n.componentProperties:n.type==="COMPONENT"?n.variantProperties:{};
 const value=k=>props?.[k]?.value??props?.[k];
 const c=n.fills?.find(p=>p.type==="SOLID")?.boundVariables?.color?.id;
 if(value("State")==="Disabled"||/Unavailable|Disabled/i.test(n.name))return "disabled";
 if(value("Style")==="Destructive"||value("Style")==="Danger"||c==="VariableID:2:47")return "danger";
 if(value("Style")==="Warning"||c==="VariableID:2:45")return "warning";
 if(value("Style")==="Primary"||/buttonPrimary|Admin\/Button\/Primary/.test(n.name)||c==="VariableID:2:38")return "primary";
 if(value("Style")==="Ghost"||/Quiet/.test(n.name))return "quiet";
 return "secondary";
}
function paint(id){const v=byId.get(id);const {r,g,b}=v.resolveForConsumer(figma.currentPage).value;return figma.variables.setBoundVariableForPaint({type:"SOLID",color:{r,g,b}},"color",v);}
function dynamic(paints){return paints?.some(p=>p.boundVariables?.color&&!/^VariableID:(2:|964:3797)/.test(p.boundVariables.color.id));}
async function fix(n,keepWidth=true){
 const labels=n.findAllWithCriteria({types:["TEXT"]}).filter(active);if(!labels.length)return;
 const oldSizing=n.layoutSizingHorizontal;
 const oldWidth=n.width;
 const r=role(n),fill=({primary:38,secondary:29,quiet:29,disabled:29,warning:45,danger:47})[r],text=({primary:"1371:34531",secondary:"2:34",quiet:"2:35",disabled:"2:37",warning:"2:44",danger:"2:46"})[r];
 if(!dynamic(n.fills)){n.fills=r==="quiet"?[]:[paint("VariableID:2:"+fill)];n.strokes=r==="primary"||r==="quiet"?[]:[paint("VariableID:2:32")];}
 const compact=/Period|Chip|Tab/i.test(n.name)||/Period|Chips|Tab/.test(n.parent.name),pad=compact?8:16;
 n.layoutMode="HORIZONTAL";n.primaryAxisAlignItems="CENTER";n.counterAxisAlignItems="CENTER";n.primaryAxisSizingMode="FIXED";n.counterAxisSizingMode="FIXED";n.paddingLeft=pad;n.paddingRight=pad;n.paddingTop=0;n.paddingBottom=0;n.itemSpacing=8;n.cornerRadius=10;
 n.setBoundVariable("paddingLeft",byId.get("VariableID:2:"+(pad===8?52:54)));n.setBoundVariable("paddingRight",byId.get("VariableID:2:"+(pad===8?52:54)));n.setBoundVariable("cornerRadius",byId.get("VariableID:2:62"));
 let natural=0;for(const t of labels){
 if(t.textStyleId!==style.id)await t.setTextStyleIdAsync(style.id);
 t.textTruncation="DISABLED";t.maxLines=null;t.textAutoResize="WIDTH_AND_HEIGHT";t.textAlignHorizontal="CENTER";t.textAlignVertical="CENTER";
 natural+=t.width;if(!dynamic(t.fills))t.fills=[paint("VariableID:"+text)];changed.add(t.id);
 }
 const iconExtra=n.findAllWithCriteria({types:["FRAME","INSTANCE","VECTOR"]}).filter(c=>/icon/i.test(c.name)&&c.width<=24&&c.height<=24).length?28:0;
 required.set(n.id,natural+2*pad+iconExtra);
 const cap=n.parent.type==="FRAME"?n.parent.width-(n.parent.paddingLeft||0)-(n.parent.paddingRight||0):oldWidth;
 const width=keepWidth?oldWidth:Math.min(cap,Math.max(oldWidth,required.get(n.id)));
 n.resize(Math.max(44,width),Math.max(compact?44:48,n.height));
 if(oldSizing==="FILL"&&n.parent.layoutMode!=="NONE")n.layoutSizingHorizontal="FILL";
 const available=Math.max(12,n.width-2*pad-iconExtra);
 const groups=n.children.filter(c=>c.type==="FRAME"&&/Content group/i.test(c.name));
 for(const group of groups){
 group.layoutMode="HORIZONTAL";group.primaryAxisAlignItems="CENTER";group.counterAxisAlignItems="CENTER";group.primaryAxisSizingMode="FIXED";group.counterAxisSizingMode="FIXED";group.paddingLeft=0;group.paddingRight=0;group.paddingTop=0;group.paddingBottom=0;group.itemSpacing=8;group.resize(n.width-2*pad,n.height);group.layoutSizingHorizontal="FILL";changed.add(group.id);
 }
 let height=compact?44:48;
 for(const t of labels){
 const local=t.parent===n?available:Math.max(12,t.parent.width-(t.parent.paddingLeft||0)-(t.parent.paddingRight||0)-iconExtra);
 if(t.width<=local){t.textAutoResize="WIDTH_AND_HEIGHT";if(t.parent.layoutMode&&t.parent.layoutMode!=="NONE")t.layoutSizingHorizontal="HUG";}
 else{t.textAutoResize="HEIGHT";t.resize(local,20);if(t.parent.layoutMode&&t.parent.layoutMode!=="NONE")t.layoutSizingHorizontal="FILL";}
 height=Math.max(height,t.height+24);
 }
 const actualWidth=n.width;n.resize(actualWidth,height);
 if(oldSizing==="FILL"&&n.parent.layoutMode!=="NONE")n.layoutSizingHorizontal="FILL";
 for(const group of groups){group.resize(n.width-2*pad,height);group.layoutSizingHorizontal="FILL";}
 changed.add(n.id);
}
