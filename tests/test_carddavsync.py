"""
Tests for module "carddavsync"
"""
from carddav2hatchbuck.carddavsync import HatchbuckParser


class HatchbuckArgsMock:  # pylint: disable=too-few-public-methods
    """
    Replacement for argparse command line arguments when used as module.
    """

    verbose = True
    update = True
    noop = True

    hatchbuck = None
    source = None
    dir = None
    file = None

    def __str__(self):
        """Show the content of this class nicely when printed"""
        return str(self.__dict__)


def test_instantion():
    """
    Tests each of two instances, HatchbuckParser and HatchbuckArgs
    """
    args = HatchbuckArgsMock()
    assert isinstance(args, HatchbuckArgsMock)

    parser = HatchbuckParser(args)
    assert isinstance(parser, HatchbuckParser)
