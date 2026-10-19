"""Auditable training-only selection for Restart 4.0."""
import os
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ.setdefault(key, '1')
import sys, csv, gzip, json, hashlib, math, warnings
from pathlib import Path
import numpy as np
from scipy.special import expit
from sklearn.metrics import average_precision_score
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
PREVIOUS = PROJECT / 'restart_3_0'
sys.path.append(str(PREVIOUS / 'scripts'))
import phase4_common as old
import phase5_common as previous
read, write, save, sha = old.read, old.write, old.save, old.sha
CITIES, SEED = old.CITIES, old.SEED
MODELS = ['M0', 'M1', 'M2']
SEEDS = list(range(20261001, 20261021))
PARAMS = {'M0': {}, 'M1': {'C': 1.0}, 'M2': {'max_depth': 2, 'reg_lambda': 10}}

def gzwrite(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    with gzip.open(path, 'wt', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def gzread(path):
    with gzip.open(path, 'rt', newline='') as f: return list(csv.DictReader(f))

def freeze(path, value):
    if path.exists():
        assert json.loads(path.read_text()) == value, f'Frozen input changed: {path}'
    else: save(path, value)

def load():
    Xold, y, meta, oldnames, distance = previous.load()
    schema = json.loads((ROOT/'results/phase3/data/feature_schema.json').read_text())
    names = schema['predictors']
    rows = {r['row_id']: r for r in read(ROOT/'results/phase3/data/features.csv')}
    assert set(rows) == {r['site_id'] for r in meta}
    X = np.array([[old.safe(rows[r['site_id']][n]) for n in names] for r in meta])
    assert np.allclose(X[:, 0], Xold[:, 0], equal_nan=True)
    return X, y, meta, names, distance

def purge(candidates, test, distance):
    return previous.purge(candidates, test, distance)

def batched_candidates(Xtrain, ytrain, Xval):
    """All background+one-feature ridge logistic fits; intercept unpenalized.

    StandardScaler population variance and SimpleImputer median semantics.
    Candidate 0 has a zero dummy feature. Newton steps are bounded for stability.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        med = np.nanmedian(Xtrain, axis=0)
    med = np.nan_to_num(med, nan=0.)
    a = np.where(np.isnan(Xtrain), med, Xtrain)
    b = np.where(np.isnan(Xval), med, Xval)
    mean, scale = a.mean(axis=0), a.std(axis=0)
    scale[scale < 1e-12] = 1.
    a, b = (a-mean)/scale, (b-mean)/scale
    k = Xtrain.shape[1]
    A = np.ones((len(a), k, 3)); B = np.ones((len(b), k, 3))
    A[:, :, 1] = a[:, 0, None]; B[:, :, 1] = b[:, 0, None]
    A[:, :, 2] = a; B[:, :, 2] = b
    A[:, 0, 2] = 0.; B[:, 0, 2] = 0.
    theta = np.zeros((k, 3))
    theta[:, 0] = np.log((ytrain.sum()+.5)/(len(ytrain)-ytrain.sum()+.5))
    ridge = np.diag([0., 1., 1.])
    for iteration in range(100):
        p = expit(np.einsum('nkj,kj->nk', A, theta))
        gradient = np.einsum('nkj,nk->kj', A, p-ytrain[:, None]) + theta @ ridge
        if np.max(np.abs(gradient)) < 1e-7: break
        hessian = np.einsum('nki,nkj,nk->kij', A, A, p*(1-p)) + ridge
        hessian[:, 0, 0] += 1e-10
        step = np.linalg.solve(hessian, gradient[..., None])[..., 0]
        step /= np.maximum(1., np.max(np.abs(step), axis=1)/2.)[:, None]
        theta -= step
    else: raise RuntimeError('Batched selection solver did not converge')
    return expit(np.einsum('nkj,kj->nk', B, theta))

def select(X, y, train, meta, distance):
    folds = np.array([int(r['spatial_fold']) % 3 for r in meta])
    scores = []; splits = []
    for f in sorted(set(folds[train])):
        val = train[folds[train] == f]
        fit = purge(train[folds[train] != f], val, distance)
        valid = len(fit) >= 10 and len(set(y[fit])) == 2 and len(set(y[val])) == 2
        splits.append({'fold': int(f), 'train': fit.tolist(), 'validation': val.tolist(), 'valid': valid})
        if not valid: continue
        ps = batched_candidates(X[fit], y[fit], X[val])
        scores.append([float(average_precision_score(y[val], ps[:, j])) for j in range(X.shape[1])])
    means = np.mean(scores, axis=0) if len(scores) >= 2 else np.full(X.shape[1], np.nan)
    winner = 0
    if len(scores) >= 2:
        for j in range(1, len(means)):
            if means[j] > means[winner]+1e-12: winner = j
    return winner, means, scores, splits

def fit_bundle(model, columns, X, y, train, names):
    if len(set(y[train])) < 2:
        return {'kind': 'constant', 'probability': float(y[train].mean()),
                'columns': columns, 'predictors': [names[j] for j in columns]}, []
    e = old.estimator(model, PARAMS[model])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always'); e.fit(X[np.ix_(train, columns)], y[train])
    return {'kind': 'pipeline', 'pipeline': e, 'columns': columns,
            'predictors': [names[j] for j in columns]}, [str(w.message) for w in caught]

def predict(bundle, X):
    if bundle['kind'] == 'constant': return np.full(len(X), bundle['probability'])
    return bundle['pipeline'].predict_proba(X[:, bundle['columns']])[:, 1]
