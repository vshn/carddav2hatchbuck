"""
This script tests the script "carddavsync.py"
"""
import unittest
from carddavsync import HatchbuckParser
from carddavsync import HatchbuckArgs


class TestCarddavsync(unittest.TestCase):
    """
    This class ....
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
        CARDDAV_ARGS = HatchbuckParser('abc123')
        # pylint: disable = invalid-name
        self.assertFalse(isinstance(CARDDAV_ARGS, HatchbuckArgs))


if __name__ == '__main__':
    unittest.main()
