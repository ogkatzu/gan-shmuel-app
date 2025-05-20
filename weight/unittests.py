import unittest
import unittest.mock 
from api import weight_api

class TestGanShmuel(unittest.TestCase):

    def test_truck_verge(self):
        service = weight_api()
        service._truck_direction.truck_in = unittest.mock.MagicMock()
        service._truck_direction.truck_out = unittest.mock.MagicMock()
        service._truck_direction.truck_none = unittest.mock.MagicMock()

        service.direction_handler['in']
        service.direction_handler['out']
        service.direction_handler['none']

        service._truck_direction.truck_in.assert_called_once
        service._truck_direction.truck_out.assert_called_once
        service._truck_direction.truck_none.assert_called_once

if __name__ == '__main__':
    unittest.main()
        