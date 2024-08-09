from datetime import date

import requests
from dateutil.relativedelta import relativedelta


def update_uptime():
    file_path = 'dark_mode.svg'
    start_date = date(2005, 3, 3)
    current_date = date.today()

    difference = relativedelta(current_date, start_date)
    years = difference.years
    months = difference.months
    days = difference.days

    with open(file_path, 'r') as file:
        svg_content = file.readlines()

        months_message = f'{months} mes' if months == 1 else 'meses'
        days_message = f'{days} día' if days == 1 else 'días'

    for i, line in enumerate(svg_content):
        if 'Uptime' in line:
            svg_content[
                i] = f'<tspan x="370" y="90" class="keyColor">Uptime</tspan>: <tspan class="valueColor">{years} años, {months} {months_message}, {days} {days_message}</tspan>\n'
            break

    with open(file_path, 'w') as file:
        file.writelines(svg_content)


def get_github_stats():
    url = 'https://api.github.com/users/pyoneerc'
    file_path = 'dark_mode.svg'
    response = requests.get(url)
    data = response.json()

    public_repos = data['public_repos']
    followers = data['followers']

    repos_url = data['repos_url']
    repos_response = requests.get(repos_url)
    repos_data = repos_response.json()

    stars = sum(repo['stargazers_count'] for repo in repos_data)

    with open(file_path, 'r') as file:
        svg_content = file.readlines()

        for i, line in enumerate(svg_content):
            if 'Repos' in line:
                svg_content[
                    i] = f'<tspan x="370" y="490" class="keyColor">Repos</tspan>: <tspan class="valueColor">{public_repos}</tspan>\n'
                break

        for i, line in enumerate(svg_content):
            if 'Followers' in line:
                svg_content[
                    i] = f'<tspan x="370" y="510" class="keyColor">Followers</tspan>: <tspan class="valueColor">{followers}</tspan>\n'
                break

        for i, line in enumerate(svg_content):
            if 'Stars' in line:
                svg_content[
                    i] = f'<tspan class="keyColor">Stars</tspan>: <tspan class="valueColor">{stars}</tspan>\n'
                break

    with open(file_path, 'w') as file:
        file.writelines(svg_content)

def main():
    update_uptime()
    get_github_stats()


if __name__ == '__main__':
    main()
