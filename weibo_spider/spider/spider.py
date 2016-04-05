#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import re
import requests
import logging
import random
import urllib
import time
import urlparse
from db.db_engine import Account
from db.db_engine import AccountDAO
from parser import Parser


class Spider(object):

    def __init__(self, account):
        assert isinstance(account, Account)
        self.account = account
        self.s = requests.session()
        self.set_session_cookie(session=self.s,
                                cookies=account.cookies)
        self.s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64) '\
            'AppleWebKit/537.36 \(KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36'
        self.referer = ''
        self.parser = Parser()

    def __del__(self):
        self.save_cookies()
        logging.info('Destory spider {email}.'.format(email=self.account.email))

    def __repr__(self):
        return "<Spider: %s>" % self.account.email

    @classmethod
    def set_session_cookie(cls, session, cookies):
        cookies = json.loads(cookies)
        for cookie in cookies:
            # domain expiry httpOnly name path secure
            session.cookies.set(
                name=cookie['name'],
                value=cookie['value'],
                path=cookie['path'],
                domain=cookie['domain'],
                expires=cookie.get('expires') or cookie.get('expiry')
            )

    @classmethod
    def get_session_cookies(cls, session):
        cookies = []
        for cookie in session.cookies:
            cookies.append(dict(
                name=cookie.name,
                value=cookie.value,
                path=cookie.path,
                domain=cookie.domain,
                expires=cookie.expires
            ))
        return cookies

    def save_cookies(slef):
        slef.account.cookies = json.dumps(slef.get_session_cookies(slef.s))
        AccountDAO.commit()

    @classmethod
    def check_avail(cls, resp):
        return True

    @classmethod
    def check_redirect(cls, resp):
        if resp.status_code in [301, 302]:
            return resp.headers['Location'], str(resp.status_code)
        groups = re.search(r'<meta\shttp-equiv=\"refresh"\s*content=\"0;\s*url=&#39;(?P<url>.*?)&#39;\"\/>', resp.text)
        if groups:
            return groups.group('url'), 'meta-refreash'
        return None, None

    @classmethod
    def check_relogin(cls, resp):
        """
        检查是否是重新登陆页面
        """

        cond1 = re.search(r'<title>Sina Visitor System</title>', resp.text)
        cond2 = re.search(r'var restore_back = function \(response\)', resp.text)
        return cond1 is not None and cond2 is not None

    def relogin(self, former_resp):
        """
        处理长时间未登录后登陆的流程
        """
        def encodeURIComponent(s):
            return urllib.quote(str(s))

        url = 'https://passport.weibo.com/visitor/visitor?a=restore&cb=restore_back&from=weibo&_rand='
        url += '%.16f' % random.random()
        logging.info('restore1 new_url: {url}'.format(url=url))
        resp = self.s.get(url=url, headers={
            'Referer': former_resp.url
        })
        if resp.status_code != 200:
            logging.info('restore failed! status_code != 200')
            return False
        try:
            groups = re.search(r'restore_back\((?P<json>.*?)\);', resp.text)
            json_resp = json.loads(groups.group('json'))
            assert(json_resp['retcode'] == 20000000)
            assert(json_resp['data'])
        except Exception:
            logging.exception('restore failed!')
            logging.info(resp.text)
            return False
        alt = json_resp['data']['alt']
        if alt != '':
            savestate = json_resp['data']['savestate']
            requrl = "&url=" + encodeURIComponent(r'http://weibo.com/?retcode=6102')
            params = "entry=sso&alt=" + encodeURIComponent(alt)
            params += "&returntype=META" + "&gateway=1&savestate=" + encodeURIComponent(savestate) + requrl
            url = r'http://login.sina.com.cn/sso/login.php?' + params
        else:  # cross_domain
            return False
            logging.info('cross_domain')
            url = "http://login.sina.com.cn/visitor/visitor?a=crossdomain&cb=return_back&s="
            url += encodeURIComponent(json_resp["data"]["sub"])
            url += "&sp=" + encodeURIComponent(json_resp["data"]["subp"])
            url += "&from=" + "weibo" + "&_rand=" + '%.16f' % random.random()

        logging.info('restore2 new_url: {url}'.format(url=url))
        resp = self.s.get(url, headers={'Referer': resp.url})
        try:
            groups = re.search(r'location.replace\(\'(?P<url>.*?)\'\);', resp.text)
            url = groups.group('url')
            assert(url)
        except Exception:
            logging.exception('restore failed!')
            logging.info(resp.text)

        logging.info('restore3 new_url: {url}'.format(url=url))
        resp = self.s.get(url, headers={'Referer': resp.url})
        return resp

    def fetch(self, url, referer=None):
        """
        抓取一个页面，处理各种需要的跳转和重登录
        """
        if referer is None:
            referer = self.referer
        resp = self.s.get(url=url, headers={'Referer': referer})
        while True:
            new_url, reason = self.check_redirect(resp)
            if new_url:  # redierct
                logging.info("Fetching encounter redirect:\nreason:{reason}\ntarget:{target}\n".format(
                    reason=reason, target=new_url))
                resp = self.s.get(url=new_url)
                continue
            if self.check_relogin(resp):
                logging.info("Fetching encounter relogin:\n")
                resp = self.relogin(resp)
                if not resp:
                    logging.info('Fetch: elogin Failed')
                resp = self.s.get(url=url, headers={'Referer': referer})
                continue
            break
        self.referer = resp.url
        return resp

    def fetch_weibo(self, user_id, weibo_id):
        pass

    def fetch_search(self, keyword, page=1):
        quote_keyword = urllib.quote(urllib.quote(keyword))  # quote 两次
        if page == 1:
            url = 'http://s.weibo.com/weibo/{quote}&nodup=1'.format(quote=quote_keyword)
            referer = 'http://s.weibo.com/weibo/{quote}?topnav=1&wvr=6'.format(quote=quote_keyword)
        else:
            url = 'http://s.weibo.com/weibo/{quote}&nodup=1&page={page}'.format(quote=quote_keyword, page=page)
            referer = 'http://s.weibo.com/weibo/{quote}&nodup=1&page={page}'.format(quote=quote_keyword, page=page - 1)
        resp = self.fetch(url=url, referer=referer)
        weibos = []
        for embed_html in self.parser.embed_html_iter(resp.text):
            weibos += self.parser.parse_search_result(embed_html)
        return weibos

    def fetch_topic(self, keyword):
        if isinstance(keyword, unicode):
            keyword = keyword.encode('utf-8')
        weibos = []
        url = 'http://huati.weibo.com/k/{quote}?from=501'.format(quote=urllib.quote(keyword))
        resp = self.fetch(url=url)

        # extract params
        domain = re.search(r'\$CONFIG\[\'domain\'\]=\'(\d+)\';', resp.text).group(1)
        page_id = re.search(r'\$CONFIG\[\'page_id\'\]=\'(\w+)\';', resp.text).group(1)
        referer = resp.url
        main_url_parsed = urlparse.urlparse(str(resp.url))
        params_main = urlparse.parse_qs(main_url_parsed.query)
        params_main['script_uri'] = main_url_parsed.path
        _weibos, lazyload = self.parser.parse_topic_result(resp.text)
        weibos += _weibos
        # fetch next (Ajax)
        url = 'http://weibo.com/p/aj/v6/mblog/mbloglist'
        params = {
            'ajwvr': 6,
            'domain': domain,
            'id': page_id,
            'pl_name': 'Pl_Third_App__9',
            'pagebar': 0,
            'domain_op': domain,
            '__rnd': int(time.time() * 1000),
            'feed_type': 1
        }
        params.update(params_main)
        params.update(lazyload['action-data'])
        params['page'] = params.get('page', 1)
        params['pre_page'] = params.get('pre_page', params['page'])
        resp = self.s.get(url=url, params=params, headers={
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': referer
        })
        return resp

    @classmethod
    def save_to_file(cls, resp, filename):
        with open(filename, 'w') as file:
            file.write(resp.content)


def get_random_spider():
    account = AccountDAO.get_random_account()
    spider = Spider(account=account)
    return spider
