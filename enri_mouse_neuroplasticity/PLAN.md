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

Группа животного не входит в \(\mathbf x\) и используется только для задания ограничений. Значение \(eNRI(death)=0\) является заданной границей шкалы, а не оценкой по функциональным данным умершего животного.

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

## 3. Определение экспериментальных состояний

Обозначения \(LPS^t\), \(run^t\), \(MCC^t\) всегда относятся к одной и той же будущей/фактической ветви животного.

На неделях 0 и 16:

- \(LPS^t\) — животные исходной LPS-группы, которые после второй рандомизации останутся в обычной LPS-ветви;
- \(run^t\) — животные исходной LPS-группы, которые после второй рандомизации попадут в ветвь run;
- \(MCC^t\) — животные исходной LPS-группы, которые после второй рандомизации попадут в ветвь MCC.

Измерения недели 16 выполняются до начала run/MCC-вмешательств.

Вся исходная LPS-когорта до второй рандомизации задаётся объединением

\[
\mathcal L^t
=
LPS^t\cup run^t\cup MCC^t,
\qquad
t\in\{0,16\}.
\]

\(\mathcal L^t\) не является новой экспериментальной группой; это сокращение для объединения трёх ветвей.

На неделе 24 используются фактические ветви

\[
LPS^{24},\qquad run^{24},\qquad MCC^{24}.
\]

## 4. Стандартизация

Исходный вектор:

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

Параметры стандартизации вычисляются только по baseline-наблюдениям train-мышей:

\[
m_j
=
\operatorname{mean}
\{r_{ij}^{0}: i\in train\},
\]

\[
s_j
=
\operatorname{sd}
\{r_{ij}^{0}: i\in train\}.
\]

Те же \(m_j,s_j\) применяются к неделям 0, 16 и 24. При финальном обучении \(m_j,s_j\) вычисляются по baseline-наблюдениям всех допустимых мышей.

Если \(s_j=0\), расчёт завершается с ошибкой.

## 5. Ограничения, связанные с рандомизацией

Для исходной рандомизации:

\[
(PBS^0,\mathcal L^0).
\]

Для второй рандомизации на неделе 16:

\[
(LPS^{16},run^{16}),
\qquad
(LPS^{16},MCC^{16}).
\]

Поэтому

\[
\mathcal E
=
\{
(PBS^0,\mathcal L^0),
(LPS^{16},run^{16}),
(LPS^{16},MCC^{16})
\}.
\]

Для пар \((A,B)\in\mathcal E\) средние значения eNRI должны быть близки.

## 6. Ограничения порядка

\[
\mathcal O_1
=
\{
(PBS^{16},\mathcal L^{16}),
(PBS^{24},LPS^{24}),
(run^{24},LPS^{24}),
(MCC^{24},LPS^{24})
\}.
\]

\[
\mathcal O_2
=
\{
(PBS^0,PBS^{16}),
(\mathcal L^0,\mathcal L^{16})
\}.
\]

\[
\mathcal O_3
=
\{
(PBS^{16},PBS^{24}),
(LPS^{16},LPS^{24})
\}.
\]

\[
\mathcal O
=
\mathcal O_1\cup
\mathcal O_2\cup
\mathcal O_3.
\]

Для \((A,B)\in\mathcal O\):

\[
\overline{eNRI}_A>\overline{eNRI}_B.
\]

Для ветвей run и MCC отношение между неделями 16 и 24 заранее не задаётся.

Фиксируется

\[
\rho=1.
\]

Для каждого неравенства вводится

\[
\eta_{AB}\ge0.
\]

## 7. Неперекрывающиеся состояния для внутригрупповой дисперсии

Чтобы одна мышь не учитывалась несколько раз в первом члене целевой функции, используется

\[
\mathcal G=
\{
PBS^0,LPS^0,run^0,MCC^0,
PBS^{16},LPS^{16},run^{16},MCC^{16},
PBS^{24},LPS^{24},run^{24},MCC^{24}
\}.
\]

Объединения \(\mathcal L^0\) и \(\mathcal L^{16}\) применяются для средних и ограничений, но не добавляются отдельно в \(\mathcal G\).

## 8. Статистики состояний

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

Для пары:

\[
\mathbf d_{AB}
=
\overline{\mathbf x}_A-
\overline{\mathbf x}_B.
\]

## 9. Задача оптимизации

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

Перед передачей в решатель:

\[
\mathbf Q
\leftarrow
\frac{\mathbf Q+\mathbf Q^{\mathsf T}}{2}.
\]

Решается

\[
\min_{\mathbf w,\boldsymbol\eta}
\left[
\mathbf w^{\mathsf T}\mathbf Q\mathbf w
+
C
\sum_{(A,B)\in\mathcal O}\eta_{AB}
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

Допустимо тривиальное решение

\[
\mathbf w=\mathbf0,
\qquad
\eta_{AB}=1,
\]

поэтому успешный статус решателя сам по себе не является критерием качества eNRI.

---

# II. Минимальный план реализации

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

Вся логика находится в одном solve.py.

## 2. Этап 1. Загрузка и проверка данных

### 2.1. Константы

В начале solve.py задать:

- список 35 признаков;
- точное соответствие признаков столбцам недель 0, 16 и 24;
- \(\mathcal E\);
- \(\mathcal O\);
- \(\mathcal G\);
- \(\varepsilon=10^{-3}\);
- сетки \(\beta,\lambda,C\);
- random seeds.

### 2.2. Прочитать Excel

1. Прочитать data/mice.xlsx.
2. Проверить наличие обязательных столбцов.
3. Проверить ID животных.
4. Проверить значения групп и допустимые переходы.
5. Преобразовать 35 признаков в числовой формат.
6. Не определять смерть автоматически по NaN.

Если схема данных нарушена, остановить расчёт.

### 2.3. Построить длинную таблицу

Одна строка:

\[
(\text{mouse\_id},t,\mathbf r_i^t),
\qquad
t\in\{0,16,24\}.
\]

Хранить mouse_id, week, ветви, известный статус alive/death и 35 признаков.

Если достоверного индикатора смерти нет, отсутствие измерений трактовать как отсутствие наблюдения, а не как death.

## 3. Этап 2. Preflight пропусков и состояний

### 3.1. Проверить пропуски до QP

Для каждой строки:

1. посчитать missing_count по 35 признакам;
2. допускать в основную модель только полные живые наблюдения;
3. живые неполные строки исключать;
4. не выполнять глобальное заполнение медианой;
5. не присваивать eNRI=0 только из-за отсутствия данных.

До продолжения вывести для каждого состояния число всех, полных и исключённых наблюдений.

Если для любого состояния из \(\mathcal G\), для которого нужна ковариационная матрица,

\[
n_A<2,
\]

остановить расчёт и сначала решить проблему пропусков.

### 3.2. Реализовать маски состояний

Одна функция:

~~~python
def mask(state, df):
    ...
~~~

должна поддерживать:

- PBS^0, LPS^0, run^0, MCC^0;
- PBS^16, LPS^16, run^16, MCC^16;
- PBS^24, LPS^24, run^24, MCC^24;
- L^0 = LPS^0 ∪ run^0 ∪ MCC^0;
- L^16 = LPS^16 ∪ run^16 ∪ MCC^16.

Проверить попарную непересекаемость LPS, run и MCC внутри каждой недели и правильность объединений \(\mathcal L^0,\mathcal L^{16}\).

## 4. Этап 3. Cross-validation и стандартизация

### 4.1. Разбиение по mouse_id

Использовать 4-fold разбиение по mouse_id со стратификацией по финальной ветви.

Все недели одной мыши должны находиться только в train или только в validation.

После построения fold проверить:

- каждое train-состояние из \(\mathcal G\) содержит минимум 2 полных наблюдения;
- каждое состояние, используемое в validation-метриках, содержит минимум 1 наблюдение.

Если split невалиден, попробовать другой seed. Если 4-fold регулярно невалиден, перейти на 3-fold.

### 4.2. Стандартизация

Для каждого fold:

1. взять только baseline train-мышей;
2. вычислить \(m_j,s_j\);
3. проверить \(s_j>0\);
4. стандартизовать train всех недель;
5. теми же \(m_j,s_j\) стандартизовать validation.

Validation не участвует в расчёте \(m_j,s_j\).

## 5. Этап 4. Построение и решение QP

### 5.1. Статистики train

Для train вычислить

\[
\overline{\mathbf x}_A,
\qquad
\mathbf S_A,
\qquad
\mathbf d_{AB}.
\]

\(\mathbf S_A\) вычислять только для \(A\in\mathcal G\).

Средние для \(\mathcal L^0\) и \(\mathcal L^{16}\) вычислять отдельно для ограничений.

### 5.2. Матрица Q

Построить

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

Затем симметризовать:

\[
\mathbf Q
\leftarrow
\frac{\mathbf Q+\mathbf Q^{\mathsf T}}{2}.
\]

Проверить размер 35×35, конечность элементов, симметрию и минимальное собственное значение.

### 5.3. CVXPY

~~~python
w = cp.Variable(35)
eta = cp.Variable(len(ORDER_PAIRS), nonneg=True)

objective = cp.quad_form(w, Q) + C * cp.sum(eta)

constraints = []

for k, d in enumerate(order_diffs):
    constraints.append(w @ d >= 1 - eta[k])

for x in X_train:
    constraints.append(
        1 + w @ (x - xbar_pbs0_train) >= epsilon
    )

problem = cp.Problem(cp.Minimize(objective), constraints)
problem.solve(solver=cp.OSQP)
~~~

Первый smoke test:

\[
\beta=\lambda=C=1.
\]

До успешного smoke test не запускать подбор параметров.

## 6. Этап 5. Защита от тривиального решения

После каждого решения вычислить

\[
\|\mathbf w\|_2,
\]

\[
\overline{\eta}
=
\frac1{|\mathcal O|}
\sum_{(A,B)\in\mathcal O}\eta_{AB},
\]

\[
\Delta_{AB}
=
\mathbf w^{\mathsf T}\mathbf d_{AB}.
\]

Сохранить долю пар с \(\Delta_{AB}>0\), долю выполненных margin, mean_eta и max_eta.

Технически отклонять решение, если

\[
\|\mathbf w\|_2<10^{-8}
\]

или доля пар с правильным знаком меньше 0.5.

mean_eta и max_eta всегда сохранять в diagnostics.csv. Эти пороги являются защитой от вырожденного решения и должны быть явно заданы в коде.

## 7. Этап 6. Подбор гиперпараметров

### 7.1. Сетка

Сначала использовать

\[
\{0.1,1,10\}.
\]

После отладки при необходимости расширить до

\[
\{10^{-3},10^{-2},10^{-1},1,10,10^2,10^3\}.
\]

### 7.2. Validation использует train-параметры

На validation использовать

\[
m_j^{train},
\qquad
s_j^{train},
\qquad
\overline{\mathbf x}_{PBS^0}^{train},
\qquad
\widehat{\mathbf w}.
\]

Центр \(\overline{\mathbf x}_{PBS^0}\) для формулы eNRI на validation не пересчитывать.

Групповые validation-средние вычислять только для проверки отношений.

### 7.3. Метрики

Положительность:

\[
V_{\mathrm{pos}}
=
\frac{
\#\{i:eNRI_i<\varepsilon\}
}{
N_{val}
}.
\]

Порядок:

\[
V_{\mathrm{ord}}
=
\frac1{|\mathcal O_{val}|}
\sum_{(A,B)\in\mathcal O_{val}}
\max
\left(
0,
1-
\widehat{\mathbf w}^{\mathsf T}
\mathbf d_{AB}^{val}
\right).
\]

Равенства:

\[
V_{\mathrm{eq}}
=
\sqrt{
\frac1{|\mathcal E_{val}|}
\sum_{(A,B)\in\mathcal E_{val}}
\left(
\widehat{\mathbf w}^{\mathsf T}
\mathbf d_{AB}^{val}
\right)^2
}.
\]

Сложность:

\[
V_w=\|\widehat{\mathbf w}\|_2.
\]

Если конкретная validation-пара недоступна из-за отсутствующего состояния, не включать её в метрику этого fold.

### 7.4. Правило выбора

После агрегации метрик по fold выбирать параметры лексикографически по

\[
(
V_{\mathrm{pos}},
V_{\mathrm{ord}},
V_{\mathrm{eq}},
V_w
).
\]

Порядок:

1. минимальное нарушение положительности;
2. минимальный order hinge;
3. минимальный equality RMSE;
4. минимальная норма весов.

Ручного выбора после расчёта не должно быть.

## 8. Этап 7. Финальная модель

После выбора

\[
(\beta^\*,\lambda^\*,C^\*)
\]

на всех допустимых данных:

1. вычислить baseline \(m_j,s_j\);
2. стандартизовать все недели;
3. построить состояния;
4. вычислить \(\overline{\mathbf x}_A,\mathbf S_A,\mathbf d_{AB}\);
5. построить и симметризовать \(\mathbf Q\);
6. решить финальный QP;
7. проверить отсутствие тривиального решения;
8. получить 35 весов;
9. рассчитать eNRI всех полных живых наблюдений.

eNRI=0 присваивать только достоверно известным смертям.

## 9. Этап 8. Результаты

Сохранять только:

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
- eNRI;
- status.

### diagnostics.csv

Хранить:

- type;
- A;
- B;
- difference;
- eta;
- condition_ok;
- mean_eta;
- max_eta;
- weight_norm;
- positive_order_fraction;
- solver_status.

### model.json

Сохранить:

~~~json
{
  "features": [],
  "feature_columns": {},
  "mean": [],
  "std": [],
  "xbar_pbs0": [],
  "weights": [],
  "beta": null,
  "lambda": null,
  "C": null,
  "epsilon": 0.001,
  "random_seeds": [],
  "solver_status": null
}
~~~

Порядок features, mean, std, xbar_pbs0 и weights должен совпадать.

## 10. Этап 9. Финальные проверки

Перед успешным завершением проверить:

1. найдено ровно 35 весов;
2. все веса конечны;
3. \(\mathbf Q\) симметрична;
4. все \(\eta_{AB}\ge0\);
5. все полные живые train-наблюдения имеют \(eNRI\ge\varepsilon\) с численной погрешностью;
6. \(\overline{eNRI}_{PBS^0}=1\) с численной погрешностью;
7. решение не является тривиальным;
8. созданы четыре выходных файла;
9. model.json достаточен для повторного вычисления eNRI без исходного training-кода.

Если обязательная проверка не проходит, программа завершается с ошибкой.

## 11. Этап 10. run.sh и requirements.txt

run.sh:

~~~bash
#!/usr/bin/env bash
set -e
pip install -r requirements.txt
python solve.py
~~~

requirements.txt:

~~~text
pandas
numpy
openpyxl
scikit-learn
cvxpy
osqp
~~~

## 12. Порядок программирования

1. Создать solve.py.
2. Задать 35 признаков, \(\mathcal E\), \(\mathcal O\), \(\mathcal G\).
3. Реализовать чтение Excel и проверки схемы.
4. Построить длинную таблицу.
5. Реализовать preflight пропусков.
6. Реализовать mask() и \(\mathcal L^0,\mathcal L^{16}\).
7. Реализовать baseline-стандартизацию.
8. Рассчитать \(\overline{\mathbf x}_A,\mathbf S_A,\mathbf d_{AB}\).
9. Реализовать один QP при \(\beta=\lambda=C=1\).
10. Добавить проверку тривиального решения.
11. Добавить валидное 4-fold/3-fold разбиение по мышам.
12. Добавить validation-метрики.
13. Добавить детерминированный выбор \(\beta,\lambda,C\).
14. Решить финальный QP.
15. Сохранить weights.csv, enri.csv, diagnostics.csv, model.json.
16. Проверить воспроизводимость.
17. Только после этого запускать через run.sh и .run.

Этого достаточно для решения текущей задачи без лишней инфраструктуры.
