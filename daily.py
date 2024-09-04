from datetime import date
from dateutil.relativedelta import relativedelta
import requests
from xml.etree import ElementTree


def update_uptime():
    file_paths = ['dark_mode.svg', 'light_mode.svg']
    start_date = date(2005, 3, 3)
    current_date = date.today()

    difference = relativedelta(current_date, start_date)
    years = difference.years
    months = difference.months
    days = difference.days

    total_days = (current_date - start_date).days

    life_expectancy_days = 26783
    life_percentage = round((total_days / life_expectancy_days) * 100, 2)
    years_rounded = round(total_days / 365, 2)


    for file_path in file_paths:
        with open(file_path, 'r') as file:
            svg_content = file.readlines()

        months_message = f'mes' if months == 1 else 'meses'
        days_message = f'día' if days == 1 else 'días'

        for i, line in enumerate(svg_content):
            if '<tspan x="370" y="90" class="keyColor">Uptime</tspan>' in line:
                svg_content[i] = f'<tspan x="370" y="90" class="keyColor">Uptime</tspan>: <tspan class="valueColor">{years} años, {months} {months_message}, {days} {days_message}</tspan>\n'
                break

        for i, line in enumerate(svg_content):
            if '<tspan x="680" y= "90" class="valueColor">' in line:
                svg_content[i] = f'<tspan x="680" y= "90" class="valueColor">({total_days}d)</tspan>\n'
                break

        for i, line in enumerate(svg_content):
            if '<tspan x="760" y= "90" class="valueColor">' in line:
                svg_content[i] = f'<tspan x="760" y= "90" class="valueColor">({life_percentage}%)</tspan>\n'
                break

        for i, line in enumerate(svg_content):
            if '<tspan x="840" y= "90" class="valueColor">' in line:
                svg_content[i] = f'<tspan x="840" y= "90" class="valueColor">({years_rounded}y)</tspan>\n'
                break

        with open(file_path, 'w') as file:
            file.writelines(svg_content)



def update_github_stats():
    url = 'https://api.github.com/users/pyoneerc'
    file_paths = ['dark_mode.svg', 'light_mode.svg']
    response = requests.get(url)
    data = response.json()

    public_repos = data['public_repos']
    followers = data['followers']

    repos_url = data['repos_url']
    repos_response = requests.get(repos_url)
    repos_data = repos_response.json()

    stars = sum(repo['stargazers_count'] for repo in repos_data)

    url = 'https://github-readme-stats.vercel.app/api?username=pyoneerc&include_all_commits=true'
    response = requests.get(url)
    svg_content = ElementTree.fromstring(response.content)

    commits_element = svg_content.find('.//{http://www.w3.org/2000/svg}text[@data-testid="commits"]')
    contributed_element = svg_content.find('.//{http://www.w3.org/2000/svg}text[@data-testid="contribs"]')
    prs_element = svg_content.find('.//{http://www.w3.org/2000/svg}text[@data-testid="prs"]')

    url = 'https://github-readme-stats.vercel.app/api?username=pyoneerc&show=prs_merged,prs_merged_percentage'
    response = requests.get(url)
    svg_content = ElementTree.fromstring(response.content)

    prs_merged_element = svg_content.find('.//{http://www.w3.org/2000/svg}text[@data-testid="prs_merged"]')
    prs_merged_percentage_element = svg_content.find('.//{http://www.w3.org/2000/svg}text[@data-testid="prs_merged_percentage"]')

    prs_merged_percentage = prs_merged_percentage_element.text[0:2]
    prs_merged_percentage += '%'

    for file_path in file_paths:
        with open(file_path, 'r') as file:
            svg_content = file.readlines()

        for i, line in enumerate(svg_content):
            if '<tspan x="370" y="490" class="keyColor">Repos</tspan>' in line:
                svg_content[
                    i] = f'<tspan x="370" y="490" class="keyColor">Repos</tspan>: <tspan class="valueColor">{public_repos}</tspan>\n'
                break

        for i, line in enumerate(svg_content):
            if '<tspan x="520" y="510" class="keyColor">|   Stars</tspan>' in line:
                svg_content[
                    i] = f'<tspan x="520" y="510" class="keyColor">|   Stars</tspan>: <tspan class="valueColor">{stars}</tspan>\n'
                break

        for i, line in enumerate(svg_content):
            if '<tspan x="370" y="510" class="keyColor">Followers</tspan>' in line:
                svg_content[
                    i] = f'<tspan x="370" y="510" class="keyColor">Followers</tspan>: <tspan class="valueColor">{followers}</tspan>\n'
                break

        for i, line in enumerate(svg_content):
            if '<tspan x="480" y="490" class="keyColor">Contributed</tspan>' in line:
                svg_content[
                    i] = f'<tspan x="480" y="490" class="keyColor">Contributed</tspan>: <tspan class="valueColor">{contributed_element.text}</tspan>\n'
                break

        for i, line in enumerate(svg_content):
            if '<tspan x="660" y="510" class="keyColor">|   Commits</tspan>' in line:
                svg_content[
                    i] = f'<tspan x="660" y="510" class="keyColor">|   Commits</tspan>: <tspan class="valueColor">{commits_element.text}</tspan>\n'
                break

        for i, line in enumerate(svg_content):
            if '<tspan x="660" y="490" class="keyColor">|   Merged PRs</tspan>' in line:
                svg_content[
                    i] = f'<tspan x="660" y="490" class="keyColor">|   Merged PRs</tspan>: <tspan class="valueColor">{prs_merged_element.text} ({prs_merged_percentage})</tspan>\n'
                break

        with open(file_path, 'w') as file:
            file.writelines(svg_content)


def main():
    update_uptime()
    update_github_stats()


if __name__ == '__main__':
    main()
