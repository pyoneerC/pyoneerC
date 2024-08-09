from datetime import date
from dateutil.relativedelta import relativedelta


def update_svg():
    file_path = 'dark_mode.svg'
    start_date = date(2005, 3, 3)
    current_date = date.today()

    difference = relativedelta(current_date, start_date)
    years = difference.years
    months = difference.months
    days = difference.days

    with open(file_path, 'r') as file:
        svg_content = file.readlines()

    for i, line in enumerate(svg_content):
        if 'Uptime' in line:
            svg_content[
                i] = f'<tspan x="370" y="90" class="keyColor">Uptime</tspan>: <tspan class="valueColor">{years} años, {months} meses y {days} días</tspan>\n'
            break

    with open(file_path, 'w') as file:
        file.writelines(svg_content)


if __name__ == '__main__':
    update_svg()
