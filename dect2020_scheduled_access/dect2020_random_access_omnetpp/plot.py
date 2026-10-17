import pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = pathlib.Path(__file__).resolve().parent
series = {}
for file in (root / 'results').glob('*.sca'):
    config = file.name.split('-')[0]
    params, metrics = {}, {}
    for line in file.read_text().splitlines():
        cols = line.split()
        if len(cols) >= 3 and cols[0] == 'itervar':
            params[cols[1]] = cols[2].strip('"')
        if len(cols) >= 4 and cols[0] == 'scalar':
            metrics[cols[2]] = float(cols[3])
    if 'interval' not in params:
        continue
    x = int(params['cw'] if config in ('Fig31a','Fig31b') else params['interval'])
    for name, value in metrics.items():
        if name not in ('delay_0','delay_1','paoi_0'):
            continue
        key = (config, name, params['interval'] if config in ('Fig31a','Fig31b') else '')
        series.setdefault(key, []).append((x,value))

for cfg in ('Fig31a', 'Fig31b', 'Fig32', 'Fig33'):
    fig, ax = plt.subplots()
    names = ('delay_0','paoi_0') if cfg=='Fig32' else ('delay_0','delay_1') if cfg=='Fig33' else ('delay_0',)
    for name in names:
        for (config, metric, period), points in series.items():
            if config != cfg or metric != name: continue
            points.sort()
            xx = [x * (2 if cfg.startswith('Fig31') else 1) for x,y in points]
            yy = [y for x,y in points]
            label = f'd={period}' if period else {'delay_0':'Delay (cluster 1)','delay_1':'Delay (cluster 2)','paoi_0':'Peak AoI'}[name]
            ax.plot(xx, yy, label=label)
    ax.set(xlabel='Backoff, symbols' if cfg.startswith('Fig31') else 'Generation interval, symbols', ylabel='Time, symbols')
    ax.grid(); ax.legend()
    fig.savefig(root / 'figures' / f'{cfg}.png', dpi=160, bbox_inches='tight')
    plt.close(fig)
