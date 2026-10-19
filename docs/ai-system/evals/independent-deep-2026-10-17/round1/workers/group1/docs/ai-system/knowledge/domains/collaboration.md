# Git/GitHub и Figma collaboration

Опоры: P01 CONTRIBUTING, P02 HANDOFF, D12 GitHub rulesets, D18 Figma publishing. Проектные процедуры не подменяют bundled Figma skills; их обязательные prerequisites читать перед соответствующим tool call.

## Git

Baseline — фактический checkout/branch/HEAD и dirty/untracked состояние; remote currency — отдельная проверка, если она нужна задаче. Не считать родительские архивы актуальным checkout после переноса. Не включать чужие файлы через add -A/reset/clean.

Один PR должен иметь понятный результат/критерий и evidence. Конфликт разрешается по смыслу актуальных решений, а не механически ours/theirs. Перед commit — предписанные проверки и staged diff, перед публикацией — scope текущего поручения. Создание PR, merge и deploy не одно действие. Protected=false у ветки не доказывает отсутствие repository/organization rulesets.

## Figma

Сначала ограничить file/page/node/роль/локаль и нужный тип чтения. Большой скан дерева не заменяет targeted read, а его timeout не доказывает отсутствие узлов. Использовать актуальные IDs и состояния, не полагаться на старый sitemap anchor.

Сохранять master/variant/variables и instance overrides осознанно. Library publish не мигрирует автоматически все экраны; instance migration/принятие изменения проверяются отдельно. Construction script — инструкция восстановления выбранной структуры, не точный backup всех свойств файла.

Handoff связывает проблему, принятые правила, изменённые IDs/tokens, RU/EN/mobile/desktop состояния, документацию и конкретные visual/structural/prototype проверки. По картинкам не заявлять keyboard/reader/performance/runtime success. Новая композиция не требует автоматически нового мастера.
