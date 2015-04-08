#!/usr/bin/env python3

from urllib.request import *
import re
import os
import binascii
import time
import logging


logging.basicConfig(
    level=logging.DEBUG
)

BASE_URL = 'http://www.89.0rtl.de/vote/node/23959/1/vote/alternate/{number}'

COUNT_URL = 'http://www.89.0rtl.de/voting/schule/wilhelm-von-humboldt-gymnasium'

VOTE_COUNT_REGEX = re.compile('class="number-of-votes".*?class="number"> (\d+?)</div>', flags=re.DOTALL)

ID_REGEX = re.compile('"/vote/node/23959/1/vote/alternate/(\w*?)"')

TIMEOUT = 60 * 61

TRY_MAX_COUNT = 4

reference_random_string = '9aedac4c64bf5bf3535ad2f09ec93f9a'

random_bits_length = len(reference_random_string) * 4


class AlreadyVoted(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return '{}: {}'.format(self.__class__.__name__, self.message)

    __repr__ = __str__


def get_base_page():
    for i in range(TRY_MAX_COUNT):
        content = urlopen(COUNT_URL).read().decode()
        if content:
            return content
    else:
        raise IOError(
            'Base page could not be retrieved within the specified {} tries'.format(
            TRY_MAX_COUNT)
        )



def get_unique_id():
    page = get_base_page()
    match = ID_REGEX.search(page)
    if match is not None:
        return match.group(1)
    else:
        raise AlreadyVoted('Unique Id could not be fetched')



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

    r = make_request(unique_id)
    document = r.read().decode()
    if document:
        logging.debug('Vote yielded a response:\n{}'.format(document))



def test_one_vote(unique_id=None):
    if unique_id == None:
        try:
            unique_id = get_unique_id()
        except AlreadyVoted as e:
            logging.info(repr(e))
            return 'undefined', 'undefined'
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
    print(
        'vote successful,'
        if before < after else 'vote failed, count: {}'.format(before)
    )
    logging.debug(
        'before: {}, after {}'.format(before, after)
    )


def watch_and_vote():
    while True:
        try:
            vote_once()
        except Exception as e:
            logging.error(repr(e))
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
