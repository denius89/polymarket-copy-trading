Сравнение ограничено synthetic EU snapshot Oct10. Цены — сценарий USD/month, не актуальные облачные предложения. Победитель без ceiling бюджета, требований нагрузки и принятого recovery профиля не определяется.

| Статья | VPS | Managed |
|---|---:|---:|
| Compute+DB+backup+monitoring | 30+0+10+5=45 | 40+70+12+8=130 |
| Ops при $25/час | 4×25=100 | 1×25=25 |
| Известный месячный subtotal | 145 | 155 |

Известная разница Managed−VPS=$10. DB0 у VPS означает включённость в host, а не отсутствие нагрузки или failure risk. Оба subtotal исключают egress, restore drill, data/API/support; эти неизвестные расходы нельзя считать нулём. Нужно добавить их диапазоны и подтвердить регион/условия/дату перед реальным решением.

Пулы соединений: 3×20+2×15+10 admin=100. При max100 и maintenance reserve20 приложению доступны80: превышение20, запрос составляет125% usable capacity. Возможный план для проверки — replicas3×15 + workers2×10 + admin10=75, оставляя5; это предложение, не доказанная достаточность. Нужны измерения pool wait, concurrency, query latency и IOPS.

VPS объединяет app/DB/signer в одном host failure domain. Managed отделяет DB, но signer остаётся app process; trust boundary не становится независимой автоматически. Paper/live credentials должны быть разделены в обоих вариантах. Residency attestation отсутствует. RPO≤15min и RTO≤60min пока proposals: сравнить backup schedules и измеренный restore в изоляции. Перед выбором согласовать бюджет, operational ownership, нагрузку, failure tolerance и exit/export plan; закупки и provisioning не выполнялись.
