# План программной реализации eNRI

# I. Описание задачи

## 1. Цель

По экспериментальным данным требуется найти вектор весов

\[
\mathbf w=(w_1,\ldots,w_{35})^{\mathsf T},
\]

задающий экспериментальный индекс нейропластичности живого состояния

\[
eNRI(\mathbf x)
=
1+
\mathbf w^{\mathsf T}
\left(
\mathbf x-\overline{\mathbf x}_{PBS^{0}}
\right).
\]

Здесь \(\mathbf x\) — стандартизованный вектор из 35 функциональных признаков. Шкала фиксируется условием

\[
\overline{eNRI}_{PBS^{0}}=1.
\]

Смерть задаётся отдельно:

\[
eNRI(death)=0.
\]

Принадлежность животного к экспериментальной группе не входит в \(\mathbf x\). Группы используются только для задания ограничений на eNRI.

## 2. Признаки

Используются 35 функциональных признаков, сопоставимых на 0-й, 16-й и 24-й неделях.

### 2.1. OFT — 5 признаков

1. OFT_distance
2. Average_speed_OFT
3. Total_time_mobile_OFT
4. Absolute_turn_angle_OFT
5. Time_inCenter_OFT

### 2.2. NOR1 — 8 признаков

6. Total distance travelled_NOR1
7. Average speed_NOR1
8. Time investigating Piramidka_NOR1
9. Latency to first investigation of Piramidka_NOR1
10. Time investigating Stakan_NOR1
11. Latency to first investigation of Stakan_NOR1
12. Latency to first investigation_NOR1
13. Total time investigating_NOR1

### 2.3. NOR2 — 9 признаков

14. Total distance travelled_NOR2
15. Average speed_NOR2
16. Time investigating Piramidka zone_NOR2
17. Latency to first investigation of Piramidka zone_NOR2
18. Time investigating Stakan zone_NOR2
19. Latency to first investigation of Stakan zone_NOR2
20. DI_NOR2
21. Latency to first investigation_NOR2
22. Total time investigating_NOR2

### 2.4. Rotarod learning — 9 признаков

23. Learning T1mean
24. Learning T1max
25. Learning T1sum
26. Learning T2mean
27. Learning T2max
28. Learning T2sum
29. Learning T3mean
30. Learning T3max
31. Learning T3sum

### 2.5. Остальные признаки — 4 признака

32. EnduranceT
33. rear_support
34. rear_nosupport
35. Weight

В основной вектор признаков не включаются группы, идентификатор животного, Eight_item_index, CoFI, Grip, Y-maze, социальные и депрессивные тесты, молекулярные и биохимические показатели, а также признаки, отсутствующие хотя бы в одной из недель 0, 16 и 24.

## 3. Исходные и стандартизованные значения

Исходный вектор измерений:

\[
\mathbf r=(r_1,\ldots,r_{35})^{\mathsf T}.
\]

Стандартизованный вектор:

\[
\mathbf x=(x_1,\ldots,x_{35})^{\mathsf T},
\]

где

\[
x_j=\frac{r_j-m_j}{s_j}.
\]

Параметры \(m_j\) и \(s_j\) должны быть общими для всех недель. При кросс-валидации они вычисляются только по обучающей части данных.

## 4. Экспериментальные состояния

Используются состояния

\[
PBS^{0},\ LPS^{0},\ run^{0},\ MCC^{0},
\]

\[
PBS^{16},\ LPS^{16},\ run^{16},\ MCC^{16},
\]

\[
PBS^{24},\ LPS^{24},\ run^{24},\ MCC^{24}.
\]

Состояния \(run^{0}\), \(MCC^{0}\), \(run^{16}\), \(MCC^{16}\) определяются по будущему назначению животного после второй рандомизации, но используют измерения до начала соответствующего вмешательства.

## 5. Ограничения, связанные с рандомизацией

\[
\mathcal E=
\{
(PBS^{0},LPS^{0}),
(LPS^{16},run^{16}),
(LPS^{16},MCC^{16})
\}.
\]

Для пар \((A,B)\in\mathcal E\) средние значения eNRI должны быть близки.

## 6. Ограничения порядка

\[
\mathcal O_1=
\{
(PBS^{16},LPS^{16}),
(PBS^{24},LPS^{24}),
(run^{24},LPS^{24}),
(MCC^{24},LPS^{24})
\}.
\]

\[
\mathcal O_2=
\{
(PBS^{0},PBS^{16}),
(LPS^{0},LPS^{16}),
(run^{0},run^{16}),
(MCC^{0},MCC^{16})
\}.
\]

\[
\mathcal O_3=
\{
(PBS^{16},PBS^{24}),
(LPS^{16},LPS^{24})
\}.
\]

\[
\mathcal O=
\mathcal O_1\cup
\mathcal O_2\cup
\mathcal O_3.
\]

Для ветвей run и MCC знак изменения между 16-й и 24-й неделями заранее не задаётся.

Фиксируется

\[
\rho=1.
\]

Для каждой пары \((A,B)\in\mathcal O\) вводится переменная послабления

\[
\eta_{AB}\ge0.
\]

## 7. Статистики экспериментальных состояний

Для каждого состояния \(A\):

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

Для каждой пары \((A,B)\in\mathcal E\cup\mathcal O\):

\[
\mathbf d_{AB}
=
\overline{\mathbf x}_A-
\overline{\mathbf x}_B.
\]

## 8. Итоговая задача оптимизации

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

\[
\min_{\mathbf w,\boldsymbol\eta}
\left[
\mathbf w^{\mathsf T}\mathbf Q\mathbf w
+
C
\sum_{(A,B)\in\mathcal O}\eta_{AB}
\right]
\]

при

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

и

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

# II. План работы

## Этап 1. Подготовка проекта и входных данных

### 1.1. Создать структуру проекта

~~~text
enri_mouse_neuroplasticity/
├── PLAN.md
├── README.md
├── requirements.txt
├── run.sh
├── .run
├── data/
│   ├── raw/
│   │   └── mice.xlsx
│   └── processed/
│       ├── observations_long.csv
│       ├── observations_complete.csv
│       └── missingness_report.csv
├── src/
│   ├── config.py
│   ├── load_data.py
│   ├── build_dataset.py
│   ├── standardize.py
│   ├── states.py
│   ├── statistics.py
│   ├── qp.py
│   ├── cross_validation.py
│   ├── bootstrap.py
│   ├── diagnostics.py
│   └── main.py
├── tests/
└── results/
~~~

### 1.2. Зафиксировать конфигурацию

В config.py:

- записать FEATURE_NAMES из 35 признаков;
- задать соответствие каждого признака столбцам Excel на неделях 0, 16 и 24;
- задать EQUALITY_PAIRS;
- задать ORDER_PAIRS;
- задать \(\varepsilon\);
- задать сетки \(\beta,\lambda,C\);
- задать random seeds.

Перед запуском проверить, что все 105 ожидаемых столбцов существуют и каждый сопоставлен ровно одному признаку и одной неделе.

### 1.3. Загрузить и проверить Excel

В load_data.py:

1. прочитать исходный лист;
2. сохранить исходные названия столбцов;
3. определить идентификатор животного;
4. проверить число уникальных животных;
5. проверить отсутствие дубликатов ID;
6. проверить значения Group_16 и Group_24;
7. проверить допустимые переходы PBS/LPS;
8. преобразовать 35 признаков в числовой тип;
9. вывести отчёт обо всех значениях, превратившихся в NaN.

При нарушении схемы данных прекращать расчёт.

### 1.4. Перевести данные в длинный формат

В build_dataset.py сформировать строки

\[
(\text{mouse\_id},t,\mathbf r_i^t),
\qquad
t\in\{0,16,24\}.
\]

В observations_long.csv хранить:

- mouse_id;
- week;
- group_16;
- group_24;
- alive;
- 35 исходных признаков.

## Этап 2. Контроль пропусков и формирование состояний

### 2.1. Обработать пропуски

1. Посчитать missing_count по 35 признакам.
2. Если missing_count = 0, допустить строку в основную модель.
3. Если week = 24 и животное умерло, не считать отсутствие функциональных данных обычным пропуском.
4. Если животное живо и missing_count > 0, исключить строку из основной complete-case модели.
5. Записать исключённые строки в missingness_report.csv.
6. Не применять глобальное заполнение медианой.

Создать observations_complete.csv только из полных живых наблюдений.

### 2.2. Реализовать состояния

В states.py реализовать

~~~python
get_state_mask(df, state_name) -> boolean mask
~~~

для всех состояний из раздела I.

Не использовать единственный категориальный столбец state как единственный источник логики, поскольку \(run^{16}\subset LPS^{16}\) и \(MCC^{16}\subset LPS^{16}\).

### 2.3. Проверить размеры состояний

Для каждого состояния вывести:

- число исходных наблюдений;
- число полных наблюдений;
- число исключённых из-за пропусков.

Для состояний, участвующих в ковариационных матрицах, должно оставаться не менее двух наблюдений.

## Этап 3. Разбиение данных и стандартизация

### 3.1. Организовать кросс-валидацию по мышам

В cross_validation.py:

1. сформировать список уникальных mouse_id;
2. стратифицировать по Group_24;
3. использовать 4-fold StratifiedGroupKFold с shuffle=True;
4. повторить разбиение для нескольких random_state;
5. все временные точки одной мыши держать в одной части.

### 3.2. Выполнять стандартизацию внутри fold

В standardize.py:

1. по train-строкам вычислить \(m_j\);
2. по train-строкам вычислить \(s_j\);
3. проверить \(s_j>0\);
4. стандартизовать train;
5. теми же \(m_j,s_j\) стандартизовать validation;
6. сохранить параметры стандартизации.

Не стандартизовать отдельно по неделям или группам.

## Этап 4. Построение статистик и QP

### 4.1. Рассчитать статистики состояний

В statistics.py реализовать:

~~~python
compute_state_mean(X, mask)
compute_state_cov(X, mask)
compute_difference(xbar_A, xbar_B)
~~~

Для train вычислить:

- \(\overline{\mathbf x}_A\);
- \(\mathbf S_A\);
- \(\mathbf d_{AB}\).

Проверить размеры, симметрию ковариационных матриц и отсутствие NaN/Inf.

### 4.2. Построить матрицу Q

В qp.py реализовать:

~~~python
build_Q(state_covs, equality_diffs, beta, lam) -> Q
~~~

После построения:

1. выполнить
   \[
   \mathbf Q\leftarrow
   \frac{\mathbf Q+\mathbf Q^{\mathsf T}}{2};
   \]
2. проверить собственные значения;
3. записать condition number;
4. проверить положительную определённость при \(\lambda>0\).

### 4.3. Реализовать QP в CVXPY

Создать

\[
\mathbf w\in\mathbb R^{35},
\qquad
\boldsymbol\eta\in\mathbb R^{K}.
\]

Целевая функция:

\[
\mathbf w^{\mathsf T}\mathbf Q\mathbf w
+
C\sum_{k=1}^{K}\eta_k.
\]

Ограничения:

\[
\mathbf w^{\mathsf T}\mathbf d_k
\ge
1-\eta_k,
\]

\[
\eta_k\ge0,
\]

\[
1+
\mathbf w^{\mathsf T}
\left(
\mathbf x_i-
\overline{\mathbf x}_{PBS^{0}}
\right)
\ge\varepsilon.
\]

Начать с

\[
\varepsilon=10^{-3}.
\]

Использовать CVXPY + OSQP.

### 4.4. Провести smoke test

Первый запуск:

\[
\beta=1,\qquad
\lambda=1,\qquad
C=1.
\]

Проверить:

- статус решателя;
- конечность 35 весов;
- неотрицательность \(\eta\);
- выполнение всех ограничений;
- минимальный eNRI;
- воспроизводимость результата.

До успешного smoke test не переходить к подбору гиперпараметров.

## Этап 5. Подбор гиперпараметров

### 5.1. Сначала использовать сокращённую сетку

\[
\beta,\lambda,C
\in
\{0.1,1,10\}.
\]

После проверки pipeline перейти к полной сетке:

\[
\{10^{-3},10^{-2},10^{-1},1,10,10^2,10^3\}.
\]

### 5.2. Для каждой тройки решить QP на train

Для каждой комбинации \((\beta,\lambda,C)\):

1. построить \(\mathbf Q\);
2. решить QP;
3. сохранить \(\widehat{\mathbf w}\);
4. сохранить \(\widehat{\boldsymbol\eta}\);
5. сохранить статус и значение целевой функции.

### 5.3. Проверить модель на validation

Не переобучать \(\mathbf w\).

Для каждой пары порядка:

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

Сохранить:

- mean_order_hinge;
- max_order_hinge;
- долю выполненных margin;
- долю пар с правильным знаком.

Для равенств:

\[
e_{AB}
=
\widehat{\mathbf w}^{\mathsf T}
\mathbf d_{AB}^{val},
\]

\[
equality\_rmse
=
\sqrt{
\frac{1}{|\mathcal E_{val}|}
\sum e_{AB}^2
}.
\]

Для положительности сохранить:

- minimum_eNRI;
- число \(eNRI<\varepsilon\);
- долю таких наблюдений.

Также вычислить внутригрупповой разброс eNRI.

### 5.4. Выбрать гиперпараметры

Порядок выбора:

1. исключить варианты с систематическим нарушением положительности;
2. минимизировать median mean_order_hinge;
3. при близком результате предпочесть меньший equality_rmse;
4. затем меньший внутригрупповой разброс;
5. при практически одинаковом результате предпочесть меньшую \(\|\mathbf w\|_2\) и более устойчивое направление весов.

Устойчивость направления оценивать через cosine similarity между \(\mathbf w\) разных fold.

Результаты сохранить в results/hyperparameter_search.csv.

## Этап 6. Обучение финальной модели

### 6.1. Переобучить на всех доступных данных

После выбора

\[
(\beta^\*,\lambda^\*,C^\*)
\]

выполнить:

1. вычислить финальные \(m_j,s_j\);
2. стандартизовать все полные живые наблюдения;
3. построить состояния;
4. вычислить \(\overline{\mathbf x}_A\), \(\mathbf S_A\), \(\mathbf d_{AB}\);
5. построить \(\mathbf Q\);
6. решить финальный QP.

### 6.2. Сохранить веса

Создать weights.csv:

- feature;
- weight;
- abs_weight;
- rank_abs_weight.

Сохранить параметры стандартизации.

### 6.3. Рассчитать eNRI

Для каждого полного живого наблюдения:

\[
eNRI_i
=
1+
\widehat{\mathbf w}^{\mathsf T}
\left(
\mathbf x_i-
\overline{\mathbf x}_{PBS^{0}}
\right).
\]

Создать enri_values.csv:

- mouse_id;
- week;
- group_16;
- group_24;
- eNRI.

Для death использовать

\[
eNRI(death)=0.
\]

## Этап 7. Диагностика финального решения

### 7.1. Ограничения порядка

Создать constraints_order.csv:

- A;
- B;
- mean_eNRI_A;
- mean_eNRI_B;
- difference;
- eta;
- margin_required;
- margin_residual;
- order_sign_ok.

### 7.2. Равенства

Создать constraints_equality.csv:

- A;
- B;
- mean_eNRI_A;
- mean_eNRI_B;
- difference;
- squared_difference.

### 7.3. Сводка состояний

Создать state_summary.csv:

- state;
- n;
- mean_eNRI;
- sd_eNRI;
- min_eNRI;
- max_eNRI.

## Этап 8. Оценка устойчивости

### 8.1. Bootstrap по мышам

1. выбирать mouse_id с возвращением;
2. включать все временные точки выбранной мыши;
3. заново стандартизовать данные;
4. заново решать QP;
5. использовать уже выбранные \(\beta^\*,\lambda^\*,C^\*\);
6. выполнить не менее 500 успешных итераций, желательно 1000.

### 8.2. Оценить устойчивость весов

Для каждого признака вычислить:

- медиану веса;
- 2.5% и 97.5% квантили;
- долю положительных значений;
- долю отрицательных значений;
- частоту смены знака относительно финального веса.

Сохранить bootstrap_weights.csv.

## Этап 9. Тесты и воспроизводимость

### 9.1. Проверить признаки

- ровно 35 признаков;
- нет дубликатов;
- есть отображение на 0, 16 и 24 недели.

### 9.2. Проверить состояния

- PBS не пересекается с LPS;
- \(run^{16}\subset LPS^{16}\);
- \(MCC^{16}\subset LPS^{16}\);
- \(run^{24}\), \(MCC^{24}\), \(LPS^{24}\) попарно не пересекаются.

### 9.3. Проверить стандартизацию

На train:

- средние близки к 0;
- стандартные отклонения близки к 1;
- validation не используется при вычислении \(m_j,s_j\).

### 9.4. Проверить QP

- \(\mathbf Q\) имеет размер \(35\times35\);
- \(\mathbf Q\) симметрична;
- веса конечны;
- \(\eta_k\ge0\);
- все ограничения выполнены;
- \(eNRI\ge\varepsilon\) для train-наблюдений.

### 9.5. Сделать единый запуск

main.py должен последовательно выполнять:

1. загрузку данных;
2. подготовку таблицы;
3. проверки;
4. подбор гиперпараметров;
5. финальное обучение;
6. диагностику;
7. bootstrap;
8. сохранение результатов.

run.sh устанавливает зависимости и запускает main.py.

.run изменяется только для запуска общего GitHub Actions workflow.

## Этап 10. Критерий завершения

Работа считается завершённой, если получены:

- подготовленная таблица данных;
- отчёт о пропусках;
- параметры стандартизации;
- выбранные \(\beta^\*,\lambda^\*,C^\*\);
- финальные 35 весов;
- eNRI всех допустимых живых наблюдений;
- значения \(\eta_{AB}\);
- отчёты по \(\mathcal E\) и \(\mathcal O\);
- результаты cross-validation;
- bootstrap-оценка устойчивости;
- run_metadata.json с random seeds, версиями библиотек и параметрами запуска.

После этого можно переходить к содержательной интерпретации весов и траекторий eNRI.
