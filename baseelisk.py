from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from discord.errors import HTTPException
from multiprocessing import Pool
import os

command_prefix = '!'
description = 'Menacingly watches over players in TNNT.'
bot = commands.Bot(command_prefix, description=description)


def quit_driver(driver):
    driver.quit()

class AnyEc:
    """ Use with WebDriverWait to combine expected_conditions
        in an OR.
    """
    def __init__(self, *args):
        self.ecs = args
    def __call__(self, driver):
        for fn in self.ecs:
            try:
                res = fn(driver)
                if res:
                    return res
            except:
                pass

def connect_to_server(url):
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    driver = webdriver.Firefox(executable_path='./geckodriver',
                               options=firefox_options)
    driver.get(url)
    return driver


def get_watch_text_pages(driver, url):
    pages = []
    iframe = driver.find_element_by_xpath(
        '/html/body/div/div[3]/div/div[2]/p[2]/iframe')
    driver.switch_to.frame(iframe)
    iframe = driver.find_element_by_xpath('/html/body/div/div[2]/div/iframe')
    driver.switch_to.frame(iframe)
    wait_by_xpath_text(driver,
                       '/html/body/x-screen/div[1]/x-row[8]', '  c) Connect')
    ActionChains(driver).send_keys('c').perform()

    if url.endswith('us'):
        x_row_index = 9
    else:
        x_row_index = 11
    wait_by_xpath_text(driver,
                       '/html/body/x-screen/div[1]/x-row[' + str(
                           x_row_index) + ']',
                       '  w) Watch games in progress')
    ActionChains(driver).send_keys('w').perform()

    WebDriverWait(driver, 10).until( AnyEc(
        EC.text_to_be_present_in_element(
            (By.XPATH, '/html/body/x-screen/div[1]/x-row[4]'),
            ' The following games are in progress:'),
        EC.text_to_be_present_in_element(
            (By.XPATH, '/html/body/x-screen/div[1]/x-row[6]'),
            '    Sorry, no games available for viewing.')))

    wait_by_xpath_text(driver,
                       '/html/body/x-screen/div[1]/x-row[3]', '')
    x_screen = driver.find_element_by_xpath('/html/body/x-screen')
    #sleep(1)
    if 'Sorry, no games available for viewing.' in x_screen.text:
        return ['']
    else:
        # while there are pages
        screen_text = x_screen.text
        pages.append(screen_text)

        #TODO handle more pages than just one
        # while more_pages_present(screen_text):
        #     ActionChains(driver).send_keys('>').perform()
        #     x_screen = driver.find_element_by_xpath('/html/body/x-screen')
        #     screen_text = x_screen.text
        #     pages.append(screen_text)
        return pages


def switch_to_frame(driver, frame_x_path):
    iframe = driver.find_element_by_xpath(frame_x_path)
    driver.switch_to.frame(iframe)


def wait_by_xpath_text(driver, xpath, text):
    WebDriverWait(driver, 10).until(
        EC.text_to_be_present_in_element(
            (By.XPATH, xpath), text), message=text + ' not found')


def parse_watch_text(watch_page_list):
    op_str = ''
    for page_text in watch_page_list:
        for line in page_text.splitlines()[3:-2]:
            if 'tnnt' in line:
                split_line = line.split()
                op_str += '{} : {}\n'.format(split_line[1], split_line[-1])
    # TODO put in data structure?
    return op_str


def more_pages_present(page_text):
    count_line = page_text.splitlines()[-2]
    num_text, total_text = count_line.split('of')
    num_shown = int(num_text.split('-')[1])
    total_games = int(total_text)
    return num_shown < total_games


def get_out_put_from_url(url):
    driver = connect_to_server(url)
    pages = get_watch_text_pages(driver, url)
    quit_driver(driver)
    return parse_watch_text(pages)


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command(pass_context=True)
async def whereis(ctx):
    url_list = ['https://www.hardfought.org/nethack/hterm/hterm-us',
                'https://www.hardfought.org/nethack/hterm/hterm-eu',
                'https://www.hardfought.org/nethack/hterm/hterm-au']
    pool_of_three = Pool(3)
    out_list = pool_of_three.map(get_out_put_from_url, url_list)
    pool_of_three.close()
    pool_of_three.join()
    all_op = ''.join(out_list)

    #all_op = get_out_put_from_url(url_list[1])
    # print('all_op', all_op)
    # await ctx.send(all_op)

    if all_op == '':
        all_op = 'No games found'

    message_not_sent = True

    while message_not_sent:
        try:
            await ctx.send(all_op)
        except HTTPException:
            continue
        print('sent')
        message_not_sent = False


bot.run(os.environ['SECRET_KEY'])