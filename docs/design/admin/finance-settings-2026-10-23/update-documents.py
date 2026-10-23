from pathlib import Path
import json,os
repo=Path.cwd();pkg=Path('docs/design/admin/finance-settings-2026-10-23')
summary='23.10.2026 — [Настройки финансов]({link}): тариф сервиса отделён от денежных условий партнёров; собственные источники показывают пригодный и свободный остаток; защита различает второй контроль и запрет. Восемь прежних экранов RU/EN и 14 возвратов из форм. Paper Alpha 0%, 1% — неактивный пример. Карта 0.39 / UI kit 0.4.26; количество экранов и компонентов прежнее. Модель переходов и изображения проверены; браузерный ручной проход ограничен зависанием Figma.\n\n'
for f in ['docs/PROJECT_STATE.md','docs/ROADMAP.md','docs/README.md','docs/design/admin/README.md','docs/design/admin/current/README.md','docs/design/admin/STYLE_GUIDE.md','docs/design/admin/sitemap.md','docs/design/admin/ui-kit/README.md']:
 p=Path(f);link=os.path.relpath(pkg/'README.md',p.parent);p.write_text(summary.format(link=link)+p.read_text())
p=Path('docs/design/admin/sitemap.json');d=json.loads(p.read_text());d['revision']='0.39';d['updatedAt']='2026-10-23';d['financeSettings']={'date':'2026-10-23','package':str(pkg.relative_to('docs/design/admin')/'README.md'),'recomposedRoots':8,'formReturnRoots':14,'newRoots':0,'manualBrowserPass':'blocked: Figma tab CDP timeout; native graph and final screenshots checked'}
labels={'pricing':('Тарифы и рефералы','Tariffs and referrals'),'referrals':('Реферальные условия','Referral terms'),'sources':('Собственные источники','Own funding sources'),'security-policy':('Защита выплат','Payout safeguards'),'security-invalid':('Защитное правило не готово','Safeguard rule incomplete')}
for section in d['sections']:
 for s in section['screens']:
  if s['key'] in labels:
   ru,en=labels[s['key']];s['title']=ru;s['english']['title']='EN · '+s['key']+' · '+en
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
p=Path('docs/design/admin/ui-kit/registry.json');d=json.loads(p.read_text());d['revision']='0.4.26';d['financeSettings']={'date':'2026-10-23','package':'../finance-settings-2026-10-23/README.md','patterns':['Current versus inactive tariff','Partner monetary rule approval distinction','Own source eligible/free balance breakdown','Payout safeguard outcomes and explicit form returns'],'newComponentSets':0,'newVariants':0,'newVisualTokens':0,'libraryPublished':False};p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
