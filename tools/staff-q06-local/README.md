# Изолированный стенд staff Q06

Одна синтетическая демо-сессия для проверки непустого снимка. Клиентский Q04 и staff Q06 читают один финансовый снимок. Временное служебное назначение разрешает чтение через существующие правила пилота. PostgreSQL хранит аудит просмотра. Компоненты собираются из Git без внешних архивов и устанавливаются только в одноразовую локальную среду.

Сборка использует [проверяемую основу Git-демо](../v00-polygon-gateway/README.md), UI из `3a4582f` и staff API из `69071e2`, а также SQL и API из локально проверенных компонентов `polygon-live-buy-compose-20261113` и `polygon-live-buy-runtime-20261113`. Изменённые части находятся в `kit/`. Используются образы Node и PostgreSQL по digest из основной сборки. Демо включает вымышленный источник, 20 долей по себестоимости 9,80 USD и временные ключи. Финансовый код фиксирует одно синтетическое исполнение. Соединений с площадками и Oracle в сценарии нет.

## Запуск на Apple Silicon

Нужны Git, Python 3.11+ и Lima 2.0+. На другом хосте можно использовать отдельную Linux ARM64 VM с Docker. У гостя должна быть собственная файловая система без подключений к проектным секретам. Команды из корня чистого Git checkout:

```bash
python3 tools/staff-q06-local/assemble.py HEAD /tmp/shadow-staff-q06
limactl start --tty=false --name=shadow-staff-q06 tools/staff-q06-local/lima.yaml
tar -C /tmp/shadow-staff-q06 -cf - . | limactl shell --tty=false shadow-staff-q06 \
  bash -ec 'mkdir -p /tmp/staff-kit && tar -xf - -C /tmp/staff-kit'
limactl shell --tty=false shadow-staff-q06 sudo bash /tmp/staff-kit/start.sh
```

Дождитесь `PILOT_PRIVATE_GATEWAY_READY`. Оставьте этот терминал открытым. Во втором терминале:

```bash
python3 tools/staff-q06-local/browser-relay.py -- limactl shell --tty=false \
  shadow-staff-q06 sudo -n python3 -B /tmp/staff-kit/relay-guest.py
```

Откройте `http://127.0.0.1:52486/admin/` во встроенном браузере ChatGPT. Одноразовые вымышленные значения доступны на `/__local_permit` того же адреса. Откройте карточку «участник пилота 1». Ожидаются 290,10 USD доступно, 0,00 USD в резерве и одна позиция на 20 долей. После одного просмотра карточки проверьте Q04, Q06, аудит и отказ обычному пользователю:

```bash
limactl shell --tty=false shadow-staff-q06 sudo python3 /tmp/staff-kit/probe.py
```

Проверка сравнивает точные финансовые поля, ID сессии и снимка с ответом Q06, прочитанным браузером. Она требует одну запись просмотра с тем же снимком и HTTP 401 при запросе Q06 под обычным пользователем. После проверки остановите relay и удалите только созданную одноразовую VM:

```bash
limactl stop shadow-staff-q06
limactl delete shadow-staff-q06
```

Порты базы и API остаются в закрытой сети гостя. Браузерный relay слушает только локальный адрес. Для запуска повторного сценария соберите новую копию и используйте новую VM.
