# eNRI: описание задачи и минимальный план реализации

# I. Описание задачи

## 1. Цель

По экспериментальным данным требуется найти вектор весов

\[
\mathbf w=(w_1,\ldots,w_{35})^{\mathsf T},
\]

задающий индекс

\[
eNRI(\mathbf x)
=
1+
\mathbf w^{\mathsf T}
\left(
\mathbf x-\overline{\mathbf x}_{PBS^{0}}
\right),
\]

где \(\mathbf x\) — стандартизованный вектор из 35 функциональных признаков.

Нормировка:

\[
\overline{eNRI}_{PBS^{0}}=1.
\]

Для смерти:

\[
eNRI(death)=0.
\]

Группа животного не входит в \(\mathbf x\) и используется только для задания ограничений.

## 2. Признаки

Используются 35 признаков, присутствующих на 0-й, 16-й и 24-й неделях.

### OFT

1. OFT_distance
2. Average_speed_OFT
3. Total_time_mobile_OFT
4. Absolute_turn_angle_OFT
5. Time_inCenter_OFT

### NOR1

6. Total distance travelled_NOR1
7. Average speed_NOR1
8. Time investigating Piramidka_NOR1
9. Latency to first investigation of Piramidka_NOR1
10. Time investigating Stakan_NOR1
11. Latency to first investigation of Stakan_NOR1
12. Latency to first investigation_NOR1
13. Total time investigating_NOR1

### NOR2

14. Total distance travelled_NOR2
15. Average speed_NOR2
16. Time investigating Piramidka zone_NOR2
17. Latency to first investigation of Piramidka zone_NOR2
18. Time investigating Stakan zone_NOR2
19. Latency to first investigation of Stakan zone_NOR2
20. DI_NOR2
21. Latency to first investigation_NOR2
22. Total time investigating_NOR2

### Rotarod learning

23. Learning T1mean
24. Learning T1max
25. Learning T1sum
26. Learning T2mean
27. Learning T2max
28. Learning T2sum
29. Learning T3mean
30. Learning T3max
31. Learning T3sum

### Остальные

32. EnduranceT
33. rear_support
34. rear_nosupport
35. Weight

Не включаются группы, ID, Eight_item_index, CoFI, Grip, Y-maze, social/depression и молекулярные показатели.

## 3. Стандартизация

Исходные значения:

\[
\mathbf r=(r_1,\ldots,r_{35})^{\mathsf T}.
\]

Стандартизованные значения:

\[
x_j=\frac{r_j-m_j}{s_j}.
\]

Одни и те же \(m_j,s_j\) используются для всех недель. При cross-validation они вычисляются только по train.

## 4. Ограничения

Пары равенства:

\[
\mathcal E=
\{
(PBS^{0},LPS^{0}),
(LPS^{16},run^{16}),
(LPS^{16},MCC^{16})
\}.
\]

Пары порядка:

\[
\mathcal O=
\{
(PBS^{16},LPS^{16}),
(PBS^{24},LPS^{24}),
(run^{24},LPS^{24}),
(MCC^{24},LPS^{24}),
(PBS^{0},PBS^{16}),
(LPS^{0},LPS^{16}),
(run^{0},run^{16}),
(MCC^{0},MCC^{16}),
(PBS^{16},PBS^{24}),
(LPS^{16},LPS^{24})
\}.
\]

Для \((A,B)\in\mathcal O\):

\[
\overline{eNRI}_A>\overline{eNRI}_B.
\]

Фиксируется

\[
\rho=1.
\]

Для каждого неравенства вводится

\[
\eta_{AB}\ge0.
\]

## 5. Статистики состояний

Для состояния \(A\):

\[
\overline{\mathbf x}_A
=
\frac{1}{|A|}
\sum_{\mathbf x\in A}\mathbf x,
\]

\[
\mathbf S_A
=
\frac{1}{|A|-1}
\sum_{\mathbf x\in A}
(\mathbf x-\overline{\mathbf x}_A)
(\mathbf x-\overline{\mathbf x}_A)^{\mathsf T}.
\]

Для пары состояний:

\[
\mathbf d_{AB}
=
\overline{\mathbf x}_A-
\overline{\mathbf x}_B.
\]

## 6. Задача оптимизации

\[
\mathbf Q=
\sum_{A\in\mathcal G}\mathbf S_A
+
\beta
\sum_{(A,B)\in\mathcal E}
\mathbf d_{AB}\mathbf d_{AB}^{\mathsf T}
+
\lambda\mathbf I.
\]

Решается

\[
\min_{\mathbf w,\boldsymbol\eta}
\left[
\mathbf w^{\mathsf T}\mathbf Q\mathbf w
+
C\sum_{(A,B)\in\mathcal O}\eta_{AB}
\right]
\]

при условиях

\[
\mathbf w^{\mathsf T}\mathbf d_{AB}
\ge
1-\eta_{AB},
\qquad
(A,B)\in\mathcal O,
\]

\[
\eta_{AB}\ge0,
\]

\[
1+
\mathbf w^{\mathsf T}
\left(
\mathbf x_i-
\overline{\mathbf x}_{PBS^{0}}
\right)
\ge\varepsilon
\]

для каждого живого наблюдения.

---

# II. Минимальный план реализации

Проект должен содержать только необходимое для решения задачи.

## 1. Минимальная структура

~~~text
enri_mouse_neuroplasticity/
├── PLAN.md
├── solve.py
├── requirements.txt
├── run.sh
├── .run
├── data/
│   └── mice.xlsx
└── results/
~~~

Никаких отдельных модулей, тестовых директорий и промежуточных скриптов не требуется.

Вся логика расчёта находится в одном файле solve.py.

## 2. solve.py: подготовка данных

В начале solve.py задать:

- список 35 признаков;
- соответствие каждого признака столбцам недель 0, 16 и 24;
- пары \(\mathcal E\);
- пары \(\mathcal O\);
- \(\varepsilon=10^{-3}\);
- сетки \(\beta,\lambda,C\);
- random seeds.

Далее:

1. прочитать data/mice.xlsx;
2. проверить наличие всех обязательных столбцов;
3. проверить ID и группы;
4. преобразовать нужные признаки в числовой формат;
5. сформировать длинную таблицу: одна строка = одна мышь в одну неделю;
6. исключить из основной оптимизации живые строки с неполным 35-мерным вектором;
7. не считать отсутствие данных у умерших животных обычным пропуском.

Промежуточные CSV сохранять только при необходимости диагностики.

## 3. solve.py: сформировать состояния

Реализовать небольшую функцию

~~~python
def mask(state, df):
    ...
~~~

которая возвращает строки для

- PBS^0, LPS^0, run^0, MCC^0;
- PBS^16, LPS^16, run^16, MCC^16;
- PBS^24, LPS^24, run^24, MCC^24.

Важно:

\[
run^{16}\subset LPS^{16},
\qquad
MCC^{16}\subset LPS^{16}.
\]

run и MCC до 24-й недели определяются по будущему назначению животного, но используют измерения до вмешательства.

## 4. solve.py: cross-validation

Использовать 4-fold разбиение по mouse_id со стратификацией по Group_24.

Все недели одной мыши должны находиться в одном fold.

Для каждого train/validation:

1. по train вычислить \(m_j,s_j\);
2. стандартизовать train;
3. теми же \(m_j,s_j\) стандартизовать validation.

Validation не должен участвовать в расчёте стандартизации.

## 5. solve.py: построить QP на train

Для train вычислить для нужных состояний:

\[
\overline{\mathbf x}_A,
\qquad
\mathbf S_A,
\qquad
\mathbf d_{AB}.
\]

Для заданных \(\beta,\lambda\):

\[
\mathbf Q=
\sum_A\mathbf S_A
+
\beta
\sum_{(A,B)\in\mathcal E}
\mathbf d_{AB}\mathbf d_{AB}^{\mathsf T}
+
\lambda\mathbf I.
\]

Затем в CVXPY создать:

~~~python
w = cp.Variable(35)
eta = cp.Variable(len(ORDER_PAIRS), nonneg=True)
~~~

Целевая функция:

~~~python
objective = cp.quad_form(w, Q) + C * cp.sum(eta)
~~~

Ограничения:

~~~python
constraints = []

for k, d in enumerate(order_diffs):
    constraints.append(w @ d >= 1 - eta[k])

for x in X_train:
    constraints.append(
        1 + w @ (x - xbar_pbs0) >= epsilon
    )
~~~

Решить:

~~~python
problem = cp.Problem(cp.Minimize(objective), constraints)
problem.solve(solver=cp.OSQP)
~~~

Первый тестовый запуск выполнить при

\[
\beta=\lambda=C=1.
\]

Если он не проходит, не запускать подбор параметров.

## 6. solve.py: подобрать \(\beta,\lambda,C\)

Сначала использовать небольшую сетку:

\[
\{0.1,1,10\}.
\]

Для каждой тройки:

1. решить QP на train;
2. получить \(\widehat{\mathbf w}\);
3. применить его к validation;
4. вычислить validation-метрики.

Основные метрики:

### Порядок

\[
h_{AB}
=
\max
\left(
0,
1-
\widehat{\mathbf w}^{\mathsf T}
\mathbf d_{AB}^{val}
\right).
\]

Использовать среднее значение \(h_{AB}\).

### Равенства

\[
e_{AB}
=
\widehat{\mathbf w}^{\mathsf T}
\mathbf d_{AB}^{val}.
\]

Использовать RMSE по парам из \(\mathcal E\).

### Положительность

Посчитать число validation-наблюдений с

\[
eNRI<\varepsilon.
\]

Параметры выбирать в таком порядке:

1. отсутствие систематических нарушений положительности;
2. минимальный order hinge;
3. меньший equality RMSE;
4. меньшая норма \(\|\mathbf w\|_2\).

Если несколько наборов почти эквивалентны, предпочесть более простое и устойчивое решение.

После отладки при необходимости расширить сетку до

\[
\{10^{-3},10^{-2},10^{-1},1,10,10^2,10^3\}.
\]

## 7. solve.py: финальная модель

После выбора

\[
(\beta^\*,\lambda^\*,C^\*)
\]

на всех доступных полных живых данных:

1. заново вычислить \(m_j,s_j\);
2. стандартизовать данные;
3. вычислить состояния;
4. вычислить \(\overline{\mathbf x}_A,\mathbf S_A,\mathbf d_{AB}\);
5. построить \(\mathbf Q\);
6. решить финальный QP;
7. получить 35 весов;
8. рассчитать eNRI для всех живых наблюдений.

## 8. Результаты

solve.py должен записать только основные файлы:

~~~text
results/
├── weights.csv
├── enri.csv
├── diagnostics.csv
└── model.json
~~~

### weights.csv

- feature;
- weight.

### enri.csv

- mouse_id;
- week;
- group_16;
- group_24;
- eNRI.

### diagnostics.csv

По каждой паре ограничений:

- type: equality/order;
- A;
- B;
- difference;
- eta — только для order;
- condition_ok.

### model.json

Сохранить:

- выбранные \(\beta,\lambda,C\);
- \(\varepsilon\);
- \(m_j,s_j\);
- 35 весов;
- random seeds;
- статус решателя.

## 9. Минимальная проверка результата

Перед завершением solve.py автоматически проверить:

1. найдено ровно 35 весов;
2. все веса конечны;
3. все \(\eta_{AB}\ge0\);
4. все живые train-наблюдения удовлетворяют \(eNRI\ge\varepsilon\) с численной погрешностью;
5. \(\overline{eNRI}_{PBS^{0}}=1\) с численной погрешностью;
6. все четыре выходных файла созданы.

Если хотя бы одна проверка не проходит, программа должна завершаться с ошибкой.

## 10. run.sh

run.sh должен быть минимальным:

~~~bash
#!/usr/bin/env bash
set -e
pip install -r requirements.txt
python solve.py
~~~

requirements.txt достаточно ограничить библиотеками:

~~~text
pandas
numpy
openpyxl
scikit-learn
cvxpy
osqp
~~~

## 11. Порядок программирования

Работать строго в таком порядке:

1. создать solve.py;
2. добавить список 35 признаков и пары \(\mathcal E,\mathcal O\);
3. прочитать Excel;
4. построить длинную таблицу;
5. реализовать mask();
6. реализовать стандартизацию;
7. вычислить \(\overline{\mathbf x}_A,\mathbf S_A,\mathbf d_{AB}\);
8. реализовать один QP при \(\beta=\lambda=C=1\);
9. проверить результат;
10. добавить 4-fold cross-validation;
11. добавить перебор небольшой сетки гиперпараметров;
12. выбрать параметры;
13. решить финальный QP на всех данных;
14. сохранить weights.csv, enri.csv, diagnostics.csv и model.json;
15. только после этого запускать через run.sh и .run.

Этого достаточно для полного решения текущей задачи. Bootstrap, дополнительные графики, отдельные модули и расширенная инфраструктура на первом этапе не нужны.
