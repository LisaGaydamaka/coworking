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
