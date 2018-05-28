import unittest


class TestSync(unittest.TestCase):

    def setUp(self):
        pass
    def test_sync(self):
        sync = carddavCall('abc123')
        self.assertTrue(isinstance(sync, carddavCall))


if __name__ == '__main__':
    unittest.main()
