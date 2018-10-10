"""
Tests the module "carddavsync"
"""
import unittest
from carddav2hatchbuck.carddavsync import HatchbuckParser
from carddav2hatchbuck.carddavsync import HatchbuckArgs


class TestCarddavsync(unittest.TestCase):
    """
    Tests each of two instances, HatchbuckParser and HatchbuckArgs
    """

    def setUp(self):
        pass

    def test_instantion(self):
        """
        this ...
        :return:
        """
        CARDDAV_PARSER = HatchbuckParser('abc123')
        # pylint: disable = invalid-name
        self.assertTrue(isinstance(CARDDAV_PARSER, HatchbuckParser))
        CARDDAV_ARGS = HatchbuckArgs()
        # pylint: disable = invalid-name
        self.assertTrue(isinstance(CARDDAV_ARGS, HatchbuckArgs))


if __name__ == '__main__':
    unittest.main()
