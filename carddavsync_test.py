from carddavsync import HatchbuckParser
from carddavsync import HatchbuckArgs
import unittest


class TestCarddavsync(unittest.TestCase):

    def setUp(self):
        pass

    def test_instantion(self):
        carddavParser = HatchbuckParser('abc123')
        self.assertTrue(isinstance(carddavParser, HatchbuckParser))
        carddavArgs = HatchbuckParser('abc123')
        self.assertFalse(isinstance(carddavArgs, HatchbuckArgs))


if __name__ == '__main__':
    unittest.main()
