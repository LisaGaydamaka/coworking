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
