"""Standardized stimulus construction for the visuospatial prototype.

Only positions are randomized; a preset and card-count always choose the same
stimuli. These are project presets, not clinically normed equivalent forms.
"""
import secrets

ALLOWED_SHAPES = ('arrow', 'triangle', 'l_shape', 'circle', 'square', 'plus', 'star', 'diamond')
COLOR = {'arrow': '#2563eb', 'triangle': '#d97706', 'l_shape': '#7c3aed',
         'circle': '#4f46e5', 'square': '#059669', 'plus': '#be123c',
         'star': '#db2777', 'diamond': '#0284c7'}

PRESETS = {
    'Standard': {'card_counts': [6, 8, 10], 'study_time_ms': [5000, 4000, 3000]},
    'Advanced': {'card_counts': [6, 8, 12], 'study_time_ms': [4000, 3000, 2500]},
}


def parse_configuration(data):
    """Reject invalid doctor controls rather than silently dropping settings."""
    difficulty = data.get('difficulty', 'Standard')
    if difficulty not in PRESETS:
        raise ValueError('Difficulty must be Standard or Advanced.')
    defaults = PRESETS[difficulty]
    counts = data.get('card_counts', defaults['card_counts'])
    if not isinstance(counts, list) or len(counts) != 3 or any(type(n) is not int or n not in (4, 6, 8, 10, 12) for n in counts):
        raise ValueError('card_counts must contain three even card counts between 4 and 12.')
    if counts != sorted(counts):
        raise ValueError('Card counts must progress from easier to harder rounds.')

    durations = data.get('study_time_ms', defaults['study_time_ms'])
    if type(durations) is int:
        durations = [durations] * 3
    if not isinstance(durations, list) or len(durations) != 3 or any(type(n) is not int or n < 1000 or n > 30000 for n in durations):
        raise ValueError('study_time_ms must be 1000 to 30000 milliseconds for each scored round.')

    shapes = data.get('shape_types', list(ALLOWED_SHAPES))
    if not isinstance(shapes, list) or not shapes or any(not isinstance(s, str) or s not in ALLOWED_SHAPES for s in shapes):
        raise ValueError('shape_types must be a nonempty list of supported geometric shapes.')
    if len(set(shapes)) != len(shapes):
        raise ValueError('shape_types may not contain duplicates.')
    return {
        'difficulty': difficulty,
        'card_counts': counts,
        'study_time_ms': durations,
        'shape_types': shapes,
        'standardized': ('card_counts' not in data and 'study_time_ms' not in data and 'shape_types' not in data),
    }


def create_deck(pair_count, mode='shapes', shape_types=None):
    """Distinct pairs match by *shape, orientation and reflection*.

    Non-rotationally symmetric symbols only are used with orientation variants.
    Reflection is only used for an L figure, whose reflection is observable.
    """
    allowed = set(shape_types or ALLOWED_SHAPES)
    if type(pair_count) is not int or pair_count < 2 or pair_count > 6:
        raise ValueError('Each round requires between 2 and 6 pairs.')
    base = [('circle', 'none', False), ('triangle', 'up', False),
            ('square', 'none', False), ('plus', 'none', False),
            ('star', 'up', False), ('diamond', 'none', False),
            ('arrow', 'up', False), ('l_shape', 'up', False)]
    oriented = [('arrow', 'up', False), ('triangle', 'up', False),
                ('arrow', 'right', False), ('l_shape', 'up', False),
                ('triangle', 'right', False), ('l_shape', 'right', False),
                ('arrow', 'down', False), ('triangle', 'down', False),
                ('l_shape', 'down', False), ('arrow', 'left', False),
                ('l_shape', 'left', False), ('triangle', 'left', False)]
    complex_cards = [('l_shape', 'up', False), ('l_shape', 'up', True),
                     ('arrow', 'up', False), ('arrow', 'right', False),
                     ('l_shape', 'right', False), ('l_shape', 'right', True),
                     ('triangle', 'up', False), ('triangle', 'right', False),
                     ('arrow', 'down', False), ('l_shape', 'down', False),
                     ('l_shape', 'down', True), ('triangle', 'down', False)]
    if mode == 'practice':
        candidates = base + oriented
    elif mode == 'direction':
        candidates = oriented + base
    elif mode == 'complex':
        candidates = complex_cards + oriented + base
    else:
        candidates = base + oriented + complex_cards
    # Permit single-type custom decks while never treating visually identical
    # rotations/reflections as different correct pairs.
    candidates += [(shape, direction, False) for shape in ('arrow', 'triangle', 'l_shape')
                   for direction in ('up', 'right', 'down', 'left')]
    candidates += [('l_shape', d, True) for d in ('up', 'right', 'down', 'left')]
    chosen = []
    seen = set()
    for shape, direction, mirrored in candidates:
        if shape not in allowed:
            continue
        # The same geometry must have the same key, regardless of phase.
        key = (shape, direction, mirrored)
        if key in seen:
            continue
        seen.add(key)
        chosen.append(key)
        if len(chosen) == pair_count:
            break
    if len(chosen) < pair_count:
        raise ValueError('Selected shape types do not provide enough distinct pairs for this card count.')
    cards = []
    for shape, direction, mirrored in chosen:
        spec = {'shape': shape, 'direction': direction, 'mirrored': mirrored,
                'color': COLOR[shape],
                'match_key': f'{shape}:{direction}:{int(mirrored)}'}
        cards.extend([dict(spec), dict(spec)])
    secrets.SystemRandom().shuffle(cards)
    for index, card in enumerate(cards):
        card['id'] = index
    return cards


def round_specs(config):
    """One practice + three scored rounds, including for Standard."""
    yield {'round_number': 1, 'is_practice': True, 'mode': 'practice_round',
           'pair_count': 2, 'card_count': 4, 'study_time_ms': 5000,
           'deck_layout': create_deck(2, 'practice')}
    for i, (count, duration, mode) in enumerate(zip(config['card_counts'], config['study_time_ms'],
                                                    ('shapes', 'direction', 'complex')), start=2):
        yield {'round_number': i, 'is_practice': False, 'mode': mode,
               'pair_count': count // 2, 'card_count': count, 'study_time_ms': duration,
               'deck_layout': create_deck(count // 2, mode, config['shape_types'])}
