// Produce small addressed scripts. Does not call Figma or publish anything.
const fs=require('node:fs');const p=__dirname;
const model=JSON.parse(fs.readFileSync(p+'/model.json','utf8')),common=fs.readFileSync(p+'/common.js','utf8'),screen=fs.readFileSync(p+'/screens.js','utf8');
const markers=["if(JOB==='entry'){","}else if(JOB==='profile'){","}else if(JOB==='denied'){","}else if(['overview','users'].includes(JOB)){","}else if(['user','session','order'].includes(JOB)){","}else if(JOB==='venue'){","}else if(JOB==='period'){","}else if(JOB==='search'){","}else if(JOB==='status'){","}else if(JOB==='columns'){","}else if(JOB==='language'){","}else if(JOB==='help'){"];
const groups=[['entry'],['profile'],['denied'],['overview','users'],['user','session','order'],['venue'],['period'],['search'],['status'],['columns'],['language'],['help']];
const prefix=screen.slice(0,screen.indexOf(markers[0]));
const finalAt=screen.indexOf("\nif(isWork)text(main,'Учебные");
const tail=screen.slice(finalAt).replace('return {createdNodeIds:created,mutatedNodeIds:mutated,root:root.id,job:JOB,mainHeight:main.height,rootHeight:root.height,reactionCount:reactions.length,variableCount:Object.keys(vars).length};','results.push({root:root.id,job:JOB,mainHeight:main.height,rootHeight:root.height});');
let code='const MODEL='+JSON.stringify(model)+';\n'+common+'\nconst results=[];\n';
for(const job of process.argv.slice(2)){const i=groups.findIndex(g=>g.includes(job));if(i<0)throw Error('Unknown job');const start=screen.indexOf(markers[i])+markers[i].length,end=i<markers.length-1?screen.indexOf(markers[i+1]):finalAt-2;code+='{ const JOB='+JSON.stringify(job)+';\n'+prefix+screen.slice(start,end)+tail+'\n}\n';}
code+='return {createdNodeIds:created,mutatedNodeIds:mutated,results,reactionCount:reactions.length};';
new (Object.getPrototypeOf(async function(){}).constructor)(code);process.stdout.write(code);
