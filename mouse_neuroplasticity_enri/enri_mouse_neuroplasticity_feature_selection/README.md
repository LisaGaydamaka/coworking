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
