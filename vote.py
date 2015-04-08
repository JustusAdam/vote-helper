#!/usr/bin/env python3

from urllib.request import *
import re
import os
import binascii
import time


BASE_URL = 'http://www.89.0rtl.de/vote/node/23959/1/vote/alternate/{number}'

COUNT_URL = 'http://www.89.0rtl.de/voting/schule/wilhelm-von-humboldt-gymnasium'

VOTE_COUNT_REGEX = re.compile('class="number-of-votes".*?class="number"> (\d+?)</div>', flags=re.DOTALL)

ID_REGEX = re.compile('"/vote/node/23959/1/vote/alternate/(.*?)"')

TIMEOUT = 60 * 61

reference_random_string = '9aedac4c64bf5bf3535ad2f09ec93f9a'


random_bits_length = len(reference_random_string) * 4


def get_base_page():
    return urlopen(COUNT_URL).read().decode()


def get_unique_id():
    page = get_base_page()
    match = ID_REGEX.search(page)
    return match.group(1)


def make_request(number):

    url = BASE_URL.format(number=number)

    return urlopen(url)


def get_count():
    document = get_base_page()

    return re_get_count_from_document(document)



def re_get_count_from_document(document):
    return int(VOTE_COUNT_REGEX.search(document).group(1))


def test():
    teststring = """
<div class="number-of-votes">Votes:
    <div class="number"> 3343</div>
</div>
"""
    match = VOTE_COUNT_REGEX.search(teststring)
    if match is not None:
        print(match.groups())
    else:
        print('match failed')


def test_get_count():
    print(get_count())


def get_random_string():
    random_bits = os.urandom(random_bits_length)

    random_string = binascii.hexlify(random_bits).decode()

    return random_string


def do_vote(unique_id=None):
    if unique_id == None:
        unique_id = get_unique_id()
    make_request(unique_id)



def test_one_vote(unique_id=None):
    if unique_id == None:
        unique_id = get_unique_id()
    count_before = get_count()

    do_vote()

    count_after = get_count()

    return count_before, count_after


def test_votes_verification(tries):
    unique_id = get_unique_id()
    tries = int(tries)

    results = tuple(
        (i, test_one_vote(unique_id)) for i in range(tries)
    )

    for number, counts in results:
        before, after = counts
        print('{}: before {}, after {}, difference {}'.format(
            number, before, after, after - before
        ))


def vote_once():
    before, after = test_one_vote()
    print('vote successful' if before < after else 'vote failed')


def watch_and_vote():
    while True:
        vote_once()
        time.sleep(TIMEOUT)


def main():
    import sys
    script, option, *args  = sys.argv

    if option == 'vote':
        vote_once()
    elif option == 'watch':
        watch_and_vote()
    elif option == 'test':
        test()
    elif option == 'test_get_count':
        test_get_count()
    elif option == 'test_vv':
        test_votes_verification(*args)


if __name__ == '__main__':
    main()
