#!/usr/bin/env python3

from urllib.request import *
import re
import os
import time
import logging
import configparser
import extensions


_config_file_name = 'conf.ini'

id_retry_timeout = 600

TRY_MAX_COUNT = 4

ACCEPTED_HEADERS = {
    'Content-Type',
    'Referer',
    'X-Requested-With',
    'Host',
    'Origin',
    'DNT',
    'User-Agent',
    'Accept',
    'Cookie'
}


class AlreadyVoted(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return '{}: {}'.format(self.__class__.__name__, self.message)

    __repr__ = __str__


def get_base_page(page, try_max_count=TRY_MAX_COUNT):

    for i in range(try_max_count):
        content = urlopen(page).read().decode()
        if content:
            return content
    else:
        raise IOError(
            'Base page could not be retrieved within the specified {} tries'.format(
            try_max_count)
        )



def get_unique_id(id_url, id_regex):
    page = get_base_page(id_url)
    match = id_regex.search(page)

    if match is not None:
        return match.group(1)
    else:
        raise AlreadyVoted('Unique Id could not be fetched')



def make_request(
    base_url,
    number,
    encoding='utf-8',
    method='get',
    headers=None,
    data=None
):

    url = base_url.format(number=number)
    data = str(data).encode(encoding) if data is not None else None
    logging.debug(headers)

    r = Request(
        url,
        data=data,
        method=method,
        headers={} if headers is None else headers
    )

    logging.debug(r.method)
    logging.debug(data)

    return urlopen(r)


def get_count(count_url, vote_count_regex):
    document = get_base_page(count_url)

    return re_get_count_from_document(vote_count_regex, document)



def re_get_count_from_document(vote_count_regex, document):
    return int(vote_count_regex.search(document).group(1))


def test(conf):
    teststring = """
<div class="number-of-votes">Votes:
    <div class="number"> 3343</div>
</div>
"""
    vote_count_regex = re.compile(conf['vote_count_regex'])
    match = vote_count_regex.search(teststring)

    if match is not None:
        print(match.groups())
    else:
        print('match failed')


def test_get_count(config):
    url = config['count_url']
    vote_count_regex = re.compile(config['vote_count_regex'])
    print(get_count(url, vote_count_regex))


def do_vote(base_url, unique_id, count_url, vote_count_regex, encoding, method, headers, data):

    count_before = get_count(count_url, vote_count_regex)

    r = make_request(base_url, unique_id, method=method, headers=headers, data=data, encoding=encoding)
    document = r.read().decode()

    success = bool(document)

    # logging.debug(document)

    count_after = get_count(count_url, vote_count_regex)

    return success, count_before, count_after


def handle_extension(extension_names, values):
    for extension in extension_names:
        try:
            func = getattr(extensions, extension)
            requires = {a:values[a] for a in getattr(func, 'requires', ())}

            producing = getattr(func, 'produces', ())

            produced = func(*requires)

            if len(producing) == 0:
                pass
            elif len(producing) == 1:
                if isinstance(produced, (tuple, list)) and len(produced) == 1:
                    produced = produced[0]
                values[producing[0]] = produced
            elif len(produced) != len(producing):
                raise ValueError('Wrong number of values created')
            else:
                values.update(zip(producing, produced))

        except NameError:
            raise
        except Exception as e:
            logging.error(e)
    return values


def report_vote_result(success, count_before, count_after):
    print(
        'vote probably successful, new count: {}'.format(count_after)
        if success and count_before < count_after
        else 'vote probably failed, count: {}'.format(count_before)
    )
    logging.debug(
        'before: {}, after {}'.format(count_before, count_after)
    )


def vote_generator(config):

    vote_count_regex = re.compile(config['vote_count_regex'], flags=re.DOTALL)
    id_regex = re.compile(config['id_regex'])
    id_url = config['id_url']

    method = config['request_method']
    headers = {a:config[a] for a in ACCEPTED_HEADERS if a in config}

    extension_names = config['extensions'].replace(' ', '').split(';')

    changable = handle_extension(extension_names, {
        'base_url': config['base_url'],
        'count_url': config['count_url'],
        'headers': headers,
        'method': method,
        'data': config.get('request_data', None) if method.lower() == 'post' else None,
        'cookies': headers.get('Cookie', '')
    })

    base_url = changable['base_url']
    count_url = changable['count_url']
    headers = changable['headers']
    method = changable['method']
    data = changable['data']

    if changable['cookies']:
        headers['Cookie'] = changable['cookies']

    encoding = config.get('Encoding', 'utf-8')

    while True:
        try:
            unique_id = get_unique_id(id_url, id_regex)
            yield do_vote(
                base_url, unique_id, count_url, vote_count_regex,
                method=method,
                headers=headers,
                data=data,
                encoding=encoding
            )
        except AlreadyVoted as e:
            logging.info(
                'Id retrieval failed with error {}, '
                'waiting {} for retry'.format(
                    e,
                    '{} seconds'.format(id_retry_timeout)
                    if id_retry_timeout < 60
                    else '{} minutes'.format(id_retry_timeout / 60.0)
                )
            )
            time.sleep(id_retry_timeout)


def vote_once(config):
    success, count_before, count_after = next(vote_generator(config))
    report_vote_result(success, count_before, count_after)


def watch_and_vote(config):
    gen = vote_generator(config)
    while True:
        try:
            success, count_before, count_after = next(gen)
            report_vote_result(success, count_before, count_after)
        except KeyboardInterrupt:
            raise
        except StopIteration as e:
            logging.critical(
                'Iterator stopped unexpectedly: {}'.format(e)
            )
            raise
        except Exception as e:
            logging.error(repr(e))
        time.sleep(float(config['vote_interval']))


def parse_args():
    import argparse
    import sys


    parser = argparse.ArgumentParser()

    parser.add_argument(
        'action', nargs=1
    )
    parser.add_argument(
        'target', nargs='?', default=None
    )
    parser.add_argument(
        '--logfile', type=str, default=None
    )

    return parser.parse_args(sys.argv[1:])


def get_config(target='DEFAULT'):

    if target == None:
        target = 'DEFAULT'

    _config = configparser.ConfigParser()
    _config.read(_config_file_name)
    return _config[target]



def main():

    args = parse_args()

    action = args.action[0]

    config = get_config(args.target)


    if args.logfile:
        print(args.logfile)
        logging.basicConfig(
            level=logging.DEBUG,
            filename=args.logfile
        )
    else:
        logging.basicConfig(
            level=logging.DEBUG
        )

    if action == 'vote':
        vote_once(config)
    elif action == 'watch':
        watch_and_vote(config)
    elif action == 'test':
        test(config)
    elif action == 'test_get_count':
        test_get_count(config)


if __name__ == '__main__':
    main()
else:
    logging.basicConfig(
        level=logging.DEBUG
    )
