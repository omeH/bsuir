#!/usr/bin/env python3.4

import os
import sys
import socket

from getaddr import getaddrserver
from manftp import doc

MAX_IBUF = 512
MAX_DBUF = 1024*5
PORT_IFTP = 21
PORT_DFTP = 20

DATA_PORT = 9090

# sock_inc = -1
# sock_data = -1


def readserv(sock, buf=MAX_IBUF):
    return sock.recv(buf).decode()[:-2]


def com(*command):
    full_name = os.path.join(*command[-2:])
    return '{0} {1}\r\n'.format(command[0], full_name)


def connectftp(addrftp):
    sock_new = socket.socket()
    if not sock_new:
        print('Error: socket not established')
        return

    try:
        sock_new.connect((addrftp, PORT_IFTP))
    except socket.error:
        print('Error: not connect to FTP-server: %s' % addrftp)
        sock_new.close()
        return
    else:
        buf = readserv(sock_new)

    if '220' in buf:
        print(buf)
        return sock_new
    else:
        sock_new.close()
        return


def account(sock):

    login = 'USER %s\r\n' % input('Enter login: ')
    sock.send(login.encode())
    buf = readserv(sock)
    if not ('331' in buf):
        print('Error: incorrect login')
        return

    password = 'PASS %s\r\n' % input('Enter password: ')
    sock.send(password.encode())
    buf = readserv(sock)
    if not ('230' in buf):
        print('Error: incorrect password')
        return
    print('Authentication is successful')

    return True


def syst(sock):
    buf = 'SYST\r\n'
    sock.send(buf.encode())
    buf = readserv(sock)
    if not ('215' in buf):
        print('Error: func syst')
    else:
        print(buf)


def typeftp(sock):
    buf = 'TYPE I\r\n'
    sock.send(buf.encode())
    buf = readserv(sock)
    if not ('200' in buf):
        print('Error: func type')
    else:
        print(buf)


def activemode(sock_inc):
    sock_new = socket.socket()
    if not sock_new:
        print('Error: socket not established')
        return

    addrs = sock_inc.getsockname()[0]
    addr = addrs.split('.')
    global DATA_PORT
    DATA_PORT += 1
    port = (DATA_PORT // 256, DATA_PORT % 256)

    try:
        sock_new.bind((addrs, DATA_PORT))
    except socket.error:
        sock_new.close()
        print('Error: func activemode -> bind')
        return

    buf = 'PORT {0},{1},{2},{3},'.format(*addr) + '{0},{1}\r\n'.format(*port)
    DATA_PORT += 1

    try:
        sock_new.listen(1)
    except socket.error:
        sock_new.close()
        print('Error: func activemode -> listen')
        return

    sock_inc.send(buf.encode())
    buf = readserv(sock_inc)
    if not ('200' in buf):
        sock_new.close()
        print('Error: could not ustanovil active connection to the server')
        return

    return sock_new


def listdata(sock_inc):
    typeftp(sock_inc)

    sock_new = activemode(sock_inc)
    if sock_new:
        buf = 'LIST -l\r\n'
        sock_inc.send(buf.encode())
        buf = readserv(sock_inc)
        if not ('150' in buf):
            sock_new.close()
            print('Error: list of files and directories are not obtained')
            return

    sock_data, addr = sock_new.accept()
    sock_new.close()

    listdir = ''
    while True:
        data = readserv(sock_data, MAX_DBUF)
        if not data:
            break
        listdir += data

    if not len(listdir):
        print('>> This directory is empty <<')
    else:
        print(listdir)

    buf = readserv(sock_inc)
    if not ('226' in buf):
        sock_data.close()
        return
    sock_data.close()


def pwd(sock):
    buf = 'PWD\r\n'
    sock.send(buf.encode())
    buf = readserv(sock)
    if not ('257' in buf):
        print('Error: func pwd')
        return
    else:
        return buf.split(' ')[1].strip('"')


def cwd(sock, directory):
    buf = 'CWD %s\r\n' % directory
    sock.send(buf.encode())
    buf = readserv(sock)
    if not ('250' in buf):
        print('Error: func cwd')


def mkd(sock, directory):
    buf = 'MKD %s\r\n' % directory
    sock.send(buf.encode())
    buf = readserv(sock)
    if not ('257' in buf):
        print('Error: func mkd')


def rmd(sock, directory):
    buf = 'RMD %s\r\n' % directory
    sock.send(buf.encode())
    buf = readserv(sock)
    if not ('250' in buf):
        print('Error: func rmd')


def delet(sock, file_):
    directory = pwd(sock)
    buf = com('CWD', directory, file_)

    sock.send(buf.encode())
    buf = readserv(sock)
    if not ('550' in buf):
        print('Error: func delete -> cwd <-')
        return

    buf = com('DELE', directory, file_)

    sock.send(buf.encode())
    buf = readserv(sock)
    if not ('250' in buf):
        print('Error: func delete -> delete <-')


def restfile(sock, r):
    rest = int(r)
    if rest < 0:
        print('Error: offset is invalid')
        return

    buf = 'REST %s\r\n' % rest
    sock.send(buf.encode())
    buf = readserv(sock)
    if not ('350' in buf):
        print('Error: func restfile -> rest <-')
        return
    return rest


def getfile(sock_inc, file_, rest=0, mod='wb'):
    directory = pwd(sock_inc)
    buf = com('CWD', directory, file_)

    sock_inc.send(buf.encode())
    buf = readserv(sock_inc)
    if not ('550' in buf):
        print('Error: func delete -> cwd <-')
        return

    typeftp(sock_inc)
    sock_new = activemode(sock_inc)
    if sock_new:
        buf = com('RETR', directory, file_)
        sock_inc.send(buf.encode())
        buf = readserv(sock_inc)
        if not ('150' in buf):
            sock_new.close()
            print('Error: file %s not found' % file_)
            listdata(sock_inc)
            return

    size = int(buf.split(' ')[-2].strip('('))
    if rest > size:
        sock_new.close()
        print('Error: offset indicates the point resume large file size')
        buf = readserv(sock_inc)
        return

    sock_data, addr = sock_new.accept()
    sock_new.close()
    f = open(file_, mod)
    if not f:
        return

    while True:
        data = sock_data.recv(MAX_DBUF)
        if not data:
            break
        f.write(data)
    f.close()

    buf = readserv(sock_inc)
    if not ('226' in buf):
        sock_data.close()
        print('Error: file %s is not transferred' % file_)
        return

    sock_data.close()


def putfile(sock_inc, file_):
    directory = pwd(sock_inc)

    typeftp(sock_inc)
    sock_new = activemode(sock_inc)
    if sock_new:
        buf = com('STOR', directory, file_)
        sock_inc.send(buf.encode())
        buf = readserv(sock_inc)
        if not ('150' in buf):
            print('Error: refusal to transfer')
            sock_new.close()
            return

    sock_data, addr = sock_new.accept()
    sock_new.close()

    try:
        f = open(file_, 'rb')
    except IOError:
        print('Error: file %s not found' % file_)
        sock_data.close()
        buf = readserv(sock_inc)
        return

    while True:
        data = f.read(MAX_DBUF)
        if not data:
            break
        sock_data.send(data)
    f.close()
    sock_data.close()

    buf = readserv(sock_inc)
    if not ('226' in buf):
        print('Error: file not transfer')
        return

    if not ('win' in sys.platform):
        buf = com('SITE CHMOD 644', directory, file_)
        sock_inc.send(buf.encode())
        buf = readserv(sock_inc)
        print(buf)


def quitftp(sock):
    buf = 'QUIT\r\n'
    sock.send(buf.encode())
    print(readserv(sock))
    sock.close()


def cmdformat(lenargs, errlen):
    if lenargs > errlen:
        print('Error: command format is not valid')


def cmdcwd(args):
    cmdformat(args['len'], 2)
    sock = args['sock']
    directory = args['data']
    cwd(sock, directory)


def cmdmkd(args):
    cmdformat(args['len'], 2)
    sock = args['sock']
    directory = args['data']
    mkd(sock, directory)


def cmdrmd(args):
    cmdformat(args['len'], 2)
    sock = args['sock']
    directory = args['data']
    rmd(sock, directory)


def cmddelet(args):
    cmdformat(args['len'], 2)
    sock = args['sock']
    filename = args['data']
    delet(sock, filename)


def cmdget(args):
    sock = args['sock']
    filename = args['data']
    if args['cmd'] == 'retr':
        cmdformat(args['len'], 2)
        getfile(sock, filename)
    else:
        cmdformat(args['len'], 3)
        count = args['count']
        getfile(sock, filename, restfile(sock, count), 'wb+')


def cmdput(args):
    cmdformat(args['len'], 2)
    sock = args['sock']
    filename = args['data']
    putfile(sock, filename)


def cmdpwd(args):
    cmdformat(args['len'], 1)
    sock = args['sock']
    print(pwd(sock))


def cmdhelp(args):
    cmdformat(args['len'], 1)
    print(doc)


def cmdlist(args):
    cmdformat(args['len'], 1)
    sock = args['sock']
    listdata(sock)


def cmdquit(args):
    cmdformat(args['len'], 1)
    sock = args['sock']
    quitftp(sock)


def workcycle(sock):
    commandlist = {
        'list': cmdlist,
        'pwd':  cmdpwd,
        'cwd':  cmdcwd,
        'mkd':  cmdmkd,
        'dele': cmddelet,
        'rmd':  cmdrmd,
        'rest': cmdget,
        'retr': cmdget,
        'stor': cmdput,
        'help': cmdhelp,
        'quit': cmdquit
    }
    data = {'sock': sock}
    while not ('closed' in sock.__repr__()):
        cmd = input('> ftp# ').split(' ')
        data['cmd'] = cmd[0]
        data['len'] = len(cmd)
        if len(cmd) == 2:
            data['data'] = cmd[1]
        elif len(cmd) == 3:
            data['data'] = cmd[1]
            data['count'] = cmd[2]

        try:
            commandlist[cmd[0]](data)
        except KeyError:
            print("Error: name '%s' is not defined" % cmd[0])


def main():
    print('Mini FTP-client.')
    # Get ip-address FTP-server
    addrserver = input('Enter ip-address FTP-server: ')
    addrserver = getaddrserver(addrserver)
    if not addrserver:
        print('Error: not get ip-address FTP-server')
        return
    # Connect with FTP-server
    sock_inc = connectftp(addrserver)
    if sock_inc:
        print('Connect with FTP-server -> %s <- good' % addrserver)
    else:
        print('Connect with FTP-server -> %s <- failure' % addrserver)
        return
    # Login to account
    acc = account(sock_inc)
    if not acc:
        sock_inc.close()
        return
    # Get info with FTP-server
    syst(sock_inc)
    listdata(sock_inc)
    #
    workcycle(sock_inc)


if __name__ == '__main__':
    main()
