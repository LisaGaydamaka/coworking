# eNRI: описание задачи и минимальный план реализации

# I. Описание задачи

## 1. Цель

Требуется найти вектор весов

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

Для достоверно умершего животного:

\[
eNRI(death)=0.
\]

Группа животного не входит в \(\mathbf x\) и используется только для построения групповых ограничений.

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

## 3. Экспериментальные когорты

До второй рандомизации вся исходная LPS-когорта обозначается

\[
\mathcal L^0,\qquad \mathcal L^{16}.
\]

Она строится непосредственно по исходному назначению LPS, а не через будущие ветви.

Обозначения

\[
LPS^t,\qquad run^t,\qquad MCC^t
\]

относятся к животным, реально назначенным во вторую рандомизацию соответственно в LPS, run и MCC.

Для животных, переживших вторую рандомизацию, можно использовать их измерения недели 16 в соответствующих будущих ветвях:

\[
LPS^{16},\qquad run^{16},\qquad MCC^{16}.
\]

Животное, умершее до второй рандомизации, не относится ни к одной из этих трёх ветвей.

На неделе 24 используются фактические ветви

\[
LPS^{24},\qquad run^{24},\qquad MCC^{24}.
\]

## 4. Импутация и стандартизация

Исходный вектор:

\[
\mathbf r=(r_1,\ldots,r_{35})^{\mathsf T}.
\]

Пропуски заполняются только для живых животных. Смерть не импутируется и имеет отдельное значение

\[
eNRI(death)=0.
\]

Основная модель использует \(IterativeImputer\) из scikit-learn. В импутер передаются 35 функциональных признаков и номер недели. Экспериментальная группа, принадлежность PBS/LPS/run/MCC и eNRI в импутации не используются.

Импутация всегда выполняется внутри train-fold:

\[
train
\rightarrow
fit\ imputer
\rightarrow
transform\ train
\rightarrow
transform\ validation.
\]

Validation никогда не используется при обучении импутера.

Полностью отсутствующий 35-мерный визит живого животного автоматически не восстанавливается. Он получает статус missing_visit. Если такой визит нужен для состояния из \(\mathcal E\) или \(\mathcal O\), основной анализ останавливается и требует отдельного решения по missing data.

Частично заполненный визит после успешной импутации получает статус imputed. Число исходно пропущенных признаков сохраняется в диагностике.

После импутации вычисляется стандартизованный вектор

\[
\mathbf x=(x_1,\ldots,x_{35})^{\mathsf T},
\]

где

\[
x_j=\frac{r_j-m_j}{s_j}.
\]

Параметры стандартизации вычисляются только по baseline train-мышам после train-only импутации:

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

При финальном обучении импутер обучается на всех допустимых живых данных, после чего \(m_j,s_j\) вычисляются по baseline-наблюдениям после импутации.

Если \(s_j=0\), расчёт завершается с ошибкой.

## 5. Средний eNRI всей когорты с учётом смертей

Для каждой когорты \(A\) в конкретный момент времени задаются:

- \(N_A\) — размер соответствующей рандомизированной когорты;
- \(R_A\) — живые животные с исходно полным функциональным вектором;
- \(I_A\) — живые животные, для которых частичные пропуски успешно импутированы;
- \(O_A=R_A\cup I_A\) — все живые животные с полным вектором после preprocessing;
- \(D_A\) — достоверно умершие к этому моменту;
- \(U_A\) — живые животные, для которых полный вектор получить нельзя.

Основная модель требует

\[
U_A=\varnothing
\]

для всех состояний, участвующих в \(\mathcal E\) или \(\mathcal O\). Тогда

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

Тогда средний eNRI всей когорты, включая смерти как нули:

\[
\boxed{
\mu_A(\mathbf w)
=
a_A+\mathbf w^{\mathsf T}\mathbf b_A.
}
\]

Таким образом, частичные пропуски живых животных входят в \(\mu_A\) после train-only импутации. Неимпутируемый живой визит не заменяется нулём и не считается смертью.

## 6. Ограничения, связанные с рандомизацией

Используются пары:

\[
\mathcal E
=
\{
(PBS^0,\mathcal L^0),
(LPS^{16},run^{16}),
(LPS^{16},MCC^{16})
\}.
\]

Для них требуется близость средних eNRI:

\[
\mu_A(\mathbf w)\approx\mu_B(\mathbf w).
\]

## 7. Ограничения порядка

Межгрупповые отношения:

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

Продольные отношения для одной и той же рандомизированной когорты:

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

Для каждой пары \((A,B)\in\mathcal O\):

\[
\mu_A(\mathbf w)
\ge
\mu_B(\mathbf w)+\rho-\eta_{AB},
\]

\[
\eta_{AB}\ge0.
\]

## 8. Margin

В основной модели фиксируется

\[
\boxed{\rho=0.1}.
\]

Он не подбирается вместе с остальными гиперпараметрами.

Дополнительно после получения основной модели выполняется sensitivity analysis при

\[
\rho\in\{0.05,0.2,0.3\}.
\]

Эти значения не используются для выбора основной модели, а только для оценки устойчивости результата.

## 9. Состояния для внутригрупповой дисперсии

Ковариационные матрицы вычисляются по живым животным с полным функциональным вектором после preprocessing, то есть по исходно полным и успешно импутированным наблюдениям.

Используются состояния:

\[
\mathcal G=
\{
PBS^0,\mathcal L^0,
PBS^{16},\mathcal L^{16},
PBS^{24},LPS^{24},run^{24},MCC^{24}
\}.
\]

Чтобы 0-я, 16-я и 24-я недели имели одинаковый суммарный вес, вводится

\[
\mathbf Q_{\mathrm{var}}
=
\frac12
\left(
\mathbf S_{PBS^0}
+
\mathbf S_{\mathcal L^0}
\right)
+
\frac12
\left(
\mathbf S_{PBS^{16}}
+
\mathbf S_{\mathcal L^{16}}
\right)
\]

\[
+
\frac14
\left(
\mathbf S_{PBS^{24}}
+
\mathbf S_{LPS^{24}}
+
\mathbf S_{run^{24}}
+
\mathbf S_{MCC^{24}}
\right).
\]

## 10. Ковариации

Для состояния \(A\), используя \(O_A=R_A\cup I_A\):

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

Смерти не имеют 35-мерного функционального вектора и в \(\mathbf S_A\) не входят.

## 11. Задача оптимизации

Для пары \((A,B)\) обозначим

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
\mu_A-\mu_B
=
c_{AB}
+
\mathbf w^{\mathsf T}\mathbf d_{AB}.
\]

Штраф за нарушение равенств:

\[
\beta
\sum_{(A,B)\in\mathcal E}
\left(
c_{AB}
+
\mathbf w^{\mathsf T}\mathbf d_{AB}
\right)^2.
\]

Итоговая задача:

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
\right]
\]

при

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

для каждого живого наблюдения с полным функциональным вектором.

Задача остаётся выпуклой квадратичной программой.

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

- список 35 признаков;
- точное соответствие признаков столбцам недель 0, 16 и 24;
- \(\mathcal E\);
- \(\mathcal O\);
- \(\mathcal G\);
- \(\varepsilon=10^{-3}\);
- \(\rho=0.1\);
- сетки \(\beta,\lambda,C\);
- фиксированные random seeds;
- CV tolerance, например \(10^{-6}\).

### 2.2. Прочитать Excel

1. Прочитать data/mice.xlsx.
2. Проверить обязательные столбцы.
3. Проверить уникальность ID.
4. Проверить первую и вторую рандомизации.
5. Проверить допустимые переходы.
6. Преобразовать 35 признаков в числовой формат.
7. Не определять смерть автоматически по NaN.

Если схема нарушена, остановить расчёт.

### 2.3. Построить длинную таблицу

Одна строка:

\[
(\text{mouse\_id},t,\mathbf r_i^t).
\]

Хранить:

- mouse_id;
- week;
- исходную рандомизированную группу;
- вторую рандомизированную ветвь, если она была;
- статус alive/death;
- missing_count;
- 35 признаков.

Статусы:

- observed — исходно полный живой вектор;
- imputed — живой вектор с успешно заполненными частичными пропусками;
- death — достоверная смерть;
- missing_visit — живой визит без достаточной информации для импутации.

## 3. Этап 2. Preflight пропусков, смертей и когорт

### 3.1. Пропуски и импутация

До QP:

1. построить missingness по week × cohort × feature;
2. для каждой живой строки сохранить missing_count;
3. отдельно посчитать исходно полные строки;
4. отдельно посчитать строки с частичными пропусками;
5. отдельно посчитать полностью отсутствующие живые визиты;
6. отдельно посчитать смерти;
7. не считать NaN смертью.

Основная модель:

- исходно полные живые строки использует без изменений;
- частичные пропуски живых строк заполняет через IterativeImputer;
- полностью отсутствующий 35-мерный живой визит не импутирует;
- смерти никогда не импутирует.

Импутер обучается только на train внутри каждого CV-fold. В validation применяется уже обученный train-imputer.

Группа лечения не используется как предиктор импутации.

После импутации обязательна проверка, что для каждого состояния из \(\mathcal E\) и \(\mathcal O\)

\[
U_A=\varnothing.
\]

Если остаётся неимпутируемый живой визит, необходимый для группового ограничения, основной анализ останавливается.

Для оценки влияния импутации дополнительно выполняются:

1. complete-case sensitivity analysis;
2. при необходимости 10 стохастических вариантов IterativeImputer с разными seed и sample_posterior=True.

Основная модель остаётся детерминированной: IterativeImputer с sample_posterior=False.

### 3.2. Размеры

Для ковариационных состояний train требуется

\[
n_{observed}^{train}\ge5.
\]

Для validation-variance требуется

\[
n_{observed}^{val}\ge2.
\]

Если эти условия систематически не выполняются, уменьшить число fold.

### 3.3. Когорты

Первая рандомизация задаёт:

- PBS;
- исходную LPS-когорту \(\mathcal L\).

Вторая рандомизация задаёт:

- LPS;
- run;
- MCC.

Животное, умершее до второй рандомизации, остаётся членом исходной LPS-когорты, но не включается ни в LPS, ни в run, ни в MCC второй рандомизации.

## 4. Этап 3. Repeated group-wise cross-validation

### 4.1. CV strata

Создать техническую переменную cv_stratum:

- PBS;
- LPS-second-LPS;
- LPS-second-run;
- LPS-second-MCC;
- LPS-not-randomized, если такие животные есть.

Все недели одной мыши должны находиться только в train или только в validation.

### 4.2. Разбиение

Начать с repeated 4-fold, например 10 фиксированных seed.

Если из-за малых strata 4-fold не позволяет получить валидные split, перейти на 3-fold.

Один и тот же набор split использовать для всех комбинаций \((\beta,\lambda,C)\).

Не разрешать разным гиперпараметрам оцениваться на разных наборах fold.

### 4.3. Импутация и стандартизация

Для каждого fold:

1. взять только train-мышей;
2. fit IterativeImputer на train-строках живых животных;
3. заполнить частичные пропуски train;
4. тем же fitted imputer заполнить частичные пропуски validation;
5. по baseline train после импутации вычислить \(m_j,s_j\);
6. проверить \(s_j>0\);
7. стандартизовать train;
8. теми же \(m_j,s_j\) стандартизовать validation;
9. вычислить \(\overline{\mathbf x}_{PBS^0}^{train}\).

Validation не участвует ни в обучении импутера, ни в расчёте стандартизации.

## 5. Этап 4. Построение QP на train

Для каждой train-когорты:

1. определить \(N_A\);
2. определить \(R_A,I_A,O_A,D_A,U_A\);
3. проверить \(U_A=\varnothing\) для состояний из \(\mathcal E\) и \(\mathcal O\);
4. вычислить \(a_A\);
5. вычислить \(\mathbf b_A\);
6. вычислить \(\mathbf S_A\) по \(O_A\).

В диагностике отдельно сохранять число исходно полных и импутированных наблюдений.

Собрать \(\mathbf Q_{\mathrm{var}}\).

Решать задачу в CVXPY непосредственно в форме:

~~~python
w = cp.Variable(35)
eta = cp.Variable(len(ORDER_PAIRS), nonneg=True)

loss = cp.quad_form(w, Q_var) + lam * cp.sum_squares(w)

for c, d in equality_terms:
    loss += beta * cp.square(c + w @ d)

constraints = []

for k, (c, d) in enumerate(order_terms):
    constraints.append(c + w @ d >= rho - eta[k])

for x in X_train_observed:
    constraints.append(
        1 + w @ (x - xbar_pbs0_train) >= epsilon
    )

loss += C * cp.sum(eta)

problem = cp.Problem(cp.Minimize(loss), constraints)
problem.solve(solver=cp.OSQP)
~~~

Первый smoke test:

\[
\rho=0.1,
\qquad
\beta=\lambda=C=1.
\]

## 6. Этап 5. Диагностика train-решения

После каждого QP сохранить:

\[
\|\mathbf w\|_2,
\qquad
\overline\eta,
\qquad
\max\eta.
\]

Для каждой пары:

\[
\Delta_{AB}
=
\mu_A-\mu_B.
\]

Сохранить:

- \(\Delta_{AB}\);
- \(\eta_{AB}\);
- выполнен ли знак;
- выполнен ли margin;
- размеры когорты;
- число observed;
- число deaths;
- число alive missing;
- solver_status.

Модель не отклоняется только из-за плохих биологических отношений. Это должно оставаться диагностикой.

Технически невалидны:

- отсутствие допустимого решения;
- NaN/Inf в весах;
- практически нулевая норма \(\mathbf w\), если решение свелось к константе;
- нарушение обязательных численных ограничений сверх tolerance.

## 7. Этап 6. Подбор \(\beta,\lambda,C\)

Начальная сетка:

\[
\beta,\lambda,C
\in
\{0.1,1,10\}.
\]

При необходимости после smoke test расширить.

\(\rho\) в основном CV фиксировано:

\[
\rho=0.1.
\]

### 7.1. Validation eNRI

На validation использовать только train-параметры:

\[
m_j^{train},
\qquad
s_j^{train},
\qquad
\overline{\mathbf x}_{PBS^0}^{train},
\qquad
\widehat{\mathbf w}.
\]

Для каждой validation-когорты вычислить

\[
\mu_A^{val}
=
a_A^{val}
+
\widehat{\mathbf w}^{\mathsf T}
\mathbf b_A^{val}.
\]

Смерти входят как нули.

Частичные пропуски validation заполняются только train-imputer. Неимпутируемые живые визиты не подменяются нулями.

### 7.2. Validation-метрики

Положительность живых observed:

\[
V_{\mathrm{pos}}
=
\frac{
\#\{i:eNRI_i<\varepsilon\}
}{
N_{observed,val}
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

Недобор margin:

\[
V_{\mathrm{margin}}
=
\frac1{|\mathcal O|}
\sum_{(A,B)\in\mathcal O}
\max
\left(
0,
\rho-\Delta_{AB}^{val}
\right).
\]

Ошибка равенств:

\[
V_{\mathrm{eq}}
=
\sqrt{
\frac1{|\mathcal E|}
\sum_{(A,B)\in\mathcal E}
\left(
\Delta_{AB}^{val}
\right)^2
}.
\]

Средний внутрисостоянийный разброс среди observed:

\[
V_{\mathrm{var}}
=
\frac1{|\mathcal G|}
\sum_{A\in\mathcal G}
\operatorname{Var}(eNRI\mid A,\ observed).
\]

Норма:

\[
V_w
=
\|\widehat{\mathbf w}\|_2.
\]

### 7.3. Правило выбора

Агрегировать метрики по одним и тем же fold и seed.

Сравнивать с tolerance

\[
10^{-6}.
\]

Выбирать лексикографически по

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

Порядок:

1. минимальное нарушение положительности;
2. минимальная доля неправильных знаков;
3. минимальный недобор margin;
4. минимальная ошибка равенств;
5. минимальный внутрисостоянийный разброс;
6. минимальная норма весов.

## 8. Этап 7. Финальная модель

После выбора

\[
(\beta^\*,\lambda^\*,C^\*)
\]

на всех допустимых данных:

1. fit финальный IterativeImputer на всех живых допустимых данных;
2. заполнить частичные пропуски;
3. проверить отсутствие неимпутируемых живых визитов в состояниях из \(\mathcal E\) и \(\mathcal O\);
4. вычислить baseline \(m_j,s_j\);
5. вычислить \(\overline{\mathbf x}_{PBS^0}\);
6. стандартизовать все observed/imputed;
7. построить когорты;
8. вычислить \(a_A,\mathbf b_A,\mathbf S_A\);
9. собрать \(\mathbf Q_{\mathrm{var}}\);
10. решить финальный QP;
11. получить 35 весов;
12. рассчитать eNRI для observed и imputed;
13. присвоить eNRI=0 только достоверным смертям;
14. оставить eNRI=NaN только для missing_visit.

## 9. Этап 8. Sensitivity analysis по \(\rho\)

После получения основной модели повторить полный финальный расчёт при

\[
\rho\in\{0.05,0.2,0.3\}
\]

с фиксированными выбранными

\[
(\beta^\*,\lambda^\*,C^\*).
\]

Сравнить:

- веса;
- знаки весов;
- групповые \(\mu_A\);
- slack;
- выполнение ограничений.

Sensitivity analysis не меняет основную модель с \(\rho=0.1\), а только показывает устойчивость решения.

## 10. Этап 9. Результаты

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
- cohort;
- eNRI;
- status.

status:

- observed;
- imputed;
- death;
- missing_visit.

Дополнительно хранить missing_count до импутации.

### diagnostics.csv

Хранить как строки разных type:

- state;
- order;
- equality;
- cv;
- sensitivity.

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

Для состояний и ограничений:

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
- difference;
- eta;
- condition_ok;
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
  "rho": 0.1,
  "beta": null,
  "lambda": null,
  "C": null,
  "epsilon": 0.001,
  "cv_tolerance": 0.000001,
  "random_seeds": [],
  "imputation_method": "IterativeImputer",
  "imputation_sample_posterior": false,
  "imputation_seed": null,
  "solver_status": null
}
~~~

Порядок features, mean, std, xbar_pbs0 и weights должен совпадать.

## 11. Этап 10. Финальные проверки

Перед завершением проверить:

1. найдено ровно 35 весов;
2. все веса конечны;
3. все \(\eta_{AB}\ge0\);
4. все observed/imputed living удовлетворяют \(eNRI\ge\varepsilon\) с численной погрешностью;
5. \(\overline{eNRI}_{PBS^0}=1\) по baseline PBS после preprocessing;
6. смерти имеют eNRI=0 только при достоверном статусе death;
7. imputed имеют конечный eNRI и сохранённый исходный missing_count;
8. missing_visit имеют eNRI=NaN;
9. в состояниях из \(\mathcal E\) и \(\mathcal O\) нет missing_visit;
10. все когорты построены из правильной рандомизации;
11. смерти до второй рандомизации не входят в LPS/run/MCC второй рандомизации;
12. одинаковые CV-split использованы для всех гиперпараметров;
13. импутер в каждом fold обучен только на train;
14. созданы четыре выходных файла;
15. model.json достаточен для повторного расчёта eNRI для полного 35-мерного вектора.

## 12. Этап 11. run.sh и requirements.txt

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

## 13. Порядок программирования

1. Создать solve.py.
2. Задать 35 признаков, \(\mathcal E\), \(\mathcal O\), \(\mathcal G\).
3. Реализовать чтение Excel и проверку рандомизаций.
4. Построить длинную таблицу.
5. Реализовать статусы observed/imputed/death/missing_visit.
6. Реализовать train-only IterativeImputer.
7. Реализовать когорты первой и второй рандомизации.
8. Реализовать baseline-стандартизацию после импутации.
9. Реализовать \(a_A,\mathbf b_A,\mathbf S_A\).
10. Реализовать \(\mathbf Q_{\mathrm{var}}\).
11. Реализовать QP при \(\rho=0.1,\beta=\lambda=C=1\).
12. Добавить диагностику.
13. Добавить repeated group-wise CV.
14. Добавить validation-метрики.
15. Добавить детерминированный выбор \(\beta,\lambda,C\).
16. Решить финальную модель.
17. Выполнить complete-case sensitivity analysis.
18. При необходимости выполнить 10 стохастических импутаций как sensitivity analysis.
19. Выполнить sensitivity analysis по \(\rho\).
20. Сохранить weights.csv, enri.csv, diagnostics.csv, model.json.
21. Проверить воспроизводимость.
22. Только после этого запускать через run.sh и .run.

Проект остаётся минимальным: один solve.py и только необходимые входы и результаты.
