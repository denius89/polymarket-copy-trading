const page=await figma.getNodeByIdAsync(PAGE_ID);await figma.setCurrentPageAsync(page);figma.skipInvisibleInstanceChildren=false;
const changed=[],created=[],plots=[];
const lavender={r:.72,g:.62,b:1},surface={r:.065,g:.075,b:.115};
const gradient={type:'GRADIENT_LINEAR',gradientTransform:[[0,1,0],[-1,0,1]],gradientStops:[{position:0,color:{...lavender,a:.25}},{position:1,color:{...lavender,a:0}}]};
const frames=page.findAllWithCriteria({types:['FRAME']}).filter(n=>/Signed cumulative|Plot ·/i.test(n.name));
for(const plot of frames){
 const signed=/Signed cumulative/.test(plot.name);
 const curves=plot.findAllWithCriteria({types:['VECTOR']}).filter(n=>n.height>4&&n.width>30&&n.strokes.length&&n.vectorPaths.length&&!/Z\s*$/i.test(n.vectorPaths[0].data));
 if(!curves.length)continue;
 const line=curves[curves.length-1]; const old={w:line.width,h:line.height,x:line.x,y:line.y,path:line.vectorPaths[0].data};
 const W=signed?plot.parent.width:plot.width,H=signed?120:plot.height;
 const minY=Math.min(old.y,signed?75:old.y),maxY=Math.max(old.y+old.h,signed?75:old.y+old.h);
 const newX=signed?16:old.x,newY=signed?12+(old.y-minY)/(maxY-minY||1)*96:old.y;
 const newW=signed?W-32:Math.min(old.w,W-old.x-16),newH=signed?old.h/(maxY-minY||1)*96:old.h;
 const sx=newW/old.w,sy=newH/old.h;
 // Existing cubic controls are transformed together with samples, preserving shape.
 const tokens=old.path.match(/[MLCQZ]|[-+]?(?:\d*\.?\d+)(?:e[-+]?\d+)?/gi);let axis=0;
 const path=tokens.map(t=>{if(/^[A-Z]$/i.test(t)){axis=0;return t;}return String(Number(t)*(axis++%2===0?sx:sy));}).join(' ');
 line.vectorPaths=[{windingRule:line.vectorPaths[0].windingRule,data:path}];line.x=newX;line.y=newY;
 line.strokes=[{type:'SOLID',color:lavender}];line.strokeWeight=2;line.strokeCap='ROUND';line.fills=[];line.effects=[{type:'DROP_SHADOW',color:{r:.58,g:.38,b:1,a:.22},offset:{x:0,y:0},radius:5,spread:0,visible:true,blendMode:'NORMAL'}];changed.push(line.id);
 for(const other of curves)if(other!==line){other.visible=false;changed.push(other.id);}
 let area=plot.findAllWithCriteria({types:['VECTOR']}).find(n=>/Area to zero|Chart\/Area/.test(n.name)||n.width>30&&n.height>4&&n.fills.length&&n.vectorPaths.some(p=>/Z\s*$/i.test(p.data)));
 if(!area){area=figma.createVector();plot.insertChild(0,area);created.push(area.id);}
 area.name='Chart/Area';area.vectorPaths=[{windingRule:'NONZERO',data:path+' L '+newW+' '+(H-12-newY)+' L 0 '+(H-12-newY)+' Z'}];area.x=newX;area.y=newY;area.fills=[gradient];area.strokes=[];area.effects=[];changed.push(area.id);
 if(signed){
 plot.resize(W,H);plot.cornerRadius=12;plot.fills=[{type:'SOLID',color:surface}];plot.clipsContent=true;changed.push(plot.id);
 const zeroY=12+(75-minY)/(maxY-minY||1)*96;
 for(const z of plot.children.filter(n=>n.type==='VECTOR'&&n.height<2)){z.visible=zeroY>14&&zeroY<106;if(z.visible){z.y=zeroY;z.strokes=[{type:'SOLID',color:lavender,opacity:.16}];z.strokeWeight=1;z.dashPattern=[3,5];}changed.push(z.id);}
 const note=plot.parent.findAllWithCriteria({types:['TEXT']}).find(n=>n.name==='Chart note');if(note){for(const s of note.getStyledTextSegments(['fontName']))await figma.loadFontAsync(s.fontName);note.characters=PAGE_ID==='33:2'||PAGE_ID==='205:2'?'Демо-данные':'Demo data';note.fontSize=12;note.lineHeight={unit:'PIXELS',value:16};note.textAutoResize='HEIGHT';note.resize(W,16);changed.push(note.id);}
 }
 const nums=path.match(/[-+]?(?:\d*\.?\d+)(?:e[-+]?\d+)?/gi).map(Number);const ex=nums[nums.length-2],ey=nums[nums.length-1];
 let dot=plot.children.find(n=>n.type==='ELLIPSE'&&/Last value|Chart\/Endpoint/.test(n.name));if(!dot){dot=figma.createEllipse();plot.appendChild(dot);created.push(dot.id);}
 dot.name='Chart/Endpoint';dot.resize(5,5);dot.x=newX+ex-2.5;dot.y=newY+ey-2.5;dot.fills=[{type:'SOLID',color:lavender}];changed.push(dot.id);
 plots.push({id:plot.id,line:line.id,signed,w:W,h:H,original:old,newPath:path});
}
return {page:PAGE_ID,changed:[...new Set(changed)],created,plots};
