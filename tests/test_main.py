import unittest
from app import create_app
from unittest import mock
import datetime

from tests.test_util import MockResponse

def mocked_requests_get(*args, **kwargs):
    if args[0] == "https://tle.ivanstanojevic.me/api/tle/25544":
        tmp_response = {"@context":"https:\\/\\/www.w3.org\\/ns\\/hydra\\/context.jsonld","@id":"https:\\/\\/tle.ivanstanojevic.me\\/api\\/tle\\/25544","@type":"Tle","satelliteId":25544,"name":"ISS (ZARYA)","date":"2026-06-07T21:37:51+00:00","line1":"1 25544U 98067A   26158.90128687  .00007994  00000+0  14961-3 0  9995","line2":"2 25544  51.6338 346.0598 0006926 145.2709 214.8733 15.49660544570312"}
        return MockResponse(200, tmp_response)
    elif args[0] == "https://tle.ivanstanojevic.me/api/tle/0":
        tmp_response = {"response":{"message":"Unable to find record with id 0"}}
        return MockResponse(404, tmp_response)

    return MockResponse(404, None)

class MainTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def test_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('A Simple Web Application for Earth-Orbiting Satellites', response.get_data(as_text=True))

    def test_calculate_get(self):
        response = self.client.get('/calculate')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Enter the date and time values to calculate the position of the ISS (Zarya)', response.get_data(as_text=True))

    def test_calculate_post_without_data(self):
        response = self.client.post('/calculate', data={})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Something went wrong. Try again.', response.get_data(as_text=True))

    def test_mocked_requests_get_variants(self):
        response_404 = mocked_requests_get("https://tle.ivanstanojevic.me/api/tle/0")
        response_fallback = mocked_requests_get("https://tle.ivanstanojevic.me/api/tle/12345")
        self.assertEqual(response_404.status_code, 404)
        self.assertIsNotNone(response_404.json())
        self.assertEqual(response_fallback.status_code, 404)
        self.assertIsNone(response_fallback.json())

    @mock.patch('app.main.views.requests.get', return_value=MockResponse(404, {"response": {"message": "Unable to find record"}}))
    def test_calculate_post_api_failure(self, mock_get):
        response = self.client.post('/calculate', data={
            'input_date_time': datetime.datetime(2026, 6, 1, 12, 0)
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Something went wrong. Try again.', response.get_data(as_text=True))

    @mock.patch('app.main.views.parse_satellite', return_value=(1, None, None))
    @mock.patch('app.main.views.requests.get', side_effect=mocked_requests_get)
    def test_calculate_post_satellite_parse_failure(self, mock_get, mock_parse_satellite):
        response = self.client.post('/calculate', data={
            'input_date_time': datetime.datetime(2026, 6, 1, 12, 0)
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Something went wrong. Try again.', response.get_data(as_text=True))
    
    @mock.patch('app.main.views.requests.get', side_effect=mocked_requests_get)
    def test_calculate(self, mock_get):
        response = self.client.post('/calculate', data={
            'input_date_time': datetime.datetime(2026, 6, 1, 12, 0)
        })
        response_text = response.get_data(as_text=True)
        self.assertIn('Satellite/space object position and velocity calculated', response_text)
        self.assertIn('Position (X, Y, Z) in km:', response_text)
        self.assertIn('Velocity (dx, dy, dz) in km/s:', response_text)