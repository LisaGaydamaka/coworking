# eNRI feature selection experiment

Отдельный эксперимент для выделения минимального устойчивого набора признаков eNRI.

Исходная модель `enri_mouse_neuroplasticity` не изменяется.

## Текущий этап: A — корреляционная структура

`stage_a.py`:

- использует те же 30 `MODEL_FEATURES` и тот же validated preprocessing, что исходная модель;
- исключает состояния смерти из корреляционного анализа;
- выполняет deterministic preprocessing и deterministic `IterativeImputer(BayesianRidge)`;
- считает pooled Spearman отдельно для недель 0, 16 и 24;
- считает group-centered Spearman после вычитания медианы внутри `group × week`;
- принимает strong edge, если `|rho_pooled| >= 0.8` минимум на 2 из 3 недель с одинаковым знаком и group-centering не даёт устойчивого разворота знака;
- формирует correlation blocks как connected components графа strong edges.

Результаты:

- `stage_a/correlation_pairs.csv`;
- `stage_a/correlation_blocks.csv`;
- `stage_a/stage_a_summary.json`.

Важно: первый запуск на всех 54 мышах — только диагностический. Эти full-data correlation blocks нельзя переносить как фиксированные в окончательный nested feature selection. Та же функция должна пересчитываться заново только на train внутри каждого outer split.


## Этап B — constrained Elastic Net

Добавлен sparse-QP:

[
L_{current}
+
\lambda_1\|w\|_1
+
0.1\|w\|_2^2
]

при фиксированных:

[
\beta=0.1,\qquad
\lambda_2=0.1,\qquad
C=0.1,\qquad
\rho=0.1.
]

Development-сетка:

[
\lambda_1\in\{0,10^{-5},3\cdot10^{-5},10^{-4},3\cdot10^{-4},
10^{-3},3\cdot10^{-3},10^{-2},3\cdot10^{-2},10^{-1},3\cdot10^{-1}\}.
]

Использованы те же 22 валидных mouse-level CV splits, что в исходной модели.
Всего выполнено 242 sparse-QP fit без итоговых solver failures.

Проверка совместимости:

- при \(\lambda_1=0\) веса воспроизводят исходную модель \(0.1/0.1/0.1\);
- max absolute difference весов = \(1.76\times10^{-8}\).

Development one-SE selection дала:

[
\lambda_1^*=0.03.
]

При этом:

- среднее число active features по CV = 17.14;
- медиана = 16.5;
- full-data fit содержит 18 active features.

Это только development-результат. В финальной nested validation \(\lambda_1^*\) будет заново выбираться внутри каждого outer-train.

Результаты:

- `stage_b/elastic_net_path.csv`;
- `stage_b/elastic_net_fold_metrics.csv`;
- `stage_b/elastic_net_weights.csv`;
- `stage_b/lambda1_selection.csv`;
- `stage_b/stage_b_summary.json`.


## Этап C — stability selection

Использовано development-значение:

[
\lambda_1^*=0.03.
]

Выполнено 200 валидных stratified mouse-level 80/20 resamples, seeds 20000–20199. Все состояния одной мыши оставались вместе. На каждом resample preprocessing, baseline scaling, censor maxima и imputation обучались только на train-подвыборке.

Для каждого признака считались:

[
\pi_j=P(|w_j|>10^{-6}),
]

частота знака среди выбранных fits и raw-scale slope

[
\gamma_j=w_j/s_j.
]

Пороги:

- core: `pi >= 0.80` и sign consistency `>= 0.90`;
- candidate: `0.60 <= pi < 0.80` и sign consistency `>= 0.80`.

Получено 6 core и 7 candidate признаков.

Core:
- `Time_inCenter_OFT` — pi=0.940, знак − в 100% выбранных fits;
- `Latency_to_first_investigation_Stakan_zone_NOR2` — pi=0.920, знак + в 100%;
- `Latency_to_first_investigation_Piramidka_NOR1` — pi=0.915, знак − в 100%;
- `rear_support` — pi=0.890, знак + в 100%;
- `Time_investigating_Stakan_zone_NOR2` — pi=0.815, знак + в 99.4%;
- `EnduranceT` — pi=0.810, знак + в 100%.

Candidate:
- `Average_speed_OFT` — pi=0.790, знак − в 100%;
- `Learning_T3sum` — pi=0.760, знак − в 100%;
- `Absolute_turn_angle_OFT` — pi=0.660, знак + в 99.2%;
- `Learning_T1max` — pi=0.655, знак − в 99.2%;
- `Time_investigating_Piramidka_zone_NOR2` — pi=0.640, знак − в 99.2%;
- `Latency_to_first_investigation_Stakan_NOR1` — pi=0.640, знак + в 97.7%;
- `rear_nosupport` — pi=0.615, знак − в 97.6%.

Два признака выбираются часто, но не проходят core по стабильности знака:
- `OFT_distance` — pi=0.975, sign consistency=0.882;
- `Average_speed_NOR1` — pi=0.900, sign consistency=0.628.

Это development stability analysis. В финальном nested validation частоты выбора должны пересчитываться заново внутри каждого outer-train.

Результаты:

- `stage_c/stability_selection.csv`;
- `stage_c/stability_resamples.csv`;
- `stage_c/stability_coefficients.csv`;
- `stage_c/stage_c_summary.json`.


## Этап D — block stability

Использованы 6 correlation blocks из Stage A и active/inactive решения по 200 resamples из Stage C.

Для каждого блока рассчитаны:

- `P(any member selected)`;
- `P(exactly one selected)`;
- `P(multiple selected)`;
- частоты выбора каждого представителя;
- pairwise joint-selection и XOR/substitution frequencies.

Основные результаты:

- B01 OFT: `P(any)=0.995`; в 94.0% resamples выбиралось минимум два представителя блока. Это устойчивый блок, но не простой случай взаимозаменяемости одного признака другим.
- B02 NOR1 distance/speed: `P(any)=0.915`; ровно один представитель выбирался в 83.5% resamples. Основной представитель — `Average_speed_NOR1` (`pi=0.90`), но его знак нестабилен.
- B04 Learning T1: `P(any)=0.72`; основной представитель — `Learning_T1max` (`pi=0.655`).
- B06 Learning T3: `P(any)=0.76`; основной представитель — `Learning_T3sum` (`pi=0.76`).
- B05 Learning T2: `P(any)=0.565`.
- B03 NOR2 distance/speed: `P(any)=0.33`; блок выбирается редко.

Это development block stability. В финальном nested validation сами correlation blocks и их stability будут пересчитываться только внутри outer-train.

Результаты:

- `stage_d/block_stability.csv`;
- `stage_d/block_stability_ranked.csv`;
- `stage_d/block_member_stability.csv`;
- `stage_d/block_pair_selection.csv`;
- `stage_d/stage_d_summary.json`.


## Этап E — paired feature/block ablation

Development-ablation выполнен при:

[
\lambda_1^*=0.03.
]

Для каждого из 13 Stage-C core/candidate признаков и каждого из 6 Stage-A correlation blocks использованы те же 22 валидных mouse-level CV splits, что и в reference-модели.

Ablation реализован как принудительное условие:

[
w_j=0
]

для удаляемого признака или всех признаков блока с полным повторным решением constrained Elastic-Net QP.

Для каждой validation-метрики:

[
\Delta V=V_{ablated}-V_{reference}.
]

Положительное (Delta V) означает ухудшение. Сохраняются median, q10/q90 и доля paired splits с (Delta V>0). Отдельного PASS/FAIL по p-value нет.

Основные feature-level наблюдения:

- `rear_support`: удаление ухудшает (V_{margin}) в 77.3% splits; median (Delta V_{margin}=+0.00276); median (Delta V_{eq}=+0.00340).
- `Absolute_turn_angle_OFT`: (V_{margin}) хуже в 81.8% splits; median (Delta V_{margin}=+0.00386).
- `Latency_to_first_investigation_Piramidka_NOR1`: (V_{margin}) хуже в 68.2% splits; median (Delta V_{margin}=+0.00177).
- `Time_inCenter_OFT`: (V_{margin}) хуже в 59.1% splits; median (Delta V_{margin}=+0.00178).
- `Latency_to_first_investigation_Stakan_zone_NOR2`: (V_{margin}) хуже в 59.1% splits; median (Delta V_{margin}=+0.00064).
- `EnduranceT`: (V_{margin}) хуже в 68.2% splits, но median effect небольшой: (+0.00027).

Некоторые стабильные/candidate признаки почти не показывают уникального ablation effect после переобучения, что указывает на заменяемость другими признаками.

Основные block-level наблюдения:

- B01 OFT — наиболее заметный block ablation: (V_{margin}) хуже в 72.7% splits, median (Delta V_{margin}=+0.00377), median (Delta V_{eq}=+0.00340), median slack increase (+0.0302).
- B02 NOR1 distance/speed часто выбирается как блок, но его полное удаление не ухудшает median validation metrics; это показывает, что высокая selection frequency сама по себе не доказывает уникальный вклад.
- B03, B04, B05 и B06 дают гораздо слабее выраженный paired ablation effect на текущем development-этапе.

В одном split (`seed=1, fold=3`) ablation `Average_speed_OFT` и `EnduranceT` дал очень большие (V_{var})/(V_{eq}). Поэтому mean этих метрик для таких ablations сильно искажён одним split; согласно заранее заданному плану основная интерпретация использует paired median, q10/q90 и (P(\Delta V>0)).

Текущий ablation проверяет вклад weighted features при сохранении all-30 train-only preprocessing/imputation. Автономный reduced preprocessing будет проверяться позднее.

Результаты:

- `stage_e/reference_fold_metrics.csv`;
- `stage_e/feature_ablation.csv`;
- `stage_e/feature_ablation_folds.csv`;
- `stage_e/block_ablation.csv`;
- `stage_e/block_ablation_folds.csv`;
- `stage_e/stage_e_summary.json`.


## Этап F — block-aware ranking, compression и \(S_k\)

После проверки реализации Stage F приведён в точное соответствие с зафиксированным планом: **все признаки вне correlation blocks остаются допустимыми кандидатами**. Категории core/candidate/other влияют на ranking, но не используются как жёсткий pre-filter для singleton-признаков.

Внутри каждого correlation block признаки ранжируются по последовательности

\[
\pi_j
\rightarrow
\text{sign consistency}
\rightarrow
\text{paired ablation}
\rightarrow
\operatorname{median}|\gamma_j|
\rightarrow
\text{canonical order}.
\]

Primary representatives:

- B01: OFT_distance;
- B02: Average_speed_NOR1;
- B03: Average_speed_NOR2;
- B04: Learning_T1max;
- B05: Learning_T2mean;
- B06: Learning_T3sum.

Within-block one-SE compression на 22 development splits оставила:

- B01: OFT_distance, Average_speed_OFT, Absolute_turn_angle_OFT, Total_time_mobile_OFT;
- B02: Average_speed_NOR1, Total_distance_travelled_NOR1;
- B03: только Average_speed_NOR2;
- B04: только Learning_T1max;
- B05: только Learning_T2mean;
- B06: только Learning_T3sum.

После compression development pool содержит 23 признака. Первые 15, используемые для \(S_3,\ldots,S_{15}\):

1. OFT_distance
2. Time_inCenter_OFT
3. Latency_to_first_investigation_Stakan_zone_NOR2
4. Latency_to_first_investigation_Piramidka_NOR1
5. Average_speed_NOR1
6. rear_support
7. Time_investigating_Stakan_zone_NOR2
8. EnduranceT
9. Average_speed_OFT
10. Learning_T3sum
11. Time_investigating_Piramidka_NOR1
12. Absolute_turn_angle_OFT
13. Learning_T1max
14. Time_investigating_Piramidka_zone_NOR2
15. Latency_to_first_investigation_Stakan_NOR1

Для каждого \(S_k\) выполнен новый reduced fit с автономным preprocessing:

- statistical imputer использует только weighted features текущего \(S_k\) + week_16 + week_24;
- group не используется;
- остальные MODEL_FEATURES не используются как statistical predictors;
- после фиксации subset constrained QP переоценивает веса с \(\lambda_1=0\), \(\lambda_2=0.1\), \(\beta=0.1\), \(C=0.1\), \(\rho=0.1\);
- веса full-модели не переносятся.

Все 13 subset sizes × 22 splits рассчитаны без solver/preprocessing failures.

На split seed=1, fold=3, начиная с \(S_5\), после включения Average_speed_NOR1 сохраняется выраженная out-of-sample нестабильность. Для \(S_5\):

- V_pos=0.06;
- minimum validation eNRI = -1476.17;
- V_eq=184.86;
- V_var=33472.02.

Для \(S_3\) и \(S_4\) на этом split такого эффекта нет. Это validation instability, а не solver failure.

Результаты:

- stage_f/within_block_ranking.csv;
- stage_f/block_compression.csv;
- stage_f/block_aware_ranking.csv;
- stage_f/candidate_sets.csv;
- stage_f/subset_cv.csv;
- stage_f/subset_cv_folds.csv;
- stage_f/stage_f_summary.json.

## Этап G — выбор минимального достаточного \(k\)

К \(S_3,\ldots,S_{15}\) применено заранее зафиксированное последовательное one-SE правило:

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

На каждом шаге сохраняются модели с

\[
\operatorname{mean}(V)
\le
\operatorname{best\ mean}(V)+SE(\operatorname{best}),
\]

где

\[
SE=\frac{SD}{\sqrt{22}}.
\]

Это эвристическая мера стабильности, а не классическая independent-sample inferential SE, поскольку development splits перекрываются.

После исправления Stage F результат Stage G не изменился:

\[
\boxed{k^*=4}.
\]

Development subset:

1. OFT_distance
2. Time_inCenter_OFT
3. Latency_to_first_investigation_Stakan_zone_NOR2
4. Latency_to_first_investigation_Piramidka_NOR1

Логика:

- по \(V_{pos}\) только \(S_3\) и \(S_4\) имеют нулевую validation positivity violation на всех 22 splits;
- \(S_5,\ldots,S_{15}\) исключаются на первом шаге;
- затем \(S_4\) имеет mean \(V_{sign}=0.3182\) против \(0.3773\) у \(S_3\);
- one-SE threshold для \(S_4\) по \(V_{sign}\) равен \(0.3481\), поэтому \(S_3\) не проходит;
- единственным survivor остаётся \(S_4\).

Development metrics для \(S_4\):

- \(V_{pos}=0\);
- mean \(V_{sign}=0.3182\);
- mean \(V_{margin}=0.09175\);
- mean \(V_{eq}=0.12660\);
- mean \(V_{var}=0.00991\);
- mean \(V_w=0.09978\).

Paired \(S_4-S_3\):

- \(V_{sign}\) улучшается в 59.1% splits, median delta = \(-0.10\);
- \(V_{margin}\) улучшается в 81.8% splits, median delta = \(-0.00896\);
- \(V_{eq}\), \(V_{var}\) и \(V_w\) у \(S_4\) чаще хуже, но имеют меньший приоритет в заранее заданном lexicographic rule.

Это только development selection. Финальный subset определяется после Stage H.

Результаты:

- stage_g/k_selection_trace.csv;
- stage_g/k_selection_status.csv;
- stage_g/selected_subset.csv;
- stage_g/selected_k_fold_metrics.csv;
- stage_g/stage_g_summary.json.

## Этап H — nested validation

Smoke-test полного nested pipeline успешно пройден.

Фиксированная production-конфигурация:

- 30 valid outer mouse-level 80/20 splits;
- outer: minimum \(O_A^{train}=5\), \(O_A^{val}=2\);
- 20 valid inner mouse-level 80/20 splits в каждом outer-train;
- inner: minimum \(O_A^{train}=4\), \(O_A^{val}=2\);
- 100 valid stability resamples внутри каждого outer-train.

Inner-порог \(4/2\) вместо \(5/2\) нужен из-за структуры nested выборки: после outer split для некоторых состояний в outer-train остаётся 6 живых наблюдений, поэтому одновременно выделить 5 в inner-train и 2 в inner-validation математически невозможно. Это правило зафиксировано до production nested результатов.

Внутри каждого outer-train заново выполняется весь selection pipeline. Outer-validation используется только для финальной оценки и не участвует в correlations, выборе \(\lambda_1\), stability selection, ablation, ranking, выборе \(k\) или subset.
