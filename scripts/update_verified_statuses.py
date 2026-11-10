"""Apply the November 2026 stability review to catalog metadata only.

UFV II/III and Unicamp regional have repeated verified uploads since Oct 28.
Campinas remains beta; UFPR's two failing endpoints and UTFPR need observation.
The UFV I closure and other universities' settings are intentionally excluded.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from UFV import Firebase

STABLE = [('ufv-vicosa', 'ru-ii'), ('ufv-vicosa', 'ru-iii'),
          ('lim', 'rli'), ('lim', 'rlii'), ('pir', 'rfop')]
OBSERVATION = [('cwb', 'ru-botanico'), ('cwb', 'ru-politecnico'), ('utf', 'ru-utfpr')]


def main():
    firebase = Firebase(os.environ.get('BASE_URL'), os.environ.get('FIREBASE_KEY'))
    changes = {}
    for city, restaurant in STABLE:
        path = f'menus/{city}/rus/{restaurant}'
        if not firebase.call(path):
            raise RuntimeError(f'Missing catalog entry: {path}')
        # Confirm actual archived meals spanning the observed period before
        # promoting a restaurant. Current absence alone never changes its state.
        for day in ('2026-10-29', '2026-11-03', '2026-11-05'):
            stored = firebase.call(f'archive/menus/{city}/rus/{restaurant}/menus/{day}')
            if not stored or len(stored.get('menu', [])) != 3 or not stored.get('timestamp'):
                raise RuntimeError(f'Unverified menu history: {city}/{restaurant}/{day}')
        changes[f'{path}/status'] = 'online'
        changes[f'{path}/isNew'] = False
    for city, restaurant in OBSERVATION:
        path = f'menus/{city}/rus/{restaurant}'
        if not firebase.call(path):
            raise RuntimeError(f'Missing catalog entry: {path}')
        changes[f'{path}/status'] = 'beta'
    firebase.call('', changes)
    for path, expected in changes.items():
        if firebase.call(path) != expected:
            raise RuntimeError(f'Catalog read-back mismatch: {path}')
        print(f'{path}: {expected} verified')


if __name__ == '__main__':
    main()
