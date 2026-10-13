from app.services.geo import Lieu, distance_m, evaluer_zone

SITE = Lieu(48.95, 2.38, 100)


def test_distance():
    # 0,001° de latitude ≈ 111 m
    assert 110 < distance_m(48.95, 2.38, 48.951, 2.38) < 112


def test_dans_zone():
    assert evaluer_zone(48.9505, 2.38, 15, [SITE], 150) == "dans_zone"


def test_hors_zone():
    assert evaluer_zone(48.96, 2.38, 15, [SITE], 150) == "hors_zone"


def test_marge_de_precision_profite_au_salarie():
    # ~111 m du site, rayon 100 m, précision 20 m : dans la zone.
    assert evaluer_zone(48.951, 2.38, 20, [SITE], 150) == "dans_zone"


def test_imprecis_indetermine():
    assert evaluer_zone(48.9505, 2.38, 800, [SITE], 150) == "indetermine"


def test_imprecis_mais_clairement_hors_zone():
    # ~11 km du site avec ± 800 m : hors zone malgré l'imprécision.
    assert evaluer_zone(49.05, 2.38, 800, [SITE], 150) == "hors_zone"


def test_position_absente():
    assert evaluer_zone(None, None, None, [SITE], 150) == "indisponible"


def test_aucun_lieu():
    assert evaluer_zone(48.95, 2.38, 10, [], 150) == "indetermine"


def test_plusieurs_lieux():
    domicile = Lieu(48.80, 2.20, 100)
    assert evaluer_zone(48.8001, 2.2001, 10, [SITE, domicile], 150) == "dans_zone"
