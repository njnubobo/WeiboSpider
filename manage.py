#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import argparse
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'weibo_spider'))


def get_praser():
    parser = argparse.ArgumentParser(description='Sina Weibo Spider')
    subparsers = parser.add_subparsers(help='sub-command help', dest='subcommand')
    # login
    _login = subparsers.add_parser('login', help='Login service')
    _login.add_argument('-d', '--demon', help='Run as demon.', action='store_true')
    _login.add_argument('-i', '--import-account', help='Import accounts from file')
    _login.add_argument('-p', '--proxy', help='Use proxy')

    # shell
    subparsers.add_parser('shell', help='Shell service')

    # db
    _db = subparsers.add_parser('db', help='Shell service')
    _db.add_argument('--create-table', help='create-table', nargs='*')

    # spider
    _spider = subparsers.add_parser('spider', help='Spider')
    _spider.add_argument('-d', '--demon', help='run as demon', action='store_true')
    _spider.add_argument('--fake', help='run a fake spider', action='store_true')

    # scheduler
    _scheduler = subparsers.add_parser('scheduler', help='Scheduler')
    _scheduler.add_argument('-d', '--demon', help='run as demon', action='store_true')

    # datacollecter
    _datacollecter = subparsers.add_parser('datacollecter', help='DataCollecter')
    _datacollecter.add_argument('-d', '--demon', help='run as demon', action='store_true')

    # Web
    _web = subparsers.add_parser('web', help='Web')
    _web.add_argument('-d', '--demon', help='run as demon', action='store_true')
    return parser


def config_logger(name, level):
    logger = logging.getLogger(name)
    hdr = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(name)s:%(levelname)s: %(message)s')
    hdr.setFormatter(formatter)
    logger.addHandler(hdr)
    logger.setLevel(level)


def main():
    parser = get_praser()
    args = parser.parse_args()
    if args.subcommand == 'shell':
        logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                            format='[%(asctime)s] %(name)s:%(levelname)s: %(message)s')
        import IPython
        IPython.embed()
    elif args.subcommand == 'login':
        if args.demon:
            pass
        elif args.import_account:
            from login.manul_login import import_account_from_file
            import_account_from_file(filename=args.import_account)
        else:
            from login.manul_login import start_login
            if args.proxy:
                start_login(proxy=args.proxy)
            else:
                start_login()
    elif args.subcommand == 'db':
        if 'create_table' in args:
            from db.db_engine import DBEngine
            db_engine = DBEngine()
            db_engine.create_db()

    elif args.subcommand == 'spider':
        if args.demon:
            from spider.worker import SpiderWorker
            config_logger('SpiderWorker', logging.DEBUG)
            if args.fake:
                config_logger('FakeSpider', logging.DEBUG)
                SpiderWorker(fake=True)
            else:
                config_logger('Spider', logging.DEBUG)
                SpiderWorker()
    elif args.subcommand == 'scheduler':
        if args.demon:
            from scheduler.scheduler import Scheduler
            from scheduler.datacollecter import DataCollecter
            config_logger('WordFollower', logging.DEBUG)
            config_logger('Scheduler', logging.INFO)
            config_logger('DataCollecter', logging.INFO)
            config_logger('DBEngine', logging.DEBUG)
            Scheduler()
            # pid = os.fork()
            # if pid == 0:
            #     DataCollecter()
            #     pass
            # else:
            #     Scheduler()
    elif args.subcommand == 'datacollecter':
        if args.demon:
            from scheduler.datacollecter import DataCollecter
            config_logger('DataCollecter', logging.INFO)
            DataCollecter()
    elif args.subcommand == 'web':
        if args.demon:
            from website import start_server
            config_logger('WordFollowUpdateHandler', logging.DEBUG)
            start_server()


if __name__ == '__main__':
    main()
