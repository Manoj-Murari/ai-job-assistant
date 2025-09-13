import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

# Import the function to be tested
from api_client import run_job_scrape

class TestApiClient(unittest.TestCase):

    @patch('api_client.scrape_jobs')
    def test_run_job_scrape_uses_country_indeed_parameter(self, mock_scrape_jobs):
        """
        Tests that run_job_scrape calls scrape_jobs with the 'country_indeed' parameter.
        This test should fail before the fix and pass after.
        """
        # Mock the return value of scrape_jobs to be an empty DataFrame
        mock_scrape_jobs.return_value = pd.DataFrame()

        search_config = {
            'search_name': 'Test Search',
            'search_term': 'software engineer',
            'country': 'USA',
            'experience_level': 'entry_level',
            'hours_old': 48
        }

        # Run the function
        run_job_scrape(search_config)

        # Assert that scrape_jobs was called
        mock_scrape_jobs.assert_called_once()

        # Get the arguments it was called with
        _, kwargs = mock_scrape_jobs.call_args

        # Assert that 'country_indeed' is in the arguments
        self.assertIn('country_indeed', kwargs)
        self.assertEqual(kwargs['country_indeed'], 'USA')
        self.assertNotIn('country', kwargs)

if __name__ == '__main__':
    unittest.main()
