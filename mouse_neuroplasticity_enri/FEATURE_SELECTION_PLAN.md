# План выделения минимального устойчивого набора признаков для eNRI

## 1. Что именно мы строим

В данных нет наблюдаемой величины true neuroplasticity и нет известного истинного индекса нейропластичности, по которому можно было бы обучить или напрямую проверить eNRI.

В этой работе eNRI — сконструированный латентный интегральный индекс функционального состояния:

\[
eNRI_i
=
1+
w^\top
\left(
x_i-\overline{x}_{PBS^0}
\right).
\]

Веса определяются из данных под заранее заданной биологической структурой.

Поэтому цель feature selection формулируется так:

\[
\boxed{
\text{найти минимальный устойчивый набор признаков, достаточный для построения eNRI}
}
\]

а не так:

\[
\boxed{
\text{найти доказанные причинные маркеры нейропластичности}
}.
\]

Признак, признанный главным в рамках этого проекта, означает:

> признак, устойчиво важный для построения eNRI с заданной биологической структурой и сохраняющий out-of-sample качество сокращённого индекса.

Это не является само по себе доказательством причинной роли признака в нейропластичности.

После построения reduced eNRI вопрос о том, насколько индекс действительно отражает нейропластичность как биологический конструкт, должен проверяться отдельно на независимых внешних показателях, если они доступны.

Главный принцип отбора:

\[
\boxed{
\text{главный признак для eNRI}
\neq
\text{большой коэффициент в одной модели}
}
\]

а

\[
\boxed{
\text{главный признак для eNRI}
=
\text{часто выбирается}
+
\text{стабилен по знаку}
+
\text{не полностью заменяется соседями}
+
\text{его удаление ухудшает модель}
+
\text{он нужен в хорошем reduced eNRI}
}
\]

## 2. Базовая модель для feature selection

В качестве исходной точки используем первую модель:

\[
\beta=0.1,\qquad
\lambda_2=0.1,\qquad
C=0.1,\qquad
\rho=0.1.
\]

Для этапа feature selection используем полный исходный набор из 10 направленных условий.

### 2.1. Мягкие равенства

\[
PBS^0\approx LPS^0
\]

\[
PBS^0\approx run^0
\]

\[
PBS^0\approx MCC^0
\]

\[
LPS^{16}\approx run^{16}
\]

\[
LPS^{16}\approx MCC^{16}
\]

### 2.2. Направленные условия

\[
PBS^{16}>LPS^{16}
\]

\[
PBS^{24}>LPS^{24}
\]

\[
run^{24}>LPS^{24}
\]

\[
MCC^{24}>LPS^{24}
\]

\[
PBS^0>PBS^{16}
\]

\[
LPS^0>LPS^{16}
\]

\[
run^0>run^{16}
\]

\[
MCC^0>MCC^{16}
\]

\[
PBS^{16}>PBS^{24}
\]

\[
LPS^{16}>LPS^{24}.
\]

Каждое направленное условие реализуется как

\[
A-B\ge\rho-\eta,\qquad \eta\ge0.
\]

Условия

\[
run^{24}>LPS^{24},
\qquad
MCC^{24}>LPS^{24}
\]

являются частью конструкции индекса. Поэтому их выполнение нельзя интерпретировать как независимое обнаружение или доказательство эффекта run/MCC.

## 3. Что не меняем во всём pipeline

На всех этапах сохраняются:

- анализ на уровне mouse_id;
- все состояния одной мыши находятся только в train или только в validation;
- train-only deterministic preprocessing;
- train-only baseline scaling;
- train-only censor maxima;
- train-only fit статистического imputer;
- фиксированная экспериментальная группа мыши;
- death \(\rightarrow eNRI=0\);
- positivity для живых:

\[
eNRI\ge0.001;
\]

- нормировка:

\[
PBS^0=1;
\]

- 30 MODEL_FEATURES как полный исходный набор;
- 5 детерминированных NOR-признаков не получают отдельных eNRI-весов;
- полный QC;
- сравнение весов между splits через raw-scale slopes:

\[
\gamma_j=\frac{w_j}{s_j}.
\]

Прямое сравнение стандартизованных \(w_j\) между splits не используется как основная оценка стабильности.

## 4. Почему нельзя выбирать признаки по одному \(|w_j|\)

При \(n=54\) и \(p=30\):

- один и тот же сигнал может распределяться между несколькими коррелированными признаками;
- знак коэффициента может меняться между splits;
- большой коэффициент может появляться из-за конкретного состава маленькой выборки;
- ridge-регуляризация стабилизирует модель, но обычно не зануляет ненужные признаки.

Поэтому величина \(|w_j|\) используется только как дополнительная характеристика.

# Этап A. Анализ коррелированных блоков

## A1. Два типа Spearman-корреляций

Для каждой пары признаков и каждой недели отдельно считаются:

\[
r_{pool}^0,\quad r_{pool}^{16},\quad r_{pool}^{24},
\]

по живым мышам соответствующей недели.

Дополнительно считаются group-centered значения. Для каждого признака внутри каждой комбинации group × week вычитается медиана группы:

\[
x_{ij}^{centered}
=
x_{ij}
-
median(x_j\mid group,week),
\]

после чего для каждой недели считаются:

\[
r_{centered}^0,\quad
r_{centered}^{16},\quad
r_{centered}^{24}.
\]

Pooled correlation показывает общую совместную изменчивость признаков. Group-centered correlation помогает отличить реальную избыточность признаков от корреляции, возникающей только потому, что оба признака разделяют экспериментальные группы.

Не объединять все недели в одну матрицу как независимые наблюдения.

## A2. Ребро сильной связи

Для пары признаков создаётся primary strong-correlation edge, если:

1. минимум в двух из трёх недель выполняется

\[
|r_{pool}|\ge0.8;
\]

2. знак strong pooled correlation совпадает в этих неделях;
3. group-centered correlations не дают противоположный знак минимум в двух доступных неделях.

Если pooled-критерий выполнен, но group-centered correlations устойчиво меняют знак, связь помечается как potentially group-driven и не используется для автоматического формирования redundancy block.

Все pooled и centered значения сохраняются в diagnostics.

## A3. Формирование блоков

Признаки — вершины графа.

Принятые strong-correlation edges — рёбра.

Correlation block определяется как connected component этого графа.

Таким образом, если

\[
A\leftrightarrow B,\qquad
B\leftrightarrow C,
\]

то

\[
\{A,B,C\}
\]

является одним блоком даже при отсутствии прямого strong edge между \(A\) и \(C\).

Коррелированные признаки автоматически не удаляются.

Блоки используются для:

- интерпретации stability selection;
- оценки взаимозаменяемости признаков;
- block stability;
- block ablation;
- block-aware ranking.

Если correlation blocks участвуют в выборе subset внутри nested validation, они вычисляются только на соответствующем train.

# Этап B. Sparse constrained eNRI

## B1. Целевая функция

К текущей целевой функции добавляется \(L_1\)-штраф:

\[
L_{\text{current}}
+
\lambda_1\|w\|_1
+
\lambda_2\|w\|_2^2.
\]

Используется constrained Elastic Net.

На первом sparse-проходе фиксируются:

\[
\beta=0.1,\qquad
\lambda_2=0.1,\qquad
C=0.1,\qquad
\rho=0.1,
\]

а меняется только

\[
\lambda_1.
\]

## B2. Сетка \(\lambda_1\)

Использовать заранее фиксированную сетку:

\[
\lambda_1\in
\{
0,\,
10^{-5},\,
3\cdot10^{-5},\,
10^{-4},\,
3\cdot10^{-4},\,
10^{-3},\,
3\cdot10^{-3},\,
10^{-2},\,
3\cdot10^{-2},\,
10^{-1},\,
3\cdot10^{-1}
\}.
\]

Если при \(\lambda_1=0.3\) модель остаётся практически полной, сетка автоматически расширяется:

\[
1,\ 3.
\]

Расширение выполняется по этому заранее заданному правилу.

## B3. Numerical zero

Признак считается active, если

\[
|w_j|>10^{-6}.
\]

Порог \(10^{-6}\) используется только как numerical zero threshold.

## B4. Метрики для каждого \(\lambda_1\)

Сохранять:

- число active features;
- список active features;
- \(V_{pos}\);
- \(V_{sign}\);
- \(V_{margin}\);
- \(V_{eq}\);
- \(V_{var}\);
- \(V_w\);
- slack sum;
- slack max;
- solver status.

## B5. Как выбирается \(\lambda_1^*\)

\(\lambda_1\) никогда не выбирается по full-data fit.

На development-этапе до nested validation используется mouse-level CV.

Внутри каждого training context:

1. для каждого \(\lambda_1\) вычисляются validation-метрики на одних и тех же inner splits;
2. метрики рассматриваются в порядке

\[
V_{pos}
\rightarrow
V_{sign}
\rightarrow
V_{margin}
\rightarrow
V_{eq}
\rightarrow
V_{var}
\rightarrow
V_w;
\]

3. на каждом шаге остаются модели, чьё среднее значение метрики не хуже лучшего более чем на one-SE threshold;
4. если после всех метрик остаётся несколько \(\lambda_1\), выбирается наибольшее \(\lambda_1\), то есть более sparse решение.

Для метрики \(V\):

\[
SE(V)
=
\frac{
SD(V_{\text{valid inner splits}})
}{
\sqrt{N_{\text{valid inner splits}}}
}.
\]

Из-за перекрывающихся repeated splits это используется как эвристическая мера стабильности, а не как классическая inferential standard error.

# Этап C. Stability selection

## C1. Какой \(\lambda_1\) используется

Stability selection проводится при фиксированном \(\lambda_1^*\), выбранном только внутри соответствующего training context по правилу B5.

Outer-validation никогда не участвует в выборе \(\lambda_1^*\).

## C2. Resampling

Для оценки стабильности выбора использовать отдельный stratified mouse-level resampling.

Цель:

\[
100
\]

валидных resamples как обязательный минимум.

Если вычислительно возможно, основной запуск выполняется на 200 валидных resamples.

В каждом resample брать 80% мышей в train с сохранением представительства групп:

\[
PBS,\ LPS,\ run,\ MCC.
\]

Все состояния одной мыши всегда остаются вместе.

## C3. Полный train-only pipeline

В каждом resample заново выполняются:

1. deterministic preprocessing;
2. censor maxima;
3. baseline scaling;
4. statistical imputation;
5. построение состояний;
6. sparse constrained QP при фиксированном \(\lambda_1^*\).

## C4. Частота выбора

Для каждого признака:

\[
\pi_j
=
\frac{
\#\{\text{валидные resamples, где } |w_j|>10^{-6}\}
}{
\#\{\text{валидные resamples}\}
}.
\]

## C5. Стабильность знака

Знак оценивается только среди resamples, где признак active:

\[
s_j
=
\max
\left[
P(w_j>0\mid selected),
P(w_j<0\mid selected)
\right].
\]

## C6. Категории

Core feature:

\[
\pi_j\ge0.8
\]

и

\[
s_j\ge0.9.
\]

Candidate feature:

\[
0.6\le\pi_j<0.8
\]

и

\[
s_j\ge0.8.
\]

Признаки ниже этих порогов не удаляются автоматически, если они входят в устойчивый correlation block.

## C7. Что сохранять

Для каждого признака:

- \(\pi_j\);
- positive sign frequency;
- negative sign frequency;
- \(s_j\);
- median \(\gamma_j\);
- q10 \(\gamma_j\);
- q90 \(\gamma_j\);
- median \(|\gamma_j|\).

# Этап D. Block stability

Для каждого correlation block считать:

\[
\pi_{block}
=
P(\text{выбран хотя бы один признак блока}).
\]

Пример:

\[
\pi_A=0.50,\qquad
\pi_B=0.50,
\]

но

\[
P(A\lor B)=0.95.
\]

В таком случае информационный блок устойчив, хотя конкретный представитель блока нестабилен.

Также сохранять:

- наиболее часто выбираемый представитель блока;
- частоты совместного выбора;
- частоты взаимного замещения признаков.

# Этап E. Ablation analysis

## E1. Feature ablation

Для каждого core/candidate признака:

1. удалить признак;
2. полностью переобучить модель;
3. использовать те же validation splits, что и reference-модель;
4. вычислить paired differences:

\[
\Delta V_{pos},
\quad
\Delta V_{sign},
\quad
\Delta V_{margin},
\quad
\Delta V_{eq},
\quad
\Delta V_{var}.
\]

Для каждой \(\Delta V\) сохранять:

- median;
- q10;
- q90;
- долю splits с

\[
\Delta V>0.
\]

Ablation не используется как отдельный p-value test.

## E2. Block ablation

Для каждого correlation block удалить весь блок и выполнить тот же paired analysis.

## E3. Роль ablation

Ablation используется для ranking и интерпретации, а не как самостоятельный жёсткий PASS/FAIL фильтр.

Чем чаще удаление признака/блока ухудшает более приоритетные validation-метрики и чем больше median deterioration, тем выше его ablation importance.

# Этап F. Block-aware ranking и наборы \(S_k\)

## F1. Ranking внутри блока

Внутри каждого correlation block признаки ранжируются по:

1. selection frequency \(\pi_j\);
2. sign stability \(s_j\);
3. ablation importance;
4. median \(|\gamma_j|\);
5. canonical feature order как детерминированный tie-break.

Первый признак является primary representative блока.

## F2. Ranking между блоками и одиночными признаками

Первоначальный общий ranking содержит:

- все признаки, не входящие в correlation blocks;
- по одному primary representative от каждого блока.

Они ранжируются по тем же критериям:

\[
\pi_j
\rightarrow
s_j
\rightarrow
ablation
\rightarrow
median|\gamma_j|.
\]

## F3. Дополнительные представители блока

Для каждого блока выполняется within-block compression check:

1. сравнить модель с полным набором кандидатов блока;
2. сравнить модель только с primary representative блока;
3. оценить эти модели на тех же inner splits.

Если модель с одним representative находится в пределах one-SE по приоритетным validation-метрикам, блок считается представимым одним признаком.

Если нет, разрешается добавить второй по ranking представитель блока и повторить проверку.

Добавление последующих представителей продолжается только пока это необходимо для выхода в one-SE область.

Таким образом, top-\(k\) не заполняется несколькими почти дублирующими признаками без evidence, что они дают дополнительную информацию.

## F4. Наборы кандидатов

После block compression строятся:

\[
S_3,S_4,\ldots,S_{15}.
\]

Если устойчивых кандидатов меньше 15, верхняя граница автоматически уменьшается до доступного числа.

Для каждого \(S_k\):

1. оставить только выбранные weighted features;
2. заново выполнить reduced preprocessing;
3. заново обучить constrained QP;
4. получить новые веса.

Старые веса полной модели не переносятся.

# Этап G. Выбор минимального достаточного \(k\)

Для каждого \(k\) оценить out-of-sample:

\[
V_{pos},
\quad
V_{sign},
\quad
V_{margin},
\quad
V_{eq},
\quad
V_{var},
\quad
V_w.
\]

Использовать smallest-within-one-SE rule.

Приоритет:

\[
V_{pos}
\rightarrow
V_{sign}
\rightarrow
V_{margin}
\rightarrow
V_{eq}
\rightarrow
V_{var}
\rightarrow
V_w.
\]

На каждом шаге сохраняются модели, чьё среднее значение текущей метрики не хуже лучшего более чем на one-SE threshold, вычисленный на тех же inner splits.

После последовательной фильтрации выбирается минимальный \(k\).

Если несколько subset имеют одинаковый \(k\) и находятся в one-SE области, tie-break:

1. меньше required acquisition/preprocessing fields;
2. выше stability selection frequency;
3. выше sign stability;
4. canonical feature order.

# Этап H. Nested mouse-level validation

## H1. Outer validation

Использовать 30 валидных repeated stratified mouse-level 80/20 outer splits.

Seeds перебираются детерминированно, начиная с 1000, пока не будет собрано 30 валидных outer splits.

Все состояния одной мыши находятся только в одной части split.

Outer-validation никогда не используется для:

- correlation blocks;
- выбора \(\lambda_1\);
- stability selection;
- block analysis;
- ablation;
- ranking;
- выбора \(k\);
- выбора subset.

## H2. Валидность outer split

Outer split принимается, если после train-only preprocessing:

\[
|O_A^{train}|\ge5
\]

для всех состояний, где требуется train covariance/QP, и

\[
|O_A^{val}|\ge2
\]

для validation variance.

Также должны быть вычислимы все необходимые equality/order states.

## H3. Inner validation

Внутри каждого outer-train используются 20 валидных repeated stratified mouse-level 80/20 inner splits.

Inner seeds задаются детерминированно:

\[
seed_{inner}
=
10000
+
100\cdot outer\_index
+
candidate\_index,
\]

где candidate_index увеличивается, пока не будут собраны 20 валидных inner splits.

Для inner split применяются те же минимальные критерии:

\[
|O_A^{train}|\ge5,
\qquad
|O_A^{val}|\ge2.
\]

## H4. Полный selection внутри outer-train

Внутри каждого outer-train полностью заново выполняются:

\[
correlations
\rightarrow
\lambda_1^*
\rightarrow
stability\ selection
\rightarrow
block\ stability
\rightarrow
ablation
\rightarrow
block\text{-}aware\ ranking
\rightarrow
S_k
\rightarrow
k^*
\rightarrow
subset.
\]

После этого reduced QP заново обучается на всём outer-train.

## H5. Outer metrics

На outer-validation только вычисляются:

\[
V_{pos},
V_{sign},
V_{margin},
V_{eq},
V_{var},
V_w.
\]

Также сохранять:

- выбранный \(\lambda_1^*\);
- выбранный \(k^*\);
- выбранный subset;
- число required acquisition fields;
- групповые средние eNRI;
- slack diagnostics;
- solver status.

После 30 outer splits считать:

- частоту выбора каждого признака;
- частоту выбора каждого блока;
- распределение выбранного \(k\);
- частоту повторения одинаковых subset;
- распределение outer validation metrics.

# Этап I. Reduced preprocessing и реальная стоимость измерения

## I1. Weighted features

Selected weighted features — только признаки, которые входят в формулу reduced eNRI и получают ненулевые/оцениваемые веса.

## I2. Required preprocessing fields

Некоторые выбранные признаки требуют дополнительных исходных полей для корректного preprocessing.

Например, structural censoring latency определяется условием:

\[
Time=0,\qquad Latency=NaN.
\]

Поэтому если selected feature — object latency, соответствующий object Time может быть обязательным acquisition/preprocessing field даже если сам Time не получает eNRI-вес.

Для каждого subset хранить два числа:

\[
k_{weighted}
\]

и

\[
k_{acquisition}.
\]

В финальной формуле участвуют только \(k_{weighted}\), но практическая стоимость reduced eNRI описывается через \(k_{acquisition}\).

## I3. Reduced imputation

Основная reduced-модель использует для statistical imputation:

\[
X_S
+
week_{16}
+
week_{24},
\]

где \(X_S\) — selected weighted features.

Не использовать:

- экспериментальную группу как predictor;
- остальные невошедшие MODEL_FEATURES как скрытые predictors.

Required preprocessing fields могут использоваться только для детерминированных правил, необходимых для получения \(X_S\), но не как дополнительные статистические predictors, если они не входят в \(S\).

Дополнительно разрешён sensitivity-анализ с all-30-assisted imputation, но он не является основной reduced-моделью.

# Этап J. Longitudinal sensitivity

Longitudinal analysis используется только как sensitivity и интерпретация, а не как selector.

Для мышей, живых в обеих соответствующих точках:

\[
\Delta x_i^{0\to16}
=
x_i^{16}-x_i^0,
\]

\[
\Delta x_i^{16\to24}
=
x_i^{24}-x_i^{16}.
\]

Особенно анализировать:

\[
16\rightarrow24,
\]

поскольку после состояния 16 начинаются различающие воздействия run/MCC.

Для умерших мышей feature-delta после смерти не вычислять и не заменять смерть нулевым значением признака.

При необходимости mixed-effects модели использовать только как дополнительный sensitivity analysis.

Отсутствие статистической значимости longitudinal signal само по себе не является основанием для удаления признака из-за низкой мощности выборки.

# Этап K. Финальный subset по результатам nested validation

После завершения 30 outer splits финальный subset выбирается без просмотра full-data fit.

Основной источник — частота выбора признаков и блоков во внешних итерациях.

Признак может войти в final candidate set, если:

1. он часто выбирается как weighted feature во внешних итерациях; или
2. он является устойчивым representative устойчивого блока.

Финальный \(k\) выбирается по распределению \(k^*\) и outer validation quality с предпочтением меньшего \(k\), если более сложные варианты не дают устойчивого улучшения.

После фиксации final subset правила больше не меняются.

# Этап L. Финальный full-data refit reduced eNRI

После фиксации окончательного subset:

1. оставить selected weighted features;
2. определить required preprocessing fields;
3. выполнить full-data reduced preprocessing;
4. пересчитать baseline scaling;
5. пересчитать \(\overline{x}_{PBS^0}\);
6. построить 12 состояний;
7. решить constrained QP со всеми 5 равенствами и 10 направленными условиями;
8. получить новые reduced-веса;
9. сохранить финальную формулу.

\[
eNRI_{\text{reduced}}
=
1+
\sum_{j\in S}
w_j^{\text{reduced}}
\left(
x_j-\overline{x}_{PBS^0,j}
\right).
\]

# Этап M. Сравнение full и reduced eNRI

Для reduced eNRI повторить robustness-анализ уровня Stage 8.

Сравнивать:

- positivity;
- equality errors;
- order errors;
- slack sum;
- slack max;
- индивидуальные eNRI;
- Spearman rank correlation;
- group-rank Spearman;
- group mean differences;
- complete-case sensitivity;
- \(\rho\)-sensitivity;
- imputation sensitivity;
- longitudinal sensitivity.

Для сравнения направлений весов reduced \(\gamma\)-вектор дополняется нулями до исходных 30 координат, после чего вычисляется cosine similarity с full-model \(\gamma\).

# Этап N. Внешняя проверка биологического смысла

Этот этап концептуально отделён от feature selection.

Если доступны независимые молекулярные, морфологические, физиологические или иные показатели, которые не использовались при построении eNRI, проверить связь:

\[
eNRI_{\text{reduced}}
\leftrightarrow
\text{independent biological endpoints}.
\]

Такая проверка нужна, чтобы обосновывать более сильное утверждение о том, что eNRI действительно отражает нейропластичность как биологический конструкт.

Без такой внешней проверки корректная формулировка результата:

> минимальный устойчивый набор признаков для сконструированного eNRI с заданной биологической структурой.

# Этап O. Критерии признания признака главным для eNRI

Признак считается главным для eNRI по совокупности:

1. высокая selection frequency;
2. стабильный знак;
3. устойчивый raw-scale slope;
4. принадлежность к устойчивому информационному блоку или самостоятельная устойчивость;
5. ухудшение out-of-sample качества при feature/block ablation;
6. повторный выбор во внешних nested-validation итерациях;
7. присутствие в минимальном достаточном reduced subset;
8. разумная longitudinal интерпретируемость.

Ни один из этих пунктов сам по себе не означает причинность.

# Этап P. Методы, которые не использовать как основной selector

Не использовать как основной способ отбора:

- top-\(|w_j|\) из одной full-data модели;
- stepwise regression;
- выбор по отдельным p-value;
- Random Forest feature importance;
- XGBoost feature importance;
- SHAP;
- PCA как финальный feature selector;
- чистый LASSO без \(L_2\)-части при сильной корреляции признаков.

Они могут использоваться только как дополнительный exploratory/sensitivity analysis.

## 5. Итоговый рабочий pipeline

\[
\boxed{
30\ features
\rightarrow
correlation\ graph
\rightarrow
constrained\ Elastic\ Net
\rightarrow
\lambda_1^*
\rightarrow
stability\ selection
\rightarrow
block\ stability
\rightarrow
feature/block\ ablation
\rightarrow
block\text{-}aware\ S_k
\rightarrow
nested\ validation
\rightarrow
minimal\ stable\ subset
\rightarrow
full\ reduced\ refit
\rightarrow
Stage\ 8
\rightarrow
longitudinal\ sensitivity
\rightarrow
external\ validation
}
\]

## 6. Основные выходные файлы будущего этапа

Минимально сохранить:

- correlation_pairs.csv
- correlation_blocks.csv
- elastic_net_path.csv
- lambda1_selection.csv
- stability_selection.csv
- block_stability.csv
- feature_ablation.csv
- block_ablation.csv
- block_compression.csv
- subset_cv.csv
- nested_outer_results.csv
- nested_feature_frequency.csv
- selected_features.csv
- required_preprocessing_fields.csv
- reduced_weights.csv
- reduced_enri.csv
- reduced_model.json
- reduced_stage8_summary.json

## 7. Критическое правило остановки

Нельзя объявлять reduced eNRI успешным только потому, что он использует мало признаков.

Сокращённая модель принимается только если:

1. её out-of-sample качество находится в one-SE области относительно лучших более сложных моделей;
2. она не демонстрирует существенно худшую устойчивость, чем полный eNRI;
3. выбранные признаки воспроизводимо появляются при изменении состава мышей;
4. модель корректно работает с selected weighted features и явно указанными required preprocessing fields;
5. правила отбора не менялись после просмотра outer-validation результатов.

Если устойчивого малого subset не существует, результатом анализа должно быть именно это, а не принудительный выбор нескольких признаков.
