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

## 3. Экспериментальные состояния

Обозначения \(LPS^t\), \(run^t\), \(MCC^t\) всегда относятся к одной и той же будущей/фактической ветви животного.

На неделях 0 и 16:

- \(LPS^t\) — животные исходной LPS-группы, которые после второй рандомизации останутся в обычной LPS-ветви;
- \(run^t\) — животные исходной LPS-группы, которые после второй рандомизации попадут в ветвь run;
- \(MCC^t\) — животные исходной LPS-группы, которые после второй рандомизации попадут в ветвь MCC.

Измерения недели 16 выполняются до начала run/MCC-вмешательств.

Вся исходная LPS-когорта определяется непосредственно как все животные исходной LPS-группы, имеющие допустимое наблюдение в соответствующую неделю:

\[
\mathcal L^0
=
\{\text{все исходные LPS-мыши с допустимым наблюдением на неделе 0}\},
\]

\[
\mathcal L^{16}
=
\{\text{все исходные LPS-мыши с допустимым наблюдением на неделе 16}\}.
\]

Если конечная ветвь известна для всех животных, дополнительно должно выполняться

\[
\mathcal L^t
=
LPS^t\cup run^t\cup MCC^t,
\qquad
t\in\{0,16\}.
\]

Это равенство используется как проверка согласованности данных, а не как единственный способ построения \(\mathcal L^t\).

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

Параметры стандартизации вычисляются только по полным baseline-наблюдениям train-мышей:

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

Те же \(m_j,s_j\) применяются к неделям 0, 16 и 24.

При финальном обучении \(m_j,s_j\) вычисляются по полным baseline-наблюдениям всех допустимых мышей.

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

Межгрупповые отношения внутри одной недели:

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

Продольные отношения:

\[
\mathcal O_2
=
\{
(PBS^0,PBS^{16}),
(\mathcal L^0,\mathcal L^{16}),
(PBS^{16},PBS^{24}),
(LPS^{16},LPS^{24})
\}.
\]

Итог:

\[
\mathcal O
=
\mathcal O_1\cup\mathcal O_2.
\]

Для \((A,B)\in\mathcal O\):

\[
\overline{eNRI}_A>\overline{eNRI}_B.
\]

Для ветвей run и MCC отношение между неделями 16 и 24 заранее не задаётся.

## 7. Margin

Margin не фиксируется равным 1.

Используется положительный гиперпараметр

\[
\rho>0.
\]

Ограничение порядка:

\[
\mathbf w^{\mathsf T}\mathbf d_{AB}
\ge
\rho-\eta_{AB},
\qquad
\eta_{AB}\ge0.
\]

Начальная сетка:

\[
\rho\in\{0.05,0.1,0.2,0.3\}.
\]

Такой выбор совместим с нормировкой \(PBS^0=1\) и положительностью живых состояний и не допускает автоматического тривиального решения с \(\mathbf w=0,\eta=0\).

## 8. Состояния для внутригрупповой дисперсии

До начала run/MCC-вмешательств будущие ветви не разделяются в члене внутригрупповой дисперсии.

Используется

\[
\mathcal G=
\{
PBS^0,\mathcal L^0,
PBS^{16},\mathcal L^{16},
PBS^{24},LPS^{24},run^{24},MCC^{24}
\}.
\]

Это уменьшает шум ковариационных матриц и не даёт одной мыши несколько раз входить в один и тот же временной слой первого члена целевой функции.

## 9. Статистики состояний

Для обычного состояния \(A\):

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

Для межгрупповой пары в одной неделе:

\[
\mathbf d_{AB}
=
\overline{\mathbf x}_A-
\overline{\mathbf x}_B.
\]

Для продольной пары сравниваются только одни и те же мыши.

Если \(A^{t_1}\) и \(B^{t_2}\) относятся к одной траектории, сначала определяется множество

\[
M_{AB}
=
\{
i:
\text{мышь }i
\text{ имеет полный вектор и в }t_1,\text{ и в }t_2
\}.
\]

Затем

\[
\mathbf d_{AB}^{paired}
=
\frac1{|M_{AB}|}
\sum_{i\in M_{AB}}
\left(
\mathbf x_i^{t_1}
-
\mathbf x_i^{t_2}
\right).
\]

Для продольных ограничений из \(\mathcal O_2\) используется именно \(\mathbf d_{AB}^{paired}\), а не разность средних по различающимся наборам мышей.

## 10. Задача оптимизации

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

при

\[
\mathbf w^{\mathsf T}\mathbf d_{AB}
\ge
\rho-\eta_{AB},
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

для каждого полного живого наблюдения.

При продольной паре в ограничение подставляется \(\mathbf d_{AB}^{paired}\).

---

# II. Минимальный план реализации

## 1. Структура проекта

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

В solve.py задать:

- 35 признаков;
- точное соответствие признаков столбцам недель 0, 16 и 24;
- \(\mathcal E\);
- межгрупповые и продольные пары \(\mathcal O\);
- \(\mathcal G\);
- \(\varepsilon=10^{-3}\);
- сетку \(\rho\);
- сетки \(\beta,\lambda,C\);
- список random seeds.

### 2.2. Прочитать Excel

1. Прочитать data/mice.xlsx.
2. Проверить обязательные столбцы.
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

Хранить:

- mouse_id;
- week;
- исходную и конечную ветвь;
- известный статус alive/death;
- 35 признаков.

Если достоверного индикатора смерти нет, отсутствие измерений трактовать как отсутствие наблюдения, а не как death.

## 3. Этап 2. Preflight пропусков и состояний

### 3.1. Отчёт по пропускам

До QP:

1. посчитать missing_count по 35 признакам для каждой строки;
2. построить таблицу пропусков по week × state × feature;
3. отдельно посчитать число полных 35-мерных наблюдений;
4. не выполнять глобальное заполнение медианой;
5. не присваивать eNRI=0 из-за отсутствия данных.

В основную модель входят только полные живые наблюдения.

Живые неполные наблюдения остаются в итоговом отчёте со статусом missing_features и eNRI = NaN.

Достоверно умершим животным можно присваивать eNRI = 0 со статусом death.

### 3.2. Минимальные размеры

Для каждого состояния из \(\mathcal G\), ковариация которого входит в \(\mathbf Q\), требуется

\[
n_A\ge5.
\]

Для продольной пары требуется достаточное пересечение ID; минимально

\[
|M_{AB}|\ge5.
\]

Если условие не выполняется, расчёт останавливается и выводится диагностика, какое состояние или продольное сравнение недостаточно обеспечено данными.

### 3.3. Маски состояний

Реализовать одну функцию

~~~python
def mask(state, df):
    ...
~~~

для:

- PBS^0, PBS^16, PBS^24;
- LPS^0, LPS^16, LPS^24;
- run^0, run^16, run^24;
- MCC^0, MCC^16, MCC^24;
- L^0;
- L^16.

\(\mathcal L^0\) и \(\mathcal L^{16}\) строить непосредственно по исходной LPS-принадлежности.

При наличии полных конечных меток проверить:

\[
\mathcal L^t
=
LPS^t\cup run^t\cup MCC^t.
\]

## 4. Этап 3. Повторная cross-validation и стандартизация

### 4.1. Разбиение

Использовать group-wise CV по mouse_id.

Начать с 4-fold со стратификацией по назначенной конечной ветви.

Использовать несколько фиксированных seed, например 10:

\[
10\times4=40
\]

validation-fold.

Все недели одной мыши находятся только в train или только в validation.

Для каждого split заранее проверить:

- \(n_A\ge5\) для train-состояний из \(\mathcal G\);
- достаточные paired-ID для продольных train-пар;
- наличие всех состояний, необходимых для validation-метрик.

Если split невалиден, он не используется. Если 4-fold систематически не позволяет получить валидные split, перейти на 3-fold.

Нельзя молча исключать разные ограничения в разных validation-fold: используемые fold должны быть сопоставимы по набору оцениваемых отношений.

### 4.2. Стандартизация

Для каждого fold:

1. взять полные baseline-наблюдения train-мышей;
2. вычислить \(m_j,s_j\);
3. проверить \(s_j>0\);
4. стандартизовать train всех недель;
5. теми же \(m_j,s_j\) стандартизовать validation.

Validation не участвует в стандартизации.

## 5. Этап 4. Построение и решение QP

### 5.1. Статистики train

Для \(A\in\mathcal G\) вычислить:

\[
\overline{\mathbf x}_A,
\qquad
\mathbf S_A.
\]

Для межгрупповых пар вычислить обычные \(\mathbf d_{AB}\).

Для продольных пар вычислить \(\mathbf d_{AB}^{paired}\) только по совпадающим mouse_id.

### 5.2. Матрица Q

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

Симметризовать:

\[
\mathbf Q
\leftarrow
\frac{\mathbf Q+\mathbf Q^{\mathsf T}}{2}.
\]

Проверить размер 35×35, конечность, симметрию и минимальное собственное значение.

### 5.3. CVXPY

~~~python
w = cp.Variable(35)
eta = cp.Variable(len(ORDER_PAIRS), nonneg=True)

objective = cp.quad_form(w, Q) + C * cp.sum(eta)

constraints = []

for k, d in enumerate(order_diffs):
    constraints.append(w @ d >= rho - eta[k])

for x in X_train:
    constraints.append(
        1 + w @ (x - xbar_pbs0_train) >= epsilon
    )

problem = cp.Problem(cp.Minimize(objective), constraints)
problem.solve(solver=cp.OSQP)
~~~

Первый smoke test выполнить при

\[
\rho=0.1,
\qquad
\beta=\lambda=C=1.
\]

## 6. Этап 5. Диагностика решения

После каждого QP вычислить:

\[
\|\mathbf w\|_2,
\]

\[
\overline{\eta},
\qquad
\max\eta,
\]

\[
\frac{\overline{\eta}}{\rho},
\qquad
\frac{\max\eta}{\rho},
\]

и для каждой пары

\[
\Delta_{AB}
=
\mathbf w^{\mathsf T}\mathbf d_{AB}.
\]

Сохранить:

- долю пар с \(\Delta_{AB}>0\);
- долю пар с \(\Delta_{AB}\ge\rho\);
- mean_eta;
- max_eta;
- mean_eta / rho;
- max_eta / rho;
- weight_norm.

Не отклонять модель только потому, что доля правильных знаков меньше некоторого произвольного порога.

Жёстко считать решение технически вырожденным только если, например,

\[
\|\mathbf w\|_2<10^{-8},
\]

или решатель не дал допустимого решения.

Если slack велики и отношения плохо поддерживаются данными, это должно быть отражено в diagnostics.csv, а не скрыто заменой модели.

## 7. Этап 6. Подбор \(\rho,\beta,\lambda,C\)

### 7.1. Начальная сетка

\[
\rho\in\{0.05,0.1,0.2,0.3\},
\]

\[
\beta,\lambda,C
\in
\{0.1,1,10\}.
\]

После отладки сетку \(\beta,\lambda,C\) при необходимости расширить.

### 7.2. Validation использует только train-параметры

Для формулы eNRI на validation использовать:

\[
m_j^{train},
\qquad
s_j^{train},
\qquad
\overline{\mathbf x}_{PBS^0}^{train},
\qquad
\widehat{\mathbf w}.
\]

Центр PBS^0 на validation не пересчитывать.

Для validation-отношений межгрупповые средние считать по validation-мышам, а продольные разности — только по paired validation-ID.

### 7.3. Validation-метрики

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

Неправильный знак:

\[
V_{\mathrm{sign}}
=
\frac{
\#\{(A,B):\Delta_{AB}^{val}\le0\}
}{
|\mathcal O|
}.
\]

Нормированный недобор margin:

\[
V_{\mathrm{margin}}
=
\frac1{|\mathcal O|}
\sum_{(A,B)\in\mathcal O}
\max
\left(
0,
1-
\frac{\Delta_{AB}^{val}}{\rho}
\right).
\]

Нормированная ошибка равенств:

\[
V_{\mathrm{eq}}
=
\sqrt{
\frac1{|\mathcal E|}
\sum_{(A,B)\in\mathcal E}
\left(
\frac{\Delta_{AB}^{val}}{\rho}
\right)^2
}.
\]

Средний внутрисостоянийный разброс:

\[
V_{\mathrm{var}}
=
\frac1{|\mathcal G|}
\sum_{A\in\mathcal G}
\operatorname{Var}(eNRI\mid A).
\]

Нормированная норма весов:

\[
V_w
=
\frac{\|\widehat{\mathbf w}\|_2}{\rho}.
\]

Нормирование на \(\rho\) нужно потому, что \(\rho\) также подбирается.

### 7.4. Правило выбора

Для каждой комбинации \((\rho,\beta,\lambda,C)\) агрегировать метрики по всем валидным fold и seed.

Выбирать параметры лексикографически по

\[
(
V_{\mathrm{pos}},
V_{\mathrm{sign}},
V_{\mathrm{margin}},
V_{\mathrm{eq}},
V_{\mathrm{var}},
V_w
).
\]

То есть по порядку:

1. минимальное нарушение положительности;
2. минимальная доля сравнений с неправильным знаком;
3. минимальный нормированный недобор margin;
4. минимальная ошибка равенств;
5. минимальный внутрисостоянийный разброс;
6. минимальная нормированная норма весов.

Правило выбора должно быть полностью автоматическим.

## 8. Этап 7. Финальная модель

После выбора

\[
(\rho^\*,\beta^\*,\lambda^\*,C^\*)
\]

на всех допустимых данных:

1. вычислить baseline \(m_j,s_j\);
2. стандартизовать все недели;
3. построить состояния;
4. вычислить \(\overline{\mathbf x}_A,\mathbf S_A\);
5. построить обычные и paired \(\mathbf d_{AB}\);
6. построить и симметризовать \(\mathbf Q\);
7. решить финальный QP;
8. выполнить диагностику slack и весов;
9. получить 35 весов;
10. рассчитать eNRI для всех полных живых наблюдений.

Для достоверно умерших животных:

\[
eNRI=0.
\]

Для живых наблюдений с неполным набором признаков:

\[
eNRI=\mathrm{NaN}.
\]

## 9. Этап 8. Результаты

Сохранять только четыре файла:

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

Допустимые status:

- observed;
- death;
- missing_features.

### diagnostics.csv

Сохранить:

- type;
- A;
- B;
- n_A;
- n_B;
- n_paired;
- difference;
- rho;
- eta;
- eta_over_rho;
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
  "rho": null,
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
7. решение не является технически вырожденным;
8. для всех продольных ограничений использованы paired-ID;
9. размеры состояний и paired-наборов удовлетворяют минимальным требованиям;
10. созданы четыре выходных файла;
11. model.json достаточен для повторного вычисления eNRI без исходного training-кода.

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
5. Реализовать отчёт по пропускам и complete-case набор.
6. Реализовать mask(), \(\mathcal L^0,\mathcal L^{16}\).
7. Реализовать baseline-стандартизацию.
8. Реализовать обычные и paired \(\mathbf d_{AB}\).
9. Рассчитать \(\mathbf S_A\) для \(\mathcal G\).
10. Реализовать QP и smoke test.
11. Добавить диагностику slack и вырожденного решения.
12. Добавить repeated group-wise CV.
13. Добавить validation-метрики.
14. Добавить автоматический выбор \(\rho,\beta,\lambda,C\).
15. Решить финальный QP.
16. Сохранить weights.csv, enri.csv, diagnostics.csv, model.json.
17. Проверить воспроизводимость.
18. Только после этого запускать через run.sh и .run.

Этого достаточно для решения текущей задачи без лишней инфраструктуры.
