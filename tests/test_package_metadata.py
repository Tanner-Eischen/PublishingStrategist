from importlib.metadata import version

import kdp_strategist


def test_installed_version_matches_setup_metadata():
    assert version("kdp_strategist") == "0.1.0"


def test_package_authorship_is_public():
    assert kdp_strategist.__author__ == "Tanner Eischen"
