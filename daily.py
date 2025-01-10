from datetime import date
from dateutil.relativedelta import relativedelta
import requests
from xml.etree import ElementTree


def update_svg(file_paths, replacements):
    """Updates SVG files with given replacements."""
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            svg_content = file.readlines()

        for key, value in replacements.items():
            for i, line in enumerate(svg_content):
                if key in line:
                    svg_content[i] = value
                    break

        with open(file_path, 'w') as file:
            file.writelines(svg_content)


def update_uptime():
    start_date = date(2005, 3, 3)
    current_date = date.today()
    diff = relativedelta(current_date, start_date)
    total_days = (current_date - start_date).days
    life_expectancy_days = 26783

    replacements = {
        '<tspan x="370" y="90" class="keyColor">Uptime</tspan>':
            f'<tspan x="370" y="90" class="keyColor">Uptime</tspan>: <tspan class="valueColor">{diff.years} years, {diff.months} {"month" if diff.months == 1 else "months"}, {diff.days} {"day" if diff.days == 1 else "days"}</tspan>\n',
        '<tspan x="680" y= "90" class="valueColor">':
            f'<tspan x="680" y= "90" class="valueColor">({total_days}d)</tspan>\n',
        '<tspan x="760" y= "90" class="valueColor">':
            f'<tspan x="760" y= "90" class="valueColor">({round((total_days / life_expectancy_days) * 100, 2)}%)</tspan>\n',
        '<tspan x="840" y= "90" class="valueColor">':
            f'<tspan x="840" y= "90" class="valueColor">({round(total_days / 365, 2)}y)</tspan>\n'
    }
    update_svg(['dark_mode.svg', 'light_mode.svg'], replacements)


def fetch_github_stats():
    """Fetches GitHub stats for the user."""
    user_url = 'https://api.github.com/users/pyoneerc'
    stats_url = 'https://github-readme-stats.vercel.app/api?username=pyoneerc'

    user_data = requests.get(user_url).json()
    repos_data = requests.get(user_data['repos_url']).json()
    readme_data = ElementTree.fromstring(requests.get(stats_url).content)

    stars = sum(repo['stargazers_count'] for repo in repos_data)
    commits = readme_data.find('.//{http://www.w3.org/2000/svg}text[@data-testid="commits"]').text
    contribs = readme_data.find('.//{http://www.w3.org/2000/svg}text[@data-testid="contribs"]').text
    prs_merged = readme_data.find('.//{http://www.w3.org/2000/svg}text[@data-testid="prs_merged"]').text
    prs_merged_percentage = readme_data.find(
        './/{http://www.w3.org/2000/svg}text[@data-testid="prs_merged_percentage"]').text[:2] + '%'

    return {
        'repos': user_data['public_repos'],
        'stars': stars,
        'followers': user_data['followers'],
        'contributed': contribs,
        'commits': commits,
        'prs_merged': f"{prs_merged} ({prs_merged_percentage})"
    }


def update_github_stats():
    stats = fetch_github_stats()
    replacements = {
        '<tspan x="370" y="490" class="keyColor">Repos</tspan>':
            f'<tspan x="370" y="490" class="keyColor">Repos</tspan>: <tspan class="valueColor">{stats["repos"]}</tspan>\n',
        '<tspan x="520" y="510" class="keyColor">|   Stars</tspan>':
            f'<tspan x="520" y="510" class="keyColor">|   Stars</tspan>: <tspan class="valueColor">{stats["stars"]}</tspan>\n',
        '<tspan x="370" y="510" class="keyColor">Followers</tspan>':
            f'<tspan x="370" y="510" class="keyColor">Followers</tspan>: <tspan class="valueColor">{stats["followers"]}</tspan>\n',
        '<tspan x="480" y="490" class="keyColor">Contributed</tspan>':
            f'<tspan x="480" y="490" class="keyColor">Contributed</tspan>: <tspan class="valueColor">{stats["contributed"]}</tspan>\n',
        '<tspan x="660" y="510" class="keyColor">|   Commits</tspan>':
            f'<tspan x="660" y="510" class="keyColor">|   Commits</tspan>: <tspan class="valueColor">{stats["commits"]}</tspan>\n',
        '<tspan x="660" y="490" class="keyColor">|   Merged PRs</tspan>':
            f'<tspan x="660" y="490" class="keyColor">|   Merged PRs</tspan>: <tspan class="valueColor">{stats["prs_merged"]}</tspan>\n'
    }
    update_svg(['dark_mode.svg', 'light_mode.svg'], replacements)


def main():
    update_uptime()
    update_github_stats()


if __name__ == '__main__':
    main()
