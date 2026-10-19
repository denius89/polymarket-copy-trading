// Examples in fenced/inline code are not navigation links.
function proseOnly(markdown) {
  let fence;
  const lines = [];
  for (const line of markdown.split('\n')) {
    const match = line.match(/^ {0,3}(`{3,}|~{3,})/);
    if (!fence && match) { fence = match[1]; continue; }
    if (fence) {
      const closing = line.match(/^ {0,3}(`+|~+)[ \t]*$/);
      if (closing && closing[1][0] === fence[0] && closing[1].length >= fence.length) fence = undefined;
      continue;
    }
    lines.push(line.replace(/(`+)([^`\n]*?)\1/g, ''));
  }
  return lines.join('\n');
}
export function relativeLinkTargets(markdown) {
  const prose = proseOnly(markdown);
  const raw = [...prose.matchAll(/!?(?:\[[^\]]*\])\(([^)]+)\)/g)].map(match => match[1]);
  raw.push(...[...prose.matchAll(/<(?:img|a)\b[^>]*?\b(?:src|href)=["']([^"']+)["'][^>]*>/gi)].map(match => match[1]));
  return raw.flatMap(value => {
    let target = value.trim();
    if (target.startsWith('<') && target.endsWith('>')) target = target.slice(1, -1);
    if (!target || target.startsWith('#') || /^[a-z][a-z0-9+.-]*:/i.test(target)) return [];
    target = target.split('#', 1)[0].split('?', 1)[0];
    return target ? [decodeURIComponent(target)] : [];
  });
}
