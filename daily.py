from datetime import date

import requests
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup


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


def scrape_repos():
    url = 'https://github.com/pyoneerC'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    repos = soup.find_all('span', class_='Counter')

    file_path = 'dark_mode.svg'
    with open(file_path, 'r') as file:
        svg_content = file.readlines()

        for i, line in enumerate(svg_content):
            if 'Repos' in line:
                svg_content[i] = f'<tspan x="370" y="110" class="keyColor">Repos</tspan>: <tspan class="valueColor">{repos[0].text}</tspan>\n'
                break


def main():
    update_uptime()
    scrape_repos()

if __name__ == '__main__':
    main()
