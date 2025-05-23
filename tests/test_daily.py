import unittest
from unittest.mock import patch, Mock
from datetime import date, timedelta # Added timedelta for date calculations
from dateutil.relativedelta import relativedelta # For accurate month/year differences

# Ensure daily.py is discoverable. If running 'python -m unittest discover tests' from root,
# the root directory is added to sys.path, so 'from daily import ...' should work.
from daily import get_uptime_data, get_github_stats_data, SVG_NAMESPACE # Import SVG_NAMESPACE for consistency if needed

class TestGetUptimeData(unittest.TestCase):
    @patch('daily.date')  # Mocking 'date' as it's imported 'from datetime import date' in daily.py
    def test_calculates_uptime_with_fixed_date(self, mock_date_module):
        # Set a fixed 'today's date for predictable results
        fixed_today = date(2024, 3, 10)
        mock_date_module.today.return_value = fixed_today
        
        # The start_date in daily.py is date(2005, 3, 3)
        start_date = date(2005, 3, 3)
        
        # Calculate expected values
        diff = relativedelta(fixed_today, start_date)
        expected_years = diff.years
        expected_months = diff.months
        expected_days = diff.days
        
        expected_total_days_lived = (fixed_today - start_date).days
        
        assumed_life_expectancy_days = 26783  # From daily.py
        expected_life_percentage_lived = round((expected_total_days_lived / assumed_life_expectancy_days) * 100, 2)
        expected_total_years_lived_rounded = round(expected_total_days_lived / 365, 2)
        
        expected_months_message = 'month' if expected_months == 1 else 'months'
        expected_days_message = 'day' if expected_days == 1 else 'days'

        expected_uptime_value = f"{expected_years} years, {expected_months} {expected_months_message}, {expected_days} {expected_days_message}"
        expected_total_days_value = f"({expected_total_days_lived}d)"
        expected_life_percentage_value = f"({expected_life_percentage_lived}%)"
        expected_years_rounded_value = f"({total_years_lived_rounded}y)"

        # Call the function
        uptime_data = get_uptime_data()

        # Assertions
        self.assertIn("uptime-value", uptime_data)
        self.assertIn("total-days-value", uptime_data)
        self.assertIn("life-percentage-value", uptime_data)
        self.assertIn("years-rounded-value", uptime_data)

        self.assertIsInstance(uptime_data["uptime-value"], str)
        self.assertIsInstance(uptime_data["total-days-value"], str)
        self.assertIsInstance(uptime_data["life-percentage-value"], str)
        self.assertIsInstance(uptime_data["years-rounded-value"], str)

        self.assertEqual(uptime_data["uptime-value"], expected_uptime_value)
        self.assertEqual(uptime_data["total-days-value"], expected_total_days_value)
        self.assertEqual(uptime_data["life-percentage-value"], expected_life_percentage_value)
        self.assertEqual(uptime_data["years-rounded-value"], expected_years_rounded_value)

class TestGetGitHubStatsData(unittest.TestCase):
    @patch('daily.ElementTree.fromstring') # To mock parsing of SVG from Vercel
    @patch('daily.requests.get')
    def test_success_all_apis(self, mock_requests_get, mock_et_fromstring):
        # --- Mock responses ---
        # 1. GitHub User API (api.github.com/users/{username})
        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            'public_repos': 50,
            'followers': 100,
            'repos_url': 'https://api.github.com/users/testuser/repos'
        }
        mock_user_response.raise_for_status = Mock()

        # 2. GitHub Repos API (for stars)
        mock_repos_response = Mock()
        mock_repos_response.status_code = 200
        mock_repos_response.json.return_value = [
            {'stargazers_count': 10},
            {'stargazers_count': 20},
            {'stargazers_count': 5} # Total 35 stars
        ]
        mock_repos_response.raise_for_status = Mock()

        # 3. Vercel API for Commits/Contributions (returns SVG)
        mock_vercel_commits_response = Mock()
        mock_vercel_commits_response.status_code = 200
        mock_vercel_commits_response.content = b"<svg></svg>" # Dummy SVG content
        mock_vercel_commits_response.raise_for_status = Mock()
        
        # Mock for ElementTree.fromstring for Vercel Commits API
        mock_svg_commits_tree = Mock()
        mock_commits_element = Mock()
        mock_commits_element.text = "1.2k"
        mock_contrib_element = Mock()
        mock_contrib_element.text = "250"
        # Configure find to return these elements based on data-testid
        def find_side_effect_commits(*args, **kwargs):
            if 'commits' in args[0]: # Simplified check for data-testid
                return mock_commits_element
            if 'contribs' in args[0]:
                return mock_contrib_element
            return None
        mock_svg_commits_tree.find.side_effect = find_side_effect_commits

        # 4. Vercel API for PRs (returns SVG)
        mock_vercel_prs_response = Mock()
        mock_vercel_prs_response.status_code = 200
        mock_vercel_prs_response.content = b"<svg></svg>" # Dummy SVG content
        mock_vercel_prs_response.raise_for_status = Mock()

        # Mock for ElementTree.fromstring for Vercel PRs API
        mock_svg_prs_tree = Mock()
        mock_prs_merged_element = Mock()
        mock_prs_merged_element.text = "100"
        mock_prs_percentage_element = Mock()
        mock_prs_percentage_element.text = "95%"
        def find_side_effect_prs(*args, **kwargs):
            if 'prs_merged' in args[0] and 'percentage' not in args[0]:
                return mock_prs_merged_element
            if 'prs_merged_percentage' in args[0]:
                return mock_prs_percentage_element
            return None
        mock_svg_prs_tree.find.side_effect = find_side_effect_prs
        
        # --- Configure side effects ---
        mock_requests_get.side_effect = [
            mock_user_response,
            mock_repos_response,
            mock_vercel_commits_response,
            mock_vercel_prs_response
        ]
        mock_et_fromstring.side_effect = [
            mock_svg_commits_tree, # For commits API
            mock_svg_prs_tree      # For PRs API
        ]

        # --- Call the function ---
        github_data = get_github_stats_data("testuser")

        # --- Assertions ---
        self.assertEqual(github_data["repos-value"], "50")
        self.assertEqual(github_data["followers-value"], "100")
        self.assertEqual(github_data["stars-value"], "35") # 10 + 20 + 5
        self.assertEqual(github_data["commits-value"], "1.2k")
        self.assertEqual(github_data["contributed-value"], "250")
        self.assertEqual(github_data["merged-prs-value"], "100 (95%)")
        
    @patch('daily.ElementTree.fromstring')
    @patch('daily.requests.get')
    def test_github_api_user_fails(self, mock_requests_get, mock_et_fromstring):
        # Simulate failure for the first API call (GitHub user API)
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Failed to connect to GitHub user API")

        github_data = get_github_stats_data("testuser")

        self.assertEqual(github_data["repos-value"], "N/A")
        self.assertEqual(github_data["followers-value"], "N/A")
        self.assertEqual(github_data["stars-value"], "N/A")
        # Vercel API calls won't be made if the first one fails and data isn't available for them.
        # However, the function initializes these to "N/A" and attempts calls, so we check for "N/A".
        # The current implementation of get_github_stats_data attempts all Vercel calls even if GitHub user API fails.
        # So, we expect these to be "N/A" as their respective mocks won't be called or will fail.
        # To be precise, if mock_requests_get has only one side_effect (the exception), subsequent calls will also raise it.
        # If we want to test only the first call failing and others potentially succeeding (if logic allowed),
        # we'd need more complex side_effect, e.g., [requests.exceptions.ConnectionError, mock_success_response_for_vercel_commits, ...].
        # For this test, assume the first failure prevents meaningful data for others or they also effectively fail.
        self.assertEqual(github_data["commits-value"], "N/A")
        self.assertEqual(github_data["contributed-value"], "N/A")
        self.assertEqual(github_data["merged-prs-value"], "N/A")

    @patch('daily.ElementTree.fromstring')
    @patch('daily.requests.get')
    def test_vercel_api_commits_fails(self, mock_requests_get, mock_et_fromstring):
        # 1. GitHub User API (success)
        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {'public_repos': 10, 'followers': 5, 'repos_url': 'http://example.com/repos'}
        mock_user_response.raise_for_status = Mock()

        # 2. GitHub Repos API (success)
        mock_repos_response = Mock()
        mock_repos_response.status_code = 200
        mock_repos_response.json.return_value = [{'stargazers_count': 1}]
        mock_repos_response.raise_for_status = Mock()
        
        # 3. Vercel API for Commits/Contributions (failure)
        mock_vercel_commits_response = Mock() # Will be used by side_effect
        mock_vercel_commits_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Vercel Commits API down")
        
        # 4. Vercel API for PRs (success - to show partial success is possible)
        mock_vercel_prs_response = Mock()
        mock_vercel_prs_response.status_code = 200
        mock_vercel_prs_response.content = b"<svg></svg>"
        mock_vercel_prs_response.raise_for_status = Mock()
        mock_svg_prs_tree = Mock() # Mock for ElementTree.fromstring
        mock_prs_merged_element = Mock(); mock_prs_merged_element.text = "5"
        mock_prs_percentage_element = Mock(); mock_prs_percentage_element.text = "50%"
        def find_side_effect_prs(*args, **kwargs):
            if 'prs_merged' in args[0] and 'percentage' not in args[0]: return mock_prs_merged_element
            if 'prs_merged_percentage' in args[0]: return mock_prs_percentage_element
            return None
        mock_svg_prs_tree.find.side_effect = find_side_effect_prs

        mock_requests_get.side_effect = [
            mock_user_response,
            mock_repos_response,
            mock_vercel_commits_response, # This call will use raise_for_status.side_effect
            mock_vercel_prs_response
        ]
        mock_et_fromstring.return_value = mock_svg_prs_tree # Only needed for the successful Vercel PRs call

        github_data = get_github_stats_data("testuser")

        self.assertEqual(github_data["repos-value"], "10")
        self.assertEqual(github_data["followers-value"], "5")
        self.assertEqual(github_data["stars-value"], "1")
        self.assertEqual(github_data["commits-value"], "N/A") # Failed
        self.assertEqual(github_data["contributed-value"], "N/A") # Failed
        self.assertEqual(github_data["merged-prs-value"], "5 (50%)") # Should still work

    @patch('daily.ElementTree.fromstring')
    @patch('daily.requests.get')
    def test_vercel_api_prs_fails(self, mock_requests_get, mock_et_fromstring):
        # 1. GitHub User API (success)
        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {'public_repos': 10, 'followers': 5, 'repos_url': 'http://example.com/repos'}
        mock_user_response.raise_for_status = Mock()

        # 2. GitHub Repos API (success)
        mock_repos_response = Mock()
        mock_repos_response.status_code = 200
        mock_repos_response.json.return_value = [{'stargazers_count': 1}]
        mock_repos_response.raise_for_status = Mock()

        # 3. Vercel API for Commits/Contributions (success)
        mock_vercel_commits_response = Mock()
        mock_vercel_commits_response.status_code = 200
        mock_vercel_commits_response.content = b"<svg></svg>"
        mock_vercel_commits_response.raise_for_status = Mock()
        mock_svg_commits_tree = Mock() # Mock for ElementTree.fromstring
        mock_commits_element = Mock(); mock_commits_element.text = "1k"
        mock_contrib_element = Mock(); mock_contrib_element.text = "200"
        def find_side_effect_commits(*args, **kwargs):
            if 'commits' in args[0]: return mock_commits_element
            if 'contribs' in args[0]: return mock_contrib_element
            return None
        mock_svg_commits_tree.find.side_effect = find_side_effect_commits

        # 4. Vercel API for PRs (failure)
        mock_vercel_prs_response = Mock() # Will be used by side_effect
        mock_vercel_prs_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Vercel PRs API down")

        mock_requests_get.side_effect = [
            mock_user_response,
            mock_repos_response,
            mock_vercel_commits_response,
            mock_vercel_prs_response # This call will use raise_for_status.side_effect
        ]
        mock_et_fromstring.return_value = mock_svg_commits_tree # Only needed for the successful Vercel commits call

        github_data = get_github_stats_data("testuser")

        self.assertEqual(github_data["repos-value"], "10")
        self.assertEqual(github_data["followers-value"], "5")
        self.assertEqual(github_data["stars-value"], "1")
        self.assertEqual(github_data["commits-value"], "1k") 
        self.assertEqual(github_data["contributed-value"], "200")
        self.assertEqual(github_data["merged-prs-value"], "N/A") # Failed

if __name__ == '__main__':
    unittest.main()
