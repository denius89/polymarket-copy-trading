# Финальные клиентские паттерны в UI kit · 16.10.2026

Источник: [секция Figma 06 · Final client patterns](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T/Controlled-Copy-Trading-%E2%80%94-Paper-MVP?node-id=2805-527), [обзор RU/EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T/Controlled-Copy-Trading-%E2%80%94-Paper-MVP?node-id=2807-535). По поручению владельца клиентский kit дополнен паттернами из утверждённых Final-экранов. Админка и сами продуктовые экраны не менялись.

| Семейство | Figma ID | Варианты | Применение |
| --- | --- | --- | --- |
| Mobile filter selector | `2805:556` | Default, Focus, Expanded, Disabled | Списки из 6–7 значений; 350×48 |
| Mobile filter option row | `2806:543` | Default, Selected, Disabled | Строка выбора в нижнем листе; 350×48 |
| Mobile filter chip | `2806:550` | Default, Selected, Disabled | Только короткие фильтры Help/Tickets; высота 36, ширина по тексту |
| Disclosure row | `2806:561` | Closed, Open | Знак +/− в 8 px от заголовка; 318×44/72 |
| Related action row | `2806:578` | Mobile/Desktop × Default/Disabled | Стрелка рядом с подписью, кликабелен весь ряд; 350×52/368×58 |
| Mobile filter sheet | `2806:619` | 6/7 options | Нижняя панель фильтра; 390×392/440 |

Названия и значения RU/EN задаются текстовыми свойствами экземпляров. Цвета, скругления и отступы привязаны к существующим семантическим переменным. В списках Positions/Orders/Activity используйте селектор с нижним листом вместо карусели или нескольких строк chips. Визуальная высота chip 36 px; область нажатия в реализации — минимум 44 px. Переменная текущего экрана задаёт показанное значение и счётчик. `SET_VARIABLES → CLOSE` и другие маршруты остаются реакциями экранных экземпляров, а не мастера kit.

Проверка: через Figma MCP прочитаны шесть новых component sets и все 18 variants, их размеры и состав секции. Обзорная панель отрендерена после правки раскрытия и длинной подписи disabled chip; примеры RU/EN читаемы без обрезания. Manual Present, работа клавиатуры, озвучивание, 200% масштаб текста и runtime-логика не проверялись. Новые masters не заменяли существующие экранные instances; переносу предшествует отдельное сравнение реакций и RU/EN сценариев.
