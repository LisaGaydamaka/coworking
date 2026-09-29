# eNRI: описание задачи и минимальный план реализации

# I. Описание задачи

## 1. Цель

Требуется найти вектор весов

\[
\mathbf w=(w_1,\ldots,w_{30})^{\mathsf T},
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

где \(\mathbf x\) — стандартизованный вектор из 30 модельных функциональных признаков.

Нормировка:

\[
\overline{eNRI}_{PBS^{0}}=1.
\]

Для достоверно умершего животного:

\[
eNRI(death)=0.
\]

Экспериментальная группа не входит в \(\mathbf x\) и используется только для построения групповых ограничений.

## 2. Датасет, исключения и фиксированные группы

Исходный Excel:

~~~text
enri_mouse_neuroplasticity/Данные по мышам.xlsx
~~~

До любых расчётов полностью исключить две строки исходного Excel:

- строка 10, мышь 3.2;
- строка 14, мышь 4.2.

Исключение применяется ко всем неделям этих мышей. Причина: на неделе 16 для них одновременно стоит CFP_16 = Dead и присутствует существенная часть функциональных измерений, поэтому момент смерти относительно обследования неоднозначен.

После исключения остаётся 54 мыши.

Экспериментальная группа фиксирована с начала эксперимента и определяется по Group_24:

\[
PBS\rightarrow PBS,
\qquad
LPS\rightarrow LPS,
\qquad
LPS+run\rightarrow run,
\qquad
LPS+MCC\rightarrow MCC.
\]

Размеры групп после исключения:

\[
N_{PBS}=11,
\qquad
N_{LPS}=14,
\qquad
N_{run}=15,
\qquad
N_{MCC}=14.
\]

Эти размеры не меняются со временем: смерть не меняет принадлежность мыши к группе.

Group_16 не определяет рандомизацию. Он используется только как проверка воздействия к неделе 16:

- для PBS ожидается Group_16 = PBS;
- для LPS, run и MCC ожидается Group_16 = LPS.

Дополнительные воздействия run и MCC начинаются после обследования недели 16. Поэтому на неделе 16 группы LPS, run и MCC рассматриваются как находившиеся в одинаковых условиях по типу воздействия.

## 3. Признаки

Из Excel обрабатываются 35 функциональных признаков, присутствующих на 0-й, 16-й и 24-й неделях. Однако в eNRI входят только 30 модельных признаков.

Пять детерминированно производных признаков сохраняются для preprocessing, QC и diagnostics, но **не получают отдельных весов eNRI**:

- Latency_to_first_investigation_NOR1;
- Total_time_investigating_NOR1;
- DI_NOR2;
- Latency_to_first_investigation_NOR2;
- Total_time_investigating_NOR2.

Причина исключения: эти показатели полностью вычисляются из других включённых признаков,

\[
TotalTime=T_P+T_S,
\]

\[
Latency_{first}=\min(Latency_P,Latency_S),
\]

\[
DI=\frac{T_P-T_S}{T_P+T_S}.
\]

Их одновременное включение вместе с исходными компонентами дублировало бы одну и ту же информацию и делало бы отдельные веса менее устойчивыми и хуже интерпретируемыми. Обычная высокая корреляция между недетерминированными признаками сама по себе не является основанием для исключения: такие признаки остаются в модели и контролируются регуляризацией и анализом устойчивости.

Итого:

\[
\boxed{35\ \text{обрабатываемых признаков}\;\rightarrow\;30\ \text{модельных признаков}.}
\]

### OFT

1. OFT_distance
2. Average_speed_OFT
3. Total_time_mobile_OFT
4. Absolute_turn_angle_OFT
5. Time_inCenter_OFT

### NOR1

6. Total_distance_travelled_NOR1
7. Average_speed_NOR1
8. Time_investigating_Piramidka_NOR1
9. Latency_to_first_investigation_Piramidka_NOR1
10. Time_investigating_Stakan_NOR1
11. Latency_to_first_investigation_Stakan_NOR1
12. Latency_to_first_investigation_NOR1
13. Total_time_investigating_NOR1

### NOR2

14. Total_distance_travelled_NOR2
15. Average_speed_NOR2
16. Time_investigating_Piramidka_zone_NOR2
17. Latency_to_first_investigation_Piramidka_zone_NOR2
18. Time_investigating_Stakan_zone_NOR2
19. Latency_to_first_investigation_Stakan_zone_NOR2
20. DI_NOR2
21. Latency_to_first_investigation_NOR2
22. Total_time_investigating_NOR2

### Rotarod learning

23. Learning_T1mean
24. Learning_T1max
25. Learning_T1sum
26. Learning_T2mean
27. Learning_T2max
28. Learning_T2sum
29. Learning_T3mean
30. Learning_T3max
31. Learning_T3sum

### Остальные

32. EnduranceT
33. rear_support
34. rear_nosupport
35. Weight

Не включаются группы, ID, Eight_item_index, CoFI, Grip, Y-maze, social/depression и молекулярные показатели.

Для всех 35 обрабатываемых признаков используется явный словарь соответствия реальным названиям столбцов Excel на неделях 0, 16 и 24; отдельный MODEL_FEATURES фиксирует 30 признаков, входящих в eNRI. Поиск столбцов по шаблону запрещён, поскольку названия между неделями неоднородны.

## 4. Смерть и статус наблюдения

Для включённых мышей:

- на неделе 0 животное считается живым;
- на неделе 16 смерть определяется только условием CFP_16 = "Dead";
- на неделе 24 смерть определяется только условием CFP_24 = "Dead";
- пустой CFP сам по себе смертью не является;
- NaN в функциональных признаках не является признаком смерти.

Если животное имеет статус death в точке \(t\), весь его функциональный вектор этой временной точки игнорируется, включая случайно оставшиеся технические нули.

После исключения мышей 3.2 и 4.2 ожидаются следующие контрольные числа:

\[
\begin{array}{c|cccc}
 & PBS & LPS & run & MCC\\
\hline
N & 11 & 14 & 15 & 14\\
alive^{16} & 9 & 12 & 12 & 11\\
death^{16} & 2 & 2 & 3 & 3\\
alive^{24} & 8 & 11 & 12 & 11\\
death^{24} & 3 & 3 & 3 & 3
\end{array}
\]

Должна выполняться монотонность смерти:

\[
death^{16}\Rightarrow death^{24}.
\]

Любое несоответствие этим контрольным значениям или монотонности останавливает расчёт.

## 5. Детерминированная обработка NOR и производных признаков

До статистической импутации выполняются правила, не требующие модели.

### 5.1. Цензурированные latency в NOR

Длительность NOR-сессии в доступных материалах не подтверждена, поэтому фиксированную длительность теста не предполагаем.

Если время исследования соответствующего объекта равно нулю и объектная latency отсутствует,

\[
Time=0,\quad Latency=NaN,
\]

такое значение считается структурно цензурированным: объект не был исследован в течение доступного времени наблюдения. Оно не считается обычным случайным пропуском.

Для модели принято следующее правило числового кодирования:

\[
\boxed{
Latency_{\mathrm{censored}}
=
\max\{Latency_{\mathrm{observed}}\}
}
\]

для того же объектного latency-признака среди живых нецензурированных наблюдений обучающей выборки.

В cross-validation максимум вычисляется **только по train** и затем применяется и к train, и к validation. Validation не участвует в выборе максимума. В финальной модели максимум вычисляется по всем включённым живым нецензурированным наблюдениям.

Каждое такое значение получает отдельный флаг

~~~text
censored_latency = 1
~~~

и поэтому остаётся отличимым от реально наблюдавшейся latency.

Если в train для конкретного latency-признака нет ни одного наблюдаемого нецензурированного значения, соответствующий CV-split считается невалидным.

Если \(Time>0\), а latency отсутствует, это обычный пропуск и он может быть импутирован.

После разрешения объектных latency для каждого NOR-дня общая latency пересчитывается как

\[
Latency_{\mathrm{first}}
=
\min(Latency_P,Latency_S).
\]

### 5.2. Total time

Для NOR1 и NOR2:

\[
TotalTime=T_P+T_S.
\]

Если ровно одно из \(T_P,T_S\) отсутствует, а TotalTime и второе слагаемое известны, отсутствующее время восстанавливается как

\[
T_{\mathrm{missing}}
=
TotalTime-T_{\mathrm{known}},
\]

только если результат неотрицателен.

После импутации базовых времён TotalTime всегда пересчитывается заново.

### 5.3. DI

После получения двух времён исследования NOR2:

\[
DI=
\frac{T_P-T_S}{T_P+T_S},
\qquad T_P+T_S>0.
\]

При

\[
T_P=T_S=0
\]

фиксируется нейтральная конвенция

\[
DI=0,
\]

а в diagnostics сохраняется флаг zero_exploration.

DI не импутируется независимо.

### 5.4. Rotarod mean, max и sum

Признаки Rotarod mean, max и sum сохраняются как самостоятельные измеряемые признаки.

Равенство

\[
T_{sum}=4T_{mean}
\]

не задаётся как общее правило preprocessing: в исходных данных оно выполняется не для всех наблюдений недели 24. Поэтому Learning_T1sum, Learning_T2sum и Learning_T3sum не пересчитываются из mean и не используются для детерминированного восстановления mean.

Пропуски в mean, max и sum рассматриваются как обычные числовые пропуски и, при выполнении общих условий импутации, заполняются IterativeImputer независимо.

Соотношение sum/mean используется только как диагностическая проверка согласованности и не изменяет исходные значения автоматически.

### 5.5. Производные признаки вне eNRI

Следующие 5 признаков являются детерминированно производными:

- Latency_to_first_investigation_NOR1;
- Total_time_investigating_NOR1;
- DI_NOR2;
- Latency_to_first_investigation_NOR2;
- Total_time_investigating_NOR2.

Они:

- не входят в 30-мерный вектор \(\mathbf x\);
- не получают отдельных компонент \(\mathbf w\);
- не являются target-признаками IterativeImputer;
- пересчитываются детерминированно после заполнения базовых признаков;
- сохраняются для QC, diagnostics и проверки тождеств.

IterativeImputer и последующая модель eNRI работают с 30 модельными признаками.

## 6. Контроль качества исходных значений

До стандартизации выполняется data-QC.

Из текущего Excel отдельно проверены следующие выраженные значения масштаба:

- мыши 8.2, 8.3, 8.4: Average_speed_NOR1_16;
- мыши 9.2, 16.1, 17.1, 21.1, 21.4: OFT_distance_24.

По решению пользователя эти восемь значений считаются корректными исходными данными и сохраняются без изменения. В diagnostics они помечаются как accepted_scale_value и не блокируют расчёт.

Код не исправляет значения масштаба автоматически.

Для каждого feature × week вычисляются median и MAD среди живых включённых мышей. Значение помечается как scale_outlier, если одновременно:

- оно конечно;
- MAD > 0;
- абсолютное отклонение от median превышает \(10\cdot MAD\).

Кроме этого проверяются физические условия:

- distance, speed, time, weight и counts неотрицательны;
- наблюдаемая latency неотрицательна; структурно цензурированная latency кодируется максимумом соответствующего признака без leakage;
- DI находится в \([-1,1]\);
- производные тождества после пересчёта выполняются с tolerance \(10^{-8}\).

MAD-флаг scale_outlier является диагностическим предупреждением и сам по себе не меняет данные. Восемь рассмотренных значений выше имеют статус accepted_scale_value. Остальные scale_outlier сохраняются как review-флаги. Расчёт останавливается только при нарушении жёстких проверок данных или при явно неразрешённой ошибке.

## 7. Стандартизация и импутация

Неделя 0 является baseline.

Исходный вектор:

\[
\mathbf r=(r_1,\ldots,r_{30})^{\mathsf T}.
\]

Для каждого признака \(j\) вычисляются среднее и выборочное стандартное отклонение только по доступным значениям этого признака на неделе 0:

\[
m_j
=
\operatorname{mean}
\{r_{ij}^{0}: r_{ij}^{0}\neq NaN\},
\]

\[
s_j
=
\sqrt{
\frac{1}{n_j-1}
\sum_{r_{ij}^{0}\neq NaN}
(r_{ij}^{0}-m_j)^2
}.
\]

Используется \(ddof=1\).

Стандартизация:

\[
x_j=\frac{r_j-m_j}{s_j}.
\]

Одни и те же \(m_j,s_j\) применяются к неделям 0, 16 и 24.

В cross-validation \(m_j,s_j\) вычисляются только по baseline train-мышам. Validation не участвует.

Порядок preprocessing внутри fold:

1. исключить 3.2 и 4.2;
2. построить фиксированную группу;
3. определить death;
4. применить детерминированные правила NOR и определить структурно цензурированные latency;
5. для каждого объектного latency-признака вычислить максимум только по живым нецензурированным train-наблюдениям и заменить им structural-censored значения в train и validation;
6. вычислить baseline \(m_j,s_j\) по train;
7. стандартизовать 30 модельных признаков, сохраняя NaN;
8. добавить два индикатора недели: week_16 и week_24;
9. fit IterativeImputer только на train по 30 модельным признакам;
10. transform train;
11. transform validation тем же fitted imputer;
12. вернуть импутированные модельные признаки в исходный масштаб;
13. пересчитать 5 производных признаков только для QC/diagnostics;
14. стандартизовать итоговый 30-мерный модельный вектор теми же \(m_j,s_j\).

Группа лечения в импутации не используется.

Основная модель:

~~~text
IterativeImputer(
    estimator=BayesianRidge(),
    sample_posterior=False,
    max_iter=20,
    tol=1e-3,
    random_state=seed
)
~~~

До импутации для каждого живого визита сохраняется missing_count по 30 модельным признакам после детерминированного восстановления. Пять производных QC-признаков в этот счётчик не входят.

После исключения пяти детерминированно производных признаков missing_count считается только по 30 модельным признакам. Используется

\[
MAX\_MISSING\_PER\_VISIT=7.
\]

Если у живого визита после детерминированного восстановления missing_count > 7, он получает статус missing_visit и статистически не импутируется.

Статусы:

- observed — исходно полный живой вектор после детерминированных преобразований;
- imputed — живой вектор с успешно заполненными статистическими пропусками;
- death — достоверная смерть;
- missing_visit — живой визит, не допускаемый к импутации.

## 8. Экспериментальные состояния

Используются фиксированные группы

\[
g\in\{PBS,LPS,run,MCC\}
\]

и недели

\[
t\in\{0,16,24\}.
\]

Состояние \(g^t\) — мыши фиксированной группы \(g\) в момент \(t\).

Полный набор состояний:

\[
\mathcal G
=
\{
PBS^0,LPS^0,run^0,MCC^0,
PBS^{16},LPS^{16},run^{16},MCC^{16},
PBS^{24},LPS^{24},run^{24},MCC^{24}
\}.
\]

## 9. Средний eNRI всей группы с учётом смертей

Для состояния \(A=g^t\):

- \(N_A\) — число мышей соответствующей фиксированной группы в рассматриваемой части данных;
- \(R_A\) — живые исходно полные наблюдения;
- \(I_A\) — живые успешно импутированные наблюдения;
- \(O_A=R_A\cup I_A\) — все живые наблюдения с полным 30-мерным модельным вектором после preprocessing;
- \(D_A\) — умершие к моменту \(t\);
- \(U_A\) — living missing_visit.

Для финальной модели:

\[
N_{PBS^t}=11,\quad
N_{LPS^t}=14,\quad
N_{run^t}=15,\quad
N_{MCC^t}=14.
\]

В cross-validation знаменатель определяется отдельно внутри каждой части:

\[
N_A^{train}=|g\cap train|,
\qquad
N_A^{val}=|g\cap validation|.
\]

Основная модель требует

\[
U_A=\varnothing
\]

для всех состояний, участвующих в \(\mathcal E\) или \(\mathcal O\).

Тогда

\[
N_A=|O_A|+|D_A|.
\]

Определим

\[
a_A=\frac{|O_A|}{N_A},
\]

\[
\mathbf b_A
=
\frac1{N_A}
\sum_{i\in O_A}
\left(
\mathbf x_i-\overline{\mathbf x}_{PBS^0}
\right).
\]

Средний eNRI всей группы:

\[
\boxed{
\mu_A(\mathbf w)
=
a_A+\mathbf w^{\mathsf T}\mathbf b_A.
}
\]

Смерти входят в среднее как нули.

## 10. Ограничения равенства

Так как четыре группы были заданы исходно, baseline-равенства:

\[
(PBS^0,LPS^0),
\qquad
(PBS^0,run^0),
\qquad
(PBS^0,MCC^0).
\]

Так как до обследования недели 16 группы LPS, run и MCC имели одинаковое воздействие LPS:

\[
(LPS^{16},run^{16}),
\qquad
(LPS^{16},MCC^{16}).
\]

Итого

\[
\mathcal E
=
\{
(PBS^0,LPS^0),
(PBS^0,run^0),
(PBS^0,MCC^0),
(LPS^{16},run^{16}),
(LPS^{16},MCC^{16})
\}.
\]

Для \((A,B)\in\mathcal E\) требуется близость:

\[
\mu_A(\mathbf w)\approx\mu_B(\mathbf w).
\]

## 11. Ограничения порядка

Межгрупповые отношения:

\[
\mathcal O_1
=
\{
(PBS^{16},LPS^{16}),
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
(LPS^0,LPS^{16}),
(run^0,run^{16}),
(MCC^0,MCC^{16}),
(PBS^{16},PBS^{24}),
(LPS^{16},LPS^{24})
\}.
\]

Для run и MCC направление изменения между 16-й и 24-й неделями заранее не фиксируется.

\[
\mathcal O=\mathcal O_1\cup\mathcal O_2.
\]

Для каждой пары \((A,B)\in\mathcal O\):

\[
\mu_A(\mathbf w)
\ge
\mu_B(\mathbf w)+\rho-\eta_{AB},
\]

\[
\eta_{AB}\ge0.
\]

Основная величина:

\[
\boxed{\rho=0.1}.
\]

Sensitivity analysis:

\[
\rho\in\{0.05,0.2,0.3\}.
\]

## 12. Внутригрупповая дисперсия

Для каждого \(A\in\mathcal G\) ковариация вычисляется по всем живым полным векторам после preprocessing:

\[
O_A=R_A\cup I_A.
\]

\[
\overline{\mathbf x}_A
=
\frac1{|O_A|}
\sum_{i\in O_A}\mathbf x_i,
\]

\[
\mathbf S_A
=
\frac1{|O_A|-1}
\sum_{i\in O_A}
(\mathbf x_i-\overline{\mathbf x}_A)
(\mathbf x_i-\overline{\mathbf x}_A)^{\mathsf T}.
\]

Все 12 состояний имеют одинаковый вес:

\[
\boxed{
\mathbf Q_{\mathrm{var}}
=
\frac1{12}
\sum_{t\in\{0,16,24\}}
\sum_{g\in\{PBS,LPS,run,MCC\}}
\mathbf S_{g^t}.
}
\]

Сингулярность отдельных \(\mathbf S_A\) при \(p=30>n_A\) допустима: каждая выборочная covariance является PSD, а \(\lambda\|\mathbf w\|^2\) обеспечивает регуляризацию.

Перед передачей в CVXPY:

\[
\mathbf Q_{\mathrm{var}}
\leftarrow
\frac12
\left(
\mathbf Q_{\mathrm{var}}+\mathbf Q_{\mathrm{var}}^{\mathsf T}
\right).
\]

Проверить конечность и минимальное собственное значение. Если

\[
\lambda_{\min}<-10^{-8},
\]

расчёт считается численно невалидным.

## 13. Задача оптимизации

Для пары \((A,B)\):

\[
c_{AB}=a_A-a_B,
\]

\[
\mathbf d_{AB}
=
\mathbf b_A-\mathbf b_B.
\]

Тогда

\[
\Delta_{AB}
=
\mu_A-\mu_B
=
c_{AB}
+
\mathbf w^{\mathsf T}\mathbf d_{AB}.
\]

Целевая функция:

\[
\min_{\mathbf w,\boldsymbol\eta}
\left[
\mathbf w^{\mathsf T}\mathbf Q_{\mathrm{var}}\mathbf w
+
\beta
\sum_{(A,B)\in\mathcal E}
\left(
c_{AB}
+
\mathbf w^{\mathsf T}\mathbf d_{AB}
\right)^2
+
\lambda\|\mathbf w\|_2^2
+
C\sum_{(A,B)\in\mathcal O}\eta_{AB}
\right].
\]

Ограничения:

\[
c_{AB}
+
\mathbf w^{\mathsf T}\mathbf d_{AB}
\ge
\rho-\eta_{AB},
\qquad
(A,B)\in\mathcal O,
\]

\[
\eta_{AB}\ge0,
\]

и для каждого живого observation из \(O_A\):

\[
1+
\mathbf w^{\mathsf T}
\left(
\mathbf x_i-
\overline{\mathbf x}_{PBS^{0}}
\right)
\ge\varepsilon,
\qquad
\varepsilon=10^{-3}.
\]

После решения вручную проверить residual всех constraints с tolerance \(10^{-7}\).

OSQP:

~~~text
eps_abs = 1e-8
eps_rel = 1e-8
max_iter = 100000
~~~

---

# II. Минимальный план реализации

## 0. Девять крупных этапов

Ниже зафиксирована основная нумерация этапов проекта. В дальнейшей работе команда вида **«сделай этап N»** относится именно к этому списку.

### Этап 1. Preflight данных

- загрузить Excel;
- исключить мышей 3.2 и 4.2;
- построить фиксированные группы PBS/LPS/run/MCC;
- проверить размеры групп \(11/14/15/14\);
- определить death по CFP;
- проверить alive/death counts;
- проверить точное соответствие 35 обрабатываемых признаков столбцам Excel и зафиксировать 30 MODEL_FEATURES;
- выполнить data-QC и выявить ошибки масштаба/аномальные значения.

Результат этапа: данные и правила их интерпретации проверены; либо сформирован список блокирующих проблем, которые требуют ручного решения до моделирования.

### Этап 2. Детерминированный preprocessing

- построить длинную таблицу mouse × week;
- применить правила смерти;
- обработать NOR TotalTime и DI;
- выделить структурно цензурированные latency;
- закодировать их максимумом соответствующего наблюдаемого latency-признака, вычисленным только по train;
- сохранить Rotarod mean/max/sum как самостоятельные признаки;
- рассчитать missing_count;
- определить статусы observed/imputed/death/missing_visit перед статистической импутацией.

Результат этапа: подготовлены данные, в которых все пропуски разделены на детерминированно разрешимые, структурно цензурированные и статистически импутируемые.

### Этап 3. Стандартизация и импутация

- вычислить baseline \(m_j,s_j\) только по неделе 0;
- в CV вычислять параметры только по train;
- стандартизовать базовые признаки;
- выполнить IterativeImputer + BayesianRidge;
- использовать индикаторы недели, но не экспериментальную группу;
- пересчитать производные NOR-признаки;
- пересчитать 5 производных признаков для QC;
- получить итоговый полный 30-мерный модельный вектор;
- проверить допустимость всех импутированных значений.

Результат этапа: для всех допустимых живых наблюдений получены 30 стандартизованных модельных признаков; 5 производных признаков сохранены отдельно для QC.

### Этап 4. Построение 12 экспериментальных состояний

Построить

\[
PBS^t,\quad LPS^t,\quad run^t,\quad MCC^t,
\qquad
t\in\{0,16,24\}.
\]

Для каждого состояния определить

\[
N_A,\ R_A,\ I_A,\ O_A,\ D_A,\ U_A,
\]

и вычислить

\[
a_A,\qquad \mathbf b_A,\qquad \mathbf S_A.
\]

Результат этапа: полностью сформированы все групповые состояния, необходимые для ограничений и целевой функции.

### Этап 5. Сборка и первый запуск QP

- сформировать \(\mathcal E\);
- сформировать \(\mathcal O\);
- собрать \(\mathbf Q_{\mathrm{var}}\);
- добавить positivity constraints;
- решить первый smoke-test при

\[
\rho=0.1,
\qquad
\beta=\lambda=C=1;
\]

- проверить residual ограничений и статус solver.

Результат этапа: получено первое технически корректное решение QP и полный набор train-диагностик.

### Этап 6. Repeated stratified 3-fold CV и выбор гиперпараметров

- разделять данные по mouse_id;
- стратифицировать по PBS/LPS/run/MCC;
- выполнять весь preprocessing строго train-only;
- использовать одинаковые splits для всех комбинаций параметров;
- перебрать

\[
\beta,\lambda,C\in\{0.1,1,10\};
\]

- вычислить validation-метрики;
- выбрать \((\beta^\*,\lambda^\*,C^\*)\) по зафиксированному лексикографическому правилу.

Результат этапа: выбраны гиперпараметры основной модели без использования validation при обучении preprocessing.

### Этап 7. Финальная модель

- выполнить preprocessing на всех 54 включённых мышах;
- использовать выбранные \((\beta^\*,\lambda^\*,C^\*)\);
- решить финальный QP;
- получить 30 весов;
- вычислить eNRI для каждой допустимой мыши и недели;
- присвоить eNRI = 0 только достоверным death.

Результат этапа: получена основная финальная модель eNRI.

### Этап 8. Проверка устойчивости

- оценить стабильность raw-scale slopes между CV-folds;
- выполнить complete-case sensitivity analysis;
- при необходимости выполнить stochastic-imputation sensitivity;
- выполнить sensitivity analysis при

\[
\rho\in\{0.05,0.2,0.3\};
\]

- сравнить веса, знаки, групповые средние, ранги и slack.

Результат этапа: оценена устойчивость eNRI к разбиениям, пропускам и выбору margin.

### Этап 9. Финальные результаты и проверки

Сформировать:

~~~text
results/
├── weights.csv
├── enri.csv
├── diagnostics.csv
└── model.json
~~~

Проверить:

- воспроизводимость;
- 30 конечных весов;
- все обязательные ограничения;
- корректность death/imputed/missing_visit;
- нормировку \(\overline{eNRI}_{PBS^0}=1\);
- отсутствие неразрешённых data-QC ошибок;
- достаточность model.json для повторного расчёта eNRI.

Результат этапа: готовый воспроизводимый набор результатов и диагностик.

## 1. Структура проекта

~~~text
enri_mouse_neuroplasticity/
├── PLAN.md
├── Данные по мышам.xlsx
├── solve.py
├── requirements.txt
├── run.sh
├── .run
└── results/
~~~

Вся логика находится в одном solve.py.

## 2. Детализация preflight данных

### 2.1. Константы

Задать:

- EXCLUDED_MOUSE_IDS = {"3.2", "4.2"};
- список 35 обрабатываемых признаков;
- MODEL_FEATURES из 30 признаков;
- DERIVED_FEATURES из 5 производных QC-признаков;
- явное соответствие 35 признаков столбцам 0/16/24;
- GROUP_MAP для Group_24;
- CENSORED_LATENCY_RULE = "train_feature_max";
- MAX_MISSING_PER_VISIT = 7;
- \(\mathcal E,\mathcal O,\mathcal G\);
- \(\varepsilon=10^{-3}\);
- \(\rho=0.1\);
- сетки \(\beta,\lambda,C\);
- CV seeds;
- CV tolerance \(10^{-6}\).

### 2.2. Прочитать Excel

1. Прочитать Данные по мышам.xlsx.
2. Проверить обязательные столбцы.
3. Нормализовать Animal как строковый mouse_id.
4. Проверить уникальность ID.
5. Исключить 3.2 и 4.2.
6. Построить фиксированную группу по Group_24.
7. Проверить размеры 11/14/15/14.
8. Проверить Group_16 как контроль воздействия.
9. Определить death только по CFP.
10. Проверить ожидаемые alive/death counts.
11. Проверить монотонность death.
12. Не определять смерть по NaN.
13. Применить data-QC.
14. Сохранить MAD-outlier как диагностику; восемь согласованных значений масштаба пометить accepted_scale_value и не блокировать расчёт.

## 3. Детализация длинной таблицы и preprocessing

Одна строка:

\[
(mouse\_id,\ group,\ week,\ \mathbf r_i^t).
\]

Хранить:

- mouse_id;
- group;
- week;
- status;
- missing_count;
- zero_exploration;
- censored_latency;
- 35 обрабатываемых признаков, из которых 30 входят в модель.

Для death функциональные признаки временной точки занулять нельзя; они должны быть недоступны для feature-processing, а eNRI задаётся отдельно как 0.

Выполнить детерминированное восстановление NOR. Структурно цензурированные latency заменить максимумом соответствующего наблюдаемого latency-признака: внутри CV максимум вычислять только по train, в финальной модели — по всем включённым живым нецензурированным наблюдениям. Затем выполнять статистическую импутацию только базовых признаков.

## 4. Детализация repeated stratified 3-fold CV

Создать одну строку на мышь с фиксированной группой

\[
PBS,\ LPS,\ run,\ MCC.
\]

Использовать repeated stratified 3-fold с 10 фиксированными seed:

~~~text
0, 1, 2, 3, 4, 5, 6, 7, 8, 9
~~~

Разбиение выполняется только на уровне mouse_id со стратификацией по фиксированной группе; все три недели одной мыши остаются в одной части split.

Все недели одной мыши всегда находятся только в train или только в validation.

Для каждого split после preprocessing проверить:

\[
|O_A^{train}|\ge5
\]

для всех covariance states и

\[
|O_A^{val}|\ge2
\]

для validation variance.

Невалидный split не использовать. Один и тот же набор принятых split используется для всех комбинаций гиперпараметров.

## 5. Детализация preprocessing внутри fold

Для каждого fold:

1. train/validation разделены по mouse_id;
2. детерминированное восстановление выполняется отдельно без использования статистик validation;
3. \(m_j,s_j\) вычисляются только по доступным baseline train;
4. 30 модельных признаков стандартизуются;
5. fit IterativeImputer выполняется только на train;
6. validation преобразуется train-imputer;
7. модельные признаки возвращаются в raw scale;
8. 5 производных признаков пересчитываются только для QC/diagnostics;
9. итоговый 30-мерный модельный вектор стандартизуется train-параметрами;
10. вычисляется \(\overline{\mathbf x}_{PBS^0}^{train}\).

Validation не участвует ни в scaling, ни в fit imputer.

## 6. Детализация QP на train

Для каждого состояния:

1. определить \(N_A^{train}\);
2. определить \(R_A,I_A,O_A,D_A,U_A\);
3. проверить \(U_A=\varnothing\) для состояний из \(\mathcal E\cup\mathcal O\);
4. вычислить \(a_A,\mathbf b_A,\mathbf S_A\);
5. собрать \(\mathbf Q_{\mathrm{var}}\).

Positivity constraint накладывается на все

\[
O_A=observed+imputed,
\]

а не только на observed.

Первый smoke test:

\[
\rho=0.1,
\qquad
\beta=\lambda=C=1.
\]

## 7. Детализация train-диагностики

Для каждой пары сохранять:

\[
\Delta_{AB}
=
\mu_A-\mu_B.
\]

Разложение:

\[
\Delta_{AB}
=
\Delta_{AB}^{mort}
+
\Delta_{AB}^{func},
\]

где

\[
\Delta_{AB}^{mort}=a_A-a_B,
\]

\[
\Delta_{AB}^{func}
=
\mathbf w^{\mathsf T}
(\mathbf b_A-\mathbf b_B).
\]

Сохранять:

- delta_total;
- delta_mortality;
- delta_functional;
- eta;
- sign_ok;
- margin_ok;
- group sizes;
- observed;
- imputed;
- deaths;
- missing_visit;
- solver_status;
- constraint residuals.

## 8. Детализация подбора \(\beta,\lambda,C\)

Начальная сетка:

\[
\beta,\lambda,C
\in
\{0.1,1,10\}.
\]

\(\rho=0.1\) фиксировано.

Validation positivity:

\[
V_{\mathrm{pos}}
=
\frac{
\#\{i\in O^{val}:eNRI_i<\varepsilon\}
}{
|O^{val}|
}.
\]

Неправильный знак:

\[
V_{\mathrm{sign}}
=
\frac{
\#\{(A,B)\in\mathcal O:\Delta_{AB}^{val}\le0\}
}{
|\mathcal O|
}.
\]

Недобор margin:

\[
V_{\mathrm{margin}}
=
\frac1{|\mathcal O|}
\sum_{(A,B)\in\mathcal O}
\max(0,\rho-\Delta_{AB}^{val}).
\]

Ошибка равенств:

\[
V_{\mathrm{eq}}
=
\sqrt{
\frac1{|\mathcal E|}
\sum_{(A,B)\in\mathcal E}
(\Delta_{AB}^{val})^2
}.
\]

Внутрисостоянийная дисперсия:

\[
V_{\mathrm{var}}
=
\frac1{|\mathcal G|}
\sum_{A\in\mathcal G}
\operatorname{Var}(eNRI\mid A,\ O_A^{val}).
\]

\[
V_w=\|\widehat{\mathbf w}\|_2.
\]

Метрики агрегируются арифметическим средним по всем принятым fold/seed.

Выбор лексикографический с tolerance \(10^{-6}\):

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

На каждом шаге сохраняются все комбинации, значение текущей метрики которых не превышает минимум по оставшимся комбинациям более чем на \(10^{-6}\). Если после всех шести метрик остаётся несколько комбинаций, используется детерминированный tie-break по возрастанию \((\beta,\lambda,C)\).

## 9. Стабильность весов

Стандартизация различается между folds, поэтому сравнивать напрямую \(\mathbf w\) между folds нельзя.

Для каждого fold вычислять raw-scale slope

\[
\gamma_j=\frac{w_j}{s_j}.
\]

В diagnostics сохранять по каждому признаку:

- median \(\gamma_j\);
- 10% и 90% quantile;
- sign frequency;
- pairwise cosine similarity векторов \(\boldsymbol\gamma\).

Это является основной оценкой стабильности весов; дополнительный bootstrap не требуется.

## 10. Детализация финальной модели

После выбора

\[
(\beta^\*,\lambda^\*,C^\*)
\]

на всех 54 включённых мышах:

1. выполнить детерминированный preprocessing;
2. выполнить data-QC;
3. вычислить baseline \(m_j,s_j\);
4. стандартизовать 30 модельных признаков;
5. fit финальный IterativeImputer;
6. заполнить статистические пропуски;
7. пересчитать 5 производных признаков только для QC/diagnostics;
8. стандартизовать 30 модельных признаков;
9. проверить отсутствие missing_visit в \(\mathcal E\cup\mathcal O\);
10. вычислить \(\overline{\mathbf x}_{PBS^0}\);
11. построить 12 состояний;
12. вычислить \(a_A,\mathbf b_A,\mathbf S_A\);
13. собрать \(\mathbf Q_{\mathrm{var}}\);
14. решить финальный QP;
15. рассчитать eNRI для observed и imputed;
16. присвоить eNRI=0 только death;
17. оставить eNRI=NaN только для missing_visit.

## 11. Sensitivity analysis

### 11.1. Стабильность между CV-folds

Для каждого из заранее допустимых repeated stratified CV-splits заново решить train-QP только с уже выбранными

\[
(\beta^\*,\lambda^\*,C^\*).
\]

Для fold \(k\) сравнивать не стандартизованные веса напрямую, а raw-scale slopes

\[
\gamma_{jk}=\frac{w_{jk}}{s_{jk}},
\]

где \(s_{jk}\) — baseline standard deviation, вычисленная только по train этого fold.

Для каждого признака сохранять median, 10% и 90% quantile \(\gamma_j\), долю положительных знаков и долю совпадения знака с финальной full-data моделью. Для всех пар fold-векторов \(\boldsymbol\gamma\) сохранять распределение cosine similarity; отдельно — cosine каждого fold с финальной моделью.

### 11.2. Margin

Повторить финальный расчёт при

\[
\rho\in\{0.05,0.2,0.3\}
\]

с фиксированными

\[
(\beta^\*,\lambda^\*,C^\*).
\]

Сравнивать с основной моделью \(\rho=0.1\):

- cosine similarity raw-scale slopes \(\boldsymbol\gamma\);
- совпадение знаков \(\gamma_j\);
- Spearman correlation индивидуальных eNRI у живых наблюдений;
- Spearman correlation рангов 12 групповых \(\mu_A\);
- максимальное изменение группового \(\mu_A\);
- slack;
- выполнение жёстких ограничений.

### 11.3. Complete-case sensitivity

Complete-case определяется **на уровне мыши**, чтобы не разрушать продольную структуру: мышь включается, если во всех её живых визитах после детерминированного preprocessing

\[
missing\_count=0.
\]

Death-визиты не считаются пропусками. Мыши хотя бы с одним статистически импутируемым MODEL_FEATURE исключаются целиком только из этого sensitivity-анализа.

На оставшихся мышах заново вычислить censor maxima, baseline scaling, \(\overline{\mathbf x}_{PBS^0}\), 12 состояний и QP при финальных \((\beta^\*,\lambda^\*,C^\*,\rho=0.1)\). Сравнить raw-scale slopes, знаки, индивидуальные ранги eNRI на общих живых наблюдениях, групповые средние и slack с основной моделью.

### 11.4. Stochastic-imputation sensitivity

Основная модель остаётся детерминированной. Поскольку в финальной модели есть статистически импутированные живые визиты, stochastic sensitivity считается необходимой и выполняется в 10 повторениях:

~~~text
IterativeImputer(
    estimator=BayesianRidge(),
    sample_posterior=True,
    random_state=seed
)
~~~

с seed \(0,1,\ldots,9\).

В каждом повторении заново импутировать данные, решить полный QP при финальных гиперпараметрах и \(\rho=0.1\), затем сравнить raw-scale slopes, знаки, индивидуальные ранги eNRI, групповые средние и slack с основной детерминированной моделью. Невалидные stochastic-runs (например, с физически недопустимыми импутированными значениями или solver failure) не скрывать: сохранять отдельно в diagnostics и учитывать в числе валидных повторений.

## 12. Результаты

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
- group;
- week;
- eNRI;
- status;
- missing_count.

### diagnostics.csv

Строки type:

- qc;
- state;
- order;
- equality;
- cv;
- stability;
- sensitivity.

Для qc:

- mouse_id;
- week;
- feature;
- value;
- flag.

Для order/equality:

- A;
- B;
- N_A;
- N_B;
- observed_A;
- observed_B;
- imputed_A;
- imputed_B;
- deaths_A;
- deaths_B;
- missing_visit_A;
- missing_visit_B;
- delta_total;
- delta_mortality;
- delta_functional;
- eta;
- condition_ok;
- solver_status.

Для CV:

- seed;
- fold;
- beta;
- lambda;
- C;
- V_pos;
- V_sign;
- V_margin;
- V_eq;
- V_var;
- V_w;
- solver_status.

### model.json

Сохранить:

~~~json
{
  "excluded_mouse_ids": ["3.2", "4.2"],
  "group_map": {},
  "features": [],  // ровно 30 MODEL_FEATURES
  "feature_columns": {},
  "derived_features": [],
  "censored_latency_rule": "train_feature_max",
  "max_missing_per_visit": 7,
  "mean": [],
  "std": [],
  "xbar_pbs0": [],
  "weights": [],
  "rho": 0.1,
  "beta": null,
  "lambda": null,
  "C": null,
  "epsilon": 0.001,
  "cv_tolerance": 0.000001,
  "random_seeds": [0,1,2,3,4,5,6,7,8,9],
  "imputation_method": "IterativeImputer",
  "imputation_sample_posterior": false,
  "imputation_seed": null,
  "solver_status": null
}
~~~

Порядок features, mean, std, xbar_pbs0 и weights должен совпадать и содержать ровно 30 MODEL_FEATURES. derived_features хранится отдельно и не имеет весов.

## 13. Финальные проверки

Перед завершением проверить:

1. анализ содержит 54 мыши и не содержит 3.2/4.2;
2. размеры групп равны 11/14/15/14;
3. alive/death counts совпадают с контрольными;
4. death монотонен;
5. найдено ровно 30 весов;
6. все веса конечны;
7. все \(\eta_{AB}\ge0\);
8. все observed/imputed living удовлетворяют \(eNRI\ge\varepsilon\) с tolerance;
9. \(\overline{eNRI}_{PBS^0}=1\);
10. death имеют eNRI=0;
11. imputed имеют конечный eNRI;
12. missing_visit имеют eNRI=NaN;
13. в \(\mathcal E\cup\mathcal O\) нет missing_visit;
14. все 12 состояний построены из фиксированной исходной группы;
15. denominator внутри CV относится только к соответствующей части split;
16. positivity и variance используют observed + imputed;
17. все производные тождества выполняются;
18. наблюдаемая latency неотрицательна, а structural-censored latency имеют censored_latency=1 и закодированы максимумом без leakage;
19. DI находится в \([-1,1]\);
20. восемь согласованных масштабных значений сохранены без изменения и отмечены accepted_scale_value; остальные MAD-outlier отражены в diagnostics;
21. одинаковые CV-split использованы для всех гиперпараметров;
22. имputer в каждом fold обучен только на train;
23. ограничения QP выполнены с численной tolerance;
24. созданы четыре выходных файла;
25. model.json достаточен для повторного расчёта eNRI для полного 30-мерного модельного вектора;

## 14. run.sh и requirements.txt

run.sh:

~~~bash
#!/usr/bin/env bash
set -e
pip install -r requirements.txt
python solve.py
~~~

requirements.txt фиксируется по версиям, использованным в финальном GitHub Actions окружении:

~~~text
pandas==3.0.6
numpy==2.5.3
openpyxl==3.1.5
scikit-learn==1.9.1
scipy==1.18.1
cvxpy==1.9.3
osqp==1.1.3
~~~

Фиксация версий выполнена на этапе 9 для воспроизводимости финального расчёта.

## 15. Порядок программирования

1. Создать solve.py.
2. Задать исключения, GROUP_MAP, точный mapping 35 обрабатываемых признаков и MODEL_FEATURES из 30 признаков.
3. Реализовать чтение Excel и preflight.
4. Реализовать фиксированные группы и death.
5. Реализовать data-QC.
6. Реализовать детерминированные правила NOR и обработку структурно цензурированных latency.
7. Реализовать baseline-стандартизацию.
8. Реализовать IterativeImputer для 30 модельных признаков.
9. Реализовать 12 состояний, \(\mathcal E,\mathcal O,\mathcal G\).
10. Реализовать \(a_A,\mathbf b_A,\mathbf S_A\).
11. Реализовать \(\mathbf Q_{\mathrm{var}}\).
12. Реализовать QP при \(\rho=0.1,\beta=\lambda=C=1\).
13. Добавить численные проверки QP.
14. Добавить repeated stratified 3-fold CV.
15. Добавить validation-метрики.
16. Добавить детерминированный выбор \(\beta,\lambda,C\).
17. Добавить stability diagnostics через raw-scale slopes.
18. Решить финальную модель.
19. Выполнить complete-case sensitivity analysis.
20. При необходимости выполнить stochastic imputation sensitivity.
21. Выполнить sensitivity analysis по \(\rho\).
22. Сохранить weights.csv, enri.csv, diagnostics.csv, model.json.
23. Проверить воспроизводимость.
24. Только после этого запускать через run.sh и .run.

Проект остаётся минимальным: один solve.py, один входной Excel и четыре выходных файла.
