from sys import platform
import urllib.request as url
import socket
import re


def gethostname():
    if 'win' in platform:
        hostname = socket.gethostname()
    elif 'linux' in platform:
        hostname = socket.gethostname() + '.local'
    return hostname


def getaddrclientint():
    addrlist = socket.gethostbyname_ex(gethostname())[2]
    for a in addrlist:
        print('%d. %s' % (addrlist.index(a)+1, a))
    index = input('Enter number ip-address: ')
    try:
        index = int(index)
    except ValueError:
        print('Func addrclient.getaddrclient error')
        return
    else:
        if index < 1:
            index = 1
        elif index > len(addrlist):
            index = len(addrlist)
        return addrlist[index-1]


def getaddrclientext():
    site = url.urlopen('http://myip.ru/').read()
    grab = re.findall('\d{2,3}.\d{2,3}.\d{2,3}.\d{2,3}', site.decode())
    return grab[0]


def getaddrserver(hostname):
    try:
        addr = socket.gethostbyname(hostname)
    except socket.gaierror:
        print('func addrserv.getaddrserv error')
        return
    else:
        return addr