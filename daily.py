"""
Updates dynamic data within SVG files (dark_mode.svg, light_mode.svg)
for display on a GitHub profile.

This script fetches real-time data such as personal uptime (age) and
GitHub statistics (repositories, stars, followers, commits, contributions, PRs)
and updates the corresponding text elements in the SVG files.
"""
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
import requests
from xml.etree import ElementTree
from typing import Dict, List, Optional, Any # Added Any for flexible JSON dicts

# Configure basic logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Global Constants ---
SVG_NAMESPACE: Dict[str, str] = {'svg': 'http://www.w3.org/2000/svg'}
FILE_PATHS: List[str] = ['dark_mode.svg', 'light_mode.svg']
ElementTree.register_namespace('', SVG_NAMESPACE['svg']) # Register namespace globally

# --- Helper Function for SVG Manipulation ---
def update_svg_elements(file_path: str, updates: Dict[str, str]) -> bool:
    """Updates text content of specified elements in an SVG file.

    Uses ElementTree to parse an SVG file, find elements by their 'id'
    attribute, and update their text content with provided values.

    Args:
        file_path: The path to the SVG file to be updated.
        updates: A dictionary where keys are the 'id' attributes of the
                 SVG elements to update, and values are the new text
                 content for those elements.

    Returns:
        True if all specified elements were found and the SVG file was
        successfully parsed and written. False if any element was not
        found, or if a file I/O or XML parsing error occurred.
    """
    try:
        tree: ElementTree.ElementTree = ElementTree.parse(file_path)
        root: ElementTree.Element = tree.getroot()
        all_elements_found: bool = True

        for element_id, new_value in updates.items():
            # XPath to find any element with the given id
            element: Optional[ElementTree.Element] = root.find(f".//*[@id='{element_id}']", SVG_NAMESPACE)
            if element is not None:
                element.text = str(new_value)
            else:
                logging.error(f"Element with ID '{element_id}' not found in {file_path}")
                all_elements_found = False
        
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        # Returns true only if all elements were found and file written successfully
        return all_elements_found
    except (IOError, FileNotFoundError) as e:
        logging.error(f"File operation error for {file_path}: {e}")
        return False
    except ElementTree.ParseError as e:
        logging.error(f"XML parsing error for {file_path}: {e}")
        return False
    except Exception as e: # General catch for other unexpected errors
        logging.error(f"An unexpected error occurred while processing {file_path} in update_svg_elements: {e}")
        return False

# --- Data Fetching/Calculation Functions ---
def get_uptime_data() -> Dict[str, str]:
    """Calculates personal uptime (age) statistics.

    Computes the time elapsed since a fixed start date (birth date) to the
    current date. This includes years, months, days, total days lived,
    a conceptual percentage of life lived based on an assumed expectancy,
    and total years lived rounded to two decimal places.

    Returns:
        A dictionary where keys are SVG element IDs and values are the
        formatted uptime strings:
        - "uptime-value": Years, months, days lived.
        - "total-days-value": Total days lived.
        - "life-percentage-value": Percentage of assumed life expectancy lived.
        - "years-rounded-value": Total years lived, rounded.
    """
    start_date: date = date(2005, 3, 3)  # My birth date
    current_date: date = date.today()

    time_difference: relativedelta = relativedelta(current_date, start_date)
    years: int = time_difference.years
    months: int = time_difference.months
    days: int = time_difference.days
    
    total_days_lived: int = (current_date - start_date).days
    
    # Conceptual value for the profile SVG (e.g., around 73 years = 26783 days)
    assumed_life_expectancy_days: int = 26783 
    life_percentage_lived: float = round((total_days_lived / assumed_life_expectancy_days) * 100, 2)
    total_years_lived_rounded: float = round(total_days_lived / 365, 2)
    
    months_message: str = 'month' if months == 1 else 'months'
    days_message: str = 'day' if days == 1 else 'days'

    uptime_values_dict: Dict[str, str] = {
        "uptime-value": f"{years} years, {months} {months_message}, {days} {days_message}",
        "total-days-value": f"({total_days_lived}d)",
        "life-percentage-value": f"({life_percentage_lived}%)",
        "years-rounded-value": f"({total_years_lived_rounded}y)"
    }
    return uptime_values_dict

def get_github_stats_data(username: str) -> Dict[str, str]:
    """Fetches GitHub statistics for a given username.

    Retrieves data from the GitHub API (public repos, followers, stars) and
    from the github-readme-stats.vercel.app API (commits, contributions, PRs).
    Handles potential errors during API requests and data parsing.

    Args:
        username: The GitHub username for which to fetch stats.

    Returns:
        A dictionary where keys are SVG element IDs and values are the
        fetched GitHub statistics as strings. Defaults to "N/A" for
        any statistic that cannot be retrieved or processed.
    """
    # Initialize stats with default "N/A" values
    public_repos: Any = "N/A" # Can be int or str "N/A"
    followers: Any = "N/A"  # Can be int or str "N/A"
    stars: Any = "N/A"      # Can be int or str "N/A"
    commits_text: str = "N/A"
    contributed_text: str = "N/A"
    prs_merged_text: str = "N/A"
    prs_merged_percentage_text: str = "N/A"
    
    # --- Fetch data from GitHub API ---
    user_api_url: str = f'https://api.github.com/users/{username}'
    try:
        response: requests.Response = requests.get(user_api_url)
        response.raise_for_status() # Check for HTTP errors
        user_data: Dict[str, Any] = response.json()
        public_repos = user_data.get('public_repos', "N/A")
        followers = user_data.get('followers', "N/A")
        
        repos_url: Optional[str] = user_data.get('repos_url')
        if repos_url:
            repos_response: requests.Response = requests.get(repos_url)
            repos_response.raise_for_status()
            repos_data: List[Dict[str, Any]] = repos_response.json()
            stars = sum(repo.get('stargazers_count', 0) for repo in repos_data)
        else:
            logging.error(f"Repos URL not found for user {username}")
            stars = "N/A"
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching GitHub user/repos data for {username}: {e}")
    except ValueError as e: # JSONDecodeError inherits from ValueError
        logging.error(f"Error decoding JSON for GitHub user/repos data for {username}: {e}")

    # --- Fetch commit and contribution stats from Vercel API ---
    stats_api_url_commits: str = f'https://github-readme-stats.vercel.app/api?username={username}&include_all_commits=true'
    try:
        response_commits: requests.Response = requests.get(stats_api_url_commits)
        response_commits.raise_for_status()
        # Response is an SVG (XML format)
        svg_content_commits: ElementTree.Element = ElementTree.fromstring(response_commits.content)
        commits_xml_element: Optional[ElementTree.Element] = svg_content_commits.find('.//svg:text[@data-testid="commits"]', SVG_NAMESPACE)
        contributed_xml_element: Optional[ElementTree.Element] = svg_content_commits.find('.//svg:text[@data-testid="contribs"]', SVG_NAMESPACE)
        if commits_xml_element is not None and commits_xml_element.text is not None:
            commits_text = commits_xml_element.text
        if contributed_xml_element is not None and contributed_xml_element.text is not None:
            contributed_text = contributed_xml_element.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching commit/contribution stats for {username} from Vercel API: {e}")
    except ElementTree.ParseError as e:
        logging.error(f"Error parsing XML for commit/contribution stats for {username}: {e}")
    except ValueError as e: # If Vercel API returns JSON by mistake
        logging.error(f"Error decoding potential JSON for commit/contribution stats for {username}: {e}")

    # --- Fetch PR stats from Vercel API ---
    stats_api_url_prs: str = f'https://github-readme-stats.vercel.app/api?username={username}&show=prs_merged,prs_merged_percentage'
    try:
        response_prs: requests.Response = requests.get(stats_api_url_prs)
        response_prs.raise_for_status()
        svg_content_prs: ElementTree.Element = ElementTree.fromstring(response_prs.content)
        prs_merged_xml_element: Optional[ElementTree.Element] = svg_content_prs.find('.//svg:text[@data-testid="prs_merged"]', SVG_NAMESPACE)
        prs_merged_percentage_xml_element: Optional[ElementTree.Element] = svg_content_prs.find('.//svg:text[@data-testid="prs_merged_percentage"]', SVG_NAMESPACE)
        
        if prs_merged_xml_element is not None and prs_merged_xml_element.text is not None:
            prs_merged_text = prs_merged_xml_element.text
        if prs_merged_percentage_xml_element is not None and prs_merged_percentage_xml_element.text is not None:
            raw_percentage_text: str = prs_merged_percentage_xml_element.text
            if raw_percentage_text and raw_percentage_text != "N/A": # Check if not empty or "N/A"
                prs_merged_percentage_text = "".join(filter(str.isdigit, raw_percentage_text)) + "%"
            else:
                prs_merged_percentage_text = "N/A" # Default if raw is "N/A" or empty
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching PR stats for {username} from Vercel API: {e}")
    except ElementTree.ParseError as e:
        logging.error(f"Error parsing XML for PR stats for {username}: {e}")
    except ValueError as e: # If Vercel API returns JSON by mistake
        logging.error(f"Error decoding potential JSON for PR stats for {username}: {e}")

    # Prepare final dictionary for SVG update
    github_stats_updates: Dict[str, str] = {
        "repos-value": str(public_repos), # Ensure string conversion
        "stars-value": str(stars),         # Ensure string conversion
        "followers-value": str(followers), # Ensure string conversion
        "contributed-value": contributed_text,
        "commits-value": commits_text,
    }
    if prs_merged_text != "N/A" and prs_merged_percentage_text != "N/A":
        github_stats_updates["merged-prs-value"] = f'{prs_merged_text} ({prs_merged_percentage_text})'
    else:
        github_stats_updates["merged-prs-value"] = "N/A"
    
    return github_stats_updates

# --- Main SVG Updating Functions ---
def update_uptime() -> None:
    """Orchestrates fetching uptime data and updating SVG files.

    Calls `get_uptime_data()` to retrieve calculated uptime statistics,
    then iterates through predefined SVG file paths and calls
    `update_svg_elements()` to apply these updates to each file.
    Logs an error if SVG update fails for any file.
    """
    uptime_data: Dict[str, str] = get_uptime_data()
    for file_path in FILE_PATHS:
        if not update_svg_elements(file_path, uptime_data):
            logging.error(f"Failed to update uptime elements in {file_path}.")

def update_github_stats() -> None:
    """Orchestrates fetching GitHub stats and updating SVG files.

    Calls `get_github_stats_data()` for a predefined GitHub username
    to retrieve various GitHub statistics. Then, it iterates through
    predefined SVG file paths and calls `update_svg_elements()`
    to apply these updates to each file. Logs an error if SVG
    update fails for any file.
    """
    github_user: str = "pyoneerc" 
    github_stats_data: Dict[str, str] = get_github_stats_data(github_user)
    for file_path in FILE_PATHS:
        if not update_svg_elements(file_path, github_stats_data):
            logging.error(f"Failed to update GitHub stats elements for {github_user} in {file_path}.")

def main() -> None:
    """Main function to orchestrate all updates.
    
    Calls functions to update both uptime and GitHub statistics in the SVG files.
    """
    update_uptime()
    update_github_stats()


if __name__ == '__main__':
    main()
