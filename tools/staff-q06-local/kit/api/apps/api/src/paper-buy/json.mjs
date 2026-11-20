// Preserve decimal/uint lexemes; reject duplicate keys rather than last-wins.
export function losslessJSON(text){
  if(typeof text!=='string'||Buffer.byteLength(text)>2_000_000)throw Error('json_bound');
  let i=0;const ws=()=>{while(/[\x20\t\r\n]/.test(text[i]??'!'))i++;};
  const string=()=>{const start=i++;while(i<text.length){const c=text[i++];if(c==='"')return JSON.parse(text.slice(start,i));if(c==='\\')i++;}throw Error('json_string');};
  function value(depth=0){
    if(depth>32)throw Error('json_depth');ws();const c=text[i];
    if(c==='"')return string();
    if(c==='['){i++;ws();const a=[];if(text[i]===']'){i++;return a;}for(;;){if(a.length>=10000)throw Error('json_array_bound');a.push(value(depth+1));ws();if(text[i++]===']')return a;if(text[i-1]!==',')throw Error('json_array');}}
    if(c==='{'){i++;ws();const o=Object.create(null);if(text[i]==='}'){i++;return o;}for(;;){ws();if(text[i]!=='"')throw Error('json_key');const k=string();if(Object.hasOwn(o,k))throw Error('json_duplicate');ws();if(text[i++]!==':')throw Error('json_colon');o[k]=value(depth+1);ws();if(text[i++]==='}')return o;if(text[i-1]!==',')throw Error('json_object');}}
    for(const [literal,v]of [['true',true],['false',false],['null',null]])if(text.startsWith(literal,i)){i+=literal.length;return v;}
    const m=text.slice(i).match(/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/);if(!m||m[0].length>256)throw Error('json_number');i+=m[0].length;return m[0];
  }
  const v=value();ws();if(i!==text.length)throw Error('json_trailing');return v;
}
