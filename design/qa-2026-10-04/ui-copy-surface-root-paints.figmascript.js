const page = await figma.getNodeByIdAsync(PAGEID);
await figma.setCurrentPageAsync(page);
const canvas = await figma.variables.getVariableByIdAsync("VariableID:2:28");
const roots = [];
function collect(n) { for (const c of n.children || []) { if (c.type === "SECTION") collect(c); else if (c.type === "FRAME") roots.push(c); } }
collect(page);
const screens = roots.filter(n => n.width >= 390 && n.height >= 600 && Array.isArray(n.fills) && n.fills.length === 1 && n.fills[0].type === "SOLID");
const mutations = [];
for (const n of screens) {
 const resolved = canvas.resolveForConsumer(n).value;
 if (!resolved || typeof resolved.r !== "number") throw new Error("Canvas token did not resolve");
 const color = { r: resolved.r, g: resolved.g, b: resolved.b };
 const prior = n.fills[0];
 const changed = prior.boundVariables?.color?.id !== canvas.id || Object.keys(color).some(k => Math.abs(prior.color[k] - color[k]) > 0.00001);
 if (changed) {
  n.fills = [figma.variables.setBoundVariableForPaint({ ...prior, color }, "color", canvas)];
  mutations.push({ id:n.id, name:n.name, before:prior, after:n.fills[0] });
 }
}
return { pageId:page.id, inspectedScreenCount:screens.length, mutatedNodeIds:mutations.map(x=>x.id), remainingMismatch:screens.filter(n=>n.fills[0].boundVariables?.color?.id!==canvas.id||Object.keys(n.fills[0].color).some(k=>Math.abs(n.fills[0].color[k]-canvas.resolveForConsumer(n).value[k])>.00001)).map(n=>n.id) };
